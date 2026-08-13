# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4>=4.14.3",
#     "pandas>=3.0.2",
#     "selenium>=4.43.0",
#     "undetected-chromedriver>=3.5.5",
#     "setuptools",
# ]
# ///

import time
import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import os
import re
import json
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from indoscraping_core import get_installed_chrome_version

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = uc.Chrome(options=options, version_main=get_installed_chrome_version())
    return driver

def get_categories(driver):
    print("Fetching Tokopedia categories directory (https://www.tokopedia.com/p)...")
    driver.get("https://www.tokopedia.com/p")
    time.sleep(8) # Wait for page to fully load
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Tokopedia categories page structure:
    # L1: Typically headers or large blocks
    # L2/L3: Links starting with /p/
    
    all_links = soup.select('a[href*="/p/"]')
    
    hierarchy = []
    l2_categories = []
    seen_urls = set()
    
    # Simple extraction logic based on URL depth
    # /p/elektronik -> L1
    # /p/elektronik/komponen-laptop -> L2
    # /p/elektronik/komponen-laptop/baterai-laptop -> L3
    
    for link in all_links:
        href = link.get('href', '')
        if not href or '?' in href: continue
        
        # Normalize URL
        if href.startswith('/'):
            full_url = 'https://www.tokopedia.com' + href
        else:
            full_url = href
            
        if full_url in seen_urls: continue
        seen_urls.add(full_url)
        
        name = link.get_text(strip=True)
        if not name: continue
        
        # Determine level based on path segments
        path = href.replace('https://www.tokopedia.com', '').strip('/')
        segments = path.split('/')
        
        # The first segment is 'p', so:
        # p/l1 -> 2 segments
        # p/l1/l2 -> 3 segments
        # p/l1/l2/l3 -> 4 segments
        
        level = len(segments) - 1 # Adjusted to match Blibli style (L1=1, L2=2...)
        
        node = {'name': name, 'url': full_url, 'level': level}
        
        if level == 1:
            hierarchy.append({'name': name, 'url': full_url, 'children': []})
        elif level == 2 and hierarchy:
            hierarchy[-1]['children'].append({'name': name, 'url': full_url, 'children': []})
            l2_categories.append({'name': name, 'url': full_url, 'parent': hierarchy[-1]['name'], 'level': 2})
        elif level == 3 and hierarchy and hierarchy[-1]['children']:
            hierarchy[-1]['children'][-1]['children'].append(node)
            # We could also include L3 in l2_categories if L2 is missing or as part of the crawl list
            
    # Collect all L3 categories (leaf nodes for better coverage as per investigation)
    crawl_list = []
    for l1 in hierarchy:
        for l2 in l1['children']:
            if not l2['children']:
                # No L3, use L2
                crawl_list.append({'name': l2['name'], 'url': l2['url'], 'parent': l1['name'], 'level': 2})
            else:
                for l3 in l2['children']:
                    crawl_list.append({'name': l3['name'], 'url': l3['url'], 'parent': l2['name'], 'level': 3})
            
    # Save the hierarchy for validation
    output_dir = 'data/tokopedia'
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'categories.json'), 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(hierarchy)} main categories to {output_dir}/categories.json")
    print(f"Extracted {len(crawl_list)} target categories (mostly Level 3).")
    
    return crawl_list

def scrape_category(driver, category_url, category_name, level):
    print(f"\nScraping category: {category_name} -> {category_url}")
    driver.get(category_url)
    
    # Wait for the page to show real products, not just skeletons
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="spnSRPProdName"]'))
        )
    except:
        print(" -> Timeout waiting for product names. Page might be empty or blocked.")

    all_products_map = {} # Use URL as key to ensure uniqueness
    
    # Capture products iteratively while scrolling
    # This helps if Tokopedia removes elements from DOM after they load
    for scroll_step in range(6):
        time.sleep(2) # Small wait for new items
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Identify cards
        boxes = soup.find_all(['div', 'a'], attrs={"data-testid": re.compile(r'(pcv6ProductCard|master-product-card|product-card|sp_list_product_card)', re.I)})
        
        if not boxes:
            # Fallback to general product card classes
            boxes = soup.select('div.css-1as3ra8, div.css-546569, div.pcv3__container, a.css-54k5sq')
            
        new_count = 0
        for box in boxes:
            try:
                # Helper to find by testid
                def find_testid(b, tid):
                    res = b.find(attrs={"data-testid": tid})
                    if not res: res = b.find(attrs={"data-testid": re.compile(tid, re.I)})
                    return res

                # URL first as it's our unique key
                url_el = box if box.name == 'a' else box.find('a', href=True)
                if not url_el: url_el = find_testid(box, "sp_list_product_link")
                
                product_url = url_el['href'] if url_el and url_el.get('href') else ""
                if not product_url: continue
                if product_url.startswith('/'):
                    product_url = 'https://www.tokopedia.com' + product_url
                
                # Skip if already captured
                if product_url in all_products_map:
                    continue

                item = {'productUrl': product_url}
                
                # Name
                name_el = find_testid(box, "spnSRPProdName")
                if not name_el: name_el = box.find('span', class_=re.compile(r'css-1bj9681|css-1bjf4sx|css-1bjf4iu'))
                
                name = ""
                if name_el:
                    name = name_el.get_text(strip=True)
                else:
                    # Final fallback: look for any text block that looks like a title
                    for el in box.find_all(['span', 'div', 'h3']):
                        t = el.get_text(strip=True)
                        if 20 < len(t) < 150 and 'Rp' not in t and 'Terjual' not in t and '|' not in t:
                            name = t
                            break
                
                if not name: continue # Skip if no name found
                item['productName'] = name
                
                # Price
                price_el = find_testid(box, "spnSRPProdPrice")
                if not price_el: price_el = box.find('div', class_=re.compile(r'css-1ksb19c|css-180733y|css-1as3ra8'))
                price_raw = price_el.get_text(strip=True) if price_el else "Rp 0"
                item['priceRaw'] = price_raw
                
                digits = re.sub(r'[^0-9]', '', price_raw)
                item['priceNumeric'] = int(digits) if digits else 0
                
                item['category'] = category_name
                item['categoryLevel'] = level
                
                # Seller & Location
                shop_el = find_testid(box, "spnSRPProdSellerName")
                if not shop_el: shop_el = find_testid(box, "spnSRPProdTabShopName")
                item['seller'] = shop_el.get_text(strip=True) if shop_el else "Unknown"
                
                loc_el = find_testid(box, "spnSRPProdSellerLocation")
                if not loc_el: loc_el = find_testid(box, "spnSRPProdTabShopLocation")
                item['location'] = loc_el.get_text(strip=True) if loc_el else "N/A"

                # Sales & Rating
                rating_sales_el = find_testid(box, "spnSRPProdRatingSales")
                rating, sold = "0", "0"
                if rating_sales_el:
                    text = rating_sales_el.get_text(strip=True)
                    if '|' in text:
                        parts = text.split('|')
                        rating, sold = parts[0].strip(), parts[1].replace('Terjual', '').strip()
                    else:
                        r_match = re.search(r'([0-5][.,][0-9])', text)
                        if r_match: rating = r_match.group(1)
                        s_match = re.search(r'Terjual\s*(.*)', text)
                        if s_match: sold = s_match.group(1)
                
                item['soldCount'], item['rating'] = sold, rating
                
                all_products_map[product_url] = item
                new_count += 1
            except:
                continue
        
        if new_count > 0:
            print(f" -> Step {scroll_step+1}: Found {new_count} new products (Total: {len(all_products_map)})")
            
        # Scroll down for next step
        driver.execute_script("window.scrollBy(0, 1000);")
        
    return list(all_products_map.values())

