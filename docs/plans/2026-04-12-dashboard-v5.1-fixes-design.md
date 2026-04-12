# Dashboard v5.1 — Fixes + GEO Tab + Drill-Down Design

**Date:** 2026-04-12
**Status:** Approved
**Fixes:** 12 issues from user testing + new GEO tab + time drill-down

---

## 1. Core Principle: EVERYTHING Reacts to Filters

Every element — hero KPIs, charts, tables, maps — MUST react to:
- **Miasto** dropdown
- **POS/Salon** dropdown (filters to single salon)
- **Date range** (date picker or quick buttons)
- **NOWY/STARY/Total** toggle
- **Granulacja** (drill-down on chart click: rok→kwartał→miesiąc→dzień)

No chart shows "global/yearly" data without explicit user choice. Default = Last 12M, Cała sieć, Total, Monthly granularity.

---

## 2. Date Picker Redesign

### Current: Dropdown "Last 12M / 6M / 3M / All time / Custom" — unintuitive, yearly data by default.

### New: Quick buttons + custom range + visible label

```
Hero bar bottom row:
┌──────────────────────────────────────────────────────────────┐
│ Okres: Kwi 2025 – Mar 2026                                  │
│ [3M] [6M] [12M] [YTD] [2024] [2025] [2026] [Własny zakres] │
│                                                              │
│ (when "Własny zakres" clicked, shows inline:)                │
│ Od: [2023-01 ▼]  Do: [2026-03 ▼]  [Zastosuj]                │
└──────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Click any quick button → instant filter, highlight active button
- "Własny zakres" → shows month selectors inline, click "Zastosuj" to apply
- **Always visible label** "Okres: Kwi 2025 – Mar 2026" so user knows what they're looking at
- Default on load: **Last 12M** (active button highlighted gold)
- Year buttons (2024, 2025, 2026) = shortcut for Jan-Dec of that year

---

## 3. Time Drill-Down on Charts (D/M/Q/R)

### UX Pattern: Click to zoom in, button to zoom out

**Default view:** MONTHLY (12 bars/points for Last 12M)

**Drill-down flow:**
```
YEARLY overview
    ↓ click on year bar
QUARTERLY (4 bars for that year)
    ↓ click on quarter bar
MONTHLY (3 bars for that quarter)
    ↓ click on month bar
DAILY (28-31 bars for that month)
    ↑ [← Wróć] button to zoom back out one level
