# Architektura Dashboard v4.x

## Pipeline danych

```
┌─────────────────────────────────────────────────────────────┐
│                    muscat_prep_data.py                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ load_bookings│  │ load_basket  │  │ load_lens    │      │
│  │   (xlsx)     │  │   (xlsx)     │  │   (xlsx)     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│  ┌──────┴───────┐  ┌─────┴────────┐                        │
│  │ load_orders  │  │  Hardcoded   │                        │
│  │   (csv)      │  │  ad_spend,   │                        │
│  └──────┬───────┘  │  cpa, reviews│                        │
│         │          └──────┬───────┘                         │
│         ▼                 ▼                                 │
│  ┌─────────────────────────────────────┐                   │
│  │      compute_aggregations(df, ...)  │                   │
│  │                                     │                   │
│  │  → monthly, yoy, salon_monthly      │                   │
│  │  → salon_summary, type_monthly      │                   │
│  │  → source_trend, source_per_salon   │                   │
│  │  → lead_time, cancel_chain          │                   │
│  │  → correlations, anomalies          │                   │
│  │  → forecast, new_salon_impact       │                   │
│  │  → basket, lens, orders analytics   │                   │
│  │  → interpretations (per chart)      │                   │
│  │  → scaling_lever, cleora_insights   │                   │
│  │  → cpa_per_city, competitive        │                   │
│  │  → black_september, ad_cpm_cpc      │                   │
│  │  → salon_ramp, cannibalization      │                   │
│  │  → strategic_insights (13 cards)    │                   │
│  └──────────────┬──────────────────────┘                   │
│                 ▼                                           │
│  ┌─────────────────────────────────────┐                   │
│  │      generate_html(data)            │                   │
│  │                                     │                   │
│  │  data → JSON.dumps → embedded in    │                   │
│  │  HTML as `const D = {...}`          │                   │
│  │                                     │                   │
│  │  HTML contains:                     │                   │
│  │  - CSS (Muscat brand design)        │                   │
│  │  - 6 tab panels                     │                   │
│  │  - JavaScript (Chart.js rendering)  │                   │
│  └──────────────┬──────────────────────┘                   │
│                 ▼                                           │
│         muscat_badania_dashboard.html (556KB)               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ cp → index.html
                 muscat-badania-dashboard/
                          │
                          ▼ git push + npx vercel --prod
                 https://muscat-badania-dashboard.vercel.app
```

## Struktura `muscat_prep_data.py`

### Stałe i mapowania (linie 1-105)
- `BOOKINGS_FILE`, `BASKET_FILE`, `LENS_FILE`, `ORDERS_FILE` — ścieżki plików
- `NEW_POS_STRIP` — mapowanie "Badanie Warszawa Arkadia" → "Warszawa Arkadia"
- `ORDERS_TO_POS` — mapowanie "POS Arkadia" → "Warszawa Arkadia"
- `CITY_GROUPS` — salon → miasto (Warszawa, Kraków, Trójmiasto, etc.)
- `LOCATION_TYPE` — salon → galeria/ulica
- `NEW_SALON_DATES` — daty otwarcia nowych salonów
- `EXCLUDE_POS` — ['Praga', 'Badanie Praga'] (czeskie salony)
- `POLISH_MONTHS` — mapowanie polskich nazw miesięcy

### Funkcje ładowania danych (linie 106-230)
- `load_bookings()` — xlsx → DataFrame, normalizacja POS, exclude Praga, computed columns
- `load_basket()` — xlsx wide → long format, exclude Czech
- `load_lens()` — xlsx wide → long format, parsowanie kolumn year.month
- `load_orders()` — csv, mapowanie POS, Polish month names → numbers

### Agregacje (linie 231-1515)
`compute_aggregations(df, basket_df, lens_df, orders_df)` — OGROMNA funkcja:
- KPI cards data
- Monthly volume, YoY, per-city, per-salon
- Source analysis (website/showroom/helpline trends)
- Lead time distribution
- Cancellation chain analysis
- Client returning analysis, cross-location movement
- New salon impact / cannibalization
- Basket, lens, orders analytics
- Correlations (Pearson, scatter data)
- Anomaly detection (z-score)
- Forecast (linear + seasonal)
- Business intelligence insights
- **Interpretations** — text comment per chart with 📢 MEDIA recommendations
- **Scaling lever** — rev/zapis growth, CPA, headroom, scenarios 2026
- **Cleora insights** — graph embedding results
- **CPA per city** — Meta (normalized) + Google (API verified)
- **Black September** — cross-data diagnosis
- **Ad CPM/CPC** — monthly trends Meta + Google
- **Strategic insights** — 13 recommendation cards

### Generacja HTML (linie 1516-3505)
`generate_html(data)` — generuje CAŁY dashboard jako f-string:
- Auth gate (hasło muscat2026)
- 6 tabów: Przegląd, Operacje, Wzrost, Przychody, Marketing, Czarny Wrzesień
- Lazy chart rendering (tylko aktywny tab renderuje)
- Fullscreen overlay (safe dataset cloning)
- Chart.js 4.4.7 + chartjs-plugin-zoom
- Muscat brand: gold #C9A96E on navy #0A1628
- Inter + DM Serif Display fonts
- "Powered by Marketing Hackers" footer

### Main (linie 3506-3530)
- Ładuje 4 źródła danych
- Wywołuje compute_aggregations
- Wywołuje generate_html
- Zapisuje do pliku

## Dashboard — 6 tabów

| Tab | ID | Renderer | Charts | Zawartość |
|-----|-----|----------|--------|-----------|
| Przegląd | `health` | `renderHealth()` | 5 | Hero, KPI, trend, salon grid, source cards |
| Operacje | `ops` | `renderOps()` | 12 | YoY, sources, cities, cancel, lead time, time |
| Wzrost | `growth` | `renderGrowth()` | 10 | Drill-down, galeria/ulica, cannibalization, ramp |
| Przychody | `revenue` | `renderRevenue()` | 12 | Basket, lens, clients, Cleora, correlations |
| Marketing | `marketing` | `renderMarketing()` | 10 | Ads, CPA, CPM/CPC, forecast, strategy, BI |
| Czarny Wrzesień | `blacksep` | `renderBlackSep()` | 3 | 5-factor diagnosis, campaign analysis, prevention |

## Kluczowe odkrycia zakodowane w danych

### MD5 Match (client_id = MD5(phone))
```python
# bookings['client_id'] = hashlib.md5(phone.encode()).hexdigest()
# To pozwala połączyć bookings ↔ orders przez telefon
# Match rate: 52.6% (46,301 z 87,975 bookings)
```

### Scaling Lever
```python
data['scaling_lever'] = {
    'rev_per_zapis': {2023: 304, 2024: 354, 2025: 491, 2026: 624},
    'cpa': {2023: 25, 2024: 31, 2025: 40},
    'margin_per_zapis': {2023: 279, 2024: 323, 2025: 451},
    'headroom_2026': 381,  # PLN zanim breakeven
    'breakeven_cpa': 421,  # PLN
}
# Rev/zapis rośnie +27%/rok, CPA stabilny → bezpieczne podwojenie budżetu
```

### CPA per city (verified)
```
Account-level: 25.8 PLN (total 2.27M spend / 87,975 bookings)
Meta: API regional, normalized ×0.738 (raw 135% → account 100%)
Google: GAQL geographic_view (82.9% account coverage)
UWAGA: CPA = ad cost per total booking, NIE per ad-attributed conversion
```
