"""Scraper for SewaKost.com (direct-from-owner kost directory in Indonesia).

Extracts kost listings with direct owner phone/WhatsApp contacts,
monthly rent prices, full facility specs, and addresses.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
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
]


class SewaKostScraper:
    def __init__(self, timeout: int = 12):
        self.timeout = timeout

    def fetch_area_listings(self, area_path: str, max_pages: int = 2) -> List[Dict[str, Any]]:
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
                    if "/kost/" in href and href != base_area_url and not href.endswith(f"/{area_path.split('/')[-1]}/"):
                        kost_urls.add(urljoin(BASE_URL, href))
                        found_page += 1
                logger.info(f"  Page {page}: found {found_page} listings")
            except Exception as e:
                logger.warning(f"Failed page {page} for {area_path}: {e}")
                break

        logger.info(f"Total unique kost listings to scrape for {area_path}: {len(kost_urls)}")

        listings = []
        for url in kost_urls:
            data = self.scrape_kost_detail(url)
            if data:
                data["_area_category"] = area_path
                listings.append(data)

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

    latest_file = str(output_base / "latest.json")
    history_file = str(history_dir / f"{date_str}.json")

    meta = {
        "scraper": "sewakost",
        "scraped_at": datetime.now().isoformat(),
        "total_records": len(data),
        "date": date_str,
    }

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

    parser = argparse.ArgumentParser(description="Scrape affordable kost listings from SewaKost.com")
    parser.add_argument(
        "--area",
        default="jakarta/jakarta-barat/palmerah",
        help="Area subpath on SewaKost (e.g., 'jakarta/jakarta-barat/palmerah' or 'jakarta/jakarta-pusat/tanah-abang')",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=2,
        help="Max pages of listings to scrape per area (default: 2)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/property/sewakost",
        help="Output directory path",
    )
    parser.add_argument(
        "--date",
        default=default_date,
        help="Crawl date string",
    )

    args = parser.parse_args()

    scraper = SewaKostScraper()
    results = scraper.fetch_area_listings(args.area, max_pages=args.max_pages)

    out_path = Path(args.output_dir)
    save_kost_results(results, out_path, args.date)


if __name__ == "__main__":
    main()
