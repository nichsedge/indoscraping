import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import json
import os
from indoscraping_core import write_latest_and_history, collect_lineage

BASE_URL = "https://www.cnnindonesia.com"
INDEX_URL = f"{BASE_URL}/indeks"
DATE = datetime.now().strftime("%Y/%m/%d")
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_categories():
    res = requests.get(INDEX_URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    select = soup.find("select", {"id": "kanalOption"})
    return [
        {"label": opt["data-label"], "id": opt["value"]}
        for opt in select.find_all("option")
        if opt.get("data-label") and opt.get("value")
    ]

def get_article_links(category_label, category_id, max_pages=1):
    page, links = 1, []
    while page <= max_pages:
        url = f"{BASE_URL}/{category_label}/indeks/{category_id}?date={DATE}&page={page}"
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")
        articles = soup.select("a.flex.group.items-center.gap-4")
        if not articles:
            break
        links += [a["href"] for a in articles if a.get("href")]
        page += 1
        time.sleep(0.5)
    return links

def scrape_article(url):
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    title = soup.find('h1', class_='text-[28px]')
    date = soup.find('div', class_='text-cnn_grey')
    tags_block = soup.find('div', class_='flex flex-wrap gap-3')
    content_div = soup.find('div', class_='detail-text')

    return {
        "url": url,
        "title": title.get_text(strip=True) if title else "",
        "date": date.get_text(strip=True) if date else "",
        "tags": [a.get_text(strip=True) for a in tags_block.find_all('a')] if tags_block else [],
        "content": "\n\n".join(p.get_text(strip=True) for p in content_div.find_all('p') if p.get_text(strip=True)) if content_div else " "
    }

def main():
    import argparse
    import os

    # Default to current date in YYYY/MM/DD format
    default_date = datetime.now().strftime("%Y/%m/%d")

    parser = argparse.ArgumentParser(description="Scrape articles from CNN Indonesia")
    parser.add_argument("--date", default=default_date, help="Date to scrape in YYYY/MM/DD format (default: today)")
    parser.add_argument("--limit-categories", type=int, default=1, help="Max categories to scrape (default: 1)")
    parser.add_argument("--limit-articles", type=int, default=3, help="Max articles per category to scrape (default: 3)")
    parser.add_argument("--output", default="data/news/cnn/latest.json", help="Output path for the latest scraping results")
    args = parser.parse_args()

    # Override the global DATE variable dynamically
    global DATE
    DATE = args.date

    all_articles = []
    categories = get_categories()
    selected_categories = categories[:args.limit_categories]
    
    for cat in selected_categories:
        print(f"Processing category: {cat['label']}")
        links = get_article_links(cat['label'], cat['id'], max_pages=1)
        selected_links = links[:args.limit_articles]
        
        for link in selected_links:
            try:
                article = scrape_article(link)
                article['category'] = cat['label']
                all_articles.append(article)
            except Exception as e:
                print(f"Error scraping {link}: {e}")
    
    # Standardized output folders via indoscraping_core
    output_path = args.output
    safe_date_str = DATE.replace("/", "-")
    history_path = f"data/news/cnn/history/{safe_date_str}.json"
    meta = collect_lineage("cnn")
    meta.update({
        "date_filter": DATE,
        "count": len(all_articles),
        "source": "CNN Indonesia"
    })
    write_latest_and_history(
        latest_path=output_path,
        history_path=history_path,
        payload=all_articles,
        meta=meta,
    )
    print(f"Exported {len(all_articles)} articles to {output_path}")
    print(f"Saved historical snapshot to {history_path}")

if __name__ == "__main__":
    main()
