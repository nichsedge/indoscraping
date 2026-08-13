from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, Iterable, List, Sequence, Optional


def get_installed_chrome_version() -> int:
    """Detect installed Google Chrome major version dynamically to avoid Selenium driver mismatches."""
    try:
        out = subprocess.check_output(["google-chrome", "--version"], text=True).strip()
        match = re.search(r"(\d+)\.\d+\.\d+", out)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 151


class DataQualityError(ValueError):
    """Raised when scraped output fails basic sanity checks."""


def clean_text(text: Optional[str]) -> str:
    """Trim whitespace, normalize spaces, and strip control characters."""
    if not text:
        return ""
    # Strip HTML tags if any residual tags exist
    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    # Replace non-breaking spaces and line breaks with normal space
    cleaned = cleaned.replace("\u00a0", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_numeric_price(price_raw: Any) -> int:
    """Extract clean integer price from various currency formats (e.g. 'Rp 15.000', 'Rp15.000,00', 15000)."""
    if isinstance(price_raw, (int, float)):
        return int(price_raw)
    if not price_raw:
        return 0
    text = str(price_raw)
    # Remove Rp and spaces
    digits_only = re.sub(r"[^\d]", "", text)
    if not digits_only:
        return 0
    try:
        return int(digits_only)
    except ValueError:
        return 0


def ensure_list_of_dicts(items: Any, *, min_items: int = 0) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        raise DataQualityError(f"Expected list, got {type(items).__name__}")
    for i, it in enumerate(items[:50]):
        if not isinstance(it, dict):
            raise DataQualityError(f"Item[{i}] expected dict, got {type(it).__name__}")
    if len(items) < min_items:
        raise DataQualityError(f"Expected at least {min_items} items, got {len(items)}")
    return items


def ensure_unique(items: Sequence[Dict[str, Any]], key: str) -> None:
    seen = set()
    dups = 0
    for it in items:
        v = it.get(key)
        if v is None:
            continue
        if v in seen:
            dups += 1
        else:
            seen.add(v)
    if dups:
        raise DataQualityError(f"Found {dups} duplicate '{key}' values")


def ensure_required_keys(items: Sequence[Dict[str, Any]], required: Iterable[str]) -> None:
    required = list(required)
    missing = {k: 0 for k in required}
    for it in items:
        for k in required:
            if k not in it or it.get(k) in (None, ""):
                missing[k] += 1
    failing = {k: n for k, n in missing.items() if n}
    if failing:
        raise DataQualityError(f"Missing/empty required keys: {failing}")


def validate_and_clean_ecommerce(items: List[Dict[str, Any]], *, strict: bool = False) -> List[Dict[str, Any]]:
    """Sanitizes and enforces data quality standards for e-commerce products."""
    items = ensure_list_of_dicts(items)
    cleaned_items = []

    for item in items:
        name = clean_text(item.get("productName") or item.get("name") or item.get("title"))
        if not name:
            if strict:
                raise DataQualityError("Product item missing valid productName/title")
            continue

        raw_price = item.get("priceRaw") or str(item.get("priceNumeric") or 0)
        num_price = item.get("priceNumeric")
        if num_price is None or num_price == 0:
            num_price = parse_numeric_price(raw_price)

        cleaned_item = {
            "productName": name,
            "priceRaw": f"Rp {num_price:,}".replace(",", ".") if num_price > 0 else clean_text(str(raw_price)),
            "priceNumeric": int(num_price),
            "category": clean_text(item.get("category")),
            "seller": clean_text(item.get("seller") or "Unknown"),
            "productUrl": clean_text(item.get("productUrl") or item.get("url")),
        }
        
        # Preserve extra metadata keys
        for k, v in item.items():
            if k not in cleaned_item and isinstance(v, (str, int, float, bool, list, dict)):
                cleaned_item[k] = clean_text(v) if isinstance(v, str) else v

        cleaned_items.append(cleaned_item)

    if strict:
        ensure_required_keys(cleaned_items, ["productName", "priceNumeric"])
        
    return cleaned_items