```

**Implementation:**
- Each chart has a small `[← Wróć]` button (hidden at default level)
- Click on a bar/point → triggers drill-down to next granularity
- Chart title updates: "Revenue — Kwi 2025 (dziennie)" / "Revenue — Q1 2025 (miesięcznie)"
- Cursor changes to `zoom-in` on hoverable bars
- Data source: 
  - Monthly = from events_monthly/sales_monthly (aggregated in Railway)
  - Daily = computed from events_raw/sales_raw (date grouping in JS)
  - Quarterly/Yearly = aggregated from monthly in JS

**Which charts support drill-down:**
- Revenue trend (all tabs)
- Bookings trend (Miasta, Klient)
- NOWY/STARY stacked bar (Klient)
- Product mix trend (Produkt)
- Google Ads spend trend (Marketing)
- Fill rate trend (Capacity)

**Which charts DON'T drill-down** (static aggregations):
- Pie/doughnut charts (product mix, demographics)
- Radar charts (strategia)
- Rankings/tables
- Maps

---

## 4. Fix: Hero KPIs Dynamic

Hero bar KPIs ALWAYS reflect current filters:

```javascript
function updateHeroKPIs() {
    // Get data based on selectedCity + selectedPOS + date range + customerFilter
    // If POS selected → show that salon's KPIs
    // If city selected → show city aggregate
    // If "Cała sieć" → show network aggregate
    // Date range → filter monthly data, sum/avg
    // NOWY/STARY → filter by customer type
}
```

KPI cards show:
```
[Revenue: 4.2M PLN ▲8.2%] [Bookings: 3,450 ▲12.1%] [AOV: 1,180 PLN ▲3.4%]
[Premium: 14.2% ▲1.8pp] [NOWY: 2,243 (65.3%)] [Fill Rate: 47%]
```

Delta = vs same period prior year (YoY).

---

## 5. Fix: % Everywhere for NOWY/STARY

Every place showing NOWY/STARY counts adds percentage:

| Where | Before | After |
|-------|--------|-------|
| Hero bar | NOWY: 2,243 | NOWY: 2,243 (65.3%) |
| Klient KPI cards | Bookings: 250 | Bookings: 250 (65.3%) |
| City cards | Nowy 250 / Stary 150 | Nowy 250 (62.5%) / Stary 150 (37.5%) |
| Chart tooltips | Nowy: 180 | Nowy: 180 (58.1%) |
| Tables | 1,207 | 1,207 (34.7%) |

---

## 6. Fix: Product Ranking with % Share

```
#  Model                           Ilość  % szt   Revenue     % rev   Avg price
1  Olivia Satin Gold/Champagne     1,011   4.2%   1.21M PLN    3.8%   1,197 PLN
2  Maggie Brown Havana               755   3.1%   890K PLN     2.8%   1,179 PLN
3  Blair Havana Moonlight            645   2.7%   780K PLN     2.4%   1,209 PLN
```

---

## 7. Fix: Google Ads Monthly Trend

Debug renderMarketing() — the chart doesn't render. Likely data format mismatch (D.marketing.google_ads_monthly month format vs Chart.js labels).

---

## 8. Fix: CPA per Miasto — Dynamic per Date Range

**Current:** Static 18 PLN for all cities.

**Fix:** Compute CPA per month per city in compute engine:
```python
# Per city per month:
# Map Meta regional spend to cities (voivodeship → city proportional split)
# Map Google Ads GEO spend to cities
# CPA[city][month] = total_ad_spend[city][month] / bookings[city][month]
```

Dashboard filters CPA by selected date range:
```javascript
const cpaByCityFiltered = filteredMonths.reduce((acc, m) => {
    acc[city].spend += m.meta_spend + m.google_spend;
    acc[city].bookings += m.bookings;
}, {});
// CPA = spend / bookings for filtered period
```

---

## 9. Fix: GDA Display Name

```python
"GDA": ("Gdańsk", "Podwale Staromiejskie", "FSS", 119.0, 60.0),
```

Display in UI: "GDA — Podwale Staromiejskie" (not just "Podwale").

---

## 10. NEW: Age × City × Revenue Matrix

**Location:** Tab Klient, new section "Matrix wiekowy"

**Interactive heatmap table:**
```
Wiek/Miasto    Warszawa    Kraków    Trójmiasto    Wrocław    ...    TOTAL
18-25          12.1%       8.4%      11.2%         9.8%              10.8%
               1.4M PLN    340K      280K          195K              2.8M
26-35          34.2%       31.0%     29.5%         33.1%             32.4%
               4.1M        1.2M      740K          660K              8.5M
