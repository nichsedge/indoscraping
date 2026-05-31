# Indoscraping

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Env Manager](https://img.shields.io/badge/uv-astral-blueviolet?style=for-the-badge&logo=python&logoColor=white)](https://github.com/astral-sh/uv)
[![License](https://img.shields.io/badge/License-ISC-orange?style=for-the-badge)](https://opensource.org/licenses/ISC)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=for-the-badge&logo=ruff)](https://github.com/astral-sh/ruff)

**A premium, unified collection of web scrapers designed to extract news, financial bank rates, and retail product information from prominent Indonesian web portals. Driven by a visual terminal CLI dashboard.**

</div>

> [!IMPORTANT]
> This repository is intended strictly for educational and academic research purposes. Please scrape responsibly, adhere to rate limits, and respect each target website's Terms of Service and `robots.txt` policy.

---

## 🚀 Key Features

*   **Unified Visual CLI Dashboard**: Discover, monitor, and run all scrapers from a single, interactive, colorized terminal screen built with `rich`.
*   **Standardized Database Layout**: Systematic and clean data organization under `data/`, automatically splitting `latest.json` for rapid dashboard access and dated snapshots inside `history/YYYY-MM-DD.json` for historical delta tracking.
*   **Highly Configurable News Crawlers**: Parameterized Python crawlers supporting dynamic target dates (`--date`), category limit overrides (`--limit-categories`), and item quotas (`--limit-articles`).
*   **Anti-Blocking Mimicry**: Emulates Google Chrome TLS handshakes using `curl_cffi` (for retail and investigatory APIs) and utilizes stealthy system browser launches via Playwright to bypass common bot defenses.

---

## 🛠️ Installation & Setup

This project leverages [uv](https://github.com/astral-sh/uv) for lightning-fast Python dependency management and environment routing.

### Prerequisites

> [!NOTE]
> Ensure you have **[uv](https://github.com/astral-sh/uv)** installed globally on your host system.

### Setup Commands

```bash
# Setup the virtual environment and restore all Python dependencies
uv sync
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

# Run a news scraper with options
uv run indoscraping run cnbc
uv run indoscraping run detik --limit-articles 5
uv run indoscraping run narasi --limit-articles 3 --date 2026-05-18

# Run retail API scrapers
uv run indoscraping run alfagift
uv run indoscraping run indomaret

# Run digital bank rates crawler
uv run indoscraping run banks
```

---

## 📰 News Scrapers Parameters Signature

All news crawlers accept a standard CLI interface for runtime overrides:
- `--date`: The target crawl date to extract. Automatically defaults to today's date.
- `--limit-categories`: Limits the number of category sectors scanned (default: 1).
- `--limit-articles`: Limits items scraped per category (perfect for rapid smoke testing).
- `--output`: Redirects the output file path.

---

## 🌐 Supported Sites

### News Portals
- **Bisnis.com**: Business and financial market indices.
- **CNBC Indonesia**: High-performance multi-threaded crawler.
- **CNN Indonesia**: General national and international news.
- **Detik.com**: Fast portal index crawler.
- **Kompas.com**: National and regional general news.
- **Narasi.tv**: Investigative news scraper powered by `curl_cffi` to bypass TLS detection.

### Finance & Digital Banks
- **Playwright Crawlers**: Fetches interest rate options from:
  - *Jenius (BTPN)*, *Bank Jago*, *SeaBank*, *blu by BCA Digital*, *LINE Bank*, *Bank Neo Commerce*, *Krom Bank*, *Superbank*.

### Retail & E-Commerce
- **Alfagift**: API scraper mimicking corporate app handshakes with resilience checkpointing.
- **Klik Indomaret**: Fast inventory API scraper.
- **Blibli**: Category discovery and keyword search-based Playwright scrapers.
- **Tokopedia**: Holistic product category scrapers.

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
├── retail/
│   ├── alfagift/latest.json & history/YYYY-MM-DD.json
│   └── indomaret/latest.json & history/YYYY-MM-DD.json
└── latest.json (Finance banks rates scraper outputs)
```

---

## ⚖️ Disclaimer

> [!WARNING]
> Web scraping may be subject to intellectual property rights, data protection regulations, and targeted terms of service. The tools and scripts provided in this repository are designed strictly for educational and academic research. Users assume all responsibility for compliance with all local laws and terms of service.
