# Metodologia — Muscat Dashboard

## 1. CPA per miasto

### Źródła:
- **Meta Ads:** API `breakdowns=["region"]` → voivodeship spend per month
- **Google Ads:** GAQL `geographic_view` per city/region, `LOCATION_OF_PRESENCE`

### Problem multi-region attribution (Meta):
Meta regional breakdown sumuje do **135% account total** bo jeden user może być przypisany do wielu regionów (podróże, VPN). Normalizujemy: `raw × 0.738 = account total`.

### Problem Google GEO coverage:
- GAQL API: **82.9%** account spend zamapowane na miasta
- CSV export: tylko **42.8%** (nie widzi PMax!)
- **17.1% unmapped** = kampanie bez geo targetowania, YouTube/Display

### CPA obliczanie:
```
CPA per miasto = (Meta normalized spend + Google API spend) / total bookings per miasto
```
**UWAGA:** To jest "koszt reklamowy per zapis", NIE "per ad-attributed conversion". 87,975 bookings = WSZYSTKIE zapisy (nie tylko z reklam).

### Account-level CPA (jedyna 100% pewna cyfra):
```
Total ad spend (Meta + Google): 2,273,308 PLN
Total bookings: 87,975
Account CPA: 25.8 PLN
```

### Audyt statystyczny (korelacja spend→bookings per miasto):
- Metoda: First-differenced Pearson r + Bonferroni correction (9 testów, próg p<0.006)
- Durbin-Watson: potwierdza brak autokorelacji na danych zróżnicowanych
- Wynik: **7/9 miast istotna korelacja** (Lublin i Szczecin nie przechodzą Bonferroni)
- **UWAGA:** Korelacja ≠ przyczynowość. Platformy kierują spend tam gdzie jest popyt.

---

## 2. Booking ↔ Order matching (MD5)

### Odkrycie:
`client_id` w bookings = `hashlib.md5(phone.encode()).hexdigest()`

### Weryfikacja:
```python
# Brute force: hash ALL order phones → check overlap z booking hashes
for phone in orders['phone']:
    for fmt in [phone, phone.lstrip('48'), '+48'+phone.lstrip('48')]:
        hash = hashlib.md5(fmt.encode()).hexdigest()
        if hash in booking_client_ids: MATCH!
```
- **30,949 hashów się matchuje = 46,301 bookings (52.6%)**

### Wyniki z matchu:
- Klienci z badaniem: AOV 925 PLN vs bez badania: 744 PLN (+24.3%)
- Revenue per done booking: 1,075 PLN
- Mean LTV: 1,230 PLN, Top 1%: 4,288 PLN
- Booking→purchase conversion (matched, same year): 90-95%

---

## 3. Scaling lever (dźwignia skalowania)

### Obliczanie rev/zapis:
```
Per year: revenue from matched booking clients / total bookings
2023: 8.1M / 26,754 = 304 PLN
2024: 9.6M / 27,167 = 354 PLN
2025: 13.0M / 26,511 = 491 PLN
2026 forecast: 491 × (1 + CAGR 27%) = 624 PLN
```

### Headroom:
```
Breakeven CPA = rev/zapis × done_rate = 624 × 0.675 = 421 PLN
Current CPA = 40 PLN (2025)
Headroom = 421 - 40 = 381 PLN per zapis
```

---

## 4. Czarny Wrzesień 2025

### Metoda: Cross-data diagnosis
Porównanie 7 źródeł danych dla Aug vs Sep vs Oct 2025:
1. Bookings per salon, per source, per status
2. Meta Ads campaign-level spend (BTS wyłączone)
3. Google Ads campaign-level spend
4. Meta CPM/CPC trends
5. Perplexity market research (brak zewnętrznych czynników)
6. Google brand search volume
7. Seasonality pattern (2023-2024-2025)

### Kluczowy fakt:
BTS kampanie kończą się co roku we wrześniu — ale spadek -20.5% YoY był TYLKO w 2025. Dlatego BTS NIE jest główną przyczyną.

### 5 współgrających czynników:
1. Zamknięcie Stawowej (-31 bookings netto, 5%)
2. Meta CPM +40% vs 2023 (kumulatywna inflacja)
3. Organic traffic na historycznym minimum
4. Brand search -14% we wrześniu
5. Sezonowość wzmocniona innymi czynnikami

---

## 5. Cleora graph embeddings

### Graf:
```python
from pycleora import SparseMatrix, embed
edges = [f"client_{phone} salon_{pos}" for matched bookings]
         + [f"client_{phone} shop_{team}" for matched orders]
graph = SparseMatrix.from_iterator(iter(edges), "complex::reflexive::entity")
embeddings = embed(graph, feature_dim=256)
```

### Segmentacja (k-means, k=5):
- Segment 0: Poznań/Katowice/Wrocław cluster (780 klientów)
- Segment 1: Warszawa Targowa cluster (2,651)
- Segment 2: Katowice dominant (4,268)
- Segment 3: Mixed metro (647)
- Segment 4: Core network (21,654)

### VIP lookalikes:
- VIP threshold: LTV > 2,293 PLN (top 10%)
- Centroid VIP → cosine similarity z non-VIP pool
- "Sleeping VIP" = high similarity but 1 purchase

---

## 6. Salon capacity

### Założenia:
- 20 badań/dzień × 26 dni roboczych = 520 badań/msc MAX
- Target: 60% = 312 badań/msc
- Current network: ~26% capacity (2,300/msc vs 5,304 target)

---

## 7. Google Maps Reviews

### Metoda scrape:
- Playwright headless Chrome, locale='pl-PL'
- Google Maps search per salon → click result → click reviews tab
- Aggressive scrolling (250 scrolls max, stale detection)
- Expand "Więcej" buttons
- Extract: author, stars (aria-label), date, text

### Sentiment analysis:
- Polish keywords: obsługa, reklamacja, cena, wad, szkła, etc.
- Per-salon negative % = (1-2 stars) / total reviews
- Relative dates parsed: "2 miesiące temu" → approximate YYYY-MM

---

## Ograniczenia i caveats

1. **Retencja 35% to artefakt** — dane od 2023, Muscat istnieje od 2015
2. **CPA = ad cost per total booking, nie per conversion** — 87K to WSZYSTKIE zapisy
3. **Meta regional = 135% konta** — normalizacja ×0.738 jest przybliżona
4. **Google GEO = 82.9% coverage** — 17.1% unmapped
5. **City ID mapping = niepewny** — ten sam ID w różnych regionach
6. **Cleora segmenty = exploratory** — nie zwalidowane przez A/B test
7. **Forecast = model liniowy** — nie uwzględnia zmian w sieci salonów
8. **Google Maps reviews daty = przybliżone** — "2 miesiące temu" ≈ ±2 tygodnie
