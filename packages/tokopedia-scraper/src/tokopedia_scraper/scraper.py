import os
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from indoscraping_core import (
    write_latest_and_history,
    collect_lineage,
    validate_and_clean_ecommerce,
    detect_schema_drift,
    EcommerceProductModel
)

def run_tokopedia_scraper(query="susu", output_format="json", output_file="data/ecommerce/tokopedia/latest.json"):
    """Scrapes live Tokopedia products using system-installed Chrome via Playwright response stream interception."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined })")

        def handle_response(response):
            if "gql" in response.url or "graphql" in response.url:
                try:
                    data_json = response.json()
                    items = data_json if isinstance(data_json, list) else [data_json]
                    for item in items:
                        data = item.get("data", {})
                        for key in data:
                            val = data[key]
                            if isinstance(val, dict):
                                prod_list = val.get("data", {}).get("products", []) or val.get("products", [])
                                for pr in prod_list:
                                    if isinstance(pr, dict) and pr.get("name"):
                                        price_info = pr.get("price")
                                        if isinstance(price_info, dict):
                                            num_price = price_info.get("number") or 0
                                            raw_price = price_info.get("text") or f"Rp {num_price}"
                                        else:
                                            num_price = int(price_info) if str(price_info).isdigit() else 0
                                            raw_price = f"Rp {price_info}"

                                        products.append({
                                            "productName": pr.get("name"),
                                            "priceRaw": str(raw_price),
                                            "priceNumeric": int(num_price),
                                            "seller": pr.get("shop", {}).get("name", "Unknown"),
                                            "productUrl": pr.get("url") or "",
                                            "category": "Search"
                                        })
                except Exception:
                    pass

        page.on("response", handle_response)
        search_url = f"https://www.tokopedia.com/search?q={query}"
        print(f"🔗 [NAVIGATE] {search_url}")
        
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(3000)
            
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 800)")
                page.wait_for_timeout(1500)
        except Exception as e:
            print(f"Warning during page load: {e}")
        finally:
            browser.close()

    products = validate_and_clean_ecommerce(products)
    if products:
        detect_schema_drift(products, EcommerceProductModel, "tokopedia", strict_raise=False)
        
    meta = collect_lineage("tokopedia")
    write_latest_and_history(latest_path=output_file, history_path=None, payload=products, meta=meta)
    print(f"✅ Tokopedia scraper extracted {len(products)} products to {output_file}")
    return products