36-45          28.5%       33.2%     31.0%         30.2%             30.1%
...
```

**Features:**
- Toggle: [% udział] [Revenue PLN] [Ilość klientów] [AOV]
- Heatmap coloring: darker = higher share
- YoY arrows ▲▼ per cell
- **Click cell → drill-down** to monthly trend of that age group in that city
- Drill-down shows: line chart of revenue/bookings for that segment over time
- Respects date range filter

---

## 11. NEW: Tab GEO (7th tab)

### Leaflet.js Heatmap

**Structure:**
```
┌───────────────────────────────────────┐
│ [Mapa Polski — Leaflet.js]           │
│ Heatmap: intensity = klienci per ZIP  │
│ Pins: salony Muscat z tooltipami      │
│ Toggle: [NOWY] [STARY] [TOTAL]       │
│ Radius: [5km] [10km] [20km]          │
└───────────────────────────────────────┘
│
│ Top 20 ZIP kodów — tabela
│ ZIP | Miasto | Klienci | NOWY% | Revenue | AOV
│ 01  | Warszawa | 166K  | 78%   | 12.3M   | 1,180
│ ...
```

**Data:** 
- geo_coverage table: zip_prefix, city, customers, returning_customers, avg_order_value
- ZIP prefix → centroid GPS: hardcoded lookup (~100 most common Polish ZIP prefixes)
- Salon locations: hardcoded GPS (16 salons)

**Interactions:**
- Zoom into city → see ZIP-level distribution
- Toggle NOWY/STARY → different heatmap colors (green=NOWY, blue=STARY)
- Click ZIP → show details panel
- Radius overlay around salons: shows how many clients within X km

**Libraries:**
- Leaflet.js 1.9.4 CDN (~40KB)
- Leaflet.heat plugin (~5KB)

---

## 12. Per-POS Charts Everywhere

**Rule:** When POS is selected in dropdown, EVERY chart shows data for that single salon.

Charts that need POS filtering:
- Revenue trend → per salon
- Bookings NOWY/STARY → per salon
- Product mix → per salon
- Demographics → per salon (from sales_demographics)
- Fill rate → per salon
- Top models → per salon
- Brand barometer → N/A (GSC is per city, not per POS)

**Implementation:** Each render function checks `selectedPOS`:
```javascript
function getFilteredData() {
    if (selectedPOS !== 'all') {
        // Return salon-level data from D.salons[selectedPOS]
        // + filter raw monthly by sale_team === selectedPOS
    } else if (selectedCity !== 'all') {
        // Return city-level data
    } else {
        // Return network-level data
    }
}
```

---

## 13. Updated Tab Structure (7 tabs)

```
[Miasta] [Klient] [Produkt] [Marketing] [Capacity] [GEO] [Strategia]
```

### Updated Hero Bar:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Muscat.Intelligence                                                 │
│                                                                     │
│ [Revenue ▲8%] [Bookings ▲12%] [AOV ▲3%] [Premium ▲1.8pp] [NOWY 65%]│
│                                                                     │
│ Miasto: [▼ Kraków] Salon: [▼ Starowiślna] [NOWY|STARY|Total]       │
│                                                                     │
│ Okres: Kwi 2025 – Mar 2026                                         │
│ [3M] [6M] [12M] [YTD] [2024] [2025] [2026] [Własny zakres]        │
│                                                              [PDF][CSV]│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 14. Compute Engine Changes (muscat_v5_compute.py)

### New data needed in output:

1. **Monthly ad spend per city** — for dynamic CPA:
   ```python
   "ad_spend_monthly_city": {
       "Warszawa": [{"month":"2025-04", "meta_spend":12000, "google_spend":8000}],
       ...
   }
   ```

2. **Daily data** for drill-down (from raw tables):
   ```python
   "daily": {
       "events": [{"date":"2025-04-01", "pos":"ARK", "bookings":12, "done":8, "new":7, "stary":5}],
       "sales": [{"date":"2025-04-01", "sale_team":"ARK", "revenue":14500, "glasses":8}]
   }
   ```
   Note: This will make the JSON much larger. Consider: compute daily only for last 3 months, or load on-demand.

3. **Age × city matrix** — pre-computed:
   ```python
   "age_city_matrix": {
       "Warszawa": {"18-25": {"revenue":1400000, "pct":12.1, "count":450, "aov":1122, "yoy_pct":"+2.3"}, ...},
       ...
   }
   ```

4. **ZIP → GPS lookup** for Leaflet:
   ```python
   "zip_coordinates": {
       "01": {"lat":52.24, "lng":21.00, "customers":166546},
       "02": {"lat":52.19, "lng":20.99, "customers":4895},
       ...
   }
   ```

### Size concern:
- Current JSON: ~150KB
- Adding daily data (last 3M): +~200KB  
- Adding ZIP coords: +~10KB
- Total: ~360KB — acceptable for static HTML

### Optimization:
- Daily data: only last 3 months (for drill-down)
- Older drill-down: aggregate to weekly in compute
- GEO: only top 100 ZIP prefixes (covers 95%+ of clients)

---

## 15. Implementation Priority

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Filters react globally (hero + all tabs) | HIGH | CRITICAL |
| 2 | Date picker redesign | MEDIUM | HIGH |
| 3 | % NOWY/STARY everywhere | LOW | HIGH |
| 4 | Product ranking with % | LOW | MEDIUM |
| 5 | Google Ads chart fix | LOW | HIGH |
| 6 | CPA dynamic per date | MEDIUM | HIGH |
| 7 | GDA display name | LOW | LOW |
| 8 | Age × city matrix | MEDIUM | HIGH |
| 9 | Tab GEO + Leaflet map | HIGH | HIGH |
| 10 | Per-POS charts | MEDIUM | HIGH |
| 11 | Drill-down D/M/Q/R | HIGH | HIGH |
| 12 | No yearly default | LOW | MEDIUM |

**Critical path:** 1 → 2 → 11 → 10 → 3+4+5+6+7 → 8 → 9 → 12
