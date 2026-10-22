# Indoscraping

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Go Version](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=for-the-badge&logo=go&logoColor=white)](README_GO.md)
[![Env Manager](https://img.shields.io/badge/uv-astral-blueviolet?style=for-the-badge&logo=python&logoColor=white)](https://github.com/astral-sh/uv)
[![License](https://img.shields.io/badge/License-ISC-orange?style=for-the-badge)](https://opensource.org/licenses/ISC)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=for-the-badge&logo=ruff)](https://github.com/astral-sh/ruff)

**A premium, unified collection of web scrapers designed to extract news, e-commerce products (Tokopedia, Blibli, Alfagift, Klik Indomaret), and real estate property data (Jendela360, SewaKost) from prominent Indonesian web portals. Driven by a visual terminal CLI dashboard.**

</div>

> [!IMPORTANT]
> This repository is intended strictly for educational and academic research purposes. Please scrape responsibly, adhere to rate limits, and respect each target website's Terms of Service and `robots.txt` policy.

---

## 🚀 Key Features

*   **Dual-Engine Architecture (Python + Go)**: Alongside the Python rich TUI dashboard, includes a native Go CLI (`bin/indoscraping`) with managed goroutine semaphore concurrency, Chrome CDP integration, and CSV export pipeline. See [README_GO.md](README_GO.md).
*   **Unified Visual CLI Dashboard**: Discover, monitor, and run all scrapers from a single, interactive, colorized terminal screen built with `rich`.
*   **Standardized Database Layout**: Systematic and clean data organization under `data/`, automatically splitting `latest.json` for rapid dashboard access and dated snapshots inside `history/YYYY-MM-DD.json` for historical delta tracking.
*   **Highly Configurable News Crawlers**: Parameterized Python crawlers supporting dynamic target dates (`--date`), category limit overrides (`--limit-categories`), and item quotas (`--limit-articles`).
*   **Anti-Blocking Mimicry**: Emulates Google Chrome TLS handshakes using `curl_cffi` (for e-commerce and investigatory APIs) and utilizes stealthy system browser launches via Playwright to bypass common bot defenses.

---

## 🛠️ Installation & Setup

This project leverages [uv](https://github.com/astral-sh/uv) for lightning-fast Python dependency management and environment routing.

### Prerequisites

> [!NOTE]
> Ensure you have **[uv](https://github.com/astral-sh/uv)** installed globally on your host system.

### Setup Commands

```bash
# Setup the virtual environment and restore all core Python dependencies
uv sync

# Optional: Install OCR extra for Indomaret nutrition label vision processing
uv sync --extra ocr
```

---

## 💻 Usage

We provide a visual CLI dashboard named `indoscraping` to manage the scraper suite interactively or run scrapers headlessly.

### 1. Interactive Visual Dashboard

To launch the premium interactive terminal menu to explore and execute scrapers:
```bash
# Launch via uv
uv run indoscraping
```

### 2. Status & Volume Metrics

Check crawled data sizes, file formats, and last-modified dates across your local datasets:
```bash
uv run indoscraping status
```

### 3. Headless CLI Execution (Automation & CRONs)

Execute individual scrapers directly without the interactive dashboard (perfect for headless environments and scheduled CRON scripts):
```bash
# List all available scraper keys
uv run indoscraping list

# Inspect scraped data preview in terminal
uv run indoscraping inspect sewakost
uv run indoscraping inspect narasi

# Run a news scraper with options
uv run indoscraping run cnbc
uv run indoscraping run detik --limit-articles 5
uv run indoscraping run bisnis --limit-articles 2
uv run indoscraping run narasi --limit-articles 3 --date 2026-05-18

# Run e-commerce API scrapers
uv run indoscraping run alfagift
uv run indoscraping run indomaret

# Run real estate & kost scrapers (Rumah123, SewaKost, Jendela360)
uv run indoscraping run rumah123 --limit-articles 5 --deal-type jual --category rumah
uv run indoscraping run sewakost --limit-articles 2
uv run indoscraping run sewakost --area jakarta/jakarta-barat/palmerah --max-pages 2
uv run indoscraping run jendela360 --limit-pages 5 --category apartment --deal-type rent

# Batch run scrapers by category
uv run indoscraping run-all --category property --limit-articles 2
uv run indoscraping run-all --category news --limit-articles 1

# Export scraped datasets to Parquet or CSV for analytics (DuckDB, Pandas)
uv run indoscraping export rumah123 --format parquet
uv run indoscraping export sewakost --format csv
```

---

## 📰 News Scrapers Parameters Signature

All news crawlers accept a standard CLI interface for runtime overrides:
- `--date`: The target crawl date to extract. Automatically defaults to today's date.
- `--limit-categories`: Limits the number of category sectors scanned (default: 1).
- `--limit-articles`: Limits items scraped per category (perfect for rapid smoke testing).
- `--output`: Redirects the output file path.

---

## 🔍 Scraper Directory & Standalone Packages (SEO Index)

For users searching for site-specific scrapers, individual packages are published standalone and can be installed independently or run via the central `indoscraping` visual CLI:

| Target Site / Search Query | Package Name | Standalone CLI | Module Path |
| :--- | :--- | :--- | :--- |
| **Blibli Scraper** (`blibli-scraper`) | `blibli-scraper` | `blibli-scraper` | `packages/blibli-scraper` |
| **Tokopedia Scraper** (`tokopedia-scraper`) | `tokopedia-scraper` | `tokopedia-scraper` | `packages/tokopedia-scraper` |
| **Alfagift Scraper** (`alfagift-scraper`) | `alfagift-scraper` | `alfagift-scraper` | `packages/alfagift-scraper` |
| **Klik Indomaret Scraper** (`indomaret-scraper`) | `indomaret-scraper` | `indomaret-scraper` | `packages/indomaret-scraper` |
| **Rumah123 Property Scraper** | `indoscraping` | `indoscraping run rumah123` | `src/indoscraping/scraper/property/rumah123.py` |
| **Jendela360 Property Scraper** | `indoscraping` | `indoscraping run jendela360` | `src/indoscraping/scraper/property/jendela360.py` |
| **SewaKost Boarding House Scraper** | `indoscraping` | `indoscraping run sewakost` | `src/indoscraping/scraper/property/sewakost.py` |
| **IDX BEI Stock Scraper** | `idx-bei` | `idx-bei` | External Repository |
| **Detik.com News Scraper** | `indoscraping` | `indoscraping run detik` | `src/indoscraping/scraper/news/detik.py` |
| **Bisnis.com Scraper** | `indoscraping` | `indoscraping run bisnis` | `src/indoscraping/scraper/news/bisnis.py` |
| **CNBC Indonesia Scraper** | `indoscraping` | `indoscraping run cnbc` | `src/indoscraping/scraper/news/cnbc.py` |
| **CNN Indonesia Scraper** | `indoscraping` | `indoscraping run cnn` | `src/indoscraping/scraper/news/cnn.py` |
| **Kompas.com Scraper** | `indoscraping` | `indoscraping run kompas` | `src/indoscraping/scraper/news/kompas.py` |
| **Narasi.tv Scraper** | `indoscraping` | `indoscraping run narasi` | `src/indoscraping/scraper/news/narasi.py` |

---

## 🏛️ Modular Workspace Architecture (`uv workspace`)

This repository is structured as a **`uv` Workspace** to balance high discoverability with zero code duplication:

```
indoscraping/
├── pyproject.toml               # Root Workspace Configuration
├── packages/
│   ├── indoscraping-core/       # Core Engine: Data Quality (dq.py), Lineage & Atomic Output
│   ├── blibli-scraper/          # Standalone Blibli Search & Category Scraper Package
│   ├── tokopedia-scraper/       # Standalone Tokopedia Catalog & Category Scraper Package
│   ├── alfagift-scraper/        # Standalone Alfamart Alfagift Catalog Scraper Package
│   └── indomaret-scraper/       # Standalone Klik Indomaret Catalog Scraper Package
├── src/indoscraping/            # Centralized Visual CLI Dashboard (`rich` UI)
└── docs/
    └── STANDALONE_REPOS.md      # Standalone GitHub Repository Mirror Guide
```

### Standalone Package Installation
```bash
# Install individual e-commerce scrapers standalone
pip install blibli-scraper
pip install tokopedia-scraper
pip install alfagift-scraper
pip install indomaret-scraper
pip install indoscraping-core
```

---

## 📂 Standardized Data Map

All scraped files systematically save into the following directory tree:
```
data/
├── news/
│   ├── detik/latest.json & history/YYYY-MM-DD.json
│   ├── bisnis/latest.json & history/YYYY-MM-DD.json
│   ├── cnbc/latest.json & history/YYYY-MM-DD.json
│   ├── cnn/latest.json & history/YYYY-MM-DD.json
│   ├── kompas/latest.json & history/YYYY-MM-DD.json
│   └── narasi/latest.json & history/YYYY-MM-DD.json
├── ecommerce/
│   ├── alfagift/latest.json & history/YYYY-MM-DD.json
│   └── indomaret/latest.json & history/YYYY-MM-DD.json
├── property/
│   ├── jendela360/latest.json & history/YYYY-MM-DD.json
│   ├── rumah123/latest.json & history/YYYY-MM-DD.json
│   └── sewakost/latest.json & history/YYYY-MM-DD.json
```

---

## ⚖️ Disclaimer

> [!WARNING]
> Web scraping may be subject to intellectual property rights, data protection regulations, and targeted terms of service. The tools and scripts provided in this repository are designed strictly for educational and academic research. Users assume all responsibility for compliance with all local laws and terms of service.
