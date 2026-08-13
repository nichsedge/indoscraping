import argparse
from datetime import datetime
from alfagift_scraper.scraper import scrape_alfagift

def main():
    default_date = datetime.now().strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(description="Alfagift Scraper Standalone CLI")
    parser.add_argument("--date", default=default_date)
    parser.add_argument("--limit-categories", type=int, default=None)
    parser.add_argument("--limit-articles", type=int, default=None)
    parser.add_argument("--output", default="data/ecommerce/alfagift/latest.json")
    parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json")
    args = parser.parse_args()

    scrape_alfagift(
        date_str=args.date,
        output_path=args.output,
        limit_categories=args.limit_categories,
        limit_articles=args.limit_articles,
        output_format=args.format
    )

if __name__ == "__main__":
    main()
