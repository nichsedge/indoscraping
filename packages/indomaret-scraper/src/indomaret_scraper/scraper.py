import os
import json
import time
import random
import uuid
from curl_cffi import requests
from indoscraping_core import write_latest_and_history, collect_lineage, validate_and_clean_ecommerce, detect_schema_drift, EcommerceProductModel

BASE_URL = "https://ap-mc.klikindomaret.com/assets-klikidmgroceries/api/get/catalog-xpress/api/webapp"

STORE_CONFIG = {
    "storeCode": "TJKT",
    "latitude": "-6.1763897",
    "longitude": "106.82667",
    "mode": "DELIVERY",
    "districtId": "141100100"
}

def get_headers():
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "apps": json.dumps({
            "app_version": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "device_class": "browser|browser",
            "device_family": "none",
            "device_id": str(uuid.uuid4()),
            "os_name": "Linux",
            "os_version": "x86_64"
        }),
        "page": "unpage",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "x-correlation-id": str(uuid.uuid4()),
        "Referer": "https://www.klikindomaret.com/"
    }

def fetch_with_retry(url, params, headers, max_retries=10, initial_delay=2.0):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, impersonate="chrome", timeout=20)
            if response.status_code == 429:
                delay = 45.0 + random.uniform(5.0, 15.0)
                time.sleep(delay)
                continue
            response.raise_for_status()
            text = response.text
            if text.strip().startswith("<!DOCTYPE"):
                raise Exception("API returned HTML instead of JSON.")
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            delay = min(initial_delay * (2 ** attempt), 60.0) + random.uniform(0.5, 2.0)
            time.sleep(delay)

def get_categories():
    params = STORE_CONFIG.copy()
    url = f"{BASE_URL}/category/meta"
    data = fetch_with_retry(url, params, get_headers())
    return data.get("data", [])

def get_products(page, meta_categories, categories, sub_categories=None, limit=20):
    params = STORE_CONFIG.copy()
    params.update({
        "metaCategories": meta_categories,
        "categories": categories,
        "page": str(page),
        "size": str(limit)
    })
    if sub_categories:
        params["subCategories"] = sub_categories
    url = f"{BASE_URL}/search/result"
    data = fetch_with_retry(url, params, get_headers())
    return data.get("data", {})

def scrape_indomaret(date_str, output_path, limit_categories=None, limit_articles=None, force=False, output_format="json"):
    print("Starting KlikIndomaret product scraping...")
    categories_data = get_categories()
    categories_to_crawl = []
    for data in categories_data:
        meta_perm = data.get("permalink")
        for category in data.get("categories", []):
            cat_perm = category.get("permalink")
            sub_categories = category.get("subCategories", [])
            if not sub_categories:
                categories_to_crawl.append({"meta": meta_perm, "category": cat_perm, "sub": None})
            else:
                for sub in sub_categories:
                    categories_to_crawl.append({"meta": meta_perm, "category": cat_perm, "sub": sub.get("permalink")})
                    
    if limit_categories:
        categories_to_crawl = categories_to_crawl[:limit_categories]
        
    all_products = []
    for idx, config in enumerate(categories_to_crawl, 1):
        try:
            res = get_products(0, config["meta"], config["category"], config["sub"])
            prods = res.get("products", [])
            all_products.extend(prods)
            if limit_articles and len(all_products) >= limit_articles:
                break
        except Exception as e:
            print(f"Error scraping category {config['category']}: {e}")
            
    all_products = validate_and_clean_ecommerce(all_products)
    detect_schema_drift(all_products, EcommerceProductModel, "indomaret", strict_raise=False)
    meta = collect_lineage("indomaret")
    write_latest_and_history(latest_path=output_path, history_path=None, payload=all_products, meta=meta)
    return all_products
