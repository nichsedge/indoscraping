import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from indoscraping_core import write_latest_and_history, collect_lineage, detect_schema_drift, NewsArticleModel

BASE_URL = "https://indeks.kompas.com/"

def get_categories():
    return ["news", "nasional", "regional", "ekonomi", "megapolitan"]

def get_article_links(category, date, limit=5):
    url = f"{BASE_URL}?site={category}&date={date}"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for a in soup.select("a.article__link, .article__title a, .articleList a"):
            href = a.get("href")
            if href and href not in links:
                links.append(href)
                if len(links) >= limit:
                    break
        return links
    except Exception as e:
        print(f"Error getting article links for {category}: {e}")
        return []

def scrape_kompas_article(url):
    try:
        soup = BeautifulSoup(requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).content, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        raw_date = soup.select_one(".read__time")
        date = raw_date.get_text(strip=True).split("-", 1)[-1].strip() if raw_date else ""
        journalists = [j.get_text(strip=True).rstrip(",") for j in soup.select(".credit-title-nameEditor")]
        tags = [t.get_text(strip=True) for t in soup.select("ul.tag__article__wrap li a")]
        img = soup.select_one(".cover-photo img")
        image_url = img["src"] if img else ""
        paragraphs = soup.select(".read__content p")
        content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        
        return {
            "url": url,
            "title": title,
            "date": date,
            "journalists": journalists,
            "tags": tags,
            "image_url": image_url,
            "content": content
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def main():
    import argparse
    default_date = datetime.now().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="Scrape articles from Kompas.com")
    parser.add_argument("--date", default=default_date, help="Date to scrape in YYYY-MM-DD format (default: today)")
    parser.add_argument("--limit-categories", type=int, default=1, help="Max categories to scrape (default: 1)")
    parser.add_argument("--limit-articles", type=int, default=2, help="Max articles per category to scrape (default: 2)")
    parser.add_argument("--output", default="data/news/kompas/latest.json", help="Output path")
    args = parser.parse_args()

    date_str = args.date
    categories = get_categories()
    all_articles = []
    
    selected_categories = categories[:args.limit_categories]
    for category in selected_categories:
        print(f"Processing category: {category}")
        article_links = get_article_links(category, date_str, limit=args.limit_articles)
        for link in article_links:
            article_data = scrape_kompas_article(link)
            if article_data:
                article_data["category"] = category
                all_articles.append(article_data)
    
    output_path = args.output
    history_path = f"data/news/kompas/history/{date_str}.json"
    
    if all_articles:
        detect_schema_drift(all_articles, NewsArticleModel, "kompas", strict_raise=False)
        
    meta = collect_lineage("kompas")
    write_latest_and_history(latest_path=output_path, history_path=history_path, payload=all_articles, meta=meta)
    print(f"Exported {len(all_articles)} articles to {output_path}")

if __name__ == "__main__":
    main()