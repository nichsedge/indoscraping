import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import json

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
    all_articles = []
    categories = get_categories()
    for cat in categories[:1]:  # limit to first category
        links = get_article_links(cat['label'], cat['id'], max_pages=1)
        for link in links[:3]:
            article = scrape_article(link)
            all_articles.append(article)
    
    with open("cnn_articles.json", "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_articles)} articles to cnn_articles.json")

if __name__ == "__main__":
    main()
