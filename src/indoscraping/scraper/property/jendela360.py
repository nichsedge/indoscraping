"""Comprehensive scraper for Jendela360 (https://jendela360.com).

Extracts property listings (apartments, houses, lands, shophouses, offices),
apartment complex directories, and unit details using both the official
Jendela360 API and Next.js SSR metadata.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("jendela360")

BASE_API_URL = "https://api.jendela360.com/api"
SEARCH_LIST_ENDPOINT = f"{BASE_API_URL}/site/search-list"
AUTOCOMPLETE_ENDPOINT = f"{BASE_API_URL}/site/search-autocomplete"
BASE_WEB_URL = "https://jendela360.com"
SITEMAP_INDEX = f"{BASE_WEB_URL}/sitemap.xml"

DEFAULT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,id;q=0.8",
    "origin": BASE_WEB_URL,
    "referer": f"{BASE_WEB_URL}/",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
}

LISTING_TYPE_MAP = {
    "apartment": 1,
    "house": 2,
    "land": 3,
    "shophouse": 4,
    "office": 5,
    "warehouse": 6,
    "commercial": 7,
}

DEAL_TYPE_MAP = {
    "rent": 0,
    "sell": 1,
}


class Jendela360Scraper:
    def __init__(self, session: Optional[requests.Session] = None, max_workers: int = 5):
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.max_workers = max_workers

    def fetch_search_page(
        self,
        listing_type_id: int,
        deal_type: int,
        page: int = 1,
        duration_filter: str = "yearly",
        retries: int = 3,
        backoff: float = 1.0,
    ) -> Dict[str, Any]:
        """Fetch a single paginated page from the search-list API."""
        params: Dict[str, Any] = {
            "listing_type_id": listing_type_id,
            "type": deal_type,
            "page": page,
        }
        if deal_type == 0:
            params["duration_filter"] = duration_filter

        url = f"{SEARCH_LIST_ENDPOINT}?{urlencode(params)}"

        for attempt in range(1, retries + 1):
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    wait_time = backoff * (2 ** (attempt - 1))
                    logger.warning(f"Rate limited (429). Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"Failed page {page} with status {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                logger.warning(f"Network error page {page} attempt {attempt}: {e}")
                time.sleep(backoff * attempt)

        return {}

    def scrape_listings(
        self,
        listing_types: Optional[List[int]] = None,
        deal_types: Optional[List[int]] = None,
        max_pages_per_category: Optional[int] = None,
        enrich_details: bool = False,
    ) -> List[Dict[str, Any]]:
        """Scrape listings across specified listing types and deal types."""
        if listing_types is None:
            listing_types = [1, 2, 3, 4, 5]
        if deal_types is None:
            deal_types = [0, 1]

        all_listings: List[Dict[str, Any]] = []

        for lt in listing_types:
            lt_name = next((k for k, v in LISTING_TYPE_MAP.items() if v == lt), f"type_{lt}")
            for dt in deal_types:
                # Land is sell-only in Jendela360
                if lt == 3 and dt == 0:
                    continue

                deal_name = "rent" if dt == 0 else "sell"
                logger.info(f"Checking catalog: {lt_name.upper()} ({deal_name})...")

                first_page = self.fetch_search_page(listing_type_id=lt, deal_type=dt, page=1)
                total = first_page.get("total", 0)
                last_page = first_page.get("last_page", 1)

                if total == 0:
                    logger.info(f"No listings found for {lt_name} ({deal_name}).")
                    continue

                target_pages = last_page
                if max_pages_per_category is not None:
                    target_pages = min(last_page, max_pages_per_category)

                logger.info(
                    f"Found {total} items across {last_page} pages for {lt_name} ({deal_name}). "
                    f"Scraping {target_pages} pages..."
                )

                items = first_page.get("data", [])
                for item in items:
                    item["_category"] = lt_name
                    item["_deal_type"] = deal_name
                    item["_scraped_at"] = datetime.now().isoformat()
                all_listings.extend(items)

                # Fetch remaining pages concurrently
                if target_pages > 1:
                    pages_to_fetch = list(range(2, target_pages + 1))
                    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        future_to_page = {
                            executor.submit(
                                self.fetch_search_page,
                                listing_type_id=lt,
                                deal_type=dt,
                                page=p,
                            ): p
                            for p in pages_to_fetch
                        }
                        for future in as_completed(future_to_page):
                            p = future_to_page[future]
                            res = future.result()
                            page_items = res.get("data", [])
                            for it in page_items:
                                it["_category"] = lt_name
                                it["_deal_type"] = deal_name
                                it["_scraped_at"] = datetime.now().isoformat()
                            all_listings.extend(page_items)
                            if p % 10 == 0 or p == target_pages:
                                logger.info(f"  [{lt_name} - {deal_name}] Processed page {p}/{target_pages}")

        logger.info(f"Total listings collected: {len(all_listings)}")

        # Deduplicate by listing ID or code
        seen_ids = set()
        deduped = []
        for l in all_listings:
            lid = l.get("id") or l.get("code")
            if lid not in seen_ids:
                seen_ids.add(lid)
                deduped.append(l)

        logger.info(f"Unique listings after deduplication: {len(deduped)}")

        if enrich_details:
            logger.info("Enriching unit details with full specs (floors, directions, charges)...")
            deduped = self.enrich_unit_listings(deduped)

        return deduped

    def fetch_unit_detail(self, deal_type_slug: str, apartment_slug: str, code: str) -> Optional[Dict[str, Any]]:
        """Fetch deep details for a single unit using Next.js SSR metadata."""
        url = f"{BASE_WEB_URL}/detail/unit/{deal_type_slug}/{apartment_slug}/{code}/id"
        try:
            resp = self.session.get(url, timeout=12)
            if resp.status_code != 200:
                return None
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text)
            if match:
                payload = json.loads(match.group(1))
                return payload.get("props", {}).get("pageProps", {}).get("unitDetailProps", {}).get("data")
        except Exception as e:
            logger.debug(f"Failed to fetch unit detail for {code}: {e}")
        return None

    def enrich_unit_listings(self, listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich a subset or all apartment unit listings with detailed data."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {}
            for item in listings:
                code = item.get("code")
                apt_slug = item.get("apartment_slug")
                deal_type_slug = "sewa" if item.get("_deal_type") == "rent" else "jual"
                if code and apt_slug:
                    future = executor.submit(self.fetch_unit_detail, deal_type_slug, apt_slug, code)
                    future_to_item[future] = item

            completed = 0
            total_enrich = len(future_to_item)
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                detail = future.result()
                if detail:
                    # Enrich with extra fields
                    for field in [
                        "floor",
                        "floor_level",
                        "view_direction",
                        "furnished",
                        "selling_price",
                        "price_per_1_month",
                        "price_per_3_months",
                        "price_per_6_months",
                        "price_per_12_months",
                        "deposit_charge",
                        "service_charge",
                        "address",
                        "latitude",
                        "longitude",
                        "unit_facilities",
                        "apartment_facilities",
                        "point_of_interests",
                        "highlight",
                    ]:
                        if field in detail:
                            item[f"detail_{field}"] = detail[field]
                completed += 1
                if completed % 25 == 0 or completed == total_enrich:
                    logger.info(f"Enriched {completed}/{total_enrich} units")

        return listings

    def scrape_apartment_complexes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape comprehensive metadata for all apartment complexes in Indonesia."""
        logger.info("Extracting apartment URLs from sitemaps...")
        apt_slugs = set()
        sitemap_sub_files = [
            "sitemap-apartment-1.xml",
            "sitemap-apartment-2.xml",
            "sitemap-apartment-sell-1.xml",
            "sitemap-apartment-sell-2.xml",
        ]

        for sm in sitemap_sub_files:
            sm_url = f"{BASE_WEB_URL}/sitemap/{sm}"
            try:
                resp = self.session.get(sm_url, timeout=15)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                        u = loc.text or ""
                        u = u.replace(f"{BASE_WEB_URL}/en/", f"{BASE_WEB_URL}/")
                        path = u.replace(f"{BASE_WEB_URL}/", "").split("/")[0]
                        if path.startswith("sewa-apartemen-") or path.startswith("jual-apartemen-"):
                            apt_slugs.add(path)
            except Exception as e:
                logger.warning(f"Error parsing sitemap {sm}: {e}")

        slug_list = sorted(list(apt_slugs))
        if limit:
            slug_list = slug_list[:limit]

        logger.info(f"Found {len(slug_list)} unique apartment complexes to scrape.")

        complexes: List[Dict[str, Any]] = []

        def _fetch_apartment(slug: str) -> Optional[Dict[str, Any]]:
            url = f"{BASE_WEB_URL}/{slug}"
            try:
                resp = self.session.get(url, timeout=12)
                if resp.status_code != 200:
                    return None
                m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text)
                if not m:
                    return None
                data = json.loads(m.group(1))
                props = data.get("props", {}).get("pageProps", {})

                return {
                    "slug": props.get("slug"),
                    "name": props.get("name"),
                    "id": props.get("id"),
                    "type": props.get("type"),
                    "address": props.get("address"),
                    "latitude": props.get("latitude"),
                    "longitude": props.get("longitude"),
                    "phone_number": props.get("phone_number"),
                    "lowest_price": props.get("lowestPrice"),
                    "highest_price": props.get("highestPrice"),
                    "monthly_fee": props.get("monthlyFee"),
                    "facilities": props.get("facilities"),
                    "unit_types": props.get("jendela_unit_types"),
                    "total_unit": props.get("total_unit"),
                    "highlights": props.get("highlights"),
                    "url": url,
                    "scraped_at": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.debug(f"Failed to scrape apartment {slug}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_slug = {executor.submit(_fetch_apartment, slug): slug for slug in slug_list}
            count = 0
            for future in as_completed(future_to_slug):
                res = future.result()
                if res:
                    complexes.append(res)
                count += 1
                if count % 50 == 0 or count == len(slug_list):
                    logger.info(f"Scraped {count}/{len(slug_list)} apartment complexes")

        return complexes

    def query_autocomplete(self, query: str, listing_type_id: int = 1) -> Dict[str, Any]:
        """Search autocomplete API for quick lookups."""
        params = {"query": query, "listing_type_id": listing_type_id}
        url = f"{AUTOCOMPLETE_ENDPOINT}?{urlencode(params)}"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()


from indoscraping_core.output import write_latest_and_history


def save_results(data: Any, output_base: Path, date_str: str, extra_meta: Optional[Dict[str, Any]] = None) -> None:
    """Save results atomically to latest.json and history/YYYY-MM-DD.json with metadata sidecar."""
    output_base.mkdir(parents=True, exist_ok=True)
    history_dir = output_base / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    latest_file = str(output_base / "latest.json")
    history_file = str(history_dir / f"{date_str}.json")

    meta = {
        "scraper": "jendela360",
        "scraped_at": datetime.now().isoformat(),
        "total_records": len(data) if isinstance(data, list) else 1,
        "date": date_str,
    }
    if extra_meta:
        meta.update(extra_meta)

    write_latest_and_history(
        latest_path=latest_file,
        history_path=history_file,
        payload=data,
        meta=meta,
    )

    logger.info(f"Saved latest snapshot to: {latest_file} ({len(data)} items)")
    logger.info(f"Saved history snapshot to: {history_file}")


def main() -> None:
    default_date = datetime.now().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="Comprehensive scraper for Jendela360 property data")
    parser.add_argument(
        "--mode",
        choices=["listings", "apartments", "autocomplete"],
        default="listings",
        help="Scrape mode: 'listings' (search catalog), 'apartments' (complexes), or 'autocomplete'",
    )
    parser.add_argument(
        "--category",
        choices=["all", "apartment", "house", "land", "shophouse", "office"],
        default="all",
        help="Property category for listings (default: all)",
    )
    parser.add_argument(
        "--deal-type",
        choices=["all", "rent", "sell"],
        default="all",
        help="Deal type: rent (sewa), sell (jual), or all (default: all)",
    )
    parser.add_argument(
        "--limit-pages",
        type=int,
        default=5,
        help="Max pages per category/deal-type (default: 5; use 0 for unlimited / all pages)",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Enrich listings with deep unit specs (floors, directions, deposit, fee details)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent worker threads (default: 5)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Query string for autocomplete mode",
    )
    parser.add_argument(
        "--date",
        default=default_date,
        help="Snapshot date string (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/property/jendela360",
        help="Base directory for output JSON files",
    )

    args = parser.parse_args()

    scraper = Jendela360Scraper(max_workers=args.workers)

    if args.mode == "autocomplete":
        res = scraper.query_autocomplete(args.query)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.mode == "apartments":
        limit = None if args.limit_pages == 0 else args.limit_pages * 12
        results = scraper.scrape_apartment_complexes(limit=limit)
        out_path = Path(args.output_dir) / "apartments"
        save_results(results, out_path, args.date)
        return

    # Listings mode
    if args.category == "all":
        listing_types = [1, 2, 3, 4, 5]
    else:
        listing_types = [LISTING_TYPE_MAP[args.category]]

    if args.deal_type == "all":
        deal_types = [0, 1]
    else:
        deal_types = [DEAL_TYPE_MAP[args.deal_type]]

    max_pages = None if args.limit_pages == 0 else args.limit_pages

    results = scraper.scrape_listings(
        listing_types=listing_types,
        deal_types=deal_types,
        max_pages_per_category=max_pages,
        enrich_details=args.enrich,
    )

    out_path = Path(args.output_dir)
    save_results(results, out_path, args.date)


if __name__ == "__main__":
    main()
