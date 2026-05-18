# Indoscraping — Developer & Agent Guide

Welcome to the modernized **Indoscraping** developer manual. This document guides developers and autonomous agents on how to execute, maintain, and expand the scraper suite.

---

## 1. Unified Scraper CLI Dashboard (`indoscraping`)

We have introduced a powerful, visual command-line interface dashboard built with `rich` that unifies all Node.js and Python scrapers.

### Running the Dashboard
To launch the interactive visual terminal menu:
```bash
# Via uv
uv run indoscraping

# Via npm script
npm run list:scrapers
```

### Direct CLI Commands (Automation / CRONs)
You can invoke specific commands non-interactively for headless execution, scripting, or automated schedulers:

```bash
# 1. List all available scrapers and their storage statuses
uv run indoscraping list

# 2. View data volume stats, file formats, and last-modified dates
uv run indoscraping status

# 3. Execute a specific scraper directly
uv run indoscraping run <scraper_id> [optional_arguments]

# 4. Batch execute multiple scrapers sequentially
uv run indoscraping run-all [--category <category>] [--limit-categories <N>] [--limit-articles <M>]

# Examples:
uv run indoscraping run cnbc --limit-categories 1 --limit-articles 3
uv run indoscraping run detik --limit-articles 5
uv run indoscraping run-all --category news
uv run indoscraping run-all --category finance
uv run indoscraping run-all --limit-articles 1 --limit-categories 1
```

---

## 2. Environment & Tooling

- **Python Env Manager (`uv`)**: We use `uv` for lightning-fast environment and package management.
  - Run `uv sync` to restore environments.
  - Run `uv add <pkg>` to install new packages (e.g. `curl-cffi`, `rich`, `BeautifulSoup4`).
- **Node.js**: Required for retail scrapers. Execute `npm install` in the workspace root if needed.
- **Playwright Bypass**: For bank rates and Blibli search scrapers, ensure the environment variable `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` is passed to rely on system-installed Chromium.

---

## 3. Standardized Output & History Layout

Scraped files are systematically directed to the standardized `data/` folder directory. Each scraper outputs both a `latest.json` for rapid dashboard access and a chronologically dated snapshot for historical delta checks.

```
data/
├── news/
│   ├── detik/latest.json & history/YYYY-MM-DD.json
│   ├── bisnis/latest.json & history/YYYY-MM-DD.json
│   ├── cnbc/latest.json & history/YYYY-MM-DD.json
│   ├── cnn/latest.json & history/YYYY-MM-DD.json
│   ├── kompas/latest.json & history/YYYY-MM-DD.json
│   └── narasi/latest.json & history/YYYY-MM-DD.json
├── retail/
│   ├── alfagift/latest.json & history/YYYY-MM-DD.json
│   └── indomaret/latest.json & history/YYYY-MM-DD.json
└── latest.json (Finance banks scraper outputs)
```

---

## 4. News Scrapers Parameters Signature

All news crawlers accept standard argparse parameter structures for dynamic overrides:
- `--date`: The crawl date to extract. Automatically defaults to today's date (or yesterday's date depending on scraper target timezone).
- `--limit-categories`: Limits number of category sectors crawled (default: 1).
- `--limit-articles`: Limits items scraped per category (perfect for rapid smoke testing).
- `--output`: Redirects the final output destination.

---

## 5. Directory & Scraper Code Map

- **Interactive CLI Core**: [src/indoscraping/cli.py](file:///home/al/Projects/indoscraping/src/indoscraping/cli.py)
- **News Scrapers**: [src/indoscraping/scraper/news/](file:///home/al/Projects/indoscraping/src/indoscraping/scraper/news/)
  - `kompas.py` — Beautifulsoup4 crawler, parses indices.
  - `detik.py` — Handles general indices.
  - `cnbcindonesia.py` — High-performance crawler using `ThreadPoolExecutor`.
  - `cnnindonesia.py` — Standard BS4 parser.
  - `bisnis.py` — Extracts business indices.
  - `narasi.py` — **High-performance API scraper using `curl_cffi` to mimic Google Chrome handshakes.**
- **Finance Scrapers**: [src/indoscraping/scraper/finance/](file:///home/al/Projects/indoscraping/src/indoscraping/scraper/finance/)
  - Uses `BaseScraper` class, custom models (`models.py`), and executes rate crawls via Playwright.
- **Retail Scrapers**: [src/indoscraping/scraper/retail/](file:///home/al/Projects/indoscraping/src/indoscraping/scraper/retail/)
  - `alfagift/index.mjs` — Scrapes Alfamart API.
  - `indomaret/index.mjs` — Scrapes KlikIndomaret API.
  - `blibli/` — Playwright search results and Python category scrapers.
  - `tokopedia/` — Selenium/Undetected Chromedriver category crawlers.