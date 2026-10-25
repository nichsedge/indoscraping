"""PassMark Hardware Benchmarks Scraper.

Scrapes live, trusted 3D graphics (G3D Mark) and CPU compute (CPU Mark) benchmark
scores from PassMark Software (videocardbenchmark.net and cpubenchmark.net).
Provides online, verified benchmark ratings to calculate Price-to-Performance
metrics across computer hardware without hardcoding.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from indoscraping_core.dq import ensure_list_of_dicts, ensure_required_keys
from indoscraping_core.lineage import collect_lineage
from indoscraping_core.output import write_latest_and_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("passmark")

GPU_URLS = [
    ("https://www.videocardbenchmark.net/high_end_gpus.html", "High-End"),
    ("https://www.videocardbenchmark.net/mid_range_gpus.html", "Mid-Range"),
]

CPU_URLS = [
    ("https://www.cpubenchmark.net/high_end_cpus.html", "High-End"),
    ("https://www.cpubenchmark.net/mid_range_cpus.html", "Mid-Range"),
]

DEFAULT_OUTPUT_DIR = Path("data/hardware/benchmarks")


def fetch_chart(
    client: httpx.Client,
    url: str,
    category: str,
    segment: str,
) -> List[Dict[str, Any]]:
    """Scrape PassMark chart list items from HTML."""
    logger.info(f"Fetching {category} ({segment}) from {url}...")
    try:
        resp = client.get(url, timeout=15.0)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    chart = soup.find("ul", {"class": "chartlist"})
    if not chart:
        logger.warning(f"No chart list found in {url}")
        return []

    results: List[Dict[str, Any]] = []
    scraped_at = datetime.now().isoformat()

    for li in chart.find_all("li"):
        prd = li.find("span", {"class": "prdname"})
        cnt = li.find("span", {"class": "count"})
        if not prd or not cnt:
            continue

        raw_name = prd.get_text(strip=True)
        raw_score = cnt.get_text(strip=True)
        score_digits = re.sub(r"[^\d]", "", raw_score)

        if not raw_name or not score_digits:
            continue

        score = int(score_digits)
        results.append(
            {
                "name": raw_name,
                "category": category,
                "segment": segment,
                "score": score,
                "benchmark": "PassMark G3D Mark" if category == "GPU" else "PassMark CPU Mark",
                "source": "passmark",
                "url": url,
                "scraped_at": scraped_at,
            }
        )

    logger.info(f"Extracted {len(results)} {category} benchmark items from {segment} chart.")
    return results


def scrape_passmark_benchmarks() -> List[Dict[str, Any]]:
    """Execute complete scrape of live PassMark GPU and CPU benchmark databases."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    client = httpx.Client(headers=headers, follow_redirects=True, timeout=20.0)
    all_benchmarks: List[Dict[str, Any]] = []

    # 1. Scrape GPUs
    for url, segment in GPU_URLS:
        items = fetch_chart(client, url, category="GPU", segment=segment)
        all_benchmarks.extend(items)
        time.sleep(0.5)

    # 2. Scrape CPUs
    for url, segment in CPU_URLS:
        items = fetch_chart(client, url, category="CPU", segment=segment)
        all_benchmarks.extend(items)
        time.sleep(0.5)

    # Deduplicate by (name, category)
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for item in all_benchmarks:
        key = (item["name"].lower(), item["category"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    logger.info(f"Total unique benchmark items scraped: {len(deduped):,}")
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape live PassMark GPU and CPU benchmark ratings")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save scraped benchmark JSON snapshots",
    )
    args = parser.parse_args()

    start_time = time.time()
    logger.info("Starting PassMark hardware benchmark scrape...")

    items = scrape_passmark_benchmarks()

    if not items:
        logger.error("No benchmark items scraped. Aborting.")
        sys.exit(1)

    # Data Quality Validation
    ensure_list_of_dicts(items)
    ensure_required_keys(items, ["name", "category", "score", "benchmark", "scraped_at"])

    # Output persistence
    today_str = datetime.now().strftime("%Y-%m-%d")
    latest_path = str(args.output_dir / "latest.json")
    history_path = str(args.output_dir / "history" / f"{today_str}.json")

    meta = {
        "scraper": "passmark",
        "category": "Hardware Benchmarks",
        "total_items": len(items),
        "gpu_count": len([x for x in items if x["category"] == "GPU"]),
        "cpu_count": len([x for x in items if x["category"] == "CPU"]),
        "scraped_at": datetime.now().isoformat(),
    }

    write_latest_and_history(
        latest_path=latest_path,
        history_path=history_path,
        payload=items,
        meta=meta,
    )

    duration = time.time() - start_time
    logger.info(f"PassMark scrape completed in {duration:.2f}s.")
    logger.info(f"Saved {len(items):,} live benchmarks to: {latest_path} and {history_path}")


if __name__ == "__main__":
    main()
