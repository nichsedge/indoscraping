from __future__ import annotations

from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
import pytest

from indoscraping.scraper.news.detik import (
    get_categories_urls as detik_categories,
    scrape_detik_article,
)
from indoscraping.scraper.news.bisnis import (
    get_categories as bisnis_categories,
    scrape_article as bisnis_scrape_article,
)
from indoscraping.scraper.news.kompas import (
    get_categories as kompas_categories,
    scrape_kompas_article,
)
from indoscraping.scraper.news.cnn import (
    get_categories as cnn_categories,
    scrape_article as cnn_scrape_article,
)
from indoscraping.scraper.news.cnbc import (
    scrape_article as cnbc_scrape_article,
)
from indoscraping.scraper.news.narasi import scrape_narasi


# Detik Tests
def test_detik_categories_mock():
    html = """
    <nav class="static-nav">
      <a href="https://news.detik.com/indeks">News</a>
      <a href="https://finance.detik.com/indeks">Finance</a>
      <a href="https://detik.com/about">About</a>
    </nav>
    """
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status.return_value = None

    with patch("indoscraping.scraper.news.detik.requests.get", return_value=mock_resp):
        urls = detik_categories()
        assert len(urls) == 2
        assert urls[0] == ("News", "https://news.detik.com/indeks")
        assert urls[1] == ("Finance", "https://finance.detik.com/indeks")


def test_detik_scrape_article_mock():
    html = """
    <html>
      <head><title>Detik Test Article</title></head>
      <body>
        <h1 class="detail__title">Sidak Flyover Selesai</h1>
        <div class="detail__date">Kamis, 22 Okt 2026 21:00 WIB</div>
        <div class="detail__author">Budi Reporter</div>
        <div class="detail__body-text">
          <p>Pembangunan flyover telah rampung.</p>
          <p>Proyek ini berjalan sesuai jadwal.</p>
        </div>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status.return_value = None

    with patch("indoscraping.scraper.news.detik.requests.get", return_value=mock_resp):
        data = scrape_detik_article("https://news.detik.com/berita/sample")
        assert data["title"] == "Sidak Flyover Selesai"
        assert "Budi Reporter" in data["author"]
        assert "Pembangunan flyover telah rampung." in data["content"]


# Bisnis.com Tests
def test_bisnis_categories_mock():
    html = """
    <label class="indeks-radio">
      <input type="radio" onclick="changeCategory('categoryId=43')">Ekonomi
    </label>
    <label class="indeks-radio">
      <input type="radio" onclick="changeCategory('categoryId=194')">Market
    </label>
    """
    mock_resp = MagicMock()
    mock_resp.text = html

    with patch("indoscraping.scraper.news.bisnis.requests.get", return_value=mock_resp):
        cats = bisnis_categories()
        assert cats.get("Ekonomi") == "43"
        assert cats.get("Market") == "194"


def test_bisnis_scrape_article_mock():
    html = """
    <html>
      <body>
        <h1 class="detailsTitleCaption">Bisnis Indonesia Bertumbuh</h1>
        <div class="detailsLead">Pertumbuhan kuartal ini solid.</div>
        <div class="detailsAttributeDates">22 Oktober 2026</div>
        <div class="detailsAuthor">
          <div class="detailsAuthorItem">Penulis : John Doe</div>
          <div class="detailsAuthorItem">Editor : Jane Doe</div>
        </div>
        <article class="detailsContent">
          <p>Pertumbuhan ekonomi nasional mencatatkan kenaikan yang memuaskan.</p>
        </article>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.content = html.encode("utf-8")
    mock_resp.raise_for_status.return_value = None

    with patch("indoscraping.scraper.news.bisnis.requests.get", return_value=mock_resp):
        data = bisnis_scrape_article("https://kabar24.bisnis.com/read/sample")
        assert data["title"] == "Bisnis Indonesia Bertumbuh"
        assert data["author"] == "John Doe"
        assert data["editor"] == "Jane Doe"
        assert len(data["content"]) == 1


