# Blibli Scraper (`blibli-scraper`)

Standalone Python package for scraping product search results, merchant data, prices, ratings, and holistic categories from **Blibli.com**.

## 🚀 Quick Start

```bash
# Install via pip
pip install blibli-scraper

# Execute search scrape CLI
blibli-scraper search "indomie goreng" --output data/blibli.json
```

## 💻 Python Usage

```python
from blibli_scraper.search import scrape_blibli

products = scrape_blibli(query="laptop gaming", output_path="laptop.json")
print(f"Scraped {len(products)} products!")
```
