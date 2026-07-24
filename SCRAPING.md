# Web Scraping & Public Data APIs — Project Report

*This document describes the separate project that collected the raw data
used in this repository (`code/data/house_prices.csv` and
`code/data/construction_cost_pt.csv` come from it). It was a hands-on
exercise covering the main ways to get data out of the web — from parsing
static HTML to querying official statistical APIs — kept here so the full
path from data collection to the published article is documented in one
place.*

*Note on the numbers below: the mini case study in §4 of this report used a
wider scope (2015–2025, ten countries) than the article in this repository,
which narrows the same underlying Eurostat/INE data to a tighter, more
recent window (2020–2025, eight countries — Ireland excluded, see the main
[README](README.md)). Both are legitimate reads of the same source data;
they just answer slightly different questions.*

---

A hands-on project exploring the main approaches to extracting data from the
web, from parsing static HTML to querying official statistical APIs. It was
built incrementally as a series of exercises, each one adding a different
data-access technique and a real, working example against a live public
source.

## 1. Objective

The goal was to cover the full spectrum of techniques used to programmatically
retrieve data from the web, and to apply them against real, publicly available
sources rather than toy pages only. Concretely, the project:

1. Implements the four standard scraping techniques: static HTML parsing,
   browser-driven dynamic scraping, large-scale crawling with a scraping
   framework, and API consumption.
2. Uses those techniques to retrieve real statistical data from national and
   international organisations (Portugal's statistics office, the World Bank,
   the UN, NASA, the EU open data portal, Eurostat).
3. Runs a small comparative case study — construction costs and house prices,
   for Portugal and for nine other European countries — as a demonstration
   that the collected data is actually usable for analysis, not just raw JSON
   dumps.

## 2. Project Structure

```
WebScraping/
├── static_scraping/          # HTML parsing without a browser
│   └── example.py
├── dynamic_scraping/          # JavaScript-rendered pages
│   ├── selenium/example.py
│   └── playwright/example.py
├── scrapy_projects/            # Framework-based crawling
│   └── example_quotes/
├── api_scraping/               # Public/official JSON & SDMX APIs
│   ├── world_bank.py
│   ├── un_data.py
│   ├── nasa_earthdata.py
│   ├── eu_open_data.py
│   ├── ine.py
│   ├── ine_construcao_habitacao.py
│   └── eurostat_housing_construction.py
├── utils/                       # Shared helpers (User-Agent rotation)
├── data/                         # CSV/JSON output of the scripts
├── requirements.txt
└── venv/
```

Each subfolder corresponds to a distinct extraction technique, and every
script in it is a small, self-contained, runnable example against a real
endpoint — not a mock.

## 3. Methodology

### 3.1 Static scraping (`static_scraping/`)

For pages that render fully server-side, an HTTP GET request already returns
the complete HTML, so no browser is required. The process was:

1. Send a `GET` request with `requests`.
2. Parse the returned HTML with `BeautifulSoup` (backed by the `lxml` parser
   for speed).
3. Select the target elements with CSS selectors and extract their text.

This is the cheapest and fastest technique, and was used as the baseline
example (`quotes.toscrape.com`).

### 3.2 Dynamic scraping (`dynamic_scraping/`)

Some pages only populate their content client-side via JavaScript after the
initial HTML has loaded, so a plain HTTP request would return an (almost)
empty page. Two different automated-browser approaches were implemented and
compared:

- **Selenium** — drives a real Chrome instance through `webdriver-manager`
  (which downloads and manages the matching ChromeDriver binary
  automatically), runs it headless, waits for the page to render, and then
  queries the DOM through `find_elements`.
- **Playwright** — a more modern alternative to Selenium, using its own
  bundled Chromium build (installed via `playwright install chromium`). It
  offers a simpler async-friendly API and generally faster, more reliable
  execution than Selenium.

Both scripts target the same JavaScript-rendered page
(`quotes.toscrape.com/js/`) so the two approaches can be directly compared.

### 3.3 Framework-based crawling (`scrapy_projects/`)

For crawling *many* pages (pagination, following links, structured output
pipelines) a dedicated framework is more appropriate than hand-rolled
requests loops. A standard Scrapy project was generated
(`scrapy startproject`) and a spider (`quotes.py`) was written that:

1. Parses the listing page with Scrapy's built-in CSS selectors.
2. Yields one structured item per quote.
3. Follows the "next page" link recursively until pagination ends.
4. Exports the aggregated result directly to JSON (`scrapy crawl quotes -o
   data/quotes.json`) — Scrapy handles concurrency, retries, and
   `robots.txt` compliance out of the box.

