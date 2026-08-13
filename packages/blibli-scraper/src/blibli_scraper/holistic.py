import time
import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import os
import re
import json
import argparse

from indoscraping_core import get_installed_chrome_version

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36')
    driver = uc.Chrome(options=options, version_main=get_installed_chrome_version())
    return driver

def get_categories(driver):
    print("Fetching master categories page...")
    driver.get("https://www.blibli.com/categories")
    time.sleep(8)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    all_links = soup.select('a[class*="category__"]')
    
    hierarchy = []
    l2_categories = []
    current_l1 = current_l2 = current_l3 = current_l4 = None
    
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
            l2_categories.append({'name': name, 'url': href, 'parent': current_l1['name'], 'level': 2})
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
            
    output_dir = 'data/blibli'
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'categories.json'), 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)
    
    return l2_categories

def scrape_category(driver, category_url, category_name, level):
    driver.get(category_url)
    time.sleep(8)
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.5)
        
    soup = BeautifulSoup(driver.page_source, "html.parser")
    clean_name = re.sub(r'^Hingga\s+\d+%\s*', '', category_name)
    boxes = soup.find_all('div', class_='product-list__card') or soup.find_all('a', class_='elf-product-card')
    if not boxes:
        boxes = [a for a in soup.find_all('a', href=True) if '/p/' in a['href'] and a.find('span')]
        
    products = []
    for box in boxes:
        try:
            product_url = box.get('href', '') if box.name == 'a' else (box.find('a', href=True)['href'] if box.find('a', href=True) else '')
            if product_url.startswith('/'):
                product_url = 'https://www.blibli.com' + product_url
            title_el = box.find('span', class_='els-product__title') or box.find('div', class_='els-product__title')
            name = title_el.get_text(strip=True) if title_el else "N/A"
            if not name or name == "N/A" or name.startswith("Kota ") or name.startswith("Kab. "):
                if product_url:
                    match = re.search(r'/p/([^/?#]+)', product_url)
                    if match:
                        name = " ".join([w.capitalize() for w in match.group(1).split('-')])
            price_el = box.find('div', class_='els-product__fixed-price') or box.find('span', class_='els-product__fixed-price')
            price_raw = price_el.get_text(strip=True) if price_el else "Rp 0"
            digits = re.sub(r'[^0-9]', '', price_raw)
            price_numeric = int(digits) if digits else 0
            
            products.append({
                'productName': name,
                'priceRaw': price_raw,
                'priceNumeric': price_numeric,
                'category': clean_name,
                'categoryLevel': level,
                'productUrl': product_url
            })
        except Exception:
            continue
    return products

def run_holistic(output_format="csv"):
    output_file = f'data/blibli/blibli_holistic_data.{output_format}'
    os.makedirs('data/blibli', exist_ok=True)
    driver = get_driver()
    try:
        categories = get_categories(driver)
        for cat in categories[:5]:
            products = scrape_category(driver, cat['url'], cat['name'], cat.get('level', 2))
            if products and output_format == 'csv':
                df = pd.DataFrame(products)
                mode = 'a' if os.path.exists(output_file) else 'w'
                header = not os.path.exists(output_file)
                df.to_csv(output_file, mode=mode, header=header, index=False, encoding='utf-8')
    finally:
        driver.quit()
