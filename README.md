# Indoscraping

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.14%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Go Version](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=for-the-badge&logo=go&logoColor=white)](README_GO.md)
[![Env Manager](https://img.shields.io/badge/uv-astral-blueviolet?style=for-the-badge&logo=python&logoColor=white)](https://github.com/astral-sh/uv)
[![License](https://img.shields.io/badge/License-ISC-orange?style=for-the-badge)](https://opensource.org/licenses/ISC)
[![Tests](https://img.shields.io/badge/Tests-45%20Passed-brightgreen?style=for-the-badge)](tests/)

**A premium, unified dual-engine web scraper suite & visual CLI dashboard for Indonesian news, e-commerce (Tokopedia, Blibli, Alfagift, Klik Indomaret), and real estate property listings (Rumah123, Jendela360, SewaKost).**

</div>

> [!IMPORTANT]
> This repository is intended strictly for educational and academic research purposes. Please scrape responsibly, adhere to rate limits, and respect each target website's Terms of Service and `robots.txt` policy.

---

## 🚀 Key Features

*   **Dual-Engine Architecture (Python + Go)**:
    - **Python Engine (`uv run indoscraping`)**: Interactive Rich terminal dashboard, standalone publishable workspace packages, and Playwright response stream interception.
    - **Go Native Engine (`bin/indoscraping` or `--engine go`)**: Zero-Python native compilation for Linux and native Termux (aarch64) with managed goroutine semaphore pools and sub-second crawls.
*   **Unified Visual CLI Dashboard**: Discover, monitor, run, inspect, and export all scrapers from a single colorized terminal screen built with `rich`.
*   **Standardized Database Layout**: Systematic data organization under `data/`, automatically saving `latest.json` for rapid dashboard access, dated snapshots under `history/YYYY-MM-DD.json`, and `.meta.json` lineage sidecars.
*   **Anti-Blocking Mimicry**: Emulates Google Chrome TLS handshakes using `curl_cffi` and utilizes stealthy system browser launches via Playwright to bypass bot mitigations.
*   **Data Export Pipeline**: One-command export from JSON to Apache Parquet or CSV (`indoscraping export <id> --format parquet|csv`).

---

## 🛠️ Quick Start & Setup

### Prerequisites
- **Python 3.14+** and **[uv](https://github.com/astral-sh/uv)** installed.
- **Go 1.22+** (optional, for native Go engine compilation).

```bash
# 1. Clone repository
git clone https://github.com/nichsedge/indoscraping.git
cd indoscraping

# 2. Setup Python environment and restore all workspace dependencies
uv sync

# 3. Optional: Build native Go binary
make build-go
```

---

## 💻 CLI Usage

### 1. Interactive Visual Dashboard
```bash
uv run indoscraping
```

### 2. Direct CLI Execution (Headless / CRONs)
```bash
# List all scrapers and active storage status
uv run indoscraping list

# Check system Chrome & Playwright environment
uv run indoscraping check-browser

# View dataset volume metrics
uv run indoscraping status

# Inspect scraped data preview in terminal
uv run indoscraping inspect sewakost
uv run indoscraping inspect tokopedia

# Execute a scraper (Python Engine by default)
uv run indoscraping run detik --limit-articles 5
uv run indoscraping run tokopedia --query "laptop"
uv run indoscraping run blibli --query "kopi"
uv run indoscraping run sewakost --limit-pages 1
uv run indoscraping run rumah123 --limit-articles 5

# Execute via Go Native Engine (High-Performance / Termux)
uv run indoscraping run sewakost --engine go --limit-pages 1
uv run indoscraping run detik --engine go --limit-articles 5
./bin/indoscraping run all --limit-items 3

# Batch execute scrapers by category
uv run indoscraping run-all --category news --limit-articles 2
uv run indoscraping run-all --category property --limit-articles 2

# Export datasets to Parquet or CSV for analytics (DuckDB, Pandas, Polars)
uv run indoscraping export rumah123 --format parquet
uv run indoscraping export tokopedia --format csv
```

---

## 🔍 Complete Scraper Catalog

| Scraper ID | Aliases | Target Name | Category | Python Engine | Go Engine |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `detik` | — | Detik.com News | News | ✅ | ✅ |
| `bisnis` | — | Bisnis.com News | News | ✅ | — |
| `cnbc` | — | CNBC Indonesia | News | ✅ | ✅ |
| `cnn` | — | CNN Indonesia | News | ✅ | ✅ |
| `kompas` | — | Kompas.com | News | ✅ | ✅ |
| `narasi` | — | Narasi.tv | News | ✅ | — |
| `alfagift` | — | Alfamart Alfagift | E-Commerce | ✅ | ✅ |
| `indomaret` | — | Klik Indomaret | E-Commerce | ✅ | ✅ |
| `blibli` | `blibli-search` | Blibli Products | E-Commerce | ✅ (Playwright) | ✅ (Mobile GW) |
| `tokopedia` | `tokped` | Tokopedia Marketplace | E-Commerce | ✅ (Playwright) | ✅ (SSR Parser) |
| `jendela360`| — | Jendela360 Property | Property | ✅ | ✅ |
| `sewakost` | — | SewaKost Boarding Rooms | Property | ✅ | ✅ |
| `rumah123` | — | Rumah123 Listings | Property | ✅ | — |

---

## 🏛️ Monorepo Workspace Architecture (`uv workspace`)

```
indoscraping/
├── pyproject.toml               # Root uv Workspace Configuration
├── Makefile                     # Unified cross-language task orchestrator
├── cmd/indoscraping/            # Go native CLI entry point
├── pkg/                         # Go scraper engines and HTTP/browser packages
├── src/indoscraping/            # Python CLI Dashboard & Monolithic Crawlers
│   ├── cli.py                   # Central interactive Rich dashboard & CLI dispatcher
│   ├── scraper/
│   │   ├── news/                # Detik, Bisnis, CNBC, CNN, Kompas, Narasi crawlers
│   │   └── property/            # Rumah123, Jendela360, SewaKost crawlers
│   └── tools/
│       └── indomaret_nutrition.py # OCR-based nutrition fact extraction tool
├── packages/                    # Standalone Publishable Packages
│   ├── indoscraping-core/       # Core Engine: Data Quality, Lineage & Output
│   ├── blibli-scraper/          # Standalone Blibli Package
│   ├── tokopedia-scraper/       # Standalone Tokopedia Package
│   ├── alfagift-scraper/        # Standalone Alfagift Package
│   └── indomaret-scraper/       # Standalone Klik Indomaret Package
└── data/                        # Standardized Scraped Data & History
```

---

## 🧪 Testing & Quality Assurance

Run the test suite across both Python and Go in a single command:

```bash
# Run all tests (Python pytest + Go test)
make test

# Run Python pytest suite directly
uv run pytest

# Run Go tests directly
go test ./...
```

---

## 📂 Standardized Data Storage

Scraped files save systematically into the following directory tree:
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
│   ├── indomaret/latest.json & history/YYYY-MM-DD.json
│   ├── blibli/latest.json & history/YYYY-MM-DD.json
│   └── tokopedia/latest.json & history/YYYY-MM-DD.json
└── property/
    ├── jendela360/latest.json & history/YYYY-MM-DD.json
    ├── rumah123/latest.json & history/YYYY-MM-DD.json
    └── sewakost/latest.json & history/YYYY-MM-DD.json
```

---

## ⚖️ Disclaimer

> [!WARNING]
> Web scraping may be subject to intellectual property rights, data protection regulations, and targeted terms of service. The tools and scripts provided in this repository are designed strictly for educational and academic research. Users assume all responsibility for compliance with all local laws and terms of service.