### 3.4 API-based access (`api_scraping/`)

Whenever a source exposes its data through a documented (or discoverable)
API, that is strictly preferable to parsing HTML: it is faster, more
stable, and does not depend on the page's visual markup. This was the bulk
of the project's effort, and the *process of finding and reverse-engineering
each API* is the most transferable skill it produced. The general recipe
that was followed for every source below:

1. **Look for official API documentation first** (a link in the site's
   footer, a `/developers` or `/api` page). When it existed, it was fetched
   and read before writing any code, rather than guessing endpoint shapes.
2. **Probe the endpoint directly with `curl`** to inspect the real response
   shape (status code, JSON structure, required parameters) before writing
   any Python. Several of these APIs return errors that are only meaningful
   once you've made a first "wrong" request — e.g. an indicator API that
   tells you *which* dimension code was invalid — so this trial step was
   essential.
3. **Only then write a small Python client** around the confirmed
   contract (`requests.get` + parameter dict + typed helper functions),
   instead of one throwaway script per query.
4. **Re-verify by actually running it** against the live endpoint and
   printing real values, not by trusting the code to "look correct".

The sources integrated this way:

| Script | Source | What it returns | Access pattern |
|---|---|---|---|
| `world_bank.py` | [World Bank Open Data](https://data.worldbank.org) | Economic/social indicators by country and year | Plain REST + JSON, well documented publicly |
| `un_data.py` | [UNdata](https://data.un.org/ws) (SDMX 2.1) | UN, WHO, UNESCO, World Bank statistical series | SDMX-JSON; discovered via the service's self-describing root page, which lists its own REST endpoints and Swagger docs |
| `nasa_earthdata.py` | [NASA Earthdata CMR](https://www.earthdata.nasa.gov) | Metadata for Earth-observation datasets and files (granules) | Common Metadata Repository REST API, no auth required for search |
| `eu_open_data.py` | [data.europa.eu](https://data.europa.eu) | Dataset search across the EU open-data catalogue | The portal's public Hub Search API |
| `ine.py` | [INE](https://www.ine.pt) — Statistics Portugal | Any official indicator (population, prices, etc.) | See §3.5 — endpoint reverse-engineered from the site itself |
| `eurostat_housing_construction.py` | [Eurostat](https://ec.europa.eu/eurostat) | House price index & construction cost index, per EU country | JSON-stat 2.0 dissemination API — see §3.6 |

### 3.5 Case study — reverse-engineering the INE (Statistics Portugal) API

INE does not put its API front and centre, but it is fully public. The
discovery path was:

1. Starting from the institutional homepage, a footer link ("Resources —
   Services, Feeds and API's") led to a page listing the SOAP/SDMX
   endpoints and, more usefully, a RESTful JSON endpoint:
   `pindica.jsp` (data) and `pindicaMeta.jsp` (metadata), under
   `https://www.ine.pt/ine/json_indicador/`.
2. The official usage page documents the query contract:
   `?op=2&varcd={indicator_code}&Dim1={period_code}&Dim2={dimension_code}...&lang=PT`,
   including advanced features (requesting *all* periods with `Dim1=T`,
   comma-separated period lists, wildcard dimension matches).
3. Each indicator has its **own** set of dimensions (time period, region,
   sex, age group, production factor, ...), each with its **own** category
   codes — there is no universal schema. So before querying any indicator's
   data, its metadata endpoint (`pindicaMeta.jsp`) had to be called first to
   read the valid dimension codes (e.g. period codes look like `S7A2022` for
   an annual series but `S3A202212` for a monthly one, geography codes are
   `PT` for the whole country, `T` means "total" for a categorical
   dimension, etc.).
4. Because INE does not expose a full-text indicator search through this
   API, relevant indicator codes were found by using the *website's own
   search box* (`ine_pesquisa`) with domain keywords (e.g. "índice de custo
   da construção"), parsing the resulting HTML links for their
   `indOcorrCod` (indicator code) parameter, and then confirming each
   candidate's real content and time coverage via its metadata endpoint.
5. This let the project retrieve two real indicators end-to-end:
   the *New housing construction cost index* (updated monthly, base 2021)
   and the *median transaction value per m² of dwellings sold*. The latter
   turned out to have been **discontinued by INE in Q3 2021** — a good
   example of why step 2 (probing before assuming) matters: a naive script
   would have silently returned stale data without that being obvious.

### 3.6 Case study — Eurostat's JSON-stat API for cross-country comparison

INE only covers Portugal, so a second, harmonised source was needed to
compare countries. Eurostat publishes the same indicators, using the same
schema, for every EU member state:

1. The dissemination API (`ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset_code}`)
   returns data in the **JSON-stat 2.0** format: values are stored in a
   flat, dictionary, addressed by a single integer index that encodes the
   position along *every* dimension at once (rather than nested JSON).
2. The relevant dataset codes (`prc_hpi_a` for the House Price Index,
   `sts_copi_a` for construction producer prices/costs) were found by
   querying the API with a guessed-but-documented-style code and inspecting
   the `dimension` section of the response, which self-describes every
   valid category for every dimension (e.g. discovering that the price
   index needed `unit=I15_A_AVG`, not an invented unit code, by requesting
   the dataset without a unit filter and reading which unit codes actually
   exist).
3. A small generic **JSON-stat decoder** was written
   (`_decode` in `eurostat_housing_construction.py`): it computes, from the
   `size` array, the positional multiplier for each dimension, then walks
   every key in `value` back to its `(country, year)` coordinate. This one
   function is reusable for *any* Eurostat dataset, not just these two.
4. Ten countries (Portugal, Spain, France, Germany, Italy, Netherlands,
   Ireland, Greece, Austria, Belgium) were queried in a single request per
   dataset (Eurostat accepts repeated `geo=` query parameters), rather than
   one request per country, to minimise API calls.

## 4. Results — comparative mini case study

Using the two case-study scripts above, house prices and construction costs
(both indexed to 2015=100) were compared:

- **Portugal** shows by far the steepest rise in house prices among the
  ten countries analysed (+164% between 2015 and 2025), while its
  construction-cost growth (+37% between 2015 and 2023) is in line with
  the rest of the sample.
- **Germany** and **France** show house prices *retreating* from their
  2021/2022 peak, unlike Portugal, Ireland or the Netherlands, where growth
  continued through 2025.
- **Italy** stands out with an essentially flat house price index over the
  full decade.
- Construction costs rose far more homogeneously across countries
  (roughly +20% to +37%) than sale prices did — suggesting the divergence
  in house prices is driven more by demand/market factors than by the
  underlying cost of building.

Full data (all years, all countries) is available as CSV in `data/`:
`ine_indice_custo_construcao.csv`, `ine_preco_habitacao.csv`,
`eurostat_preco_habitacao.csv`, `eurostat_custo_construcao.csv`.

## 5. Setup

```bash
git clone <this-repo-url>
cd WebScraping
python3 -m venv venv
source venv/bin/activate           # venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium        # only needed for dynamic_scraping/playwright
```

## 6. Running the examples

```bash
# Static scraping
python static_scraping/example.py

# Dynamic scraping
python dynamic_scraping/selenium/example.py
python dynamic_scraping/playwright/example.py

# Scrapy crawler
cd scrapy_projects/example_quotes
scrapy crawl quotes -o ../../data/quotes.json
cd ../..

# API-based access
python api_scraping/example.py
python api_scraping/world_bank.py
python api_scraping/un_data.py
python api_scraping/nasa_earthdata.py
python api_scraping/eu_open_data.py
python api_scraping/ine.py

# Case studies
python api_scraping/ine_construcao_habitacao.py
python api_scraping/eurostat_housing_construction.py
```

## 7. Tools & Technologies

| Purpose | Library |
|---|---|
| HTTP requests | `requests` |
| HTML parsing | `beautifulsoup4`, `lxml` |
| Browser automation | `selenium`, `webdriver-manager`, `playwright` |
| Large-scale crawling | `scrapy` |
| Data handling | `pandas` |
| Misc. | `fake-useragent`, `python-dotenv` |

## 8. Good practices followed

- Every scraper checks the target site's public documentation or
  `robots.txt` before extraction; no authentication bypass or paywall
  circumvention was attempted anywhere in the project.
- API endpoints were always preferred over HTML parsing when a real one
  existed, for stability and to minimise unnecessary load on the source's
  servers.
- Requests use conservative timeouts and no concurrent hammering of any
  single host; the Scrapy spider relies on the framework's built-in
  auto-throttling instead of a custom retry loop.
- All example scripts query small, publicly documented endpoints and do
  not scrape personal or sensitive data.

## 9. Conclusion

The project demonstrates that "web scraping" is not a single technique but
a spectrum, and that the right choice depends entirely on what the target
exposes: parse HTML only when there is no alternative, prefer a documented
API when one exists, and when it doesn't, treat the site's own search and
error responses as a way to reverse-engineer one. The two closing case
studies (INE and Eurostat) show that this process scales from a single
country's statistics office to a fully harmonised, multi-country data
source, and that the resulting data is directly usable for a real
comparative analysis rather than just a proof of concept.
