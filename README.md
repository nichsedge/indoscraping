# Indoscraping

Indoscraping is a collection of web scrapers designed to extract data from various Indonesian websites. This project provides tools for scraping news articles and retail product information. The scrapers are written in both Python and JavaScript, depending on the target site's structure and technology.

This repository is intended for educational and research purposes. Please be responsible and respect the terms of service of the websites you scrape.

## Installation

This project contains scrapers written in both Python and JavaScript. You will need to install dependencies for both environments to use all the scrapers.

### Python Dependencies

The Python scrapers rely on packages listed in `pyproject.toml`. You can install them using `pip`:

```bash
pip install -e .
```

### JavaScript Dependencies

The JavaScript scrapers require Node.js. Each scraper has its own dependencies defined in a `package.json` file. To install them, navigate to the scraper's directory and run `npm install`:

```bash
# Example for the alfagift scraper
cd src/indoscraping/scraper/retail/alfagift
npm install
```

## Usage

Each scraper is a standalone script that can be executed directly. The scraped data is typically saved to a JSON file in the same directory as the scraper.

### News Scrapers (Python)

To run a news scraper, execute the Python script from the root of the project:

```bash
python src/indoscraping/scraper/news/detik.py
```

This will scrape articles from detik.com for the date specified within the script and save them to `detik_articles.json`.

### Retail Scrapers (JavaScript)

To run a retail scraper, first navigate to the scraper's directory and install the dependencies as mentioned in the Installation section. Then, run the script using Node.js:

```bash
# Navigate to the scraper directory
cd src/indoscraping/scraper/retail/alfagift

# Run the scraper
node index.mjs
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
