"""Panganku.org Indonesian Food & Nutrition Scraper.

Extracts the official Tabel Komposisi Pangan Indonesia (TKPI) from panganku.org
(Kementerian Kesehatan RI), including macro and micronutrients per 100g portion,
scientific names, categories, and edible portions (BDD).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
from curl_cffi import requests
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
logger = logging.getLogger("panganku")
logging.getLogger("curl_cffi").setLevel(logging.WARNING)

INDEX_URL = "https://www.panganku.org/id-ID/semua_nutrisi"
VIEW_URL = "https://www.panganku.org/id-ID/view"
DEFAULT_OUTPUT = "data/food/panganku/latest.json"
DEFAULT_PROGRESS = "data/food/panganku/.progress.json"

METADATA_KEYS = {
    "Kode",
    "Nama",
    "Nama Latin",
    "Asal",
    "Kelompok",
    "Kategori",
    "Tipe",
    "Tipe Bahan",
    "Deskripsi",
    "Keterangan",
    "jumlah",
}


def parse_numeric_value(value_str: Any) -> float | int | None:
    """Parse raw Indonesian nutritional text into float/int or None.

    E.g. '11.6 g' -> 11.6, '1,147.1 mg' -> 1147.1, '513 Kal' -> 513, '-' -> None.
    """
    if value_str is None:
        return None
    if isinstance(value_str, (int, float)):
        return value_str

    clean_str = str(value_str).replace("\u00a0", " ").replace(":", "").strip()
    if clean_str in ("", "-"):
        return None

    match = re.search(r"^-?[0-9,.]+", clean_str)
    if not match:
        return None

    num_str = match.group(0)
    if "," in num_str and "." in num_str:
        num_str = num_str.replace(",", "")
    elif "," in num_str:
        num_str = num_str.replace(",", "")

    try:
        val = float(num_str)
        return int(val) if val.is_integer() else val
    except ValueError:
        return None


def fetch_codes(session: requests.Session | None = None) -> list[str]:
    """Fetch all valid food codes from panganku.org index table."""
    logger.info("Fetching food index and codes from %s...", INDEX_URL)
    sess = session or requests.Session(impersonate="chrome")
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.panganku.org/id-ID/view",
    }
    resp = sess.get(INDEX_URL, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    codes: list[str] = []

    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            code = tds[1].get_text(strip=True)
            if re.match(r"^[A-Z]{2}\d{3}$", code):
                codes.append(code)

    logger.info("Total food codes found in national registry: %d", len(codes))
    return codes


def fetch_nutrisi_data(code: str, session: requests.Session | None = None) -> dict[str, Any]:
    """Fetch and parse nutritional data for a specific food code."""
    sess = session or requests.Session(impersonate="chrome")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Origin": "https://www.panganku.org",
        "Referer": INDEX_URL,
    }
    resp = sess.post(VIEW_URL, data={"haha": code}, headers=headers, timeout=12)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    result: dict[str, Any] = {"Kode": code}

    # 1. Detail metadata
    for tr in soup.find_all("tr"):
        b_tag = tr.find("b")
        if b_tag:
            key = b_tag.get_text(strip=True)
            tds = tr.find_all("td")
            if tds:
                val = tds[-1].get_text(strip=True)
                result[key] = val

    # 2. Base portion quantity and BDD (Berat Dapat Dimakan)
    strong_tags = soup.find_all("strong")
    if len(strong_tags) >= 2:
        result["jumlah"] = strong_tags[0].get_text(strip=True)
        bdd_match = re.search(r"(\d+)\s*%", strong_tags[1].get_text())
        result["BDD"] = int(bdd_match.group(1)) if bdd_match else None
    else:
        result.setdefault("jumlah", "100 g")
        result.setdefault("BDD", None)

    # 3. Nutrient composition table
    for tr in soup.find_all("tr"):
        first_td = tr.find("td")
        if first_td:
            i_tag = first_td.find("i")
            if i_tag:
                key = i_tag.get_text(strip=True)
                tds = tr.find_all("td")
                if tds:
                    val = tds[-1].get_text(strip=True)
                    parsed_val = parse_numeric_value(val)
                    if key and parsed_val is not None:
                        result[key] = parsed_val

    return result


def scrape_panganku(
    limit: int | None = None,
    workers: int = 5,
    max_retries: int = 3,
    progress_file: str = DEFAULT_PROGRESS,
    output_path: str = DEFAULT_OUTPUT,
) -> list[dict[str, Any]]:
    """Execute concurrent scrape with checkpointing and backoff."""
    os.makedirs(os.path.dirname(progress_file) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    results: list[dict[str, Any]] = []
    scraped_codes: set[str] = set()

    # Load incremental checkpoint if present
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if isinstance(cached, list):
                    results = cached
                    scraped_codes = {item.get("Kode") for item in results if item.get("Kode")}
                    logger.info("Resumed from checkpoint: %d records previously scraped.", len(results))
        except Exception as e:
            logger.warning("Corrupted progress file %s (%s). Starting fresh.", progress_file, e)
            results = []
            scraped_codes = set()

    # Fetch index of codes
    all_codes = fetch_codes()
    if limit is not None and limit > 0:
        all_codes = all_codes[:limit]

    codes_to_scrape = [c for c in all_codes if c not in scraped_codes]
    logger.info("Total codes in scope: %d (Remaining to fetch: %d)", len(all_codes), len(codes_to_scrape))

    if not codes_to_scrape:
        logger.info("All targeted food items already collected.")
        return results

    # Graceful SIGINT handler to preserve progress
    def handle_sigint(_sig: int, _frame: Any) -> None:
        logger.warning("\n[SIGINT] Interrupted! Preserving %d items to %s...", len(results), progress_file)
        try:
            with open(progress_file, "w", encoding="utf-8") as pf:
                json.dump(results, pf, ensure_ascii=False, indent=2)
        except Exception:
            pass
        sys.exit(130)

    signal.signal(signal.SIGINT, handle_sigint)

    def fetch_worker(code: str) -> dict[str, Any] | None:
        sess = requests.Session(impersonate="chrome")
        for attempt in range(1, max_retries + 1):
            try:
                # Polite random delay (100ms - 350ms)
                time.sleep(random.uniform(0.10, 0.35))
                data = fetch_nutrisi_data(code, session=sess)
                if data and data.get("Kode"):
                    return data
            except Exception as e:
                if attempt == max_retries:
                    logger.error("Permanently failed code %s after %d retries: %s", code, max_retries, e)
                    return None
                time.sleep((2**attempt) + random.uniform(0.2, 0.6))
        return None

    completed_count = len(results)
    total_scope = len(all_codes)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_code = {executor.submit(fetch_worker, c): c for c in codes_to_scrape}
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            completed_count += 1
            try:
                item_data = future.result()
                if item_data:
                    results.append(item_data)
                    logger.info(
                        "[%d/%d] Scraped: %s - %s",
                        completed_count,
                        total_scope,
                        item_data.get("Kode"),
                        item_data.get("Nama", "Unknown"),
                    )
                else:
                    logger.warning("[%d/%d] Skipped or failed: %s", completed_count, total_scope, code)
            except Exception as e:
                logger.error("Worker error for code %s: %s", code, e)

            # Checkpoint every 25 records
            if len(results) % 25 == 0:
                with open(progress_file, "w", encoding="utf-8") as pf:
                    json.dump(results, pf, ensure_ascii=False, indent=2)

    # Clean up checkpoint upon complete run
    if os.path.exists(progress_file) and len(results) >= len(all_codes):
        try:
            os.remove(progress_file)
        except OSError:
            pass

    return results


def main() -> None:
    """CLI execution entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape official Indonesian food & nutrition composition database from panganku.org"
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of food items to scrape (for testing)")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent HTTP worker pool threads (default: 5)")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Path to save output JSON")
    parser.add_argument("--progress-file", type=str, default=DEFAULT_PROGRESS, help="Checkpoint file path")
    args = parser.parse_args()

    items = scrape_panganku(
        limit=args.limit,
        workers=args.workers,
        progress_file=args.progress_file,
        output_path=args.output,
    )

    if not items:
        logger.error("No items scraped or loaded.")
        sys.exit(1)

    # Data Quality Validation
    ensure_list_of_dicts(items)
    ensure_required_keys(items, ["Kode", "Nama"])
    ensure_unique(items, "Kode")

    # Lineage Metadata
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta = collect_lineage(scraper_id="panganku")
    meta.update(
        {
            "date": today_str,
            "count": len(items),
            "source": "https://www.panganku.org",
            "description": "Tabel Komposisi Pangan Indonesia (TKPI) - Kementerian Kesehatan RI",
        }
    )

    history_path = f"data/food/panganku/history/{today_str}.json"
    write_latest_and_history(
        latest_path=args.output,
        history_path=history_path,
        payload=items,
        meta=meta,
    )

    logger.info("Successfully saved %d verified nutrition records to %s", len(items), args.output)
    logger.info("Historical snapshot created at %s", history_path)


if __name__ == "__main__":
    main()
