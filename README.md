# Indoscraping

Indoscraping is a collection of web scrapers designed to extract data from various Indonesian websites. This project provides tools for scraping news articles and retail product information. The scrapers are written in both Python and JavaScript, depending on the target site's structure and technology.

This repository is intended for educational and research purposes. Please be responsible and respect the terms of service of the websites you scrape.

## Installation

This project is streamlined using `uv`. It manages both Python and Node.js environments.

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed.
- Node.js installed (for retail scrapers).

### Setup

```bash
# Install Python dependencies and setup venv
uv sync

# Install JavaScript dependencies (if any are added to root package.json)
npm install
```

## Usage

You can run all scrapers using `npm run`. This provides a unified interface for both Python and JavaScript scrapers.

### News Scrapers (Python)

```bash
# Run a specific scraper
npm run scrape:detik
```

### Retail Scrapers (JavaScript/Node.js)

```bash
# Run a specific retail scraper
npm run scrape:alfagift
npm run scrape:indomaret
```

### List Available Scrapers

```bash
npm run list:scrapers
```

This will scrape product data from Alfagift and save it to `alfagift_products.json`.

## Supported Sites

This library supports scraping from the following websites:

### News

- **Bisnis.com**: Financial and business news.
- **CNBC Indonesia**: Business and financial news.
- **CNN Indonesia**: National and international news.
- **Detik.com**: General news portal.
- **Kompas.com**: National and regional news.
- **Narasi.tv**: In-depth and investigative journalism.

### Retail

- **Alfagift**: Online store for Alfamart.
- **Klik Indomaret**: Online store for Indomaret.

## Disclaimer

The scrapers in this repository are provided for educational and research purposes only. Web scraping may be against the terms of service of some websites. Users of this repository are responsible for ensuring they comply with all applicable laws and terms of service.

The authors and contributors of this project are not responsible for any misuse of the provided tools.
