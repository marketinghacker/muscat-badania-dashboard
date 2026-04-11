# City Intelligence Dashboard v5 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace dashboard v4.4 with City Intelligence Hub reading from Railway PostgreSQL (777K rows), 6 tabs, NOWY/STARY toggle, PDF/CSV export.

**Architecture:** Python script reads from Railway PostgreSQL → computes all metrics (CPA, brand barometer, capacity, correlations) → generates single static HTML with embedded JSON + Chart.js + interactive JS filters. Deploy to Vercel.

**Tech Stack:** Python 3.9+ (psycopg2, pandas, numpy), Chart.js 4.4.7, jsPDF, html2canvas, Vercel static hosting.

**Design doc:** `docs/plans/2026-04-11-city-intelligence-dashboard-v5-design.md`

---

## Task 1: Data Layer — Railway connector + city mapping

**Files:**
- Create: `muscat_v5_data.py` (in `/Users/marcinmichalski/Downloads/`)
- Reference: `etl/muscat_etl.py` (city mapping), `Sale_team_report(Arkusz1).csv` (metraż)

**Step 1: Create data loading module**

```python
# muscat_v5_data.py — loads all data from Railway PostgreSQL
import psycopg2, pandas as pd, numpy as np, json

RAILWAY_URL = "postgresql://postgres:bEKDQPLAdGSOmgbPdPOXFXWjdsLRRilq@mainline.proxy.rlwy.net:12657/railway"

CITY_MAP = {
    "ARK": {"city":"Warszawa","salon":"Arkadia","type":"CH","m2":82,"m2_sala":57},
    "WAW": {"city":"Warszawa","salon":"Chmielna","type":"FSS","m2":60,"m2_sala":40},
    "TRG": {"city":"Warszawa","salon":"Targowa","type":"FSS","m2":87,"m2_sala":70},
    "WA4": {"city":"Warszawa","salon":"Wola Park","type":"CH","m2":67,"m2_sala":40.1},
    "WA5": {"city":"Warszawa","salon":"Mokotów","type":"CH","m2":76,"m2_sala":46.5},
    "KRA": {"city":"Kraków","salon":"Starowiślna","type":"FSS","m2":70,"m2_sala":50},
    "KR2": {"city":"Kraków","salon":"Pawia","type":"FSS","m2":73,"m2_sala":50},
    "GA1": {"city":"Gdynia","salon":"Riviera","type":"CH","m2":92,"m2_sala":53.9},
    "GDA": {"city":"Gdańsk","salon":"Podwale","type":"FSS","m2":119,"m2_sala":60},
    "KAT": {"city":"Katowice","salon":"Silesia","type":"CH","m2":58,"m2_sala":36.4},
    "LDZ": {"city":"Łódź","salon":"Manufaktura","type":"CH","m2":66,"m2_sala":52},
    "LUB": {"city":"Lublin","salon":"Lublin","type":"FSS","m2":48,"m2_sala":30},
    "POZ": {"city":"Poznań","salon":"Posnania","type":"CH","m2":103,"m2_sala":78},
    "SZC": {"city":"Szczecin","salon":"Szczecin","type":"FSS","m2":74,"m2_sala":50},
    "WRO": {"city":"Wrocław","salon":"Wroclavia","type":"CH","m2":64,"m2_sala":34},
    "WR2": {"city":"Wrocław","salon":"Magnolia","type":"CH","m2":89.5,"m2_sala":50.4},
}

CITIES = ["Warszawa","Kraków","Trójmiasto","Wrocław","Łódź","Katowice","Poznań","Lublin","Szczecin"]
# Trójmiasto = Gdańsk GDA + Gdynia GA1

def load_all():
    """Load all tables from Railway, return dict of DataFrames."""
    conn = psycopg2.connect(RAILWAY_URL)
    tables = {}
    for t in ['events_monthly','sales_monthly','traffic_monthly','customers_city',
              'demographics_temporal','sales_demographics','product_trends',
              'geo_coverage','customers_raw','events_raw','sales_raw',
              'mcp_google_ads_monthly','mcp_google_ads_geo','mcp_meta_regional',
              'mcp_meta_demographics','mcp_gsc_daily','mcp_gsc_queries',
              'mcp_ahrefs_history']:
        tables[t] = pd.read_sql(f"SELECT * FROM {t}", conn)
        print(f"  {t}: {len(tables[t])} rows")
    conn.close()
    return tables
```

