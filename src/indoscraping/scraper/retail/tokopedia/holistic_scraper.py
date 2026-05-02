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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    # Set window size to something realistic
    driver = uc.Chrome(options=options, version_main=147)
    return driver

def get_categories(driver):
    print("Fetching Tokopedia home page for categories...")
    driver.get("https://www.tokopedia.com/")
    time.sleep(5) # wait for page to load
    
    time.sleep(6) # wait for page to load
    
    try:
        # Look for the 'Kategori' button
        # Selector from browser subagent: [data-testid="header-kategori"]
        wait = WebDriverWait(driver, 10)
        print("Clicking 'Kategori' menu...")
        
        # Try finding by testid first, then by text
        try:
            kategori_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="header-kategori"]')))
            kategori_btn.click()
        except:
            # Fallback to text-based search
            kategori_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Kategori')]")
            kategori_btn.click()
            
        time.sleep(3) # Wait for menu to open
        
    except Exception as e:
        print(f"Warning: Could not click Kategori menu: {e}")
        # Continue anyway, maybe some are visible on homepage
        
    # Scroll a bit to trigger any lazy-loaded category sections if menu didn't open
    driver.execute_script("window.scrollBy(0, 500);")
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    categories = []
    seen_urls = set()
    
    # Also look for the specific classes identified by subagent
    # Main: css-1xwye2v, Sub: css-1s5ma3k, Sub-sub: css-izd3et
    cat_elements = soup.select('a.css-1xwye2v, a.css-1s5ma3k, a.css-izd3et, a[href*="/p/"], a[href*="/kategori/"]')
    
    print(f"Found {len(cat_elements)} potential category links in DOM.")
    
    for link in cat_elements:
        href = link.get('href', '')
        if not href: continue
        
        # Filter for category-like URLs
        # Ignore search, promo, discovery (unless it's a category landing)
        if (href.startswith('/p/') or '/kategori/' in href) and '?' not in href:
            # Clean up URL
            full_url = href
            if href.startswith('/'):
                full_url = 'https://www.tokopedia.com' + href
            
            if full_url in seen_urls:
                continue
                
            name = link.get_text(strip=True)
            # If no text, try finding it in child elements or attributes
            if not name:
                img = link.find('img')
                if img and img.get('alt'):
                    name = img['alt']
                if not name:
                    name = link.get('title', '')
            
            # Clean name from "New", "Promo" etc
            name = re.sub(r'(New|Promo|Diskon)\s*', '', name, flags=re.I).strip()
            
            if name and 2 < len(name) < 40: 
                seen_urls.add(full_url)
                categories.append({'name': name, 'url': full_url})
    
    # Fallback if no categories found via simple link search
    if not categories:
        print("No categories found via simple search. Trying specific selectors...")
        # Try selectors identified by subagent
        cat_elements = soup.select('a.css-1xwye2v, a.css-1s5ma3k')
        for el in cat_elements:
            href = el.get('href')
            if href:
                full_url = href if href.startswith('http') else 'https://www.tokopedia.com' + href
                name = el.get_text(strip=True)
                if name and full_url not in seen_urls:
                    seen_urls.add(full_url)
                    categories.append({'name': name, 'url': full_url})

    return categories

