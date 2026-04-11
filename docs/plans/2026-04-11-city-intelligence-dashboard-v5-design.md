# Muscat City Intelligence Dashboard v5 — Design Document

**Date:** 2026-04-11
**Author:** Marketing Hackers + Claude
**Status:** Approved
**Replaces:** Dashboard v4.4 (6 tabów, hardcoded CSV/XLSX)

---

## 1. Context & Goals

### Problem
Dashboard v4.4 działa na 12+ hardcoded plików. Brak analizy per miasto, brak podziału NOWY/STARY, brak korelacji z wydatkami marketingowymi, brak capacity planning.

### Goal
Najlepsza analiza marki optycznej jaka kiedykolwiek powstała. **30% wzrost MoM w ujęciu YoY** przez dwie dźwignie:
1. **VOLUME** — więcej kobiet 25-44 per miasto
2. **AOV** — wyższy koszyk per klientka (premium konstrukcje)

### Users
- **CEO Muscat** — big picture, city performance, strategic decisions
- **Marketing Hackers** — performance marketing, budget allocation, campaign optimization

### Brand positioning
**Muscat = optyk modowy.** Komunikacja do kobiet 25-44. Nie medyczny, nie dla 55+. Progresywne to upsell dla istniejących klientek, nie acquisition target.

---

## 2. Data Sources (777K rows in Railway PostgreSQL)

### Odoo ETL (775K rows, via VPN → Railway)
| Table | Rows | Content |
|-------|------|---------|
| customers_raw | 394,136 | Full customer base (MD5 hash, age, sex, ZIP, city, NOWY/STARY, consents) |
| events_raw | 152,191 | All eye exams 2020-2026 (source, status, POS, client_id) |
| sales_raw | 205,968 | All orders 2023-2026 (product details, prices, SKU, construction, index) |
| events_monthly | 509 | Aggregated bookings per POS per month |
| sales_monthly | 555 | Aggregated sales per POS per month with product breakdown |
| traffic_monthly | 237 | Footfall per POS per month (from 2025-01) |
| customers_city | 7,330 | Customer demographics aggregated by city |
| demographics_temporal | 548 | Age/sex per POS per year (bookings) |
| sales_demographics | 585 | AOV per age group per POS per year |
| product_trends | 11,748 | Top frame models per POS per quarter |
| geo_coverage | 1,251 | Customer ZIP prefix distribution |
| city_mapping | 16 | POS → city, salon name, type (CH/FSS), m² |

### MCP Sources (2,453 rows)
| Table | Rows | Source |
|-------|------|--------|
| mcp_google_ads_monthly | 742 | Campaign spend/clicks/conv per month |
| mcp_google_ads_geo | 689 | Spend per voivodeship per month |
| mcp_meta_regional | 11 | Meta spend per voivodeship (last 90d) |
| mcp_meta_demographics | 12 | Meta age/gender targeting (last 90d) |
| mcp_gsc_daily | 490 | GSC clicks/impressions daily |
| mcp_gsc_queries | 500 | Top 500 search queries |
| mcp_ahrefs_history | 9 | Organic traffic monthly |

### Additional data file
- `Sale_team_report.csv` — salon metraż (m² total, m² sala sprzedaży, CH vs FSS)

---

## 3. Architecture

```
Railway PostgreSQL (777K rows, public endpoint)
    │
    ▼
muscat_prep_data.py v5 (Python)
    ├── Connect to Railway
    ├── Query all tables
    ├── Compute: CPA nowy/stary, brand barometer, capacity, correlations
    ├── Run Cleora embeddings (optional, cached)
    ├── Generate JSON data structure
    └── Embed in HTML template
         │
         ▼
    index.html (~600KB, static)
    ├── CSS: Muscat brand (gold #C9A96E, navy #0A1628)
    ├── JS: Chart.js 4.4 + custom filters + export
    ├── Data: embedded JSON (`const D = {...}`)
    └── Auth: password gate (muscat2026)
         │
         ▼
    Vercel (static deploy)
    https://muscat-badania-dashboard.vercel.app
```

