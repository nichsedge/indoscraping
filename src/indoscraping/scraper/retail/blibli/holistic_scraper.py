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

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36')
    driver = uc.Chrome(options=options, version_main=147)
    return driver

def get_categories(driver):
    print("Fetching home page for categories...")
    driver.get("https://www.blibli.com/")
    time.sleep(5) # wait for page to load
    
    # Try to find category links in the DOM
    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = soup.find_all('a', href=True)
    
    categories = []
    seen_urls = set()
    
    for link in links:
        href = link['href']
        # Blibli category URLs often contain '/c/' or '/kategori/' 
        if '/c/' in href or '/kategori/' in href:
            name = link.get_text(strip=True)
            # If no text, try title or image alt
            if not name:
                name = link.get('title', '')
                if not name:
                    img = link.find('img')
                    if img and img.get('alt'):
                        name = img['alt']
            
            # Clean up URL
            if href.startswith('/'):
                href = 'https://www.blibli.com' + href
                
            if name and href not in seen_urls:
                seen_urls.add(href)
                # Ignore very long texts (likely not just a category name)
                if len(name) < 50:
                    categories.append({'name': name, 'url': href})
    
    return categories

def scrape_category(driver, category_url, category_name):
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
    import re
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
            # Name
            title_el = box.find('span', class_='els-product__title')
            if not title_el: title_el = box.find('div', class_='els-product__title')
            if not title_el: title_el = box.find('div', class_='product-title-wrapper')
            if not title_el:
                # Generic fallback: first span with substantial text
                for s in box.find_all('span'):
                    t = s.get_text(strip=True)
                    if len(t) > 15: # Category titles are usually long
                        title_el = s
                        break
            item['name'] = title_el.get_text(strip=True) if title_el else "N/A"
            
            # Price
            price_el = box.find('div', class_='els-product__fixed-price')
            if not price_el: price_el = box.find('span', class_='els-product__fixed-price')
            if not price_el: price_el = box.find('div', class_='price-container')
            if not price_el:
                # Look for text containing "Rp"
                rp_text = box.find(string=lambda t: 'Rp' in str(t))
                if rp_text:
                    price_el = rp_text.parent
            
            item['price'] = price_el.get_text(strip=True) if price_el else "N/A"
            
            item['category'] = clean_name
            item['category_url'] = category_url
            
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
            
        # Select up to 5 top categories to test
        test_categories = categories[:5]
        if not test_categories:
            print("\nNo categories found on homepage. Testing with a hardcoded one.")
            test_categories = [{'name': 'Handphone & Tablet', 'url': 'https://www.blibli.com/c/handphone-tablet/54593'}]
            
        for cat in test_categories:
            products = scrape_category(driver, cat['url'], cat['name'])
            all_data.extend(products)
            
    finally:
        driver.quit()
        
    df = pd.DataFrame(all_data)
    if not df.empty:
        output_file = 'blibli_holistic_test_data.csv'
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nScraping finished. Data saved to {output_file}.")
        print(df.head())
    else:
        print("\nNo data collected.")

if __name__ == "__main__":
    main()
