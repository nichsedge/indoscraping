import time
import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import os
import re
import json
import argparse
from indoscraping_core import write_latest_and_history, collect_lineage, validate_and_clean_ecommerce, detect_schema_drift, EcommerceProductModel, get_installed_chrome_version

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
    time.sleep(8)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    all_links = soup.select('a[href*="/p/"]')
    
    hierarchy = []
    l2_categories = []
    seen_urls = set()
    
    for link in all_links:
        href = link.get('href', '')
        if not href or '?' in href: continue
        full_url = ('https://www.tokopedia.com' + href) if href.startswith('/') else href
        if full_url in seen_urls: continue
        seen_urls.add(full_url)
        name = link.get_text(strip=True)
        if not name: continue
        
        path = href.replace('https://www.tokopedia.com', '').strip('/')
        segments = path.split('/')
        level = len(segments) - 1
        node = {'name': name, 'url': full_url, 'level': level}
        
        if level == 1:
            hierarchy.append({'name': name, 'url': full_url, 'children': []})
        elif level == 2 and hierarchy:
            hierarchy[-1]['children'].append({'name': name, 'url': full_url, 'children': []})
            l2_categories.append({'name': name, 'url': full_url, 'parent': hierarchy[-1]['name'], 'level': 2})
            
    output_dir = 'data/tokopedia'
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'categories.json'), 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)
        
    return l2_categories

def run_tokopedia_scraper(output_format="json", output_file="data/ecommerce/tokopedia/latest.json"):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    driver = get_driver()
    try:
        categories = get_categories(driver)
        products = []
        if categories:
            driver.get(categories[0]['url'])
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select('div[data-testid="master-product-card"]')
            for card in cards:
                title = card.select_one('[data-testid="spnSRPProdName"]')
                price = card.select_one('[data-testid="spnSRPProdPrice"]')
                if title and price:
                    products.append({
                        "productName": title.get_text(strip=True),
                        "priceRaw": price.get_text(strip=True),
                        "category": categories[0]['name']
                    })
        products = validate_and_clean_ecommerce(products)
        detect_schema_drift(products, EcommerceProductModel, "tokopedia", strict_raise=False)
        meta = collect_lineage("tokopedia")
        write_latest_and_history(latest_path=output_file, history_path=None, payload=products, meta=meta)
        return products
    finally:
        driver.quit()