# Kompas Tests
def test_kompas_categories():
    cats = kompas_categories()
    assert "news" in cats
    assert "ekonomi" in cats


def test_kompas_scrape_article_mock():
    html = """
    <html>
      <head><title>Berita Terkini Kompas</title></head>
      <body>
        <div class="read__time">22/10/2026, 20:00 WIB</div>
        <div class="credit-title-nameEditor">Ahmad Editor,</div>
        <div class="read__content">
          <p>Paragraf berita pertama mengenai layanan kesehatan.</p>
        </div>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.content = html.encode("utf-8")

    with patch("indoscraping.scraper.news.kompas.requests.get", return_value=mock_resp):
        data = scrape_kompas_article("https://nasional.kompas.com/read/sample")
        assert data["title"] == "Berita Terkini Kompas"
        assert "Ahmad Editor" in data["journalists"]
        assert "Paragraf berita pertama mengenai layanan kesehatan." in data["content"]


# CNN Indonesia Tests
def test_cnn_categories_mock():
    html = """
    <select id="kanalOption">
      <option value="1" data-label="nasional">Nasional</option>
      <option value="2" data-label="internasional">Internasional</option>
    </select>
    """
    mock_resp = MagicMock()
    mock_resp.text = html

    with patch("indoscraping.scraper.news.cnn.requests.get", return_value=mock_resp):
        cats = cnn_categories()
        assert len(cats) == 2
        assert cats[0]["label"] == "nasional"
        assert cats[0]["id"] == "1"


def test_cnn_scrape_article_mock():
    html = """
    <html>
      <head><title>CNN Headline</title></head>
      <body>
        <h1 class="mb-2 text-[28px] leading-9 text-cnn_black">Judul CNN</h1>
        <div class="text-cnn_grey text-sm">Kamis, 22 Okt 2026 21:00 WIB</div>
        <div class="detail-text text-cnn_black">
          <p>Paragraf berita CNN Indonesia terpercaya.</p>
        </div>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.text = html

    with patch("indoscraping.scraper.news.cnn.requests.get", return_value=mock_resp):
        data = cnn_scrape_article("https://www.cnnindonesia.com/nasional/sample")
        assert data["title"] == "Judul CNN"
        assert "Paragraf berita CNN Indonesia" in data["content"]


# CNBC Indonesia Tests
def test_cnbc_scrape_article_mock():
    html = """
    <html>
      <head><title>CNBC Market Update</title></head>
      <body>
        <h1>CNBC Market Update</h1>
        <div class="text-cm text-gray">22 October 2026 15:00</div>
        <div class="author">Market Reporter</div>
        <div class="detail_text">
          <p>Indeks Harga Saham Gabungan (IHSG) menguat signifikan hari ini.</p>
        </div>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.text = html
    mock_resp.raise_for_status.return_value = None

    with patch("indoscraping.scraper.news.cnbc.requests.get", return_value=mock_resp):
        data = cnbc_scrape_article("https://www.cnbcindonesia.com/market/sample")
        assert data["title"] == "CNBC Market Update"
        assert "22 October 2026" in data["date"]


# Narasi Tests
def test_narasi_api_mock():
    mock_json = {
        "data": {
            "articles": [
                {
                    "title": "Investigasi Narasi",
                    "short": "Ringkasan liputan mendalam",
                    "publishDate": "2026-10-22",
                    "slug": "investigasi-narasi-1"
                }
            ]
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_json
    mock_resp.raise_for_status.return_value = None

    with patch("indoscraping.scraper.news.narasi.requests.get", return_value=mock_resp):
        items = scrape_narasi(limit_articles=1)
        assert len(items) == 1
        assert items[0]["title"] == "Investigasi Narasi"
        assert items[0]["link"] == "https://narasi.tv/investigasi-narasi-1"
