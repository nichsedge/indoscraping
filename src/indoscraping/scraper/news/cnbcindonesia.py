import requests
import logging
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import datetime
import json
import os

from fake_useragent import UserAgent
ua = UserAgent()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cnbc_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.cnbcindonesia.com"
INDEX_URL = f"{BASE_URL}/indeks"

HEADERS = {
    "User-Agent": ua.random
}

def get_categories():
    logger.info("Fetching categories from CNBC Indonesia")
    start_time = time.time()
    
    try:
        res = requests.get(INDEX_URL, headers=HEADERS)
        res.raise_for_status()
        logger.debug(f"Categories page response status: {res.status_code}")
        
        soup = BeautifulSoup(res.text, "html.parser")
        select = soup.find("select", {"onchange": "articleKanalHandle(this)"})
        
        if not select:
            logger.warning("Could not find category select element")
            return []
        
        categories = []
        for option in select.find_all("option"):
            value = option.get("value")
            name = option.text.strip()
            if value:
                try:
                    slug, cat_id = value.split("/")
                    categories.append({
                        "name": name,
                        "slug": slug,
                        "id": cat_id
                    })
                    logger.debug(f"Found category: {name} (slug: {slug}, id: {cat_id})")
                except ValueError:
                    logger.warning(f"Invalid category format: {value}")
        
        logger.info(f"Successfully fetched {len(categories)} categories in {time.time() - start_time:.2f}s")
        return categories
    
    except requests.RequestException as e:
        logger.error(f"Failed to fetch categories: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching categories: {str(e)}")
        return []

def get_articles_for_category(category, date_str):
    slug = category['slug']
    cat_id = category['id']
    articles = []
    
    logger.info(f"Starting to fetch articles for category: {category['name']} (slug: {slug})")
    start_time = time.time()
    
    page = 1
    total_articles = 0
    
    try:
        while True:
            url = f"{BASE_URL}/{slug}/indeks/{cat_id}?date={date_str}&page={page}"
            logger.debug(f"Fetching page {page} for category {category['name']}: {url}")
            
            try:
                res = requests.get(url, headers=HEADERS)
                res.raise_for_status()
                
                soup = BeautifulSoup(res.text, "html.parser")
                article_tags = soup.select("article a")

                if not article_tags:
                    logger.debug(f"No articles found on page {page}, stopping pagination")
                    break

                page_articles = 0
                for tag in article_tags:
                    href = tag.get("href")
                    if href:
                        articles.append(href)
                        page_articles += 1

                logger.info(f"Fetched {page_articles} articles from {slug} page {page}")
                total_articles += page_articles
                page += 1
                
                # Add small delay to be respectful
                time.sleep(0.5)
                
            except requests.RequestException as e:
                logger.error(f"Error fetching page {page} for category {category['name']}: {str(e)}")
                break
            except Exception as e:
                logger.error(f"Unexpected error on page {page} for category {category['name']}: {str(e)}")
                break
    
    except Exception as e:
        logger.error(f"Critical error in get_articles_for_category for {category['name']}: {str(e)}")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Completed fetching {total_articles} articles for {category['name']} in {elapsed_time:.2f}s")
    
    return articles

