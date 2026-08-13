from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Sequence
from pydantic import BaseModel, Field, ValidationError


class SchemaDriftError(RuntimeError):
    """Raised when target site HTML/API structure changed and selectors no longer match."""
    pass


class EcommerceProductModel(BaseModel):
    productName: str = Field(..., min_length=2)
    priceNumeric: int = Field(..., ge=1)
    priceRaw: Optional[str] = None
    category: Optional[str] = None
    seller: Optional[str] = None
    productUrl: Optional[str] = None


class NewsArticleModel(BaseModel):
    title: str = Field(..., min_length=3)
    url: str = Field(...)
    date: Optional[str] = None
    category: Optional[str] = None


class SchemaHealthReport(BaseModel):
    scraper_id: str
    total_items: int
    valid_items: int
    invalid_items: int
    null_rates: Dict[str, float]
    drift_detected: bool
    warnings: List[str]


def detect_schema_drift(
    items: List[Dict[str, Any]],
    model_class: Type[BaseModel],
    scraper_id: str,
    critical_fields: Optional[Sequence[str]] = None,
    max_null_rate: float = 0.3,
    min_items_threshold: int = 1,
    strict_raise: bool = True
) -> SchemaHealthReport:
    """Validates items against a Pydantic schema and measures null field ratios on critical fields.
    
    If critical fields have null/invalid rates exceeding `max_null_rate`, or if zero items match,
    a `SchemaDriftError` is raised so CI/CD or monitoring alerts immediately.
    """
    total_items = len(items)
    warnings: List[str] = []

    if total_items < min_items_threshold:
        msg = f"SCHEMA DRIFT ALERT [{scraper_id}]: Scraper extracted {total_items} items (expected at least {min_items_threshold}). Target site DOM or API schema likely changed!"
        if strict_raise:
            raise SchemaDriftError(msg)
        return SchemaHealthReport(
            scraper_id=scraper_id,
            total_items=total_items,
            valid_items=0,
            invalid_items=total_items,
            null_rates={},
            drift_detected=True,
            warnings=[msg]
        )

    valid_count = 0
    invalid_count = 0
    field_null_counts: Dict[str, int] = {}
    model_fields = list(model_class.model_fields.keys())

    # Default critical fields to required fields in the model
    if critical_fields is None:
        critical_fields = [
            name for name, field_info in model_class.model_fields.items()
            if field_info.is_required()
        ]

    for f_name in model_fields:
        field_null_counts[f_name] = 0

    for item in items:
        for f_name in model_fields:
            val = item.get(f_name)
            if val in (None, "", 0, "0", "N/A", "Unknown"):
                field_null_counts[f_name] += 1

        try:
            model_class.model_validate(item)
            valid_count += 1
        except ValidationError:
            invalid_count += 1

    null_rates: Dict[str, float] = {
        f_name: round(count / total_items, 4) for f_name, count in field_null_counts.items()
    }

    drift_detected = False

    # Check null rates ONLY for critical fields
    for f_name in critical_fields:
        rate = null_rates.get(f_name, 0.0)
        if rate > max_null_rate:
            drift_detected = True
            warn_msg = f"High null rate ({rate * 100:.1f}%) for critical field '{f_name}' in '{scraper_id}'"
            warnings.append(warn_msg)

    if invalid_count / total_items > max_null_rate:
        drift_detected = True
        warnings.append(f"High schema validation failure rate: {invalid_count}/{total_items} items failed Pydantic validation")

    if drift_detected and strict_raise:
        summary = "; ".join(warnings)
        raise SchemaDriftError(
            f"SCHEMA DRIFT DETECTED [{scraper_id}]: Target site layout changed! Details: {summary}"
        )

    return SchemaHealthReport(
        scraper_id=scraper_id,
        total_items=total_items,
        valid_items=valid_count,
        invalid_items=invalid_count,
        null_rates=null_rates,
        drift_detected=drift_detected,
        warnings=warnings
    )