def scrape_category(driver, category_url, category_name):
    print(f"\nScraping category: {category_name} -> {category_url}")
    driver.get(category_url)
    time.sleep(8) # Wait for page load
    
    # Scroll down to load more products (Tokopedia uses infinite scroll/lazy loading)
    for _ in range(4):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(2)
        
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Attempt to find a cleaner category name from page header or breadcrumbs
    clean_name = category_name
    breadcrumb = soup.select_one('div[data-testid="divBreadcrumb"]')
    if breadcrumb:
        items = breadcrumb.find_all(['a', 'span'])
        if items:
            last_item = items[-1].get_text(strip=True)
            if last_item:
                clean_name = last_item

    # Find product cards
    # Tokopedia search results often use a tags with dynamic classes as cards
    # We can also look for elements inside divSRPProductList
    boxes = soup.find_all('div', attrs={"data-testid": "master-product-card"})
    if not boxes:
        # Try to find all cards inside the product list container
        product_list = soup.select_one('[data-testid="divSRPProductList"]')
        if product_list:
            # Look for a tags that have a price or name inside
            boxes = [a for a in product_list.find_all('a') if a.select_one('[data-testid*="Prod"]')]
        
    if not boxes:
        # On CLP pages, it might be data-testid="product-card" or similar
        boxes = soup.find_all(attrs={"data-testid": re.compile(r'product-card', re.I)})
        
    if not boxes:
        # Fallback: look for common container classes or structure
        boxes = soup.select('div.css-546569, div.css-llwpbs, div.pcv3__container') 
    
    if not boxes:
        # Final fallback: look for any element that contains "Rp"
        potential_boxes = soup.find_all(['div', 'a'], recursive=True)
        boxes = []
        for b in potential_boxes:
            if b.name == 'a' and b.find(string=re.compile(r'Rp')):
                if len(boxes) < 50: # Limit
                    boxes.append(b)

    print(f"Found {len(boxes)} potential products in '{clean_name}'")
    
    products = []
    for box in boxes:
        item = {}
        try:
            # Helper to find by testid (check self and children)
            def find_testid(el, tid):
                if el.get('data-testid') == tid: return el
                return el.select_one(f'[data-testid="{tid}"]')

            # Name
            name_el = find_testid(box, "spnSRPProdName")
            if not name_el:
                name_el = box.select_one('span.css-1bjf4iu, div.css-1163sk3')
            
            if name_el:
                item['name'] = name_el.get_text(strip=True)
            else:
                # Fallback: first span with 20+ chars
                for s in box.find_all(['span', 'div']):
                    t = s.get_text(strip=True)
                    if 20 < len(t) < 200 and 'Rp' not in t:
                        item['name'] = t
                        break
                else:
                    item['name'] = "N/A"
            
            if item['name'] == "N/A": continue

            # Price
            price_el = find_testid(box, "divSRPProdPrice")
            if not price_el: price_el = find_testid(box, "spnSRPProdPrice")
            
            if price_el:
                item['price'] = price_el.get_text(strip=True)
            else:
                # Look for Rp pattern
                rp_match = box.find(string=re.compile(r'Rp\s*[\d.]+'))
                item['price'] = rp_match.strip() if rp_match else "N/A"
            
            item['category'] = clean_name
            item['category_url'] = category_url
            
            # Seller & Location
            shop_el = find_testid(box, "divSRPProdStoreName")
            if not shop_el: shop_el = find_testid(box, "spnSRPProdTabShopName")
            item['seller'] = shop_el.get_text(strip=True) if shop_el else "N/A"
            
            loc_el = find_testid(box, "divSRPProdLoc")
            if not loc_el: loc_el = find_testid(box, "spnSRPProdTabShopLocation")
            item['location'] = loc_el.get_text(strip=True) if loc_el else "N/A"

            # Sales & Rating
            sold_el = find_testid(box, "divSRPProdSold")
            if not sold_el: sold_el = find_testid(box, "lblSRPProdSoldNumber")
            item['sold'] = sold_el.get_text(strip=True) if sold_el else "0"
            
            rating_el = find_testid(box, "divSRPProdRating")
            if not rating_el: rating_el = find_testid(box, "spnSRPProdRatingNumber")
            item['rating'] = rating_el.get_text(strip=True) if rating_el else "0"
            
            # URL
            url_el = box if box.name == 'a' else box.find('a', href=True)
            item['url'] = url_el['href'] if url_el and url_el.get('href') else "N/A"
            if item['url'].startswith('/'):
                item['url'] = 'https://www.tokopedia.com' + item['url']

            products.append(item)
        except Exception:
            continue
            
    return products

def main():
    driver = get_driver()
    all_data = []
    
    try:
        categories = get_categories(driver)
        print(f"\nFound {len(categories)} categories on homepage.")
        
        # Display the first few
        for i, c in enumerate(categories[:10]):
            print(f"{i+1}. {c['name']} - {c['url']}")
            
        # Select all discovered categories
        test_categories = categories
        if not test_categories:
            print("\nNo categories found on homepage. Testing with hardcoded ones.")
            test_categories = [
                {'name': 'Elektronik', 'url': 'https://www.tokopedia.com/search?st=product&q=elektronik'},
                {'name': 'Handphone', 'url': 'https://www.tokopedia.com/search?st=product&q=handphone'}
            ]
            
        for cat in test_categories:
            products = scrape_category(driver, cat['url'], cat['name'])
            all_data.extend(products)
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
        
    df = pd.DataFrame(all_data)
    if not df.empty:
        os.makedirs("data", exist_ok=True)
        output_file = 'data/tokopedia_holistic_data.csv'
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nScraping finished. Data saved to {output_file}.")
        print(df.head())
    else:
        print("\nNo data collected.")

if __name__ == "__main__":
    main()
