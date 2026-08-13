import argparse
import sys
from datetime import datetime
from blibli_scraper.search import scrape_blibli

def main():
    default_date = datetime.now().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(description="Blibli Scraper Standalone CLI")
    parser.add_argument("--query", default="xiaomi note 15 pro", help="Search query (default: 'xiaomi note 15 pro')")
    parser.add_argument("--date", default=default_date, help="Date string YYYY-MM-DD")
    parser.add_argument("--output", default="data/ecommerce/blibli/latest.json", help="Output JSON path")
    parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json", help="Output format")
    args = parser.parse_args()

    scrape_blibli(query=args.query, output_path=args.output, output_format=args.format)

if __name__ == "__main__":
    main()
