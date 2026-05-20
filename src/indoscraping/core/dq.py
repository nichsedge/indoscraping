from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence


class DataQualityError(ValueError):
    """Raised when scraped output fails basic sanity checks."""


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
