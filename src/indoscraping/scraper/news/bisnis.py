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
            'content': [p.get_text(strip=True) for p in soup.select('article.detailsContent p') if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20],
            'image_url': '',
            'image_alt': '',
            'image_caption': ''
        }

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

def save_to_file(data, filename='bisnis_articles.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(data)} articles to {filename}")

if __name__ == "__main__":
    date = "2025-07-28"
    categories = get_categories()
    selected_category_id = categories.get("Ekonomi", "43")  # Default to "43" if not found

    links = get_article_links(selected_category_id, date)
    print(f"Found {len(links)} unique articles. Scraping...")

    articles = [scrape_article(url) for url in links]
    save_to_file(articles)