**Step 2: Test it loads**
```bash
python3 -c "from muscat_v5_data import load_all; d = load_all(); print(f'Loaded {sum(len(v) for v in d.values())} total rows')"
```
Expected: ~777K rows loaded.

**Step 3: Commit**
```bash
git add muscat_v5_data.py
git commit -m "feat: add Railway data loader for dashboard v5"
```

---

## Task 2: Compute Engine — all metrics per city

**Files:**
- Create: `muscat_v5_compute.py`

**Step 1: Build compute_city_data() function**

Computes for EACH city:
- Monthly bookings (NOWY/STARY split via JOIN events_raw↔customers_raw)
- Monthly revenue + AOV + premium share
- CPA_nowy = ad_spend / new_bookings
- Brand barometer = GSC "muscat+miasto" trend
- Fill rate = planned bookings / capacity
- Demographics: age/sex shift YoY
- Product mix: top models, construction, index breakdown
- GEO coverage: ZIP distribution, new ZIP appearance
- Revenue per m²

All metrics output as a single JSON-serializable dict.

Key queries to run on DataFrames:
```python
# NOWY/STARY split for bookings
events_with_type = events_raw.merge(
    customers_raw[['unique_id','customer_type']],
    left_on='client_id', right_on='unique_id', how='left'
)
events_with_type['is_new'] = events_with_type['customer_type'] == 'NOWY'

# CPA per city
city_spend = meta_regional + google_geo (mapped to city)
cpa_nowy = city_spend / new_bookings_per_city

# Brand barometer
brand_queries = gsc_queries[gsc_queries.query.str.contains('muscat')]
brand_per_city = {city: brand_queries[brand_queries.query.str.contains(city.lower())] for city}

# Premium share
premium = sales_raw[sales_raw.product_construction == 'Asfera'].groupby(city)
total_glasses = sales_raw[sales_raw.is_glasses == 1].groupby(city)
premium_share = premium.count() / total_glasses.count()
```

**Step 2: Test with one city**
```bash
python3 -c "from muscat_v5_compute import compute_all; d = compute_all(); print(json.dumps(d['cities']['Kraków'], indent=2, default=str)[:2000])"
```

**Step 3: Commit**
```bash
git add muscat_v5_compute.py
git commit -m "feat: add compute engine for city metrics"
```

---

## Task 3: HTML Generator — template + CSS + auth

**Files:**
- Create: `muscat_v5_generate.py`
- Output: `muscat_badania_dashboard.html`

**Step 1: Build HTML template**

Structure:
```
<!DOCTYPE html>
<html>
<head>
  <title>Muscat City Intelligence</title>
  <style>/* Muscat brand CSS — gold #C9A96E, navy #0A1628 */</style>
  <script src="chart.js 4.4.7 CDN"></script>
  <script src="jspdf CDN"></script>
  <script src="html2canvas CDN"></script>
</head>
<body>
  <!-- Auth gate -->
  <div id="auth">...</div>
  
  <!-- Main dashboard (hidden until auth) -->
  <div id="app" style="display:none">
    <!-- Hero bar with KPIs -->
    <!-- City selector + filters -->
    <!-- 6 tab panels -->
  </div>
  
  <script>
    const D = {DATA_JSON};  // embedded from Python
    // Tab rendering functions
    // Filter logic (city, period, nowy/stary)
    // Chart creation
    // Export (PDF, CSV, clipboard)
  </script>
</body>
</html>
```

**Step 2: Generate with test data, open in browser**
```bash
python3 muscat_v5_generate.py
open muscat_badania_dashboard.html
```

**Step 3: Commit**
```bash
git add muscat_v5_generate.py
git commit -m "feat: add HTML generator with auth + hero bar"
```

---

## Task 4: Tab 0 — Miasta (landing page with city cards)

**Files:**
- Modify: `muscat_v5_generate.py` (add renderMiasta() JS function)

**Step 1: Build 9 city cards with sparklines**

