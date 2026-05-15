# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4>=4.14.3",
#     "pandas>=3.0.2",
#     "selenium>=4.43.0",
#     "undetected-chromedriver>=3.5.5",
# ]
# ///
import time
import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# Configuration
SEARCH_KEYWORD = 'xiaomi15t'
BASE_URL = f'https://www.blibli.com/cari/{SEARCH_KEYWORD}'
TOTAL_PAGES = 5 

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # Use a real User Agent to avoid "unsupported browser" redirection
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36')
    
    # Set version_main to match your installed Chrome version
    driver = uc.Chrome(options=options, version_main=147)
    return driver

def scrape_blibli():
    driver = get_driver()
    all_products = []

    try:
        for page_num in range(1, TOTAL_PAGES + 1):
            print(f"Scraping page {page_num}...")
            url = BASE_URL if page_num == 1 else f'{BASE_URL}?page={page_num}'
            
            driver.get(url)
            time.sleep(8) 

            # Scroll to trigger lazy loading
            for _ in range(5):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1.5)

            # Parse HTML
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Extract category from the sidebar filters (more specific than the header)
            # Heuristic: Look for specific sub-categories in the sidebar
            category_name = SEARCH_KEYWORD
            category_sidebar = soup.find('div', class_='nested-category-filter')
            if category_sidebar:
                # Find all category labels in the sidebar
                labels = [l.get_text(strip=True) for l in category_sidebar.find_all('label', class_='blu-checkbox__content')]
                
                # Priority list for smartphone search
                priorities = ["Android", "iOS", "Smartphone", "Handphone", "Handphone & Tablet"]
                found_priority = None
                label_set = set(labels)
                for p in priorities:
                    if p in label_set:
                        found_priority = p
                        break
                
                if found_priority:
                    category_name = found_priority
                elif labels:
                    # If no priority found, take the most specific-looking one (usually longer or deeper in the list)
                    # For now, let's just take the first non-"Semua Kategori" one
                    clean_labels = [l for l in labels if "semua" not in l.lower()]
                    if clean_labels:
                        category_name = clean_labels[0]
            else:
                # Fallback to the search info link if sidebar is not found
                info_el = soup.find('span', class_='info__found__category__result__link')
                if info_el:
                    clean_text = info_el.get_text(strip=True).replace('semua kategori.', '').strip()
                    if clean_text: category_name = clean_text

            # Updated selectors to handle Blibli's latest structure
            boxes = soup.find_all('div', class_='product-list__card')
            if not boxes:
                boxes = soup.find_all('a', class_='elf-product-card')
            
            print(f"Found {len(boxes)} products on page {page_num} (Category: {category_name})")

            for box in boxes:
                item = {}
                try:
                    # Name
                    title_el = box.find('span', class_='els-product__title')
                    if not title_el: title_el = box.find('div', class_='els-product__title')
                    item['name'] = title_el.get_text(strip=True) if title_el else "N/A"
                    
                    # Price
                    price_el = box.find('div', class_='els-product__fixed-price')
                    if not price_el: price_el = box.find('span', class_='els-product__fixed-price')
                    item['price'] = price_el.get_text(strip=True) if price_el else "N/A"
                    
                    # Category
                    item['category'] = category_name
                    
                    # Seller & Location
                    seller_spans = box.find_all('span', class_='els-product__seller-name')
                    seller_texts = [s.get_text(strip=True) for s in seller_spans if s.get_text(strip=True)]
                    
                    if len(seller_texts) >= 2:
                        item['location'] = seller_texts[-1]
                        item['seller'] = seller_texts[-2]
                    else:
                        item['seller'] = seller_texts[0] if seller_texts else "N/A"
                        item['location'] = "N/A"

                    # Sales & Rating
                    sold_el = box.find('div', class_='els-product__sold')
                    item['sold'] = sold_el.get_text(strip=True) if sold_el else "0"
                    
                    rating_wrapper = box.find('div', class_='els-product__rating-wrapper')
                    if rating_wrapper:
                        rating_val = rating_wrapper.find_next('span')
                        item['rating'] = rating_val.get_text(strip=True) if rating_val else "0"
                    else:
                        item['rating'] = "0"
                    
                    all_products.append(item)
                except Exception:
                    continue

    finally:
        driver.quit()

    # Convert to DataFrame and Save
    df = pd.DataFrame(all_products)
    if not df.empty:
        output_file = f'blibli_{SEARCH_KEYWORD}_data.csv'
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Scraping finished. Data saved to {output_file}.")
    else:
        print("No data collected.")
    return df

if __name__ == "__main__":
    df_result = scrape_blibli()
    if not df_result.empty:
        print(df_result.head())
