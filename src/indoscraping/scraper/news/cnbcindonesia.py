import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import datetime

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

def main():
    categories = get_categories()
    today = datetime.datetime.now().strftime("%Y/%m/%d")

    # Scrape articles from all categories
    for cat in categories[:1]:
        print(f"\n📂 Scraping category: {cat['name']}")
        links = get_articles_for_category(cat, today)
        print(f"✅ Total articles in '{cat['name']}': {len(links)}")
        
        # Scrape first few articles as example
        for link in links[:3]:
            article_data = scrape_article(link)
            print(article_data)

if __name__ == "__main__":
    main()