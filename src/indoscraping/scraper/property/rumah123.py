"""Scraper for Rumah123.com (Leading Indonesian Property Portal).

Extracts property listings (houses, apartments, lands, shophouses) for sale (jual)
and rent (sewa), including prices, locations, bedrooms, bathrooms, surface areas,
and agent information using curl_cffi Chrome impersonation.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests
from indoscraping_core.output import write_latest_and_history
from indoscraping_core.lineage import collect_lineage

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rumah123")

BASE_URL = "https://www.rumah123.com"


def parse_idr_price(price_str: str) -> Optional[int]:
    """Parse Indonesian property price format to integer IDR.

    Handles 'Rp 33,8 Miliar', 'Rp 35 Juta /bulan', 'Rp 1.500.000.000', etc.
    """
    if not price_str:
        return None
    clean = price_str.lower().replace("rp", "").strip()
    clean = clean.split("/")[0].strip()

    m_match = re.search(r"([\d\.,]+)\s*miliar", clean)
    if m_match:
        val = float(m_match.group(1).replace(".", "").replace(",", "."))
        return round(val * 1_000_000_000)

    j_match = re.search(r"([\d\.,]+)\s*juta", clean)
    if j_match:
        val = float(j_match.group(1).replace(".", "").replace(",", "."))
        return round(val * 1_000_000)

    digits = re.sub(r"[^\d]", "", clean)
    return int(digits) if digits else None


class Rumah123Scraper:
    def __init__(self, timeout: int = 15, max_workers: int = 5):
        self.timeout = timeout
        self.max_workers = max_workers

    def build_search_url(
        self, deal_type: str = "jual", city: str = "dki-jakarta", category: str = "rumah", page: int = 1
    ) -> str:
        """Construct the search URL for Rumah123."""
        clean_deal = deal_type.lower().strip()
        clean_city = city.lower().strip().replace(" ", "-")
        clean_cat = category.lower().strip()
        return f"{BASE_URL}/{clean_deal}/{clean_city}/{clean_cat}/?page={page}"

    def parse_listing_card(self, card: BeautifulSoup, deal_type: str, category: str) -> Optional[Dict[str, Any]]:
        """Parse an individual propertyCardRoot element."""
        try:
            a_tag = card.select_one("a[href*='/properti/'], a[href*='/perumahan-baru/']")
            if not a_tag:
                return None

            href = a_tag.get("href", "")
            full_url = urljoin(BASE_URL, href)

            title_elem = card.select_one("h2.propertyCardTitleText, h2, a[title]")
            title = (
                a_tag.get("title")
                or (title_elem.get_text(strip=True) if title_elem else "")
            ).strip()

            if not title:
                return None

            # Price extraction
            price_elem = card.select_one("span.text-primary.font-bold, [class*='price']")
            price_raw = price_elem.get_text(strip=True) if price_elem else ""
            numeric_price = parse_idr_price(price_raw)

            # Location extraction
            loc_elem = card.select_one("p.propertyCardLocationRoot, [class*='Location']")
            location = loc_elem.get_text(strip=True) if loc_elem else ""

            # Description snippet
            desc_elem = card.select_one("p.propertyCardMetaDescription, [class*='Description']")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Agent name
            agent_elem = card.select_one("p.propertyCardAgentName, [class*='AgentName']")
            agent_name = agent_elem.get_text(strip=True) if agent_elem else ""

            # Specs (Bedrooms, Bathrooms, LT, LB)
            specs: Dict[str, Any] = {}
            for span in card.select("span.flex"):
                text = span.get_text(strip=True)
                if text.startswith("LT:"):
                    specs["land_area"] = text.replace("LT:", "").strip()
                elif text.startswith("LB:"):
                    specs["building_area"] = text.replace("LB:", "").strip()

            # Badges / Chips
            chips = [c.get_text(strip=True) for c in card.select("[class*='propertyChips'], [class*='Chip']")]

            return {
                "title": title,
                "url": full_url,
                "deal_type": deal_type,
                "category": category,
                "price_raw": price_raw,
                "price_numeric": numeric_price,
                "location": location,
                "description": description,
                "agent": agent_name,
                "specs": specs,
                "chips": chips,
                "scraped_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.debug(f"Error parsing card: {e}")
            return None

    def fetch_search_page(
        self, deal_type: str = "jual", city: str = "dki-jakarta", category: str = "rumah", page: int = 1
    ) -> List[Dict[str, Any]]:
        """Fetch and parse property listings from a single paginated search page."""
        url = self.build_search_url(deal_type=deal_type, city=city, category=category, page=page)
        logger.info(f"Fetching: {url}")

        try:
            resp = requests.get(url, impersonate="chrome120", timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch {url} (HTTP {resp.status_code})")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("article.propertyCardRoot, div.propertyCardRoot")
            logger.info(f"Found {len(cards)} listing cards on page {page}")

            listings = []
            for card in cards:
                item = self.parse_listing_card(card, deal_type=deal_type, category=category)
                if item:
                    listings.append(item)

            return listings

        except Exception as e:
            logger.error(f"Error requesting page {page}: {e}")
            return []

    def scrape_catalog(
        self,
        deal_type: str = "jual",
        city: str = "dki-jakarta",
        category: str = "rumah",
        max_pages: int = 1,
        limit_articles: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Scrape multiple pages with optional article quota and multithreading."""
        all_listings: List[Dict[str, Any]] = []

        # First page
        first_page_items = self.fetch_search_page(deal_type=deal_type, city=city, category=category, page=1)
        all_listings.extend(first_page_items)

        if limit_articles and len(all_listings) >= limit_articles:
            return all_listings[:limit_articles]

        if max_pages > 1:
            pages = list(range(2, max_pages + 1))
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_page = {
                    executor.submit(
                        self.fetch_search_page,
                        deal_type=deal_type,
                        city=city,
                        category=category,
                        page=p,
                    ): p
                    for p in pages
                }
                for future in as_completed(future_to_page):
                    try:
                        items = future.result()
                        all_listings.extend(items)
                        if limit_articles and len(all_listings) >= limit_articles:
                            break
                    except Exception as e:
                        p = future_to_page[future]
                        logger.warning(f"Page {p} thread error: {e}")

        # Deduplicate by URL
        seen_urls = set()
        deduped = []
        for l in all_listings:
            u = l.get("url")
            if u and u not in seen_urls:
                seen_urls.add(u)
                deduped.append(l)

        if limit_articles:
            deduped = deduped[:limit_articles]

        logger.info(f"Scraped {len(deduped)} unique property listings.")
        return deduped


