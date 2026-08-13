import os
import json
import time
import random
from datetime import datetime
from curl_cffi import requests
from indoscraping_core import write_latest_and_history, collect_lineage, validate_and_clean_ecommerce, detect_schema_drift, EcommerceProductModel

headers = {
    "accept": "application/json",
    "accept-language": "id",
    "devicemodel": "chrome",
    "devicetype": "Web",
    "fingerprint": "hNvsXdRTVhrqH5gGgHkI8OnvtKOGC8E/vIk1u9NwkKyV1i1yorHlQQr52UMqtait",
    "latitude": "0",
    "longitude": "0",
    "priority": "u=1, i",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "Referer": "https://alfagift.id/"
}

def get_trxid():
    return str(random.randint(0, 9999999999))

def fetch_with_retry(url, req_headers, max_retries=5, initial_delay=1.0):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=req_headers, impersonate="chrome", timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            delay = initial_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
            time.sleep(delay)

def get_categories():
    req_headers = headers.copy()
    req_headers["trxid"] = get_trxid()
    url = "https://webcommerce-gw.alfagift.id/v2/categories"
    data = fetch_with_retry(url, req_headers)
    sub_category_ids = []
    for category in data.get("categories", []):
        if category.get("subCategories"):
            for sub in category["subCategories"]:
                if sub.get("categoryId"):
                    sub_category_ids.append(sub["categoryId"])
    return sub_category_ids

def get_products(category_id, page=0, limit=60):
    req_headers = headers.copy()
    req_headers["trxid"] = get_trxid()
    url = f"https://webcommerce-gw.alfagift.id/v2/products/category/{category_id}?sortDirection=asc&start={page}&limit={limit}"
    return fetch_with_retry(url, req_headers)

def scrape_alfagift(date_str, output_path, limit_categories=None, limit_articles=None, force=False, output_format="json"):
    print("Starting Alfagift product scraping...")
    category_ids = get_categories()
    if limit_categories:
        category_ids = category_ids[:limit_categories]
        
    all_products = []
    for idx, category_id in enumerate(category_ids, 1):
        try:
            first_page = get_products(category_id, page=0)
            total_pages = first_page.get("totalPage", 0)
            for page in range(total_pages + 1):
                data = first_page if page == 0 else get_products(category_id, page=page)
                products = data.get("products", [])
                all_products.extend(products)
                if limit_articles and len(all_products) >= limit_articles:
                    break
                time.sleep(0.3)
        except Exception as e:
            print(f"Error scraping category {category_id}: {e}")
            
    all_products = validate_and_clean_ecommerce(all_products)
    detect_schema_drift(all_products, EcommerceProductModel, "alfagift", strict_raise=False)
    meta = collect_lineage("alfagift")
    write_latest_and_history(latest_path=output_path, history_path=None, payload=all_products, meta=meta)
    return all_products
