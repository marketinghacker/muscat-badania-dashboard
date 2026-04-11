# Źródła danych — Muscat Dashboard

## 1. Bookings (badania wzroku)

**Plik:** `badania_wg_daty_zapisu_2026-04-03T16_20_05.275751827Z.xlsx`
**Rekordów:** 87,975 (po wykluczeniu Czech Praga)
**Zakres:** 2023-01-01 → 2026-03-31 (39 miesięcy)
**Źródła:** website (56.5%), showroom (37.1%), helpline (6.5%)
**Kolumny:** registration_date, registration_datetime, exam_datetime, source, status_post, source_cancellation, cancellation_datetime, pos, client_id, client_name

### Kluczowe transformacje:
- `client_id` = MD5 hash numeru telefonu (odkryte podczas analizy!)
- `pos` normalizowane z "Badanie Warszawa Arkadia" → "Warszawa Arkadia"
- **Praga (Czech)** wykluczona (`EXCLUDE_POS = ['Praga', 'Badanie Praga']`)
- Kolumny computed: city_group, location_type, lead_time_days, month, year

### Wykluczenia:
- "Badanie Praga" = salon w Pradze (Czechy), telefony +420, czeskie imiona
- Warszawa Targowa NIE jest nowym salonem (istnieje od Jan 2023)
- Wrocław Stawowa = salon tymczasowy, zamknięty IX 2025, zrelokowany do Wroclavia

---

## 2. Orders z telefonami

**Plik:** `Zamówienia_Muscat_Nr_Telefonów - Export.csv`
**Rekordów:** 139,968
**Kolumny:** phone, order_number, Sale team, Reve (revenue), Kod pocztowy, Czy powracający klient?, Miasto, order_datetime (Rok/Miesiąc/Dzień), sex

### Mapowanie Sale team → POS:
```
POS Arkadia → Warszawa Arkadia
POS Chmielna → Warszawa Chmielna
POS Katowicka → Katowice (uwaga: "Katowicka" nie "Katowice")
POS Manufaktura → Łódź
POS Posnania → Poznań
POS Wroclavia → Wrocław Stawowa (NIE Galeria Wroclavia!)
```

### Wykluczenia:
- POS Praga CZ, eCommerce CZ — czeskie dane

### Match z bookings:
- `client_id` w bookings = `MD5(phone)` z orders
- Match rate: 52.6% (30,949 unikalnych telefonów)
- Weryfikacja: brute force hash ALL order phones → check overlap z booking hashes

---

## 3. Koszyk okularowy (AOV)

**Plik:** `Średni koszyk okularowy po latach.xlsx`
**Format:** Wide — rows=salony, cols=lata (2022-2026)
**Rekordów:** 72 (po wykluczeniu Czech i unpivot)

### Transformacja:
- Row 0 = header labels (skip)
- "Total" row = skip
- "Zastosowane filtry" row = skip
- eCommerce CZ = skip
- Unpivot: salon × year → long format

### Key data:
- Total avg: 705 PLN (2022) → 1,044 PLN (2026) = +48%
- Wzrost = efekt polityki upsellingu, NIE organicznego popytu

---

## 4. Wolumen soczewek (lens)

**Plik:** `data (10).xlsx`
**Format:** Wide — rows=salony, cols=year.month_index
**Rekordów:** 534 (po unpivot)
**Filtr:** sun mirror + sun polarised + sun standard

### Transformacja kolumn:
- Kolumny: `2023`, `2023.1`, `2023.2`... gdzie `.N` = N-ty miesiąc od stycznia
- Kolumna `Total` = skip
- Row "Total" = skip
- Row "Zastosowane filtry" = skip

---

## 5. Meta Ads (via GoMarble MCP)

**API:** `mcp__a8beb748...facebook_get_adaccount_insights`
**Konto:** act_2866864676927281 ([PL] Muscat PERFO)
**Zakres:** Apr 2023 → Mar 2026 (36 miesięcy)

### Dane account-level (monthly):
- spend, impressions, clicks, cpm, cpc, ctr
- Hardcoded w `data['ad_spend']['meta']` i `data['ad_cpm_cpc']['meta']`

### Dane regional (GEO breakdown):
- `breakdowns=["region"]` → voivodeship-level
- **UWAGA:** Regional sum = 135% account total (multi-region attribution!)
- Normalizacja: raw × 0.738 = account total
- Zapisane w: `meta_perfo_regional_full.json`

### Dane campaign-level (dla Czarnego Września):
- `level="campaign"`, `time_increment="monthly"`
- Kluczowe: "Back to School" kampanie wyłączone we wrześniu 2025

### Drugie konto:
- act_781998882743478 ([PL] Muscat Marketing) — NIE używane w analizie (per user request)

---

## 6. Google Ads (via Marketing Hackers MCP)

**API 1 (GoMarble):** `mcp__4bc24780...google_ads_run_query` (GAQL)
**API 2 (GADS v2):** `mcp__1e4d3d07...search_gaql` (GAQL)
**Konto:** 5506922679 (Muscat), Manager: 3386507395 (MCC Marketing Hackers)

### Dane account-level (monthly):
- GAQL: `SELECT segments.month, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions FROM customer`
- Hardcoded w `data['ad_spend']['google']`

