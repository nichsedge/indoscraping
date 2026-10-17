from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from indoscraping.scraper.property.sewakost import SewaKostScraper, save_kost_results


def test_sewakost_scraper_init():
    scraper = SewaKostScraper(timeout=10)
    assert scraper.timeout == 10


def test_scrape_kost_detail_mock():
    scraper = SewaKostScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
      <body>
        <h1>Kost Cozy Palmerah Slipi</h1>
        <p>Harga sewa: Rp 1.500.000 / bulan</p>
        <p>Hubungi: 0812-3456-7890</p>
        <ul>
          <li>Fasilitas: AC, WiFi, Kamar Mandi Dalam, Kasur</li>
        </ul>
      </body>
    </html>
    """

    with patch("indoscraping.scraper.property.sewakost.requests.get", return_value=mock_resp):
        res = scraper.scrape_kost_detail("https://www.sewakost.com/sample")
        assert res is not None
        assert res["title"] == "Kost Cozy Palmerah Slipi"
        assert res["min_price"] == 1500000
        assert "081234567890" in res["phone_numbers"]
        assert "AC" in res["facilities"]
        assert "WiFi" in res["facilities"]


def test_save_kost_results(tmp_path):
    data = [{"title": "Kost Test", "url": "https://example.com", "min_price": 1000000}]
    save_kost_results(data, tmp_path, "2026-10-17")

    latest_file = tmp_path / "latest.json"
    sidecar_file = tmp_path / "latest.meta.json"
    history_file = tmp_path / "history" / "2026-10-17.json"

    assert latest_file.exists()
    assert sidecar_file.exists()
    assert history_file.exists()

    with open(sidecar_file) as f:
        meta = json.load(f)
        assert meta["scraper"] == "sewakost"
        assert meta["total_records"] == 1
