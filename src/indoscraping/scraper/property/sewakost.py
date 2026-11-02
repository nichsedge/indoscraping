"""Scraper for SewaKost.com (direct-from-owner kost directory in Indonesia).

Extracts kost listings with direct owner phone/WhatsApp contacts,
monthly rent prices, full facility specs, and addresses.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests
from indoscraping_core.output import write_latest_and_history

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sewakost")

BASE_URL = "https://www.sewakost.com"

# Common districts around Jakarta Pusat & Barat
DEFAULT_AREAS = [
    "jakarta/jakarta-barat/palmerah",
    "jakarta/jakarta-pusat/tanah-abang",
    "jakarta/jakarta-barat/grogol-petamburan",
    "jakarta/jakarta-barat/kebon-jeruk",
    "jakarta/jakarta-pusat/cempaka-putih",
    "jakarta/jakarta-selatan/kebayoran-baru",
    "jakarta/jakarta-selatan/setiabudi",
    "jakarta/jakarta-selatan/tebet",
    "jakarta/jakarta-selatan/cilandak",
    "jakarta/jakarta-selatan/mampang-prapatan",
    "jakarta/jakarta-timur/matraman",
    "jakarta/jakarta-utara/kelapa-gading",
    "jakarta",
]


class SewaKostScraper:
    def __init__(self, timeout: int = 12, max_workers: int = 5):
        self.timeout = timeout
        self.max_workers = max_workers

    def fetch_area_listings(
        self, area_path: str, max_pages: int = 2, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch list of kost listings from a specific area category."""
        base_area_url = f"{BASE_URL}/kost/{area_path.strip('/')}/"
        logger.info(f"Scanning category: {base_area_url}")

        kost_urls = set()

        for page in range(1, max_pages + 1):
            page_url = base_area_url if page == 1 else f"{base_area_url}page/{page}/"
            try:
                resp = requests.get(page_url, impersonate="chrome", timeout=self.timeout)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                links = soup.select("h2 a, h3 a, a[title]")
                found_page = 0
                for a in links:
                    href = a.get("href", "")
                    full_href = urljoin(BASE_URL, href)
                    # Strictly ensure it is a real Jakarta kost listing ending with listing ID
                    if re.search(r"/kost/jakarta/[a-z0-9\-]+/[a-z0-9\-]+-\d{4,8}/?$", full_href):
                        kost_urls.add(full_href)
                        found_page += 1
                logger.info(f"  Page {page}: found {found_page} listings")
                if limit and len(kost_urls) >= limit:
                    break
            except Exception as e:
                logger.warning(f"Failed page {page} for {area_path}: {e}")
                break

        url_list = list(kost_urls)
        if limit:
            url_list = url_list[:limit]

        logger.info(f"Total unique kost listings to scrape for {area_path}: {len(url_list)}")

        listings: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_kost_detail, url): url for url in url_list}
            for future in as_completed(future_to_url):
                try:
                    data = future.result()
                    if data:
                        data["_area_category"] = area_path
                        listings.append(data)
                except Exception as e:
                    url = future_to_url[future]
                    logger.warning(f"Failed scraping kost detail for {url}: {e}")

        return listings

    def scrape_kost_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape details, price, facilities, and owner contact from a kost page."""
        try:
            resp = requests.get(url, impersonate="chrome", timeout=self.timeout)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")

            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""

            text = soup.get_text()

            # Extract prices (Rp ...)
            price_matches = re.findall(r"Rp\s*[0-9\.\,]+", text)
            prices_clean = []
            for p in price_matches:
                clean_p = p.replace("Rp", "").replace(".", "").replace(",", "").strip()
                if clean_p.isdigit() and 300000 <= int(clean_p) <= 15000000:
                    prices_clean.append(int(clean_p))

            min_price = min(prices_clean) if prices_clean else None
            max_price = max(prices_clean) if prices_clean else None

            # Extract Indonesian phone / WhatsApp numbers (08... or +628...)
            phone_matches = re.findall(r"(?:08|\+628)[0-9\-\s]{8,15}", text)
            clean_phones = list(
                {re.sub(r"[^\d+]", "", ph) for ph in phone_matches if len(re.sub(r"[^\d+]", "", ph)) >= 10}
            )

            # Extract facilities tags
            facilities = []
            for f_kw in [
                "AC",
                "WiFi",
                "Kamar Mandi Dalam",
                "Kamar Mandi Luar",
                "Spring Bed",
                "Kasur",
                "Lemari",
                "Meja",
                "Kursi",
                "Water Heater",
                "Cuci Setrika",
                "Dapur",
                "Parkir Motor",
                "Parkir Mobil",
                "CCTV",
                "Security",
            ]:
                if re.search(rf"\b{re.escape(f_kw)}\b", text, re.I):
                    facilities.append(f_kw)

            return {
                "title": title,
                "url": url,
                "min_price": min_price,
                "max_price": max_price,
                "phone_numbers": clean_phones,
                "facilities": facilities,
                "scraped_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.debug(f"Failed to scrape {url}: {e}")
            return None


def save_kost_results(data: Any, output_base: Path, date_str: str) -> None:
    output_base.mkdir(parents=True, exist_ok=True)
    history_dir = output_base / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    latest_file = output_base / "latest.json"
    history_file = history_dir / f"{date_str}.json"

    # Merge with existing records by URL
    combined: Dict[str, Any] = {}
    if latest_file.exists():
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
                if isinstance(prev_data, list):
                    for item in prev_data:
                        if isinstance(item, dict) and item.get("url"):
                            combined[item["url"]] = item
        except Exception as e:
            logger.warning(f"Could not load previous latest.json for merging: {e}")

    for item in data:
        if isinstance(item, dict) and item.get("url"):
            combined[item["url"]] = item

    merged_list = list(combined.values())

    meta = {
        "scraper": "sewakost",
        "scraped_at": datetime.now().isoformat(),
        "total_records": len(merged_list),
        "newly_scraped": len(data),
        "date": date_str,
    }

    write_latest_and_history(
        latest_path=str(latest_file),
        history_path=str(history_file),
        payload=merged_list,
        meta=meta,
    )

    logger.info(f"Saved latest snapshot to: {latest_file} ({len(merged_list)} total items, {len(data)} in this run)")
    logger.info(f"Saved history snapshot to: {history_file}")


def main() -> None:
    default_date = datetime.now().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="Scrape affordable kost listings from SewaKost.com")
    parser.add_argument(
        "--area",
        default="all",
        help="Area subpath on SewaKost or 'all' to scrape all key Jakarta commuter districts",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Max pages of listings to scrape per area (default: 3)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/property/sewakost",
        help="Output directory path",
    )
    parser.add_argument(
        "--limit-articles",
        "--limit",
        type=int,
        default=None,
        help="Max number of kost listings to scrape per area",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of concurrent detail scraping workers (default: 8)",
    )
    parser.add_argument(
        "--date",
        default=default_date,
        help="Crawl date string",
    )

    args = parser.parse_args()

    areas_to_scrape = DEFAULT_AREAS if args.area.lower() == "all" else [a.strip() for a in args.area.split(",") if a.strip()]

    scraper = SewaKostScraper(max_workers=args.workers)
    all_results = []
    for area in areas_to_scrape:
        logger.info(f"--- Scraping Area: {area} ---")
        area_res = scraper.fetch_area_listings(area, max_pages=args.max_pages, limit=args.limit_articles)
        all_results.extend(area_res)

    out_path = Path(args.output_dir)
    save_kost_results(all_results, out_path, args.date)


if __name__ == "__main__":
    main()
