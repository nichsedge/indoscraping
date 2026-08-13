import pytest

from indoscraping_core.dq import (
    DataQualityError,
    clean_text,
    parse_numeric_price,
    ensure_list_of_dicts,
    ensure_required_keys,
    ensure_unique,
    validate_and_clean_ecommerce,
)
from indoscraping_core.schema_drift import (
    SchemaDriftError,
    EcommerceProductModel,
    detect_schema_drift,
)


def test_ensure_list_of_dicts_ok():
    ensure_list_of_dicts([{"a": 1}, {"a": 2}])


def test_ensure_list_of_dicts_type_error():
    with pytest.raises(DataQualityError):
        ensure_list_of_dicts({"a": 1})


def test_required_keys_missing():
    with pytest.raises(DataQualityError):
        ensure_required_keys([{"url": "x"}, {}], ["url", "title"])


def test_unique_detects_dups():
    with pytest.raises(DataQualityError):
        ensure_unique([{"url": "x"}, {"url": "x"}], "url")


def test_clean_text():
    assert clean_text("  Indomie   Goreng \n Special ") == "Indomie Goreng Special"
    assert clean_text("<span>Harga <b>Termurah</b></span>") == "Harga Termurah"


def test_parse_numeric_price():
    assert parse_numeric_price("Rp 15.000") == 15000
    assert parse_numeric_price("Rp 25.500") == 25500
    assert parse_numeric_price(50000) == 50000


def test_validate_and_clean_ecommerce():
    raw_payload = [
        {
            "productName": "  Xiaomi   Redmi Note 12  \n",
            "priceRaw": "Rp 2.500.000",
            "category": "Handphone & Tablet",
            "seller": "Official Store  "
        }
    ]
    cleaned = validate_and_clean_ecommerce(raw_payload)
    assert len(cleaned) == 1
    assert cleaned[0]["productName"] == "Xiaomi Redmi Note 12"
    assert cleaned[0]["priceNumeric"] == 2500000
    assert cleaned[0]["priceRaw"] == "Rp 2.500.000"
    assert cleaned[0]["seller"] == "Official Store"


def test_schema_drift_detection_ok():
    valid_data = [
        {"productName": "Susu UHT 1L", "priceNumeric": 18000, "priceRaw": "Rp 18.000"}
    ]
    report = detect_schema_drift(valid_data, EcommerceProductModel, "test_ok", strict_raise=True)
    assert not report.drift_detected
    assert report.valid_items == 1


def test_schema_drift_detection_raises_on_dom_change():
    broken_dom_data = [
        {"productName": "", "priceNumeric": 0, "priceRaw": "N/A"}
    ]
    with pytest.raises(SchemaDriftError):
        detect_schema_drift(broken_dom_data, EcommerceProductModel, "test_drift", max_null_rate=0.2, strict_raise=True)
