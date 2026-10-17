from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from indoscraping.scraper.property.jendela360 import Jendela360Scraper, save_results


def test_jendela360_scraper_init():
    scraper = Jendela360Scraper(max_workers=2)
    assert scraper.max_workers == 2
    assert "user-agent" in [k.lower() for k in scraper.session.headers.keys()]


def test_fetch_search_page_mock():
    scraper = Jendela360Scraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "current_page": 1,
        "last_page": 10,
        "total": 120,
        "data": [
            {
                "id": 101,
                "code": "TEST01",
                "name": "Luxury Suite",
                "price": 10000000,
                "bedroom": 2,
                "bathroom": 1,
            }
        ],
    }

    with patch.object(scraper.session, "get", return_value=mock_resp):
        res = scraper.fetch_search_page(listing_type_id=1, deal_type=0, page=1)
        assert res["total"] == 120
        assert len(res["data"]) == 1
        assert res["data"][0]["code"] == "TEST01"


def test_query_autocomplete_mock():
    scraper = Jendela360Scraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "apartments": [
            {"id": 6, "name": "1 Park Residence", "areas": "Jakarta Selatan"}
        ],
        "districts": [
            {"id": 25, "slug": "kuningan", "label": "Kuningan - Jakarta Selatan"}
        ],
    }

    with patch.object(scraper.session, "get", return_value=mock_resp):
        res = scraper.query_autocomplete(query="kuningan", listing_type_id=1)
        assert len(res["apartments"]) == 1
        assert res["apartments"][0]["name"] == "1 Park Residence"
        assert len(res["districts"]) == 1


def test_fetch_unit_detail_mock():
    scraper = Jendela360Scraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_next_data = {
        "props": {
            "pageProps": {
                "unitDetailProps": {
                    "data": {
                        "id": 70679,
                        "code": "1PAC068",
                        "floor": 8,
                        "view_direction": "City View",
                        "furnished": "full",
                        "selling_price": 0,
                        "price_per_12_months": 202000000,
                    }
                }
            }
        }
    }
    mock_resp.text = f'<html><body><script id="__NEXT_DATA__" type="application/json">{json.dumps(mock_next_data)}</script></body></html>'

    with patch.object(scraper.session, "get", return_value=mock_resp):
        detail = scraper.fetch_unit_detail("sewa", "1-park-residence", "1PAC068")
        assert detail is not None
        assert detail["code"] == "1PAC068"
        assert detail["floor"] == 8
        assert detail["view_direction"] == "City View"


def test_save_results(tmp_path):
    data = [{"id": 1, "code": "U01", "name": "Test Unit"}]
    save_results(data, tmp_path, "2026-10-17")

    latest_file = tmp_path / "latest.json"
    sidecar_file = tmp_path / "latest.meta.json"
    history_file = tmp_path / "history" / "2026-10-17.json"

    assert latest_file.exists()
    assert sidecar_file.exists()
    assert history_file.exists()

    with open(latest_file) as f:
        loaded = json.load(f)
        assert len(loaded) == 1
        assert loaded[0]["code"] == "U01"

    with open(sidecar_file) as f:
        meta = json.load(f)
        assert meta["scraper"] == "jendela360"
        assert meta["total_records"] == 1
