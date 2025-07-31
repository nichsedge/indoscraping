import json
import logging
import time
from urllib.parse import quote, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Configure logging with proper formatting and level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress noisy third-party logs
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

ua = UserAgent()
HEADERS = {
    "User-Agent": ua.random
}

def get_categories_urls(start_url="https://news.detik.com/indeks"):
    """Get all kanal category URLs ending with /indeks from the top nav."""
    logger.info(f"Fetching categories from: {start_url}")
    
    try:
        resp = requests.get(start_url, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        kanal_urls = []
        nav_links = soup.select("nav.static-nav a[href$='/indeks']")
        
        for a in nav_links:
            href = a.get("href")
            text = a.get_text(strip=True)
            if href and href.endswith("/indeks"):
                kanal_urls.append((text, href))
                logger.debug(f"Found category: {text} -> {href}")
        
        logger.info(f"Found {len(kanal_urls)} categories")
        return kanal_urls
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch categories from {start_url}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error while fetching categories: {e}")
        return []

def get_max_page(kanal_url, date_str):
    """Get the maximum page number for a given kanal and date."""
    logger.info(f"Getting max page for {kanal_url} on date {date_str}")
    
    try:
        encoded_date = quote(date_str, safe="")
        url = f"{kanal_url}?date={encoded_date}"
        
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
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
                        logger.warning(f"Invalid page number: {page_nums[0]}")
                        continue
        
        logger.info(f"Max page for {kanal_url}: {max_page}")
        return max_page
        
    except requests.RequestException as e:
        logger.error(f"Failed to get max page for {kanal_url}: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error while getting max page: {e}")
        return 1

def scrape_articles(kanal_url, date_str):
    """Scrape all article URLs from a kanal for a specific date."""
    logger.info(f"Starting article scraping for {kanal_url} on {date_str}")
    
    try:
        encoded_date = quote(date_str, safe="")
        max_page = get_max_page(kanal_url, date_str)
        
        articles = []
        
        for page in range(1, max_page + 1):
            url = f"{kanal_url}?page={page}&date={encoded_date}"
            logger.debug(f"Fetching page {page}/{max_page}: {url}")
            
            try:
                resp = requests.get(url, headers=HEADERS)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                
                links = soup.select("a.media__link")
                page_articles = []
                
                for link in links:
                    href = link.get("href")
                    if href:
                        page_articles.append(href)
                
                articles.extend(page_articles)
                logger.debug(f"Page {page}: found {len(page_articles)} articles")
                
            except requests.RequestException as e:
                logger.error(f"Failed to fetch page {page} for {kanal_url}: {e}")
                continue
        
        logger.info(f"Total articles found for {kanal_url}: {len(articles)}")
        return articles
        
    except Exception as e:
        logger.exception(f"Unexpected error while scraping articles: {e}")
        return []

def scrape_detik_article(url):
    """Scrape a single article from detik.com."""
    logger.info(f"Scraping article: {url}")
    
    try:
        headers = {"User-Agent": ua.random}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Extract title
        title_tag = soup.find('h1', class_='detail__title') or soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else None
        if not title:
            logger.warning(f"No title found for {url}")
        
        # Extract author
        author_tag = soup.find('div', class_='detail__author')
        author = None
        if author_tag:
            for span in author_tag.find_all('span'):
                span.decompose()
            author = author_tag.get_text(strip=True)
        else:
            logger.debug(f"No author found for {url}")
        
        # Extract date
        date_tag = soup.find('div', class_='detail__date')
        date = date_tag.get_text(strip=True) if date_tag else None
        if not date:
            logger.warning(f"No date found for {url}")
        
        # Extract tags
        tag_div = soup.find('div', class_='nav')
        tags = []
        if tag_div:
            for a in tag_div.find_all('a', class_='nav__item'):
                tag_text = a.get_text(strip=True)
                tag_href = a.get('href')
                tags.append({'text': tag_text, 'href': tag_href})
        logger.debug(f"Found {len(tags)} tags for {url}")
        
        # Extract content
        content_div = soup.find('div', class_='detail__body-text') or soup.find('div', class_='text--detail')
        paragraphs = []
        if content_div:
            for p in content_div.find_all('p'):
                txt = p.get_text(strip=True)
                if txt:
                    paragraphs.append(txt)
        
        if not paragraphs:
            logger.warning(f"No content found for {url}")
        
        article_data = {
            "url": url,
            "title": title,
            "author": author,
            "date": date,
            "tags": tags,
            "content": paragraphs
        }
        
        logger.info(f"Successfully scraped article: {title}")
        return article_data
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch article {url}: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error while scraping article {url}: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    # Allow setting log level via command line
    log_level = logging.INFO
    if len(sys.argv) > 1 and sys.argv[1].upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        log_level = getattr(logging, sys.argv[1].upper())
        logging.getLogger().setLevel(log_level)
    
    date = "07/28/2025"
    start_url = "https://finance.detik.com/indeks"
    
    logger.info(f"Starting detik.com scraping for date: {date}")
    
    all_articles = []
    seen_urls = set()
    
    # Get article links
    article_links = scrape_articles('https://news.detik.com/indeks', date)
    logger.info(f"Found {len(article_links)} total article links")
    
    # Scrape individual articles
    for i, link in enumerate(article_links, 1):
        if link in seen_urls:
            logger.info(f"Skipping duplicate ({i}/{len(article_links)}): {link}")
            continue
        
        try:
            logger.info(f"Processing article ({i}/{len(article_links)}): {link}")
            article_data = scrape_detik_article(link)
            all_articles.append(article_data)
            seen_urls.add(link)
            
            # Respectful delay between requests
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed to scrape article {link}: {e}")
            continue
    
    # Save results
    try:
        output_file = "detik_articles.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Scraping complete. Saved {len(all_articles)} articles to {output_file}")
        
    except Exception as e:
        logger.exception(f"Failed to save articles to JSON: {e}")
