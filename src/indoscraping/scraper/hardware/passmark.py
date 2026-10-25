"""PassMark Hardware Benchmarks Scraper.

Scrapes live, trusted 3D graphics (G3D Mark) and CPU compute (CPU Mark) benchmark
scores from PassMark Software (videocardbenchmark.net and cpubenchmark.net).
Provides online, verified benchmark ratings to calculate Price-to-Performance
metrics across computer hardware without hardcoding.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup
from indoscraping_core.dq import ensure_list_of_dicts, ensure_required_keys
from indoscraping_core.output import write_latest_and_history

logger = logging.getLogger("passmark")

GPU_URLS = [
    ("https://www.videocardbenchmark.net/high_end_gpus.html", "High-End"),
    ("https://www.videocardbenchmark.net/mid_range_gpus.html", "Mid-Range"),
]

CPU_URLS = [
    ("https://www.cpubenchmark.net/high_end_cpus.html", "High-End"),
    ("https://www.cpubenchmark.net/mid_range_cpus.html", "Mid-Range"),
]

DEFAULT_OUTPUT_DIR = Path("data/benchmarks/passmark")


def fetch_chart(
    client: httpx.Client,
    url: str,
    category: str,
    segment: str,
) -> list[dict[str, Any]]:
    """Scrape PassMark chart list items from HTML."""
    logger.info("Fetching %s (%s) from %s...", category, segment, url)
    try:
        resp = client.get(url, timeout=15.0)
        resp.raise_for_status()
    except httpx.HTTPError as err:
        logger.error("Failed to fetch %s: %s", url, err)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    chart = soup.find("ul", {"class": "chartlist"})
    if not chart:
        logger.warning("No chart list found in %s", url)
        return []

    results: list[dict[str, Any]] = []
    scraped_at = datetime.now(UTC).isoformat()

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

    logger.info("Extracted %d %s benchmark items from %s chart.", len(results), category, segment)
    return results


def scrape_passmark_benchmarks() -> list[dict[str, Any]]:
    """Execute complete scrape of live PassMark GPU and CPU benchmark databases."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    all_benchmarks: list[dict[str, Any]] = []

    with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
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
    deduped: list[dict[str, Any]] = []
    for item in all_benchmarks:
        key = (item["name"].lower(), item["category"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    logger.info("Total unique benchmark items scraped: %d", len(deduped))
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape live PassMark GPU and CPU benchmark ratings")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save scraped benchmark JSON files",
    )
    args = parser.parse_args()

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    logger.info("Starting live online PassMark benchmark ingestion...")
    start_time = time.time()

    benchmarks = scrape_passmark_benchmarks()
    if not benchmarks:
        logger.error("PassMark scrape yielded 0 items.")
        sys.exit(1)

    # Validate Data Quality
    ensure_list_of_dicts(benchmarks, "passmark")
    ensure_required_keys(benchmarks, ["name", "category", "score", "benchmark", "source"], "passmark")

    # Output persistence
    latest_path = args.output_dir / "latest.json"
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    history_path = args.output_dir / f"passmark_{today_str}.json"

    meta = {
        "scraper": "passmark",
        "category": "benchmarks",
        "record_count": len(benchmarks),
        "gpu_count": sum(1 for b in benchmarks if b["category"] == "GPU"),
        "cpu_count": sum(1 for b in benchmarks if b["category"] == "CPU"),
        "scraped_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(time.time() - start_time, 2),
    }

    write_latest_and_history(
        latest_path=latest_path,
        history_path=history_path,
        payload=benchmarks,
        meta=meta,
    )

    logger.info(
        "Successfully saved %d benchmarks (%d GPUs, %d CPUs) to %s",
        len(benchmarks),
        meta["gpu_count"],
        meta["cpu_count"],
        latest_path,
    )


if __name__ == "__main__":
    main()
