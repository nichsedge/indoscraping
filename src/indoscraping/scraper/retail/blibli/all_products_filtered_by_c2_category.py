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

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36')
    driver = uc.Chrome(options=options, version_main=147)
    return driver

def scrape_category(driver, category_url, category_name, level):
    print(f"\nScraping category: {category_name} -> {category_url}")
    driver.get(category_url)
    time.sleep(8) # Wait for page load
    
    # Scroll to trigger lazy loading
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.5)
        
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Try to find a cleaner category name from breadcrumbs or headers
    # Fallback: strip "Hingga XX%" from the homepage label
    clean_name = re.sub(r'^Hingga\s+\d+%\s*', '', category_name)
    
    breadcrumb = soup.find('div', class_='breadcrumb-wrapper')
    if not breadcrumb:
        breadcrumb = soup.find('ul', class_='breadcrumb')
    
    if breadcrumb:
        # Get the last item in the breadcrumb
        items = breadcrumb.find_all(['a', 'span'])
        if items:
            last_item = items[-1].get_text(strip=True)
            if last_item and len(last_item) < 30:
                clean_name = last_item
    else:
        # Check if there's an active link that looks like a category name
        active_link = soup.select_one('a.link-active')
        if active_link:
            clean_name = active_link.get_text(strip=True)

    boxes = soup.find_all('div', class_='product-list__card')
    if not boxes:
        boxes = soup.find_all('a', class_='elf-product-card')
    
    # Fallback for category pages if the standard search result classes are missing
    if not boxes:
        # Look for links that point to product pages and contain some content (like a span)
        boxes = [a for a in soup.find_all('a', href=True) if '/p/' in a['href'] and a.find('span')]
        
    print(f"Found {len(boxes)} products in '{clean_name}'")
    
    products = []
    for box in boxes:
        item = {}
        try:
            # Get URL first as it helps with naming fallbacks
            product_url = ""
            if box.name == 'a' and box.get('href'):
                product_url = box['href']
            else:
                a_tag = box.find('a', href=True)
                if a_tag:
                    product_url = a_tag['href']
            
            if product_url and product_url.startswith('/'):
                product_url = 'https://www.blibli.com' + product_url

            # Name
            title_el = box.find('span', class_='els-product__title')
            if not title_el: title_el = box.find('div', class_='els-product__title')
            if not title_el: title_el = box.find('div', class_='product-title-wrapper')
            
            name = title_el.get_text(strip=True) if title_el else "N/A"
            
            # Fallback if name is N/A or looks like location (from index.mjs logic)
            if not name or name == "N/A" or name.startswith("Kota ") or name.startswith("Kab. "):
                if product_url:
                    match = re.search(r'/p/([^/?#]+)', product_url)
                    if match:
                        name = " ".join([w.capitalize() for w in match.group(1).split('-')])
            
            item['productName'] = name
            
            # Price
            price_el = box.find('div', class_='els-product__fixed-price')
            if not price_el: price_el = box.find('span', class_='els-product__fixed-price')
            if not price_el: price_el = box.find('div', class_='price-container')
            
            price_raw = price_el.get_text(strip=True) if price_el else "Rp 0"
            if not price_el:
                # Look for text containing "Rp"
                rp_text = box.find(string=lambda t: 'Rp' in str(t))
                if rp_text:
                    price_raw = rp_text.strip()
            
            item['priceRaw'] = price_raw
            
            # Numeric Price
            price_numeric = 0
            if price_raw:
                digits = re.sub(r'[^0-9]', '', price_raw)
                if digits:
                    price_numeric = int(digits)
            item['priceNumeric'] = price_numeric
            
            item['category'] = clean_name
            item['categoryLevel'] = level
            
            # Seller & Location
            seller_spans = box.find_all('span', class_='els-product__seller-name')
            seller_texts = [s.get_text(strip=True) for s in seller_spans if s.get_text(strip=True)]
            
            seller = "Unknown"
            location = "N/A"
            
            if len(seller_texts) >= 2:
                location = seller_texts[-1]
                seller = seller_texts[-2]
            elif seller_texts:
                seller = seller_texts[0]
            
            item['seller'] = seller.replace('Disediakan', '').strip()
            item['location'] = location

            # Installment (Extra Mile from index.mjs)
            full_text = box.get_text().lower()
            item['installmentAvailable'] = "Yes" if ("cicilan" in full_text or "0%" in full_text) else "No"

            # Sales & Rating
            sold_el = box.find('div', class_='els-product__sold')
            item['soldCount'] = sold_el.get_text(strip=True) if sold_el else "0"
            
            rating_wrapper = box.find('div', class_='els-product__rating-wrapper')
            rating = "0"
            if rating_wrapper:
                rating_val = rating_wrapper.find_next('span')
                if rating_val:
                    rating = rating_val.get_text(strip=True)
            
            
            # Fallback rating regex from index.mjs
            if rating == "0":
                rating_match = re.search(r'([0-5][,.][0-9])', full_text)
                if rating_match:
                    rating = rating_match.group(1)
            
            item['rating'] = rating
            item['productUrl'] = product_url
            
            products.append(item)
        except Exception:
            continue
    return products

def main():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    priority_csv = os.path.join(script_dir, 'blibli_c2_priority_list.csv')
    output_file = 'data/blibli/blibli_priority_data.csv'
    progress_file = 'data/blibli/priority_completed_urls.txt'
    
    if not os.path.exists(priority_csv):
        print(f"Error: Priority list CSV not found at {priority_csv}")
        return

    os.makedirs('data/blibli', exist_ok=True)
    
    # Load priority list
    print(f"Loading priority list from {priority_csv}...")
    df_priority = pd.read_csv(priority_csv)

    # Filter only top 20 percent
    df_priority = df_priority[df_priority["is_top_20_percent"] == True]
    print(f"Filtered to {len(df_priority)} 'is_top_20_percent' categories.")
    
    # Map CSV columns to internal format
    # Columns: c1_name,c2_name,c2_url,c3_sub_category_count,priority_score,is_top_20_percent
    categories = []
    for _, row in df_priority.iterrows():
        categories.append({
            'name': row['c2_name'],
            'url': row['c2_url'],
            'level': 2,
            'priority': row['priority_score']
        })
    
    completed_urls = set()
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            completed_urls = set(line.strip() for line in f if line.strip())
        print(f"Resuming: Found {len(completed_urls)} already scraped priority categories.")
    
    driver = get_driver()
    try:
        print(f"\nTargeting {len(categories)} Level 2 priority categories...")
        for i, cat in enumerate(categories):
            cat_url = cat['url']
            print(f"\n[{i+1}/{len(categories)}] {cat['name']} (Priority: {cat['priority']})")
            
            if cat_url in completed_urls:
                print(" -> Already scraped. Skipping.")
                continue
                
            try:
                products = scrape_category(driver, cat_url, cat['name'], cat.get('level', 2))
                
                if products:
                    df = pd.DataFrame(products)
                    # Add priority info to the output data
                    df['priority_score'] = cat['priority']
                    
                    # Append to CSV
                    mode = 'a' if os.path.exists(output_file) else 'w'
                    header = not os.path.exists(output_file)
                    df.to_csv(output_file, mode=mode, header=header, index=False, encoding='utf-8')
                    print(f" -> Saved {len(products)} products to CSV.")
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
        print(f"\nPriority scraping session ended. Data appended to {output_file}.")


if __name__ == "__main__":
    main()
