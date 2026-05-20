import pytest

from indoscraping.core.dq import DataQualityError, ensure_list_of_dicts, ensure_required_keys, ensure_unique


def test_ensure_list_of_dicts_ok():
    ensure_list_of_dicts([{"a": 1}, {"a": 2}])


def test_ensure_list_of_dicts_type_error():
    with pytest.raises(DataQualityError):
        ensure_list_of_dicts({"a": 1})


def test_required_keys_missing():
    with pytest.raises(DataQualityError):
        ensure_required_keys([{ "url": "x" }, {}], ["url", "title"])


def test_unique_detects_dups():
    with pytest.raises(DataQualityError):
        ensure_unique([{ "url": "x" }, {"url": "x"}], "url")
