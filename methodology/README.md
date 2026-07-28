# Methodology — detailed breakdown

*Companion to [the article](../index.html). The article's "How this was
done" note gives the short version; this is the long version — where the
data came from, exactly how it was cleaned and compared, and what the
analysis can't tell you. There's also a formatted version of this same page
at [`index.html`](index.html) (or the live site's `/methodology/`). The code
referenced throughout is in [`/code`](../code/).*

## 1. Data sources

Every series was retrieved directly from the issuing agency's own public
API — no scraping was involved in getting this specific data. Country
borders for the map are a separate, static public-domain file (no API).

| Source | Series | Coverage | Base year | Accessed | License |
|---|---|---|---|---|---|
| [Eurostat](https://ec.europa.eu/eurostat/databrowser/view/prc_hpi_a), House Price Index (`prc_hpi_a`) | House price index, 9 countries | 2015–2025 | 2015 = 100 | 2026-07-23 | Free reuse with attribution (Eurostat data policy) |
| [INE](https://www.ine.pt) — Statistics Portugal | New-housing construction cost index, Portugal | 2016–2025 | 2021 = 100 | 2026-07-23 | Free reuse with attribution (INE data policy) |
| [Natural Earth](https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json) / world-atlas | Country boundary polygons, 1:110m (map only, not part of the numeric analysis) | — | — | 2026-07-23 | Public domain |

Access method for the two statistical series:

- **Eurostat**: JSON-stat dissemination API, queried directly for all 9
  countries in a single request.
- **INE**: public JSON indicator API (`pindica.jsp`).

Both APIs are public, require no key, and are documented in full —
including the exact endpoints, query parameters, and how the right
indicator/dataset codes were found — in
[SCRAPING.md, §3.5–3.6](../SCRAPING.md#35-case-study--reverse-engineering-the-ine-statistics-portugal-api).
That document also covers a separate set of exercises in HTML parsing and
browser-automated scraping; those techniques were practiced on unrelated
example pages and were **not** used to obtain the Eurostat or INE data used
here.

## 2. Cleaning the raw files

Two small formatting problems had to be fixed before the numbers could be
compared, both handled in [`code/process_data.py`](../code/process_data.py):

- **Decimal commas.** INE's file uses Portuguese number formatting
  (`"95,02"` instead of `95.02`), so the value column is parsed as text and
  the comma replaced with a period before converting to a number.
- **Text dates.** INE's periods are written out as `"Dezembro de 2020"`; the
  four-digit year is pulled out with a regular expression rather than
  trying to parse the whole string as a date.

```python
# from process_data.py
df["year"] = df["period"].str.extract(r"(\d{4})").astype(int)
df["value"] = df["value"].str.replace(",", ".").astype(float)
```

## 3. Putting both series on the same scale

Eurostat's house-price index is published as 2015 = 100; INE's
construction-cost index is published as 2021 = 100. Comparing the raw
numbers would be meaningless, since they start from different baselines.
Both series are re-based so that **2020 = 100**, which makes the two
directly comparable as growth from the same starting point:

```
index[year] = raw_value[year] / raw_value[2020] * 100
```

This is done once per country for the price series, and once for
Portugal's cost series. Re-basing only changes the reference point — the
growth rate between any two years is identical whether it's computed on
the raw series or the re-based one.

## 4. Growth and CAGR

For each country's house-price index, and for Portugal's
construction-cost index, two numbers are computed over the 2020–2025
window:

- **Total growth**: `index_2025 − index_2020` (with `index_2020` always
  100 after re-basing).
- **Compound annual growth rate (CAGR)**, over the 5 years:
  `((index_2025 / index_2020) ** (1/5) − 1) * 100`.

Portugal's price/cost gap — the article's central number — is simply the
difference between the two re-based index values in the same year: a
house-price index of 171 against a construction-cost index of 133 in 2025
is a 38-point gap. That is a gap in *percentage points*, not a percentage —
the two are kept separate deliberately, since conflating them is an easy
way to overstate a result like this one.

## 5. Why Ireland is excluded

Nine countries have complete Eurostat house-price data through 2025, but
only eight are compared. Ireland's series was left out on editorial
grounds, not a data problem: its market crashed by more than half after
2008 and only recovered from that unusually low base, so its 2020–2025
growth rate reflects a different, incomparable trajectory rather than the
same dynamic playing out elsewhere. Ireland's raw data is still in
[`code/data/house_prices.csv`](../code/data/house_prices.csv) for anyone
who wants to include it.

## 6. What this analysis doesn't show

- A construction-cost index measures materials and labor. It excludes land
  price, developer margin, financing costs and taxes — all plausible
  contributors to the gap that this analysis can't separate out or
  quantify individually.
- Eurostat's house-price index covers new and existing homes together;
  INE's construction-cost index covers new housing only. Re-basing both to
  2020 = 100 makes their growth rates comparable — it doesn't make the two
  series measure the same thing.
- Portugal is the only country here with a construction-cost series
  reaching 2025, so the price-vs-cost comparison — the analysis's main
  finding — could only be run for Portugal. Whether Spain or the
  Netherlands show a similar gap between their own prices and costs isn't
  known from this data.
- Eight countries is not all of Europe — it's the set with a complete
  2015–2025 Eurostat series. Most of Eastern and Southern Europe besides
  Spain and Italy isn't represented.

**A note on the construction-cost cross-check mentioned in the article:**
INE's figure was checked against Eurostat's own, separately published
construction-cost series for Portugal, which uses a different methodology
and base year but overlaps through 2023 — the two agreed within 1.1
percentage points of cumulative growth. That comparison was done directly
on the two raw series rather than through a saved script, so it isn't
reproduced as code in this repository.

## 7. Reproducing it

Everything above runs from
[`code/process_data.py`](../code/process_data.py), which reads the CSVs in
`code/data/` and writes the cleaned, re-based tables back out as CSV. The
charts and map are built from those outputs by two further scripts:

```bash
cd code
pip install pandas
python process_data.py    # clean + re-base + growth/CAGR -> data/processed_*.csv
python make_charts.py     # -> ../assets/chart-*.svg
python make_map.py        # -> ../assets/map.html
```

No manual editing happens between steps. To try this on a different
country or period, swap the files in `code/data/` for an equivalent pair of
series and adjust the `YEARS` and `COUNTRY_NAMES` constants at the top of
`process_data.py`.

---

Companion page to [the article](../index.html). Code: [`/code`](../code/).
Data-collection write-up: [`SCRAPING.md`](../SCRAPING.md).
