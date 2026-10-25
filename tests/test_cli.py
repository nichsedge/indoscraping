from __future__ import annotations

import json
from unittest.mock import patch
import pytest
from rich.table import Table

from indoscraping.cli import (
    SCRAPERS,
    list_scrapers_table,
    view_output_statistics,
    inspect_scraper_data,
    export_scraper_data,
    main,
)


def test_scrapers_catalog():
    assert "banks" not in SCRAPERS
    assert "rumah123" in SCRAPERS
    assert "sewakost" in SCRAPERS
    assert "kompas" in SCRAPERS
    assert "alfagift" in SCRAPERS
    assert "enterkomputer" in SCRAPERS
    assert "viraindo" in SCRAPERS
    assert "lhkpn" in SCRAPERS

    categories = {info["category"] for info in SCRAPERS.values()}
    assert categories == {"News", "E-Commerce", "Property", "Hardware", "Governance"}


def test_list_scrapers_table():
    table = list_scrapers_table()
    assert isinstance(table, Table)
    assert table.title == "Available Scrapers"
    col_names = [col.header for col in table.columns]
    assert "ID" in col_names
    assert "Scraper Name" in col_names
    assert "Category" in col_names


def test_view_output_statistics_runs():
    # Should run and render table without throwing exceptions
    view_output_statistics()


def test_inspect_scraper_data_missing(capsys):
    inspect_scraper_data("invalid_scraper_id")
    # Should not crash and handle invalid ID gracefully


def test_inspect_scraper_data_existing(tmp_path, capsys):
    test_json = tmp_path / "test.json"
    test_json.write_text(json.dumps([{"title": "Item 1", "price_raw": "Rp 500.000", "url": "https://example.com"}]))

    with patch.dict(SCRAPERS, {"test_scraper": {"name": "Test", "output_path": str(test_json)}}):
        inspect_scraper_data("test_scraper")


def test_cli_subcommands():
    with patch("sys.argv", ["indoscraping", "list"]):
        main()

    with patch("sys.argv", ["indoscraping", "status"]):
        main()

    with patch("sys.argv", ["indoscraping", "inspect", "sewakost"]):
        main()


def test_export_scraper_data_parquet_and_csv(tmp_path):
    test_json = tmp_path / "test.json"
    test_json.write_text(json.dumps([{"title": "Item A", "price_raw": "Rp 1.000.000", "specs": {"area": "100m"}}]))

    out_parquet = tmp_path / "export.parquet"
    out_csv = tmp_path / "export.csv"

    with patch.dict(SCRAPERS, {"test_scraper": {"name": "Test", "output_path": str(test_json)}}):
        # Parquet export
        ok_pq = export_scraper_data("test_scraper", export_format="parquet", output_path=str(out_parquet))
        assert ok_pq is True
        assert out_parquet.exists()

        # CSV export
        ok_csv = export_scraper_data("test_scraper", export_format="csv", output_path=str(out_csv))
        assert ok_csv is True
        assert out_csv.exists()

    with patch("sys.argv", ["indoscraping", "export", "rumah123", "--format", "csv"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0


def test_cli_canonical_and_aliases():
    assert "tokopedia" in SCRAPERS
    assert "tokped" in SCRAPERS
    assert "blibli" in SCRAPERS
    assert "blibli-search" in SCRAPERS


def test_cli_check_browser():
    with patch("sys.argv", ["indoscraping", "check-browser"]):
        main()

