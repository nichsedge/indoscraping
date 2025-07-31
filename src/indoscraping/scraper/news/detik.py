import requests
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from fake_useragent import UserAgent
from urllib.parse import quote, urlparse, parse_qs
import requests

ua = UserAgent()

HEADERS = {
    "User-Agent": ua.random
}

def get_kanal_urls(start_url="https://news.detik.com/indeks"):
    """Get all kanal category URLs ending with /indeks from the top nav."""
    resp = requests.get(start_url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")

    # print(soup.select("nav"))

    kanal_urls = []
    nav_links = soup.select("nav.static-nav a[href$='/indeks']")
    for a in nav_links:
        href = a.get("href")
        text = a.get_text(strip=True)  # This grabs nested text like <div>Finance</div>
        if href and href.endswith("/indeks"):
            kanal_urls.append((text, href))

    return kanal_urls

def get_max_page(kanal_url, date_str):
    encoded_date = quote(date_str, safe="")
    url = f"{kanal_url}?date={encoded_date}"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")

    max_page = 1
    pagination_links = soup.select("div.pagination a[href*='?page=']")
    for a in pagination_links:
        href = a.get("href")
        if href:
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            page_nums = qs.get("page")
            if page_nums:
                try:
                    num = int(page_nums[0])
                    if num > max_page:
                        max_page = num
                except ValueError:
                    continue
    return max_page

def scrape_articles(kanal_url, date_str):
    encoded_date = quote(date_str, safe="")
    max_page = get_max_page(kanal_url, date_str)
    print(f"[{kanal_url}] Max page: {max_page}")

    articles = []

    for page in range(1, max_page + 1):
        url = f"{kanal_url}?page={page}&date={encoded_date}"
        print(f"Fetching: {url}")
        resp = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")

        links = soup.select("a.media__link")
        for link in links:
            href = link.get("href")
            if href:
                articles.append(href)

    return articles

def scrape_detik_article(url):
    headers = {
        "User-Agent": ua.random
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.find('h1', class_='detail__title') or soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else None

    author_tag = soup.find('div', class_='detail__author')
    author = None
    if author_tag:
        for span in author_tag.find_all('span'):
            span.decompose()
        author = author_tag.get_text(strip=True)

    date_tag = soup.find('div', class_='detail__date')
    date = date_tag.get_text(strip=True) if date_tag else None

    tag_div = soup.find('div', class_='nav')
    tags = []
    if tag_div:
        for a in tag_div.find_all('a', class_='nav__item'):
            tag_text = a.get_text(strip=True)
            tag_href = a.get('href')
            tags.append({'text': tag_text, 'href': tag_href})

    content_div = soup.find('div', class_='detail__body-text') or soup.find('div', class_='text--detail')
    paragraphs = []
    if content_div:
        for p in content_div.find_all('p'):
            txt = p.get_text(strip=True)
            if txt:
                paragraphs.append(txt)

    return {
        "url": url,
        "title": title,
        "author": author,
        "date": date,
        "tags": tags,
        "content": paragraphs
    }

if __name__ == "__main__":
    date = "07/28/2025"
    start_url = "https://finance.detik.com/indeks"  # can be any valid indeks URL

    # kanal_urls = get_kanal_urls("https://news.detik.com/indeks")
    # print(kanal_urls)

    all_articles = []
    seen_urls = set()

    article_links = scrape_articles('https://news.detik.com/indeks', date)
    for link in article_links:
        if link in seen_urls:
            print(f"    Skipping duplicate: {link}")
            continue

        try:
            print(f"    Scraping: {link}")
            article_data = scrape_detik_article(link)
            all_articles.append(article_data)
            seen_urls.add(link)
            time.sleep(1)  # be respectful to server
        except Exception as e:
            print(f"    Failed to scrape article: {e}")


    with open("detik_articles.json", "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Scraping complete. Saved {len(all_articles)} articles to detik_articles.json")
