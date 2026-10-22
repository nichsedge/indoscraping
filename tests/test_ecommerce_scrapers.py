from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from indomaret_scraper.scraper import (
    get_categories as indomaret_get_categories,
    get_products as indomaret_get_products,
    scrape_indomaret,
)
from alfagift_scraper.scraper import (
    get_categories as alfagift_get_categories,
    get_products as alfagift_get_products,
    scrape_alfagift,
)


def test_indomaret_get_categories_mock():
    mock_data = {
        "data": [
            {
                "id": 1,
                "name": "Supermarket",
                "permalink": "produk-supermarket",
                "categories": [
                    {
                        "id": 10,
                        "name": "Makanan",
                        "permalink": "makanan",
                        "subCategories": []
                    }
                ]
            }
        ]
    }
    with patch("indomaret_scraper.scraper.fetch_with_retry", return_value=mock_data):
        cats = indomaret_get_categories()
        assert len(cats) == 1
        assert cats[0]["permalink"] == "produk-supermarket"


def test_indomaret_scrape_flow_mock(tmp_path):
    cats_mock = [
        {
            "permalink": "produk-supermarket",
            "categories": [
                {"permalink": "makanan", "subCategories": []}
            ]
        }
    ]
    products_mock = {
        "content": [
            {
                "productName": "Indomie Goreng Spesial 85g",
                "price": 3100,
                "finalPrice": 2900,
                "permalink": "indomie-goreng-spesial",
                "brandName": "Indomie"
            },
            {
                "productName": "Susu UHT Full Cream 1L",
                "price": 18000,
                "finalPrice": 16500,
                "permalink": "susu-uht-full-cream",
                "brandName": "Ultra Milk"
            }
        ]
    }

    out_file = str(tmp_path / "indomaret.json")

    with patch("indomaret_scraper.scraper.get_categories", return_value=cats_mock):
        with patch("indomaret_scraper.scraper.get_products", return_value=products_mock):
            results = scrape_indomaret(
                date_str="2026-10-22",
                output_path=out_file,
                limit_categories=1,
                limit_articles=1
            )
            # Verify limit_articles=1 is respected
            assert len(results) == 1
            assert results[0]["productName"] == "Indomie Goreng Spesial 85g"
            # Verify price parsing preserved numeric price and raw string
            assert results[0]["priceNumeric"] == 2900
            assert "2.900" in results[0]["priceRaw"]
            assert results[0]["seller"] == "Indomie"
            assert "indomie-goreng-spesial" in results[0]["productUrl"]


def test_alfagift_scrape_flow_mock(tmp_path):
    cats_mock = ["101", "102"]
    page_mock = {
        "totalPage": 1,
        "products": [
            {
                "productName": "Beras Premium 5kg",
                "price": 69000,
                "priceNumeric": 69000,
                "productUrl": "https://alfagift.id/p/beras-premium"
            },
            {
                "productName": "Minyak Goreng 2L",
                "price": 34000,
                "priceNumeric": 34000,
                "productUrl": "https://alfagift.id/p/minyak-goreng"
            }
        ]
    }

    out_file = str(tmp_path / "alfagift.json")

    with patch("alfagift_scraper.scraper.get_categories", return_value=cats_mock):
        with patch("alfagift_scraper.scraper.get_products", return_value=page_mock):
            results = scrape_alfagift(
                date_str="2026-10-22",
                output_path=out_file,
                limit_categories=1,
                limit_articles=1
            )
            assert len(results) == 1
            assert results[0]["productName"] == "Beras Premium 5kg"
            assert results[0]["priceNumeric"] == 69000
