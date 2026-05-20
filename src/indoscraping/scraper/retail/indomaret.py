import argparse
import os
import json
import time
import random
import uuid
import shutil
from datetime import datetime
from curl_cffi import requests

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
    """Fetch URL using curl_cffi requests with exponential backoff retry on errors.
    Specially handles rate limiting (HTTP 429) and network loss with verbose console outputs."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, impersonate="chrome", timeout=20)
            
            # Specifically handle HTTP 429 Rate Limiting
            if response.status_code == 429:
                delay = 45.0 + random.uniform(5.0, 15.0)
                print(f"  [Attempt {attempt + 1}/{max_retries}] WARNING: HTTP 429 (Too Many Requests). Rate limited by server.")
                print(f"  Respecting server request: Cooling down for {delay:.2f} seconds before retrying...")
                time.sleep(delay)
                continue
                
            response.raise_for_status()
            
            # Check for <!DOCTYPE html
            text = response.text
            if text.strip().startswith("<!DOCTYPE"):
                raise Exception("API returned HTML instead of JSON.")
                
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  [Attempt {attempt + 1}/{max_retries}] Fatal error: All retries exhausted. Error details: {e}")
                raise e
            
            # Exponential backoff with a cap, plus a random jitter
            delay = min(initial_delay * (2 ** attempt), 60.0) + random.uniform(0.5, 2.0)
            
            # Check for connection errors specifically to give friendly network-loss messages
            err_msg = str(e)
            if "connection" in err_msg.lower() or "resolve" in err_msg.lower() or "timeout" in err_msg.lower():
                print(f"  [Attempt {attempt + 1}/{max_retries}] Network connection lost or timed out: {e}")
                print(f"  Waiting {delay:.2f} seconds for internet reconnection before retrying...")
            else:
                print(f"  [Attempt {attempt + 1}/{max_retries}] Request failed: {e}. Retrying in {delay:.2f}s...")
                
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

def write_merged_output(cache_dir, output_path, output_format="json"):
    """Merges all scraped category JSONs in the cache folder and writes to output_path in the specified format."""
    import csv
    try:
        merged_products = []
        if os.path.exists(cache_dir):
            for file_name in sorted(os.listdir(cache_dir)):
                if file_name.endswith('.json'):
                    file_path = os.path.join(cache_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            products = json.load(f)
                            merged_products.extend(products)
                    except Exception as e:
                        print(f"Warning: Failed to read cache file {file_path}: {e}")
                            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if output_format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(merged_products, f, ensure_ascii=False, indent=2)
        elif output_format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                for p in merged_products:
                    f.write(json.dumps(p, ensure_ascii=False) + '\n')
        elif output_format == "csv":
            if not merged_products:
                return
            keys = set()
            for p in merged_products:
                keys.update(p.keys())
            fieldnames = sorted(list(keys))
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for p in merged_products:
                    row = {}
                    for k in fieldnames:
                        v = p.get(k, "")
                        if isinstance(v, (dict, list)):
                            row[k] = json.dumps(v, ensure_ascii=False)
                        else:
                            row[k] = v
                    writer.writerow(row)
    except Exception as e:
        print(f"Error merging cache to live data: {e}")

def scrape_indomaret(date_str, output_path, limit_categories=None, limit_articles=None, force=False, output_format="json"):
    print("Starting KlikIndomaret product scraping...")
    
    # Establish cache directory based on date
    cache_dir = f"data/retail/indomaret/.cache/{date_str}"
    os.makedirs(cache_dir, exist_ok=True)
    
    try:
        categories_data = get_categories()
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []
        
    # Flatten categories hierarchy
    categories_to_crawl = []
    for data in categories_data:
        meta_perm = data.get("permalink")
        for category in data.get("categories", []):
            cat_perm = category.get("permalink")
            sub_categories = category.get("subCategories", [])
            
            if not sub_categories:
                categories_to_crawl.append({
                    "meta": meta_perm,
                    "category": cat_perm,
                    "sub": None
                })
            else:
                for sub in sub_categories:
                    categories_to_crawl.append({
                        "meta": meta_perm,
                        "category": cat_perm,
                        "sub": sub.get("permalink")
                    })
                    
    if not categories_to_crawl:
        print("No category configurations found.")
        return []
        
    if limit_categories:
        categories_to_crawl = categories_to_crawl[:limit_categories]
        print(f"Limited crawling to {limit_categories} category sectors.")
        
    all_products = []
    
    for idx, config in enumerate(categories_to_crawl, 1):
        meta = config["meta"]
        cat = config["category"]
        sub = config["sub"]
        
        # Build cache filename and partial directory
        sub_str = sub if sub else "null"
        cache_file = os.path.join(cache_dir, f"{meta}_{cat}_{sub_str}.json")
        partial_dir = os.path.join(cache_dir, f"_partial_{meta}_{cat}_{sub_str}")
        
        # Check cache if force is False
        if not force and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_products = json.load(f)
                print(f"[{idx}/{len(categories_to_crawl)}] Category: {meta} -> {cat} -> {sub_str} - LOADED {len(cached_products)} products from cache (Cache hit)")
                all_products.extend(cached_products)
                write_merged_output(cache_dir, output_path, output_format=output_format)
                continue
            except Exception as e:
                print(f"[{idx}/{len(categories_to_crawl)}] Category: {meta} -> {cat} -> {sub_str} - Error loading cache: {e}. Crawling fresh...")

        # If forcing, clear any partial directory to avoid dirty state
        if force and os.path.exists(partial_dir):
            try:
                shutil.rmtree(partial_dir)
            except Exception:
                pass

        print(f"[{idx}/{len(categories_to_crawl)}] Scraping category: {meta} -> {cat} -> {sub_str}")
        category_products = []
        page = 0
        
        # Check for partial progress to resume
        if not force and os.path.exists(partial_dir):
            try:
                page_files = sorted(
                    [f for f in os.listdir(partial_dir) if f.startswith("page_") and f.endswith(".json")],
                    key=lambda x: int(x.split("_")[1].split(".")[0])
                )
                if page_files:
                    print(f"  [Checkpoint] Found partial progress directory with {len(page_files)} cached page(s). Restoring...")
                    for pf in page_files:
                        pf_path = os.path.join(partial_dir, pf)
                        with open(pf_path, 'r', encoding='utf-8') as f:
                            pf_data = json.load(f)
                            category_products.extend(pf_data)
                    highest_page = int(page_files[-1].split("_")[1].split(".")[0])
                    page = highest_page + 1
                    print(f"  [Checkpoint] Restored {len(category_products)} products. Resuming from page {page}.")
            except Exception as e:
                print(f"  [Checkpoint] Failed to restore partial progress: {e}. Starting from page 0.")
                category_products = []
                page = 0

        # Ensure partial directory exists for saving progress
        os.makedirs(partial_dir, exist_ok=True)
        
        try:
            while True:
                # Respect the server: add adaptive randomized delay (1.0s to 2.2s)
                if page > 0 or len(category_products) > 0:
                    delay = random.uniform(1.0, 2.2)
                    print(f"  [Sleep] Respecting server: waiting {delay:.2f}s before fetching page {page}...")
                    time.sleep(delay)

                data = get_products(page, meta, cat, sub)
                products = data.get("content", [])
                
                if not products:
                    print(f"  Page {page}: No more products returned. Category pagination completed.")
                    break
                    
                # Add category mapping info to each product
                for product in products:
                    product.update({
                        "metaCategories": meta,
                        "categories": cat,
                        "subCategories": sub
                    })
                    
                # Save this page's products to the partial cache directory immediately
                page_cache_file = os.path.join(partial_dir, f"page_{page}.json")
                with open(page_cache_file, "w", encoding="utf-8") as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)

                category_products.extend(products)
                print(f"  Page {page}: Scraped {len(products)} products (Total in segment: {len(category_products)})")
                
                # Check if we should limit articles per category segment
                if limit_articles and len(category_products) >= limit_articles:
                    category_products = category_products[:limit_articles]
                    print(f"  Reached per-category limit of {limit_articles} products.")
                    break
                    
                page += 1
                
            # Write to completed cache
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(category_products, f, ensure_ascii=False, indent=2)
            
            # Clean up the partial directory now that the category finished successfully
            try:
                shutil.rmtree(partial_dir)
                print(f"  [Cleanup] Cleaned up temporary page caches for {meta} -> {cat} -> {sub_str}")
            except Exception as e:
                print(f"  [Cleanup] Warning: Failed to delete partial directory {partial_dir}: {e}")

            all_products.extend(category_products)
            
            # Update live output dynamically
            write_merged_output(cache_dir, output_path, output_format=output_format)
            
        except Exception as e:
            print(f"  [Segment Error] Failed scraping category {meta}/{cat}/{sub_str} on page {page}: {e}")
            print(f"  Checkpoint saved! You can resume from page {page} on the next run.")
            
        # Small delay between categories
        category_delay = random.uniform(1.5, 3.0)
        print(f"  [Sleep] Finished category segment. Waiting {category_delay:.2f}s before next segment...")
        time.sleep(category_delay)

    return all_products

def main():
    default_date = datetime.now().strftime("%Y-%m-%d")
    
    parser = argparse.ArgumentParser(description="Scrape products from KlikIndomaret")
    parser.add_argument("--date", default=default_date, help="Date to scrape in YYYY-MM-DD format (default: today)")
    parser.add_argument("--limit-categories", type=int, default=None, help="Max categories to scrape (default: all)")
    parser.add_argument("--limit-articles", type=int, default=None, help="Max products to scrape per category (default: all)")
    parser.add_argument("--output", default="data/retail/indomaret/latest.json", help="Output path for the latest scraping results")
    parser.add_argument("--force", action="store_true", help="Force scrape all categories, bypassing cache")
    parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json", help="Output format (default: json)")
    args = parser.parse_args()
    
    # Adjust output file extension based on format
    output_path = args.output
    if args.format != "json":
        base, _ = os.path.splitext(output_path)
        output_path = f"{base}.{args.format}"
        
    all_products = scrape_indomaret(
        date_str=args.date,
        output_path=output_path,
        limit_categories=args.limit_categories,
        limit_articles=args.limit_articles,
        force=args.force,
        output_format=args.format
    )
    
    if all_products:
        # Save historical snapshot of the merged final output
        date_str = args.date
        history_ext = args.format
        history_path = f"data/retail/indomaret/history/{date_str}.{history_ext}"
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        
        # Read compiled live output to save the full final snapshot
        try:
            if args.format == "json":
                with open(output_path, "r", encoding="utf-8") as f:
                    final_merged = json.load(f)
            else:
                with open(output_path, "rb") as f:
                    final_merged_content = f.read()
        except Exception:
            final_merged = all_products
            final_merged_content = None
            
        if args.format == "json" or not final_merged_content:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(final_merged, f, ensure_ascii=False, indent=2)
        else:
            with open(history_path, "wb") as f:
                f.write(final_merged_content)
            
        print(f"\nCompleted successfully!")
        print(f"Total merged products saved: {len(all_products)}")
        print(f"Saved latest to {output_path}")
        print(f"Saved historical snapshot to {history_path}")
    else:
        print("No products crawled or error occurred.")

if __name__ == "__main__":
    main()