Each card shows:
- City name + salon count
- Revenue sparkline (last 12M) + YoY delta
- Bookings NOWY|STARY stacked bar
- AOV + premium share badge
- Fill rate gauge
- Brand search mini trend

**Step 2: Add network heatmap below cards**
- Growth Potential Score scatter plot
- CH vs FSS comparison bars

**Step 3: Test + commit**

---

## Task 5: Tab 1 — Klient (demographics, NOWY/STARY, GEO)

**Files:**
- Modify: `muscat_v5_generate.py` (add renderKlient() JS function)

**Sections to implement:**
1. NOWY vs STARY stacked monthly bar + AOV comparison
2. Age/sex pie + YoY shift stacked bars
3. ZIP heatmap (sorted bar chart of top ZIP prefixes)
4. Retencja: consent rates, orders frequency
5. Cross-city flow table

**Commit after each section works.**

---

## Task 6: Tab 2 — Produkt (models, upsell, product mix)

**Files:**
- Modify: `muscat_v5_generate.py` (add renderProdukt() JS function)

**Sections:**
1. Top 10 models ranking table with velocity arrows
2. Premium Share trend line (Asfera % per city per quarter)
3. Product mix doughnut (Blue Block/Relax/Classic/Sun)
4. Index upgrade stacked bar (Basic/Slim/Ultra-Slim/Invisible)
5. Revenue per m² bar chart per salon
6. Ticket waterfall (frame + lens + coat = total)

**Business language labels, not optical jargon.**

---

## Task 7: Tab 3 — Marketing (funnel, CPA, brand barometer)

**Files:**
- Modify: `muscat_v5_generate.py` (add renderMarketing() JS function)

**Sections:**
1. Full funnel horizontal bar: Impressions→Clicks→Bookings→Sales→Revenue
2. CPA NOWY vs STARY per city bar chart + scatter (CPA vs AOV)
3. Brand Barometer: "muscat+miasto" GSC search trend per city line chart
4. Brand search → bookings correlation (lag chart)
5. Meta targeting: age/gender spend pie vs actual buyer profile
6. Organic health: Ahrefs traffic line + GSC CTR trend
7. Impressions↔footfall correlation scatter (if traffic data available)

---

## Task 8: Tab 4 — Capacity (fill rate, alerts)

**Files:**
- Modify: `muscat_v5_generate.py` (add renderCapacity() JS function)

**Sections:**
1. Fill rate heatmap table: per salon, color-coded
2. Booking velocity sparklines (7d, 14d, 30d trailing)
3. Planned vs empty slots bar per salon
4. Alert cards: red/yellow/green per city
5. Spend→fill correlation chart

---

## Task 9: Tab 5 — Strategia (scorecard, anomalies, actions)

**Files:**
- Modify: `muscat_v5_generate.py` (add renderStrategia() JS function)

**Sections:**
1. 8-axis radar chart per city
2. City vs network comparison bars
3. Anomaly alert cards (z-score based)
4. Action items per city (computed recommendations)
5. Comparison mode (side-by-side when enabled)

---

## Task 10: Interactive Filters + Export

**Files:**
- Modify: `muscat_v5_generate.py` (add filter JS + export functions)

**Step 1: City selector dropdown**
- Changes global `selectedCity` variable
- All render functions re-execute with filtered data

**Step 2: NOWY|STARY|TOTAL toggle**
- Three radio buttons in hero bar
- Filters bookings, revenue, demographics data

**Step 3: Period selector**
- Last 3M / 6M / 12M / All time
- Filters time-series data

**Step 4: Compare mode**
- Checkbox + second city dropdown
- Duplicates each chart side-by-side

**Step 5: PDF export**
```javascript
async function exportPDF() {
    const pdf = new jsPDF('l', 'mm', 'a4');
    // Capture each section with html2canvas
    // Add Muscat branding header/footer
    pdf.save(`Muscat_${selectedCity}_${new Date().toISOString().slice(0,10)}.pdf`);
}
```

**Step 6: CSV export**
```javascript
function exportCSV(tableName, data) {
    const csv = data.map(row => Object.values(row).join(',')).join('\n');
    const blob = new Blob([csv], {type: 'text/csv'});
    // download
}
```