def scrape_article(url):
    logger.info(f"Starting to scrape article: {url}")
    start_time = time.time()
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        logger.debug(f"Article response status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "No title"
        logger.debug(f"Extracted title: {title[:50]}...")

        # Extract publication date
        date_tag = soup.find("div", class_="text-cm text-gray")
        date = date_tag.get_text(strip=True) if date_tag else "No date found"
        logger.debug(f"Extracted date: {date}")

        # Extract author
        author_tag = soup.find("div", class_="mb-1 text-base font-semibold")
        author = author_tag.get_text(strip=True) if author_tag else "No author found"
        logger.debug(f"Extracted author: {author}")

        # Extract main article content
        content_div = soup.find("div", class_="detail-text")
        paragraphs = content_div.find_all("p") if content_div else []
        article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
        logger.debug(f"Extracted content length: {len(article_text)} characters")

        # Extract tags
        tag_section = soup.find('section', class_='px-4 py-4 stretch bg-white')
        tags = []
        if tag_section:
            for tag in tag_section.find_all('a'):
                tag_text = tag.get_text(strip=True)
                tag_href = tag['href']
                tags.append((tag_text, tag_href))
        logger.debug(f"Extracted {len(tags)} tags")

        elapsed_time = time.time() - start_time
        logger.info(f"Successfully scraped article in {elapsed_time:.2f}s: {title[:50]}...")
        
        return {
            "title": title,
            "date": date,
            "author": author,
            "content": article_text,
            "tags": tags,
            "url": url
        }
        
    except requests.RequestException as e:
        logger.error(f"Network error scraping article {url}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error scraping article {url}: {str(e)}", exc_info=True)
        raise

def export_to_json(data, filename=None):
    """Export scraped data to JSON file"""
    logger.info("Starting data export to JSON")
    start_time = time.time()
    
    try:
        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cnbc_scraped_{timestamp}.json"
        
        # Ensure the output directory exists
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.debug(f"Created output directory: {output_dir}")
        
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(filepath)
        elapsed_time = time.time() - start_time
        
        logger.info(f"Successfully exported {len(data.get('articles', []))} articles to {filepath} ({file_size} bytes) in {elapsed_time:.2f}s")
        return filepath
        
    except Exception as e:
        logger.error(f"Failed to export data to JSON: {str(e)}", exc_info=True)
        raise

def main():
    logger.info("Starting CNBC Indonesia scraper")
    overall_start_time = time.time()
    
    try:
        categories = get_categories()
        if not categories:
            logger.error("No categories found, aborting scraper")
            return
        
        today = datetime.datetime.now().strftime("%Y/%m/%d")
        logger.info(f"Scraping articles for date: {today}")
        
        all_articles = []
        total_categories = len(categories)
        
        # Scrape articles from all categories
        for cat_idx, cat in enumerate(categories[:1], 1):  # Limit to first category for demo
            category_start_time = time.time()
            logger.info(f"Processing category {cat_idx}/{total_categories}: {cat['name']}")
            
            try:
                links = get_articles_for_category(cat, today)
                logger.info(f"Found {len(links)} articles in category '{cat['name']}'")
                
                if not links:
                    logger.warning(f"No articles found for category: {cat['name']}")
                    continue
                
                # Scrape articles and collect data
                category_articles = []
                total_links = min(5, len(links))  # Limit to 5 articles for demo
                
                for i, link in enumerate(links[:5], 1):
                    logger.info(f"Scraping article {i}/{total_links} in {cat['name']}: {link}")
                    
                    try:
                        article_data = scrape_article(link)
                        article_data['category'] = cat['name']
                        article_data['category_slug'] = cat['slug']
                        category_articles.append(article_data)
                        
                        logger.debug(f"Successfully scraped article {i}/{total_links}")
                        
                    except Exception as e:
                        logger.error(f"Failed to scrape article {link}: {str(e)}", exc_info=True)
                        continue
                
                all_articles.extend(category_articles)
                category_elapsed = time.time() - category_start_time
                logger.info(f"Completed category '{cat['name']}' - scraped {len(category_articles)} articles in {category_elapsed:.2f}s")
                
            except Exception as e:
                logger.error(f"Error processing category {cat['name']}: {str(e)}", exc_info=True)
                continue
        
        # Export all articles to JSON
        if all_articles:
            logger.info(f"Preparing to export {len(all_articles)} total articles")
            
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
            logger.warning("No articles were scraped")
    
    except Exception as e:
        logger.error(f"Critical error in main scraper: {str(e)}", exc_info=True)
    
    finally:
        overall_elapsed = time.time() - overall_start_time
        logger.info(f"CNBC Indonesia scraper completed in {overall_elapsed:.2f}s")

if __name__ == "__main__":
    main()