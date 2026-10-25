from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from indoscraping.scraper.hardware.viraindo import parse_viraindo_table
from indoscraping.scraper.hardware.enterkomputer import fetch_category_products, CATEGORY_MAP


SAMPLE_VIRAINDO_HTML = """
<table>
  <tr>
    <td>Intel Core i5-13400F 2.5GHz Box</td>
    <td>3.150.000</td>
    <td>AMD Ryzen 5 5600 3.5Ghz Box</td>
    <td>1.850.000</td>
  </tr>
  <tr>
    <td>Intel Core i7-14700K Box</td>
    <td>Call</td>
    <td>AMD Ryzen 7 7800X3D Box</td>
    <td>7.500.000</td>
  </tr>
</table>
"""


def test_parse_viraindo_table():
    products = parse_viraindo_table(SAMPLE_VIRAINDO_HTML, category="proc")
    assert len(products) == 3  # "Call" row must be filtered out

    p1 = products[0]
    assert p1["name"] == "Intel Core i5-13400F 2.5GHz Box"
    assert p1["price"] == 3150000
    assert p1["price_raw"] == "Rp 3.150.000"
    assert p1["category"] == "proc"
    assert p1["source"] == "viraindo"

    p2 = products[1]
    assert p2["name"] == "AMD Ryzen 5 5600 3.5Ghz Box"
    assert p2["price"] == 1850000

    p3 = products[2]
    assert p3["name"] == "AMD Ryzen 7 7800X3D Box"
    assert p3["price"] == 7500000


def test_parse_viraindo_limit():
    products = parse_viraindo_table(SAMPLE_VIRAINDO_HTML, category="proc", limit_items=2)
    assert len(products) == 2


def test_fetch_enterkomputer_products_mock():
    mock_payload = {
        "status": True,
        "result": [
            {
                "PPRNT": [
                    {
                        "PCHLD": [
                            {
                                "PLIST": [
                                    {
                                        "PCODE": 12345,
                                        "PNAME": "Intel Core i5-12400F",
                                        "KNAME": "Processor",
                                        "PPRCZ": [1800000, 1850000],
                                        "PWGHT": 500,
                                        "PLINK": "Intel-Core-i5-12400F",
                                        "PIMGZ": ["https://example.com/img.jpg"],
                                        "PLOLZ": ["https://tokopedia.com/item"],
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch("curl_cffi.requests.post", return_value=mock_resp):
        products = fetch_category_products(cat_id="17", cat_slug="processor", max_pages=1)
        assert len(products) == 1
        item = products[0]
        assert item["product_id"] == "12345"
        assert item["name"] == "Intel Core i5-12400F"
        assert item["price"] == 1800000
        assert item["price_raw"] == "Rp 1.800.000"
        assert item["category"] == "processor"
        assert item["source"] == "enterkomputer"
        assert item["url"] == "https://www.enterkomputer.com/detail/12345/Intel-Core-i5-12400F"


def test_category_map_integrity():
    assert "processor" in CATEGORY_MAP
    assert "vga" in CATEGORY_MAP
    assert "solid-state-drive" in CATEGORY_MAP