def main():
    parser = argparse.ArgumentParser(description="Scrape all products from Tokopedia categories.")
    parser.add_argument("--format", choices=["csv", "json", "jsonl"], default="csv", help="Output format (default: csv)")
    args = parser.parse_args()
    
    output_format = args.format
    
    # Ensure we use a consistent data directory at the repo root
    # Find the repo root (assuming it's 5 levels up from this script or just use 'data/' if run from root)
    # To be safe, we'll try to find 'data' relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # The script is at src/indoscraping/scraper/ecommerce/tokopedia.py
    # We want to go up to the repo root
    repo_root = os.path.abspath(os.path.join(script_dir, "../../../../"))
    output_dir = os.path.join(repo_root, 'data/tokopedia')
    
    output_file = f'{output_dir}/tokopedia_holistic_data.{output_format}'
    progress_file = f'{output_dir}/completed_urls.txt'
    
    os.makedirs(output_dir, exist_ok=True)
    
    all_products = []
    # Only load for 'json' format (standard array) which is memory-intensive
    if output_format == 'json' and os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                all_products = json.load(f)
            print(f"Loaded {len(all_products)} existing products from JSON.")
        except Exception as e:
            print(f"Warning: Could not load existing JSON: {e}")
            all_products = []
    elif output_format == 'jsonl':
        print(f"Using JSONL format for memory efficiency. Appending to {output_file}")
    
    completed_urls = set()
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            completed_urls = set(line.strip() for line in f if line.strip())
        print(f"Resuming: Found {len(completed_urls)} already scraped categories.")
    
    driver = get_driver()
    try:
        categories = get_categories(driver)
        
        if not categories:
            print("\nNo categories found. Testing with a hardcoded one.")
            categories = [{'name': 'Elektronik', 'url': 'https://www.tokopedia.com/p/elektronik', 'level': 2}]
            
        print(f"\nTargeting {len(categories)} Level 2 categories...")
        for i, cat in enumerate(categories):
            cat_url = cat['url']
            print(f"\n[{i+1}/{len(categories)}] {cat['name']}")
            
            if cat_url in completed_urls:
                print(" -> Already scraped. Skipping.")
                continue
                
            try:
                products = scrape_category(driver, cat_url, cat['name'], cat.get('level', 2))
                
                if products:
                    if output_format == 'csv':
                        df = pd.DataFrame(products)
                        # Append to CSV
                        mode = 'a' if os.path.exists(output_file) else 'w'
                        header = not os.path.exists(output_file)
                        df.to_csv(output_file, mode=mode, header=header, index=False, encoding='utf-8')
                        print(f" -> Saved {len(products)} products to CSV.")
                    elif output_format == 'jsonl':
                        # Memory efficient: Append line by line
                        with open(output_file, 'a', encoding='utf-8') as f:
                            for p in products:
                                f.write(json.dumps(p, ensure_ascii=False) + '\n')
                        print(f" -> Appended {len(products)} products to JSONL.")
                    else:
                        # Standard JSON array (Memory intensive for large files)
                        all_products.extend(products)
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(all_products, f, indent=2, ensure_ascii=False)
                        print(f" -> Updated JSON with {len(products)} new products (Total: {len(all_products)}).")
                else:
                    print(" -> No products found on this page.")
                
                # Mark as completed
                with open(progress_file, 'a') as f:
                    f.write(cat_url + '\n')
                completed_urls.add(cat_url)
                
            except Exception as e:
                print(f" -> Error scraping category {cat['name']}: {e}")
                print(" -> Will retry on next run.")
            
            # Be nice to the server between categories
            time.sleep(3)
            
    finally:
        driver.quit()
        print(f"\nScraping session ended. Data appended to {output_file}.")

if __name__ == "__main__":
    main()