def main() -> None:
    default_date = datetime.now().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="Scrape property listings from Rumah123.com")
    parser.add_argument(
        "--deal-type",
        choices=["jual", "sewa"],
        default="jual",
        help="Deal type: 'jual' (for sale) or 'sewa' (for rent)",
    )
    parser.add_argument(
        "--category",
        choices=["rumah", "apartemen", "tanah", "ruko"],
        default="rumah",
        help="Property category (default: rumah)",
    )
    parser.add_argument(
        "--city",
        default="dki-jakarta",
        help="City or region slug (e.g., 'dki-jakarta', 'tangerang', 'bandung', 'surabaya')",
    )
    parser.add_argument(
        "--limit-pages",
        type=int,
        default=1,
        help="Maximum pages to scrape (default: 1)",
    )
    parser.add_argument(
        "--limit-articles",
        "--limit",
        type=int,
        default=None,
        help="Maximum listings quota for early stopping / testing",
    )
    parser.add_argument(
        "--output",
        default="data/property/rumah123/latest.json",
        help="Path for output JSON file",
    )
    parser.add_argument(
        "--date",
        default=default_date,
        help="Snapshot date string (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    scraper = Rumah123Scraper()
    results = scraper.scrape_catalog(
        deal_type=args.deal_type,
        city=args.city,
        category=args.category,
        max_pages=args.limit_pages,
        limit_articles=args.limit_articles,
    )

    if not results:
        logger.warning("No listings were extracted from Rumah123.")
        return

    output_path = args.output
    history_path = f"data/property/rumah123/history/{args.date}.json"

    meta = collect_lineage("rumah123")
    meta.update({
        "deal_type": args.deal_type,
        "category": args.category,
        "city": args.city,
        "count": len(results),
        "date": args.date,
    })

    write_latest_and_history(
        latest_path=output_path,
        history_path=history_path,
        payload=results,
        meta=meta,
    )

    logger.info(f"Saved {len(results)} items to {output_path}")
    logger.info(f"Saved historical snapshot to {history_path}")


if __name__ == "__main__":
    main()