**Step 7: Clipboard on KPI cards**

---

## Task 11: Main Script — orchestrate everything

**Files:**
- Create: `muscat_v5_main.py` (in `/Users/marcinmichalski/Downloads/`)

```python
#!/usr/bin/env python3
"""Muscat City Intelligence Dashboard v5 — Main Generator"""
from muscat_v5_data import load_all
from muscat_v5_compute import compute_all
from muscat_v5_generate import generate_html

def main():
    print("Loading data from Railway...")
    tables = load_all()
    
    print("Computing city metrics...")
    data = compute_all(tables)
    
    print("Generating HTML...")
    html = generate_html(data)
    
    output = 'muscat_badania_dashboard.html'
    with open(output, 'w') as f:
        f.write(html)
    print(f"Dashboard saved to {output}")

if __name__ == '__main__':
    main()
```

**Run:**
```bash
python3 muscat_v5_main.py
open muscat_badania_dashboard.html
```

---

## Task 12: Deploy to Vercel

**Step 1: Copy to repo**
```bash
cp muscat_badania_dashboard.html muscat-badania-dashboard/index.html
```

**Step 2: Commit + push**
```bash
cd muscat-badania-dashboard
git add index.html
git commit -m "feat: City Intelligence Dashboard v5 — replaces v4.4"
git push origin main
```

**Step 3: Deploy**
```bash
npx vercel --yes --prod
```

**Step 4: Verify**
- Open https://muscat-badania-dashboard.vercel.app
- Login with muscat2026
- Test all 6 tabs
- Test city selector, NOWY/STARY toggle, period filter
- Test PDF export
- Test CSV export

---

## Task 13: Cleora Embeddings (optional, post-launch)

**Files:**
- Create: `muscat_v5_cleora.py`

```python
from pycleora import SparseMatrix, embed

# Build graph: client→salon, client→product, client→city, client→age_group
edges = []
for _, row in events_raw.iterrows():
    if row['client_id']:
        edges.append(f"client_{row['client_id']} salon_{row['pos']}")
for _, row in sales_raw.iterrows():
    if row['client_unique_id']:
        edges.append(f"client_{row['client_unique_id']} product_{row['product_name']}")
        edges.append(f"client_{row['client_unique_id']} city_{CITY_MAP[row['sale_team']]['city']}")

graph = SparseMatrix.from_iterator(iter(edges), "complex::reflexive::entity")
embeddings = embed(graph, feature_dim=128)

# Find sleeping premium clients, cross-salon affinity, product clusters
```

**Run after main dashboard is live.**

---

## Task 14: Update Documentation

**Files:**
- Modify: `muscat-badania-dashboard/README.md`
- Modify: `muscat-badania-dashboard/ARCHITECTURE.md`
- Modify: `muscat-badania-dashboard/DATA_SOURCES.md`

Update all docs to reflect v5 architecture, Railway data source, new tabs, ETL pipeline.

---

## Execution Order

| # | Task | Est. | Dependencies |
|---|------|------|-------------|
| 1 | Data layer | 5min | Railway DB ready |
| 2 | Compute engine | 20min | Task 1 |
| 3 | HTML template + CSS + auth | 15min | None |
| 4 | Tab 0: Miasta | 15min | Tasks 2+3 |
| 5 | Tab 1: Klient | 20min | Tasks 2+3 |
| 6 | Tab 2: Produkt | 20min | Tasks 2+3 |
| 7 | Tab 3: Marketing | 25min | Tasks 2+3 |
| 8 | Tab 4: Capacity | 15min | Tasks 2+3 |
| 9 | Tab 5: Strategia | 15min | Tasks 2+3 |
| 10 | Filters + Export | 20min | Tasks 4-9 |
| 11 | Main script | 5min | Tasks 1-3 |
| 12 | Deploy | 5min | Task 11 |
| 13 | Cleora | 30min | Task 12 (post-launch) |
| 14 | Docs | 10min | Task 12 |

**Tasks 4-9 can run in PARALLEL** (independent tab renderers).

**Critical path:** 1 → 2 → 3 → [4-9 parallel] → 10 → 11 → 12
