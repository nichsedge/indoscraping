"""EnterKomputer Scraper for Indonesian PC Hardware Retail Pricing.

Queries EnterKomputer's product catalog API using curl-cffi browser TLS impersonation
to extract computer hardware prices, stock info, and marketplace links.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from curl_cffi import requests
from fake_useragent import UserAgent

from indoscraping_core.dq import ensure_list_of_dicts, ensure_required_keys, ensure_unique
from indoscraping_core.lineage import collect_lineage
from indoscraping_core.output import write_latest_and_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("enterkomputer")
logging.getLogger("curl_cffi").setLevel(logging.WARNING)

API_ENDPOINT = "https://www.enterkomputer.com/jeanne/v2/product-list"
DEFAULT_TOKEN = "U2FsdGVkX1-E55sT1JEmUtTtgjHvzgK98PZU8pKsTjQf8t2cV6U0Rrrd5ijzmdtRiKOvKb944B267vLzsZdvag"
DEFAULT_SIGNATURE = "5a512f74fbd61e01a14cf94c7b90b972"

CATEGORY_MAP = {
    "processor": "17",
    "vga": "24",
    "memory-ram": "11",
    "solid-state-drive": "101",
    "motherboard": "12",
    "casing": "3",
    "lcd": "9",
    "cooler": "4",
    "keyboard": "8",
    "psu": "19",
    "hard-disk": "6",
}


def fetch_category_products(
    cat_id: str,
    cat_slug: str,
    max_pages: int = 5,
    limit_items: Optional[int] = None,
    token: str = DEFAULT_TOKEN,
    signature: str = DEFAULT_SIGNATURE,
) -> List[Dict[str, Any]]:
    """Fetch product records for a given category from EnterKomputer."""
    ua = UserAgent()
    products: List[Dict[str, Any]] = []
    page = 1
    has_more = True

    while has_more and page <= max_pages:
        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.enterkomputer.com",
            "Referer": f"https://www.enterkomputer.com/category/{cat_id}/{cat_slug}",
        }

        data = {
            "KCODE": cat_id,
            "SCODE": "all",
            "BCODE": "all",
            "BNAME": "",
            "MORDR": "default",
            "MSTGE": "mapping",
            "MKYWD": "",
            "MTAGS": "",
            "MSGMN": "category",
            "MPAGE": page,
            "token": token,
            "signature": signature,
        }

        try:
            resp = requests.post(
                API_ENDPOINT,
                headers=headers,
                json=data,
                impersonate="chrome",
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"EnterKomputer [{cat_slug}] HTTP {resp.status_code} on page {page}")
                break

            result = resp.json()
            status = result.get("status", False)
            if not status:
                logger.info(f"End of catalog for [{cat_slug}] at page {page}")
                break

            items_found = 0
            for prnt in result.get("result", []):
                for pprnt in prnt.get("PPRNT", []):
                    for pchld in pprnt.get("PCHLD", []):
                        for raw_item in pchld.get("PLIST", []):
                            pname = (raw_item.get("PNAME") or "").strip()
                            if not pname:
                                continue

                            prices = raw_item.get("PPRCZ", [])
                            first_price = prices[0] if (prices and isinstance(prices, list)) else None
                            pcode = str(raw_item.get("PCODE", ""))
                            plink = raw_item.get("PLINK", "")
                            detail_url = (
                                f"https://www.enterkomputer.com/detail/{pcode}/{plink}"
                                if pcode and plink
                                else None
                            )

                            product_entry = {
                                "product_id": pcode,
                                "name": pname,
                                "category": cat_slug,
                                "category_name": raw_item.get("KNAME", cat_slug),
                                "price": int(first_price) if first_price is not None else None,
                                "price_raw": f"Rp {first_price:,}".replace(",", ".") if first_price else None,
                                "all_prices": prices,
                                "weight_grams": raw_item.get("PWGHT"),
                                "url": detail_url,
                                "images": raw_item.get("PIMGZ", []),
                                "marketplace_links": [l for l in raw_item.get("PLOLZ", []) if l],
                                "source": "enterkomputer",
                                "scraped_at": datetime.now().isoformat(),
                            }
                            products.append(product_entry)
                            items_found += 1

                            if limit_items and len(products) >= limit_items:
                                logger.info(f"Reached item limit {limit_items} for [{cat_slug}]")
                                return products

            logger.info(f"Fetched page {page} for [{cat_slug}]: {items_found} items (total: {len(products)})")
            if items_found == 0:
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error fetching page {page} for [{cat_slug}]: {e}")
            break

    return products


def upload_to_bigquery(products: List[Dict[str, Any]], table_id: str) -> bool:
    """Optionally export scraped items to Google BigQuery if GCP credentials exist."""
    credentials_json = os.getenv("GCP_CREDENTIALS")
    if not credentials_json:
        logger.warning("GCP_CREDENTIALS environment variable not set, skipping BigQuery upload.")
        return False

    try:
        import pandas as pd
        import pandas_gbq
        from google.oauth2 import service_account

        try:
            creds = service_account.Credentials.from_service_account_info(
                json.loads(credentials_json),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except Exception:
            creds = service_account.Credentials.from_service_account_file(
                credentials_json,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        df = pd.DataFrame(products)
        df["inserted_at"] = datetime.now().date()
        df = df.astype(str)

        pandas_gbq.to_gbq(
            dataframe=df,
            credentials=creds,
            destination_table=table_id,
            if_exists="append",
        )
        logger.info(f"Successfully uploaded {len(products)} records to BigQuery: {table_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload to BigQuery {table_id}: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Indonesian PC hardware prices from EnterKomputer")
    parser.add_argument(
        "--categories",
        default="processor,vga,memory-ram,solid-state-drive",
        help="Comma-separated category slugs (options: processor, vga, memory-ram, solid-state-drive, motherboard, casing, lcd, cooler, keyboard, psu, hard-disk)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=2,
        help="Max pages per category (default: 2)",
    )
    parser.add_argument(
        "--limit-articles",
        "--limit-items",
        "--limit",
        type=int,
        default=None,
        dest="limit_items",
        help="Max total products to scrape across all categories (useful for smoketesting)",
    )
    parser.add_argument(
        "--output",
        default="data/hardware/enterkomputer/latest.json",
        help="Path for latest JSON output",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Execution snapshot date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--upload-gbq",
        action="store_true",
        help="Upload results to Google BigQuery if GCP_CREDENTIALS is present",
    )
    parser.add_argument(
        "--table-id",
        default="de_zoomcamp.enterkomputer_raw",
        help="Target BigQuery destination table",
    )

    args = parser.parse_args()

    requested_cats = [c.strip().lower() for c in args.categories.split(",") if c.strip()]
    all_products: List[Dict[str, Any]] = []

    for cat in requested_cats:
        cat_id = CATEGORY_MAP.get(cat)
        if not cat_id:
            logger.warning(f"Unknown category '{cat}', skipping. Supported: {list(CATEGORY_MAP.keys())}")
            continue

        remaining = None
        if args.limit_items is not None:
            remaining = args.limit_items - len(all_products)
            if remaining <= 0:
                break

        logger.info(f"Processing category: {cat} (ID: {cat_id})")
        cat_products = fetch_category_products(
            cat_id=cat_id,
            cat_slug=cat,
            max_pages=args.max_pages,
            limit_items=remaining,
        )
        all_products.extend(cat_products)

    if not all_products:
        logger.warning("No products scraped from EnterKomputer.")

    # Deduplicate by product_id if present, otherwise by name
    deduped = []
    seen = set()
    for item in all_products:
        key = item.get("product_id") or item.get("name")
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    all_products = deduped

    # Run indoscraping-core DQ validations
    if all_products:
        try:
            ensure_list_of_dicts(all_products)
            ensure_required_keys(all_products, ["name", "source"])
            ensure_unique(all_products, "name")
        except Exception as e:
            logger.error(f"DQ validation error: {e}")

    # Build lineage and save files
    meta = collect_lineage(scraper_id="enterkomputer")
    meta.update({
        "category": "Hardware",
        "date": args.date,
        "count": len(all_products),
        "categories_scraped": requested_cats,
    })

    safe_date_str = args.date.replace("/", "-")
    history_path = f"data/hardware/enterkomputer/history/{safe_date_str}.json"

    write_latest_and_history(
        latest_path=args.output,
        history_path=history_path,
        payload=all_products,
        meta=meta,
    )

    logger.info(f"Saved {len(all_products)} products to {args.output}")
    logger.info(f"Saved historical snapshot to {history_path}")

    if args.upload_gbq:
        upload_to_bigquery(all_products, args.table_id)


if __name__ == "__main__":
    main()
