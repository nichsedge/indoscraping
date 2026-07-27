import argparse
import os
import json
import time
import random
from datetime import datetime
from curl_cffi import requests

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
    """Fetch URL using curl_cffi requests with exponential backoff retry on errors."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=req_headers, impersonate="chrome", timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            delay = initial_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
            print(f"  [Attempt {attempt + 1}/{max_retries}] Request failed: {e}. Retrying in {delay:.2f}s...")
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

def scrape_alfagift(date_str, output_path, limit_categories=None, limit_articles=None, force=False, output_format="json"):
    print("Starting Alfagift product scraping...")
    
    # Establish cache directory based on targeted date
    cache_dir = f"data/ecommerce/alfagift/.cache/{date_str}"
    os.makedirs(cache_dir, exist_ok=True)
    
    try:
        category_ids = get_categories()
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []
    
    if not category_ids:
        print("No categories found.")
        return []
    
    if limit_categories:
        category_ids = category_ids[:limit_categories]
        print(f"Limited crawling to {limit_categories} categories.")
        
    all_products = []
    
    for idx, category_id in enumerate(category_ids, 1):
        cache_file = os.path.join(cache_dir, f"{category_id}.json")
        
        # Check cache if force is False
        if not force and os.path.exists(cache_file):
            print(f"[{idx}/{len(category_ids)}] Category {category_id} (Loaded from local cache)")
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_products = json.load(f)
                all_products.extend(cached_products)
                # Ensure the live output file is merged and updated
                write_merged_output(cache_dir, output_path, output_format=output_format)
                continue
            except Exception as e:
                print(f"  Error loading cache for category {category_id}: {e}. Crawling fresh...")
                
        print(f"[{idx}/{len(category_ids)}] Scraping category: {category_id}")
        category_products = []
        try:
            # Fetch first page
            first_page = get_products(category_id, page=0)
            total_pages = first_page.get("totalPage", 0)
            
            # Page range is 0 to total_pages (inclusive)
            for page in range(total_pages + 1):
                if page == 0:
                    data = first_page
                else:
                    data = get_products(category_id, page=page)
                
                products = data.get("products", [])
                category_products.extend(products)
                print(f"  Page {page}/{total_pages}: {len(products)} products")
                
                # Check if we should limit articles (products) per category
                if limit_articles and len(category_products) >= limit_articles:
                    category_products = category_products[:limit_articles]
                    print(f"  Reached per-category limit of {limit_articles} products.")
                    break
                
                # Short sleep between page requests to avoid rate limits
                time.sleep(0.3)
                
            # Save category products to cache immediately on completion
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(category_products, f, ensure_ascii=False, indent=2)
                
            all_products.extend(category_products)
            
            # Dynamic live merge so user can view data directly!
            write_merged_output(cache_dir, output_path, output_format=output_format)
            
        except Exception as e:
            print(f"Error scraping category {category_id}: {e}")
            print(f"Category {category_id} failed. Will be retried on next execution.")
            
        # Small delay between categories
        time.sleep(0.5)
        
    return all_products

def main():
    default_date = datetime.now().strftime("%Y-%m-%d")
    
    parser = argparse.ArgumentParser(description="Scrape products from Alfagift")
    parser.add_argument("--date", default=default_date, help="Date to scrape in YYYY-MM-DD format (default: today)")
    parser.add_argument("--limit-categories", type=int, default=None, help="Max categories to scrape (default: all)")
    parser.add_argument("--limit-articles", type=int, default=None, help="Max products to scrape per category (default: all)")
    parser.add_argument("--output", default="data/ecommerce/alfagift/latest.json", help="Output path for the latest scraping results")
    parser.add_argument("--force", action="store_true", help="Force scrape all categories, bypassing cache")
    parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json", help="Output format (default: json)")
    args = parser.parse_args()
    
    # Adjust output file extension based on format
    output_path = args.output
    if args.format != "json":
        base, _ = os.path.splitext(output_path)
        output_path = f"{base}.{args.format}"
        
    all_products = scrape_alfagift(
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
        history_path = f"data/ecommerce/alfagift/history/{date_str}.{history_ext}"
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        
        # Read compiled live output to save the full final snapshot
        try:
            if args.format == "json":
                with open(output_path, "r", encoding="utf-8") as f:
                    final_merged = json.load(f)
            else:
                # For non-json formats, copy/read content directly
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
