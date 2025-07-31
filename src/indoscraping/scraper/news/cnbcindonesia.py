import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import datetime
import json
import os

BASE_URL = "https://www.cnbcindonesia.com"
INDEX_URL = f"{BASE_URL}/indeks"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_categories():
    res = requests.get(INDEX_URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    select = soup.find("select", {"onchange": "articleKanalHandle(this)"})
    categories = []

    for option in select.find_all("option"):
        value = option.get("value")
        name = option.text.strip()
        if value:
            slug, cat_id = value.split("/")
            categories.append({
                "name": name,
                "slug": slug,
                "id": cat_id
            })
    return categories

def get_articles_for_category(category, date_str):
    slug = category['slug']
    cat_id = category['id']
    articles = []

    page = 1
    while True:
        url = f"{BASE_URL}/{slug}/indeks/{cat_id}?date={date_str}&page={page}"
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")
        article_tags = soup.select("article a")

        if not article_tags:
            break

        for tag in article_tags:
            href = tag.get("href")
            if href:
                articles.append(href)

        print(f"Fetched {len(article_tags)} articles from {slug} page {page}")
        page += 1

    return articles

def scrape_article(url):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract title
    title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "No title"

    # Extract publication date
    date_tag = soup.find("div", class_="text-cm text-gray")
    date = date_tag.get_text(strip=True) if date_tag else "No date found"

    # Extract author
    author_tag = soup.find("div", class_="mb-1 text-base font-semibold")
    author = author_tag.get_text(strip=True) if author_tag else "No author found"

    # Extract main article content
    content_div = soup.find("div", class_="detail-text")
    paragraphs = content_div.find_all("p") if content_div else []
    article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)

    # Extract tags
    tag_section = soup.find('section', class_='px-4 py-4 stretch bg-white')
    tags = []
    if tag_section:
        for tag in tag_section.find_all('a'):
            tag_text = tag.get_text(strip=True)
            tag_href = tag['href']
            tags.append((tag_text, tag_href))

    return {
        "title": title,
        "date": date,
        "author": author,
        "content": article_text,
        "tags": tags,
        "url": url
    }

def export_to_json(data, filename=None):
    """Export scraped data to JSON file"""
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cnbc_scraped_{timestamp}.json"
    
    # Ensure the output directory exists
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Data exported to {filepath}")
    return filepath

def main():
    categories = get_categories()
    today = datetime.datetime.now().strftime("%Y/%m/%d")
    
    all_articles = []
    
    # Scrape articles from all categories
    for cat in categories[:1]:  # Limit to first category for demo
        print(f"\n📂 Scraping category: {cat['name']}")
        links = get_articles_for_category(cat, today)
        print(f"✅ Total articles in '{cat['name']}': {len(links)}")
        
        # Scrape articles and collect data
        category_articles = []
        for i, link in enumerate(links[:5]):  # Limit to 5 articles for demo
            print(f"📝 Scraping article {i+1}/{min(5, len(links))}: {link}")
            try:
                article_data = scrape_article(link)
                article_data['category'] = cat['name']
                article_data['category_slug'] = cat['slug']
                category_articles.append(article_data)
            except Exception as e:
                print(f"❌ Error scraping {link}: {e}")
        
        all_articles.extend(category_articles)
        print(f"✅ Scraped {len(category_articles)} articles from {cat['name']}")
    
    # Export all articles to JSON
    if all_articles:
        export_data = {
            "metadata": {
                "total_articles": len(all_articles),
                "scraped_at": datetime.datetime.now().isoformat(),
                "date_filter": today,
                "source": "CNBC Indonesia"
            },
            "articles": all_articles
        }
        
        export_to_json(export_data)
    else:
        print("⚠️ No articles were scraped")

if __name__ == "__main__":
    main()