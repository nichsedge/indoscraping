from __future__ import annotations

from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
import pytest

from indoscraping.scraper.property.rumah123 import (
    Rumah123Scraper,
    parse_idr_price,
)


def test_parse_idr_price():
    assert parse_idr_price("Rp 33,8 Miliar") == 33800000000
    assert parse_idr_price("Rp 2,5 Miliar") == 2500000000
    assert parse_idr_price("Rp 850 Juta") == 850000000
    assert parse_idr_price("Rp 35 Juta /bulan") == 35000000
    assert parse_idr_price("Rp 1.500.000.000") == 1500000000
    assert parse_idr_price("") is None
    assert parse_idr_price(None) is None


def test_build_search_url():
    scraper = Rumah123Scraper()
    url = scraper.build_search_url(deal_type="jual", city="dki-jakarta", category="rumah", page=2)
    assert url == "https://www.rumah123.com/jual/dki-jakarta/rumah/?page=2"

    url_rent = scraper.build_search_url(deal_type="sewa", city="tangerang selatan", category="apartemen", page=1)
    assert url_rent == "https://www.rumah123.com/sewa/tangerang-selatan/apartemen/?page=1"


def test_parse_listing_card():
    scraper = Rumah123Scraper()
    html = """
    <article class="propertyCardRoot">
      <a href="/properti/jakarta-selatan/rumah-mewah-hos123/" title="Rumah Mewah Kemang">
        <h2 class="propertyCardTitleText">Rumah Mewah Kemang</h2>
      </a>
      <span class="text-primary font-bold">Rp 15 Miliar</span>
      <p class="propertyCardLocationRoot">Kemang, Jakarta Selatan</p>
      <p class="propertyCardMetaDescription">Rumah mewah dengan kolam renang pribadi</p>
      <p class="propertyCardAgentName">Budi Agen</p>
      <span class="flex">LT:500 m²</span>
      <span class="flex">LB:450 m²</span>
      <p class="propertyChipsPremier">Premier</p>
    </article>
    """
    card = BeautifulSoup(html, "html.parser").select_one("article.propertyCardRoot")
    parsed = scraper.parse_listing_card(card, deal_type="jual", category="rumah")

    assert parsed is not None
    assert parsed["title"] == "Rumah Mewah Kemang"
    assert parsed["url"] == "https://www.rumah123.com/properti/jakarta-selatan/rumah-mewah-hos123/"
    assert parsed["price_raw"] == "Rp 15 Miliar"
    assert parsed["price_numeric"] == 15000000000
    assert parsed["location"] == "Kemang, Jakarta Selatan"
    assert parsed["agent"] == "Budi Agen"
    assert parsed["specs"]["land_area"] == "500 m²"
    assert parsed["specs"]["building_area"] == "450 m²"
    assert "Premier" in parsed["chips"]


def test_fetch_search_page_mock():
    scraper = Rumah123Scraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
      <body>
        <article class="propertyCardRoot">
          <a href="/properti/test/sample-1/">
            <h2 class="propertyCardTitleText">Sample Property 1</h2>
          </a>
          <span class="text-primary font-bold">Rp 2 Miliar</span>
          <p class="propertyCardLocationRoot">Tebet, Jakarta Selatan</p>
        </article>
      </body>
    </html>
    """
    with patch("indoscraping.scraper.property.rumah123.requests.get", return_value=mock_resp):
        items = scraper.fetch_search_page(page=1)
        assert len(items) == 1
        assert items[0]["title"] == "Sample Property 1"
        assert items[0]["price_numeric"] == 2000000000
