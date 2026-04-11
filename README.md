# Muscat Badania Dashboard v4.4

> **Holistyczna analiza biznesowa sieci salonów optycznych Muscat.pl**
> Dashboard łączy 12+ źródeł danych w jeden interaktywny panel z 6 tabami, 40+ wykresami, i actionable insightami marketingowymi.

**LIVE:** https://muscat-badania-dashboard.vercel.app
**Hasło:** `muscat2026`
**Repo:** https://github.com/marketinghacker/muscat-badania-dashboard

---

## Szybki start (nowa sesja Claude Code)

```bash
cd /Users/marcinmichalski/Downloads

# 1. Regeneruj dashboard (Python przetwarza dane → generuje HTML)
python3 muscat_prep_data.py

# 2. Skopiuj do repo deploymentu
cp muscat_badania_dashboard.html muscat-badania-dashboard/index.html

# 3. Deploy
cd muscat-badania-dashboard
git add index.html && git commit -m "Update dashboard" 
PATH="/opt/homebrew/bin:$PATH" git push origin main
PATH="/opt/homebrew/bin:$PATH" npx vercel --yes --prod
```

### Kluczowe pliki

| Plik | Lokalizacja | Rola |
|------|-------------|------|
| `muscat_prep_data.py` | `/Users/marcinmichalski/Downloads/` | **GŁÓWNY SKRYPT** — ładuje dane, przetwarza, generuje HTML |
| `index.html` | `muscat-badania-dashboard/` | Wygenerowany dashboard (deploy na Vercel) |
| `regional.html` | `muscat-badania-dashboard/` | Stara strona regionalna (legacy, dane wchłonięte do index) |
| `cleora.html` | `muscat-badania-dashboard/` | Stara strona Cleora (legacy, dane wchłonięte do index) |

### Pliki danych (w `/Users/marcinmichalski/Downloads/`)

| Plik | Typ | Zawartość | Rozmiar |
|------|-----|-----------|---------|
| `badania_wg_daty_zapisu_2026-04-03T16_20_05.275751827Z.xlsx` | xlsx | **87,975 bookings** (Jan 2023–Mar 2026, ALL sources) | ~5MB |
| `Zamówienia_Muscat_Nr_Telefonów - Export.csv` | csv | **139,968 orders** z numerami telefonów | 14MB |
| `Średni koszyk okularowy po latach.xlsx` | xlsx | AOV per salon per rok (2022-2026) | 4KB |
| `data (10).xlsx` | xlsx | Lens volume per salon per miesiąc | 5KB |
| `Konwersje (2).csv` | csv | Google Ads GEO raport (regiony PL) | ~10MB |
| `Muscat_analiza_geo/muscat_v3_clean_orders.csv` | csv | Orders z postal codes (134K) | 19MB |
| `muscat_google_reviews_full.json` | json | 3,563 opinii Google Maps (14 salonów) | 1.2MB |
| `muscat_cpa_extrapolated.json` | json | CPA per miasto (ekstrapolowane) | 80KB |
| `muscat_cpa_corrected.json` | json | CPA per miasto (zweryfikowane z API) | 5KB |
| `muscat_cleora_results.json` | json | Wyniki Cleora (segmenty, VIP) | 3KB |
| `muscat_scaling_lever.json` | json | Dźwignia skalowania (rev/zapis, CPA, headroom) | 2KB |
| `muscat_black_september.json` | json | Diagnoza Czarnego Września 2025 | 5KB |
| `meta_perfo_regional_full.json` | json | Meta Ads spend per region per miesiąc (36 msc) | 80KB |
| `google_ads_regional.json` | json | Google Ads spend per region per miesiąc (39 msc) | 30KB |

---

## Architektura

Patrz: [ARCHITECTURE.md](ARCHITECTURE.md)

## Źródła danych

Patrz: [DATA_SOURCES.md](DATA_SOURCES.md)

## Metodologia

Patrz: [METHODOLOGY.md](METHODOLOGY.md)

## Kontekst biznesowy

Patrz: [BUSINESS_CONTEXT.md](BUSINESS_CONTEXT.md)

---

## Kontakt

- **Agencja:** Marketing Hackers (Marcin Michalski)
- **Klient:** Muscat.pl (sieć salonów optycznych)
- **Cel:** 2x więcej zapisów na badania wzroku → więcej sprzedaży okularów
