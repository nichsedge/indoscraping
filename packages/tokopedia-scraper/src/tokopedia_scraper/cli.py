import argparse
from tokopedia_scraper.scraper import run_tokopedia_scraper

def main():
    parser = argparse.ArgumentParser(description="Tokopedia Scraper Standalone CLI")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", default="data/ecommerce/tokopedia/latest.json")
    args = parser.parse_args()

    run_tokopedia_scraper(output_format=args.format, output_file=args.output)

if __name__ == "__main__":
    main()
