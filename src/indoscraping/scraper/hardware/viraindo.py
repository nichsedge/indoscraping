"""Viraindo Scraper for Indonesian PC Hardware Retail Pricing.

Parses price list tables from Viraindo (https://viraindo.com) across computer
components including processors, graphics cards, motherboards, RAM, and storage.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup
from curl_cffi import requests
from curl_cffi.requests.errors import RequestsError
from fake_useragent import UserAgent
from indoscraping_core.dq import (
    ensure_list_of_dicts,
    ensure_required_keys,
    ensure_unique,
)
from indoscraping_core.lineage import collect_lineage
from indoscraping_core.output import write_latest_and_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("viraindo")
logging.getLogger("curl_cffi").setLevel(logging.WARNING)

BASE_URL = "https://viraindo.com"
FALLBACK_BASE_URL = "https://www.viraindo.com"

AVAILABLE_CATEGORIES = [
    "proc",
    "motherboard",
    "vga",
    "storage",
    "memory",
    "lcd",
    "casing",
    "psu",
    "cooler",
    "keymouse",
    "audio",
    "aksesoris",
    "networking",
    "printer",
    "office",
    "tinta",
    "software",
    "ups-stabilizer",
    "notebook",
    "partnotebook",
    "gadget",
    "pcbranded",
    "projector",
    "server",
    "rackserver",
    "mcardflashdisk",
]


def fetch_category_html(category: str, timeout: int = 15) -> str | None:
    """Fetch HTML table for category with browser impersonation."""
    ua = UserAgent()
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "X-Requested-With": "XMLHttpRequest",
    }

    url = f"{BASE_URL}/{category}.html"
    try:
        resp = requests.get(url, headers=headers, impersonate="chrome", timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except (RequestsError, OSError) as e:
        logger.debug(f"Failed primary URL {url}: {e}")

    fallback_url = f"{FALLBACK_BASE_URL}/{category}.html"
    try:
        resp = requests.get(fallback_url, headers=headers, impersonate="chrome", timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except (RequestsError, OSError) as e:
        logger.error(f"Failed fallback URL {fallback_url}: {e}")

    return None


def parse_viraindo_table(
    html: str, category: str, limit_items: int | None = None
) -> list[dict[str, Any]]:
    """Parse HTML table rows into structured product records."""
    soup = BeautifulSoup(html, "html.parser")
    products: list[dict[str, Any]] = []

    for tr in soup.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue

        for i in range(0, len(cells) - 1, 2):
            raw_name = cells[i]
            raw_price = cells[i + 1]

            if not raw_name or not raw_price:
                continue

            # Skip header labels or call-to-order placeholders
            clean_price_str = raw_price.strip()
            if clean_price_str.lower() in ("call", "harga", "price", "-"):
                continue

            numeric_digits = re.sub(r"[^\d]", "", clean_price_str)
            if not numeric_digits:
                continue

            price_int = int(numeric_digits)

            products.append({
                "name": raw_name.strip(),
                "category": category,
                "price": price_int,
                "price_raw": f"Rp {clean_price_str}",
                "url": f"{BASE_URL}/{category}.html",
                "source": "viraindo",
                "scraped_at": datetime.now().isoformat(),
            })

            if limit_items and len(products) >= limit_items:
                return products

    return products


def upload_to_bigquery(products: list[dict[str, Any]], table_id: str) -> bool:
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
        except (json.JSONDecodeError, TypeError, ValueError):
            creds = service_account.Credentials.from_service_account_file(
                credentials_json,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )

        df = pd.DataFrame(products)
        df["inserted_at"] = datetime.now(UTC).date()
        df = df.astype(str)

        pandas_gbq.to_gbq(
            dataframe=df,
            credentials=creds,
            destination_table=table_id,
            if_exists="append",
        )
        logger.info(f"Successfully uploaded {len(products)} records to BigQuery: {table_id}")
        return True
    except (ImportError, OSError, RuntimeError) as e:
        logger.error(f"Failed to upload to BigQuery {table_id}: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Indonesian PC hardware prices from Viraindo")
    parser.add_argument(
        "--categories",
        default="proc,motherboard,vga,storage,memory",
        help="Comma-separated category slugs (e.g. proc,motherboard,vga,storage,memory,lcd,casing,psu)",
    )
    parser.add_argument(
        "--limit-articles",
        "--limit-items",
        "--limit",
        type=int,
        default=None,
        dest="limit_items",
        help="Max total products to scrape across categories",
    )
    parser.add_argument(
        "--output",
        default="data/hardware/viraindo/latest.json",
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
        default="de_zoomcamp.viraindo_raw",
        help="Target BigQuery destination table",
    )

    args = parser.parse_args()

    requested_cats = [c.strip().lower() for c in args.categories.split(",") if c.strip()]
    all_products: list[dict[str, Any]] = []

    for cat in requested_cats:
        remaining = None
        if args.limit_items is not None:
            remaining = args.limit_items - len(all_products)
            if remaining <= 0:
                break

        logger.info(f"Processing category: {cat}")
        html = fetch_category_html(cat)
        if not html:
            logger.warning(f"Could not load HTML for category: {cat}")
            continue

        cat_products = parse_viraindo_table(html, cat, limit_items=remaining)
        logger.info(f"Parsed {len(cat_products)} products from category [{cat}]")
        all_products.extend(cat_products)

        time.sleep(0.3)

    if not all_products:
        logger.warning("No products scraped from Viraindo.")

    # Deduplicate by name
    deduped = []
    seen = set()
    for item in all_products:
        name = item.get("name")
        if name and name not in seen:
            seen.add(name)
            deduped.append(item)
    all_products = deduped

    # Run indoscraping-core DQ validations
    if all_products:
        try:
            ensure_list_of_dicts(all_products)
            ensure_required_keys(all_products, ["name", "price", "source"])
            ensure_unique(all_products, "name")
        except (TypeError, ValueError) as e:
            logger.error(f"DQ validation error: {e}")

    # Build lineage and save files
    meta = collect_lineage(scraper_id="viraindo")
    meta.update({
        "category": "Hardware",
        "date": args.date,
        "count": len(all_products),
        "categories_scraped": requested_cats,
    })

    safe_date_str = args.date.replace("/", "-")
    history_path = f"data/hardware/viraindo/history/{safe_date_str}.json"

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
