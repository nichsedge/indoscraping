# Indoscraping

Indoscraping is a modern, unified collection of web scrapers designed to extract news, financial bank rates, and retail product information from prominent Indonesian web portals. The suite is driven by a premium, interactive terminal CLI dashboard built with `rich`, offering structured data organization and headless automation capabilities.

This repository is intended for educational and research purposes. Please scrape responsibly and respect target websites' terms of service.

---

## 🚀 Key Features

*   **Unified Visual CLI Dashboard**: Explore, monitor, and run all scrapers from a single, interactive, colorized terminal screen.
*   **Standardized Database Directory**: Organized data structures under `data/` separating `latest.json` configurations and chronological dated backups inside `history/YYYY-MM-DD.json`.
*   **Highly Configurable News Crawlers**: Parameterized Python crawlers supporting dynamic date targeting (`--date`), limit overrides (`--limit-articles`), and custom outputs (`--output`).
*   **Anti-Blocking Mimicry**: Leverages `curl_cffi` to emulate Chrome TLS handshakes (for API scrapers) and Playwright for headless browser execution.

---

## 🛠️ Installation & Setup

This project uses `uv` for lightning-fast Python dependency management and environment routing.

### Prerequisites
- [uv](https://github.com/astral-sh/uv) installed globally.
- Node.js installed (required for retail API scrapers).

### Setup Command
```bash
# Setup the virtual environment and install Python packages
uv sync

# Install Node.js package dependencies
npm install
```

---

## 💻 Usage

We provide a premium CLI dashboard named `indoscraping` to manage the scraper suite.

### 1. Interactive Visual Dashboard
To start the visual terminal dashboard menu to discover and run scrapers interactively:
```bash
# Via uv
uv run indoscraping

# Via npm script
npm run list:scrapers
```

### 2. Status & Volume Metrics
View the size, last-modified timestamps, and format statuses of all crawled data files across the database directory:
```bash
uv run indoscraping status
```

### 3. Non-Interactive Command-Line Scraper Running
Execute any scraper headlessly or inside scheduled CRON jobs:
```bash
# List all available scraper keys
uv run indoscraping list

# Run a specific news scraper
uv run indoscraping run cnbc
uv run indoscraping run detik --limit-articles 5
uv run indoscraping run narasi --limit-articles 3 --date 2026-05-18

# Run retail scrapers
uv run indoscraping run alfagift
uv run indoscraping run indomaret

# Run digital bank rates
uv run indoscraping run banks
```

---

## 📰 News Scrapers Parameters Signature
All news crawlers accept standard parameter overrides:
*   `--date`: Crawl date to extract (defaults to today's date or yesterday depending on scraper).
*   `--limit-categories`: Limits category sectors scanned.
*   `--limit-articles`: Limits items scraped per category (perfect for rapid smoke testing).
*   `--output`: Redirects the final output destination.

---

## 🌐 Supported Sites

### News
- **Bisnis.com**: Financial and business news.
- **CNBC Indonesia**: High-performance category crawler.
- **CNN Indonesia**: National and international news.
- **Detik.com**: General news portal indices.
- **Kompas.com**: National and regional indices.
- **Narasi.tv**: Investigative tags scraper (powered by `curl_cffi`).

### Finance & Digital Banks
- **Jenius (BTPN)**, **Bank Jago**, **SeaBank**, **blu by BCA Digital**, **LINE Bank**, **Bank Neo Commerce**, **Krom Bank**, **Superbank** (powered by Playwright).

### Retail
- **Alfagift**: Online store for Alfamart API.
- **Klik Indomaret**: Online store for Indomaret API.
- **Blibli**: Category and search-based crawlers.
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

Web scraping may be subject to intellectual property limits and website terms of service. The tools provided in this repository are for educational and academic research purposes only. Users are solely responsible for ensuring compliance with all local laws and terms of service.