### Dane GEO (per region/city):
- GAQL: `SELECT segments.geo_target_region, segments.geo_target_city, metrics.cost_micros, metrics.clicks, metrics.conversions FROM geographic_view WHERE geographic_view.location_type = LOCATION_OF_PRESENCE`
- **82.9% account spend mapped** (vs CSV export 42.8%)
- **BUG:** Dedykowany tool `google_ads_get_geographic_report` nie działa (segments.geo_target_country incompatible)
- **Workaround:** GAQL query via `run_query` / `search_gaql`

### Dane campaign-level:
- Per campaign per month spend, clicks, conversions
- Campaign names: PMax, Search Brand/Generic, Shopping

### City ID mapping (z GAQL):
```
geoTargetConstants/1011419 w regionie 20853 = Kraków (Małopolskie)
geoTargetConstants/1011419 w regionie 9231592 = Warszawa (Mazowieckie)
geoTargetConstants/1011243 = Wrocław (Dolnośląskie, 20847)
geoTargetConstants/1011367 = Łódź (Łódzkie, 20852)
geoTargetConstants/1011615 = Szczecin (Zachodniopomorskie, 20861)
geoTargetConstants/1011475 = Gdańsk? (Pomorskie, 20857)
geoTargetConstants/1011521 = Katowice (Śląskie, 20859)
geoTargetConstants/1011320 = Lublin (Lubelskie, 20850)
geoTargetConstants/1011672 = Poznań (Wielkopolskie, 20862)
geoTargetConstants/1011476 = Gdynia (Pomorskie, 20857)
```
**UWAGA:** Ten sam city ID (1011419) pojawia się w 2 regionach! Mapuj po REGIONIE, nie city ID.

---

## 7. Google Ads CSV (ręczny eksport)

**Plik:** `Konwersje (2).csv`
**Encoding:** UTF-16
**Format:** Region (lokalizacja użytkownika) × Miesiąc × metryki
**Zakres:** Jan 2023 → Mar 2026

### Zawartość:
- Konwersje, Koszt, Koszt konwersji per region per miesiąc
- 25,163 linii (w tym tysiące regionów z 0 PLN)
- **Powiat Warszawa** jest SUBSET Województwa mazowieckiego — nie dodawać obu!
- **Pokrywa tylko 42.8%** account spend — reszta to PMax/YouTube/Display bez GEO

---

## 8. Google Maps Reviews (scraped via Playwright)

**Plik:** `muscat_google_reviews_full.json`
**Rekordów:** 3,563 opinii z 14 salonów
**Metoda:** Playwright headless Chrome, aggressive scrolling, expand "Więcej"

### Per salon:
| Salon | Rating | Reviews | Neg% |
|-------|--------|---------|------|
| Katowice | 4.9 | 475 | 3.4% |
| Lublin | 4.9 | 159 | 3.1% |
| Chmielna | 4.5 | 690 | 10.9% |
| Arkadia | 4.2 | 327 | 20.3% |

### Top skargi:
1. Obsługa klienta (38%)
2. Jakość badania (12%)
3. Jakość szkieł (10%)
4. Reklamacje (10%)
5. Cena (7%)

---

## 9. Perplexity API

**Token:** Przechowywany w zmiennej środowiskowej / pamięci Claude (nie commitować!)

### Użyte endpoints:
- **Search API:** `POST https://api.perplexity.ai/search` — competitive pricing
- **Agent API:** `POST https://api.perplexity.ai/v1/responses` — market research, purchase triggers
- **Embeddings API:** `POST https://api.perplexity.ai/v1/embeddings` — review embeddings (tested, base64 output)

### Wyniki:
- Ceny konkurencji: Kodano 1 PLN, Vision Express 149 PLN
- Purchase triggers: 51% zmiana recepty, 27% zniszczone okulary, 82% cena
- Polish optical market: $1.13B (2024), +9.7% CAGR
- Czarny Wrzesień: brak zewnętrznych czynników rynkowych

---

## 10. Cleora (graph embeddings)

**Biblioteka:** `pycleora` 3.2.1 (Rust-powered, CPU-only)
**Graf:** 87,700 edges, 30,983 nodes

### Edges:
- `client_{phone}` → `salon_{name}` (z bookings, matched)
- `client_{phone}` → `shop_{name}` (z orders, matched)

### Wyniki:
- 5 segmentów klientów (k-means na graph embeddings)
- VIP lookalikes: 3,001 VIP (LTV >2,293 PLN), 4,200 "sleeping VIP"
- Salon similarity network (shared clients between salons)
- Kraków Pawia ↔ Starowiślna: 439 wspólnych klientów!

---

## 11. GA4 (via GoMarble MCP)

**Property:** 354306770
**API:** `mcp__a8beb748...google_analytics_run_report`
**Dane:** Traffic declining 104K → 22K sessions/msc (-79%)

---

## 12. Ahrefs (via Ahrefs MCP)

**MCP:** `mcp__a3377b99...site-explorer-*`
**Domain:** muscat.pl
**DR:** 29
**Organic traffic:** 48K peak → 29K current (-40%)
**Brand search "muscat optyk":** 70/msc (vs Vision Express 33K/msc)