### Tech stack
- **Charts:** Chart.js 4.4.7 + chartjs-plugin-zoom
- **PDF export:** jsPDF + html2canvas
- **CSV export:** native JS Blob
- **Clipboard:** navigator.clipboard API
- **No backend** — all data embedded, filters in JS

---

## 4. Navigation & Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  HERO BAR                                                            │
│  Revenue ▲12% | Bookings ▲8% | AOV 1,180 PLN | Fill Rate 47%       │
│  Brand Search ▲15%                                                   │
│                                                                      │
│  [Miasto ▼ Kraków] [Okres ▼ Last 12M] [NOWY|STARY|TOTAL] [Compare]  │
│  [PDF ↓] [CSV ↓]                                                    │
├──────────────────────────────────────────────────────────────────────┤
│  [Miasta] [Klient] [Produkt] [Marketing] [Capacity] [Strategia]     │
└──────────────────────────────────────────────────────────────────────┘
```

### Global controls
- **Miasto dropdown** — filters ALL tabs
- **Okres dropdown** — Last 3M / 6M / 12M / All time / Custom
- **NOWY|STARY|TOTAL toggle** — splits ALL metrics by customer type
- **Compare checkbox** — enables side-by-side 2 cities
- **PDF** — generates A4 report for selected city
- **CSV** — exports current view data

---

## 5. Tabs

### Tab 0: MIASTA (landing page)

**9 city cards** with:
- Revenue trend sparkline + YoY delta
- Bookings/msc (NOWY vs STARY stacked)
- AOV + premium share %
- Fill rate (capacity indicator)
- Brand search trend mini-sparkline
- Color coding: green (growing), red (declining), gold (top performer)

**Below cards:**
- Network heatmap: "Growth Potential Score" = volume headroom × AOV headroom per city
- Efficiency scatter: X = revenue/m², Y = bookings/m², bubble size = ad spend

**CH vs FSS comparison:**
- Aggregate KPIs for galeria vs ulica format
- "FSS avg AOV 1,180 vs CH 1,050 — ulica klientki wydają więcej"

---

### Tab 1: KLIENT (per selected city)

**Sections:**

1. **NOWY vs STARY split**
   - Stacked bar: NOWY/STARY bookings per month trend
   - "Kraków: 65% NOWY — acquisition market"
   - AOV comparison: NOWY avg vs STARY avg
   - Revenue contribution: "62% revenue ze STARYCH mimo 24% bazy"

2. **Demografia**
   - Age/sex pie chart + YoY shift
   - Core audience tracking: % kobiet 25-44 trend
   - "Shift: 18-25 spadek -11% ale 36-45 wzrost +22%"
   - AOV × age group bar chart

3. **Pokrycie GEO**
   - ZIP prefix heatmap per salon
   - NEW client ZIP: "Czy pojawiają się klienci z nowych obszarów?"
   - Cross-city flow: klientki z miast bez salonu (Bydgoszcz 328, Rzeszów 321)
   - "Whitespace: ZIP 03-xxx ma 3.1K klientek ale zero targetowania"

4. **Retencja**
   - NOWY → STARY conversion rate (ile wraca?)
   - Consent rates: email/sms opt-in % per city
   - Orders frequency distribution
   - "Email opt-in 12% vs Katowice 28% — niska retencja"

---

### Tab 2: PRODUKT (per selected city)

**Sections:**

1. **Top 10 modeli**
   - Ranking per kwartał + velocity (rosnące/spadające)
   - "Olivia Satin Gold = #1 od 4 kwartałów (1,011 szt)"
   - City-specific: "Kraków kupuje inne modele niż Warszawa?"

2. **Upsell Tracker**
   - Premium Share % trend: Asfera / (Asfera + Sfera)
   - Index upgrade: % na Basic(1.5) vs Slim(1.6) vs Ultra-Slim(1.67) vs Invisible(1.74)
   - "ARK: 15% premium vs TRG: 8% — co ARK robi lepiej?"
   - NOWY vs STARY product mix: "NOWY: 80% Classic, STARY: 40% Relax"

3. **Product mix**
   - Digital Protection (Blue Block) / Comfort Vision (Relax) / Essential (Classic) / Sun breakdown
   - Coat penetration: Clear vs Transition vs Tint
   - Ticket waterfall: oprawka + szkła + coat = total

4. **Revenue per m²**
   - Revenue / m² sala sprzedaży per salon
   - Bookings / m² trend
   - "POZ: 78m² → highest revenue/m², LUB: 30m² → highest density"

*Business language translations:*
- Sfera/Asfera → "Standard / Premium konstrukcja"
- Index 1.5/1.6/1.67/1.74 → "Basic / Slim / Ultra-Slim / Invisible"
- Blue Block → "Digital Protection"
- Relax → "Comfort Vision"
- product_power Zero/Low/Medium → "Modowy / Lekka korekcja / Poważna korekcja"

---

### Tab 3: MARKETING (per selected city)

**Sections:**

1. **Full funnel**
   - Sankey: Impressions → Clicks → Sessions → Bookings → Done → Sales → Revenue
   - Per city, split by NOWY/STARY at booking level
   - Channel: Meta vs Google vs Organic vs Showroom

2. **CPA NOWY vs STARY**
   - CPA_nowy = ad spend per city / new bookings per city
   - CPA_stary ≈ 0 (organic return)
   - Blend CPA = total spend / total bookings
   - "Kraków: CPA_nowy 31 PLN, NOWY AOV 977 PLN → ROAS 31x"
   - Scatter: X = CPA_nowy, Y = AOV_nowy, bubble = volume

3. **Brand Barometer**
   - GSC "muscat + [miasto]" monthly search volume trend
   - Correlation: brand search [t] → bookings [t+1] (lag analysis)
   - "Brand search 'muscat katowice' +25% MoM → expect +15% bookings next month"
   - Brand gap: cities with low brand search vs high bookings = pure performance

4. **Meta targeting accuracy**
   - Meta age/gender spend vs actual buyer profile from Odoo
   - "Targeting 25-34F = correct (core audience, 30% spend)"
   - Spend per voivodeship vs bookings per city → geographic efficiency

5. **Organic health**
   - Ahrefs organic traffic trend
   - GSC CTR trend (declining: 3.4% → 2.8%)
   - Top non-brand queries + position tracking
   - "Organic -24% za 8 msc — SEO intervention needed"

6. **Impressions ↔ footfall correlation**
   - Monthly: Meta impressions vs traffic_monthly entries (from 2025-01)
   - Lag analysis: 0, 1, 2 month lag
   - "Meta impressions lag 1 msc → footfall r=0.72"

---

### Tab 4: CAPACITY (per selected city)

**Sections:**

1. **Fill Rate Heatmap**
   - Per salon: planned bookings / max capacity (520/msc)
   - Color: red <40%, yellow 40-60%, green >60%
   - "Gdańsk: 27% fill rate — KRYTYCZNE, dopal budżet"

2. **Booking velocity**
   - Rate of new bookings coming in (trailing 7d, 14d, 30d)
   - Trend: accelerating or decelerating?
   - "Booking velocity Kraków: -15% vs last week → campaign check"

3. **Planned vs empty slots**
   - Future slots: planned (booked) vs empty (available)
   - Calendar view: next 4 weeks per salon
   - Source of upcoming bookings: website vs showroom vs helpline

4. **Alert system**
   - Fill rate < 40% → "DOPAL BUDŻET — [miasto] ma [X] pustych slotów"
   - Fill rate > 80% → "PEŁNE — rozważ dodatkowe godziny"
   - Velocity drop > 20% WoW → "Booking velocity maleje — sprawdź kampanie"

5. **Spend → fill correlation**
   - Meta spend [t-1] → fill rate [t]
   - Google spend [t-1] → fill rate [t]
   - "Zwiększenie Meta o 5K PLN w Katowice → +12% fill rate miesiąc później"

---

### Tab 5: STRATEGIA (per selected city)

**Sections:**

1. **City Scorecard**
   - 8-axis radar: volume, AOV, growth YoY, retention, premium%, CPA, organic, brand search
   - vs network average on each axis

2. **Anomaly alerts**
   - Z-score per city per metric
   - "ALERT: Łódź cancel rate +18% vs network"
   - "ALERT: Katowice AOV highest in network (1,363 PLN)"

3. **Action Items**
   - 3-5 konkretnych rekomendacji per miasto
   - Priorytet (high/medium/low) + estimated revenue impact
   - Examples:
     - "Kraków: Podnieś premium share 12%→20% → +340K PLN/rok"
     - "Warszawa: Whitespace ZIP 03-xxx → Meta GEO campaign"
     - "Łódź: Lowest AOV 876 PLN → upsell training"

4. **City comparison**
   - Side-by-side when Compare mode enabled
   - Same metrics, two cities, delta highlighted

5. **Cleora insights** (if available)
   - "4,200 sleeping premium klientek" → win-back campaign candidates
   - Cross-salon affinity: which salons share client profiles
   - Product affinity clusters: what goes with what
   - Geographic expansion signals: ZIP codes with untapped potential

---

## 6. Key Computed Metrics

### CPA NOWY per city
```
CPA_nowy = (meta_spend_city + google_spend_city) / new_bookings_city
```
Assumption: 100% ad spend drives NEW clients. Returning clients come organically.

### Brand Barometer
```
brand_search_city = GSC clicks WHERE query CONTAINS 'muscat' AND query CONTAINS [city_name]
brand_trend = MoM % change
leading_indicator = pearson_correlation(brand_search[t], bookings[t+1])
```

### Fill Rate
```
fill_rate = planned_future_bookings / (20 bookings/day × working_days × salons_in_city)
```

### Premium Share
```
premium_share = asfera_count / (asfera_count + sfera_count) per city
```

### Revenue per m²
```
revenue_per_m2 = monthly_glasses_revenue / m2_sala_sprzedazy
```

### Growth Potential Score
```
volume_headroom = (capacity_max - current_bookings) / capacity_max
aov_headroom = (network_max_aov - city_aov) / network_max_aov
growth_potential = volume_headroom × 0.5 + aov_headroom × 0.5
```

---

## 7. Export

### PDF Report
- Button in hero bar → jsPDF + html2canvas
- A4 landscape, Muscat branding (gold/navy)
- Contains: all KPIs, charts as images, action items
- Options: single city / comparison / network overview
- Footer: "Powered by Marketing Hackers"

### CSV Export
- Button per table/chart → native JS Blob
- Pre-computed data (not raw), Polish column names
- Filename: `Muscat_{miasto}_{sekcja}_{data}.csv`

### Clipboard
- Click KPI card → copy value
- Click table → copy as TSV (paste to Excel)

---

## 8. Key Discoveries Already in Data

1. **Demographic shift = SUCCESS** — lost 18-25 (-11%) but gained 36-55 (+20%) with 33% higher AOV = +1M PLN net
2. **Asfera = 3x price of Sfera** — avg 3,122 vs 1,012 PLN per pair
3. **55+ = highest AOV 1,666 PLN** — but NOT the acquisition target (they come organically)
4. **Core audience 25-34F** — correctly targeted at 30% Meta spend
5. **Brand search = 84% of GSC clicks** — strong brand, weak non-brand
6. **Organic declining -24%** — from 37.8K to 28.7K in 8 months
7. **NOWY = 76%, STARY = 24%** — acquisition-heavy, retention opportunity
8. **Katowice = highest AOV 1,363 PLN** — best premium market
9. **GSC "muscat + miasto"** per city varies wildly — brand awareness gap between cities
10. **CH vs FSS** — FSS (ulica) clients spend more per visit

---

## 9. Verification

1. Run muscat_prep_data.py → verify all charts render
2. Check: NOWY/STARY toggle works across all tabs
3. Check: city selector filters everything
4. Check: CPA calculations match known account-level CPA (25.8 PLN)
5. Check: PDF export produces readable A4 document
6. Check: CSV export opens correctly in Excel
7. Deploy to Vercel, test with password muscat2026
8. Compare key metrics with v4.4 to ensure consistency
