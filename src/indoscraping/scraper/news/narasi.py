import argparse
import os
import json
import time
from datetime import datetime
from curl_cffi import requests

API_URL = "https://gateway.narasi.tv/core/api/tags/special/1"

def scrape_narasi(limit_articles=None):
    print(f"Fetching Narasi.tv spotlight articles from API...")
    try:
        # Use curl_cffi to impersonate Google Chrome browser
        response = requests.get(API_URL, impersonate="chrome", timeout=15)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("data", {}).get("articles", [])
        
        if not articles:
            print("No spotlight articles found in Narasi.tv response.")
            return []
            
        scraped_data = []
        selected_articles = articles[:limit_articles] if limit_articles else articles
        
        print("\n--- Articles from Narasi.tv API ---")
        for i, article in enumerate(selected_articles, 1):
            title = article.get("title", "No Title")
            short_desc = article.get("short", "")
            publish_date = article.get("publishDate", "")
            slug = article.get("slug", "")
            link = f"https://narasi.tv/{slug}"
            
            print(f"\nArticle {i}:")
            print(f"Title: {title}")
            print(f"Short Description: {short_desc}")
            print(f"Publish Date: {publish_date}")
            print(f"Link: {link}")
            
            scraped_data.append({
                "title": title,
                "short_description": short_desc,
                "publish_date": publish_date,
                "link": link,
                "slug": slug,
                "scraped_at": datetime.now().isoformat()
            })
            
        return scraped_data

    except Exception as e:
        print(f"Error scraping Narasi.tv API: {e}")
        return []

def main():
    default_date = datetime.now().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="Scrape articles from Narasi.tv")
    parser.add_argument("--date", default=default_date, help="Date to scrape in YYYY-MM-DD format (default: today)")
    parser.add_argument("--limit-articles", type=int, default=None, help="Max articles to scrape (default: all)")
    parser.add_argument("--output", default="data/news/narasi/latest.json", help="Output path for the latest scraping results")
    args = parser.parse_args()

    # Perform scraping
    articles = scrape_narasi(limit_articles=args.limit_articles)

    if articles:
        # Standardized output folders
        output_path = args.output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save latest results
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"\nExported {len(articles)} articles to {output_path}")

        # Save historical snapshot
        date_str = args.date
        history_path = f"data/news/narasi/history/{date_str}.json"
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"Saved historical snapshot to {history_path}")

if __name__ == "__main__":
    main()
