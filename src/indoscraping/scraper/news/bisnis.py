import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re

BASE_URL = "https://www.bisnis.com"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def get_categories():
    res = requests.get(f"{BASE_URL}/index", headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    categories = {}
    for label in soup.select("label.indeks-radio"):
        match = re.search(r"categoryId=([^']+)", label.find("input").get("onclick", ""))
        if match:
            categories[label.text.strip()] = match.group(1)
    return categories

def get_max_page(category_id, date_str):
    res = requests.get(f"{BASE_URL}/index?categoryId={category_id}&type=indeks&date={date_str}", headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    total_page = soup.select_one("#total_page")
    return int(total_page['value']) if total_page else 1

def get_article_links(category_id, date_str):
    max_page = get_max_page(category_id, date_str)
    links = set()
    for page in range(1, max_page + 1):
        url = f"{BASE_URL}/index?categoryId={category_id}&type=indeks&date={date_str}&page={page}"
        soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")
        for a in soup.select("a.artLink"):
            href = a.get("href", "")
            if href.startswith("http"):
                links.add(href)
    return list(links)

def scrape_article(url):
    try:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, 'html.parser')

        data = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'title': soup.find('h1', class_='detailsTitleCaption').get_text(strip=True) if soup.find('h1', class_='detailsTitleCaption') else 'No title found',
            'lead': soup.find('div', class_='detailsLead').get_text(strip=True) if soup.find('div', class_='detailsLead') else '',
            'publish_date': soup.find('div', class_='detailsAttributeDates').get_text(strip=True) if soup.find('div', class_='detailsAttributeDates') else '',
            'author': '',
            'editor': '',
            'tags': [a.get_text(strip=True) for a in soup.select('ul.detailsTagList a.detailsTagLink')],
            'content': [],
            'image_url': '',
            'image_alt': '',
            'image_caption': ''
        }

        for p in soup.select('article.detailsContent p'):
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                data['content'].append(text)

        for item in soup.select('div.detailsAuthor div.detailsAuthorItem'):
            text = item.get_text(strip=True)
            if text.startswith('Penulis :'):
                data['author'] = text.replace('Penulis :', '').strip()
            elif text.startswith('Editor :'):
                data['editor'] = text.replace('Editor :', '').strip()

        img_tag = soup.select_one('figure.detailsCoverImg img')
        caption = soup.select_one('figcaption.detailsImgCaption')
        if img_tag:
            data['image_url'] = img_tag.get('src', '')
            data['image_alt'] = img_tag.get('alt', '')
        if caption:
            data['image_caption'] = caption.get_text(strip=True)

        return data
    except Exception as e:
        return {'url': url, 'error': str(e)}

def main():
    import argparse
    import os

    # Default to current date in YYYY-MM-DD format
    default_date = datetime.now().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="Scrape articles from Bisnis.com")
    parser.add_argument("--date", default=default_date, help="Date to scrape in YYYY-MM-DD format (default: today)")
    parser.add_argument("--limit-categories", type=int, default=1, help="Max categories to scrape (default: 1)")
    parser.add_argument("--limit-articles", type=int, default=2, help="Max articles per category to scrape (default: 2)")
    parser.add_argument("--output", default="data/news/bisnis/latest.json", help="Output path for the latest scraping results")
    args = parser.parse_args()

    date_str = args.date
    categories = get_categories()
    all_articles = []
    
    selected_categories = list(categories.keys())[:args.limit_categories]
    if not selected_categories:
        selected_categories = ["Ekonomi"]
        categories["Ekonomi"] = "43"

    for cat_name in selected_categories:
        cat_id = categories.get(cat_name, "43")
        print(f"Processing category: {cat_name} (ID: {cat_id})")
        links = get_article_links(cat_id, date_str)
        print(f"Found {len(links)} articles. Scraping up to {args.limit_articles}...")
        
        selected_links = links[:args.limit_articles]
        for url in selected_links:
            article_data = scrape_article(url)
            if article_data and 'error' not in article_data:
                article_data['category'] = cat_name
                all_articles.append(article_data)

    # Standardized output folders
    output_path = args.output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(all_articles)} articles to {output_path}")

    # Save historical snapshot
    history_path = f"data/news/bisnis/history/{date_str}.json"
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    print(f"Saved historical snapshot to {history_path}")

if __name__ == "__main__":
    main()
