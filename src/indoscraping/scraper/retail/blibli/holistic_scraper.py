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
    import json
    print("Fetching master categories page...")
    driver.get("https://www.blibli.com/categories")
    time.sleep(8) # Wait for page to fully load
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Follow the logic from categories.mjs but in Python/BeautifulSoup
    all_links = soup.select('a[class*="category__"]')
    
    hierarchy = []
    l2_categories = []
    
    current_l1 = None
    current_l2 = None
    current_l3 = None
    current_l4 = None
    
    for link in all_links:
        name = link.get_text(strip=True)
        href = link.get('href', '')
        if href.startswith('/'):
            href = 'https://www.blibli.com' + href
            
        classes = link.get('class', [])
        class_str = " ".join(classes)
        
        node = {'name': name, 'url': href, 'children': []}
        
        if 'category__item-header' in class_str:
            current_l1 = node
            hierarchy.append(current_l1)
            current_l2 = current_l3 = current_l4 = None
        elif 'level-2' in class_str and current_l1:
            current_l1['children'].append(node)
            current_l2 = node
            l2_categories.append({'name': name, 'url': href, 'parent': current_l1['name']})
            current_l3 = current_l4 = None
        elif 'level-3' in class_str and current_l2:
            current_l2['children'].append(node)
            current_l3 = node
            current_l4 = None
        elif 'level-4' in class_str and current_l3:
            current_l3['children'].append(node)
            current_l4 = node
        elif 'level-5' in class_str and current_l4:
            current_l4['children'].append(node)
            
    # Save the hierarchy for validation
    output_dir = 'data/blibli'
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'categories.json'), 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(hierarchy)} main categories to {output_dir}/categories.json")
    print(f"Extracted {len(l2_categories)} Level 2 categories.")
    
    return l2_categories

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
        
        # Select top 5 Level 2 categories for testing as requested
        test_categories = categories[:5]
        
        if not test_categories:
            print("\nNo categories found. Testing with a hardcoded one.")
            test_categories = [{'name': 'Handphone & Tablet', 'url': 'https://www.blibli.com/c/handphone-tablet/54593'}]
            
        print(f"\nScraping {len(test_categories)} sample Level 2 categories:")
        for i, cat in enumerate(test_categories):
            print(f"{i+1}. {cat['name']} (Parent: {cat.get('parent', 'N/A')})")
            
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
