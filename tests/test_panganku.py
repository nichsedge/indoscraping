from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from indoscraping.scraper.food.panganku import (
    parse_numeric_value,
    fetch_codes,
    fetch_nutrisi_data,
    scrape_panganku,
)


def test_parse_numeric_value():
    assert parse_numeric_value("11.6 g") == 11.6
    assert parse_numeric_value("1,147.1 mg") == 1147.1
    assert parse_numeric_value("513 Kal") == 513
    assert parse_numeric_value("435") == 435
    assert parse_numeric_value(25.5) == 25.5
    assert parse_numeric_value("-") is None
    assert parse_numeric_value("") is None
    assert parse_numeric_value(None) is None
    assert parse_numeric_value("  : 6.4 g  ") == 6.4


def test_fetch_codes_parsing():
    html_mock = """
    <table>
        <tbody>
            <tr><td>1</td><td>GP054</td><td>Abon ikan</td></tr>
            <tr><td>2</td><td>GP053</td><td>Abon haruwan</td></tr>
            <tr><td>3</td><td>INVALID</td><td>Bad code</td></tr>
        </tbody>
    </table>
    """
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = html_mock
    mock_session.get.return_value = mock_resp

    codes = fetch_codes(session=mock_session)
    assert codes == ["GP054", "GP053"]


def test_fetch_nutrisi_data_parsing():
    html_mock = """
    <table>
        <tr><td><b>Kode</b></td><td>GP054</td></tr>
        <tr><td><b>Nama</b></td><td>Abon ikan</td></tr>
        <tr><td><b>Kategori</b></td><td>Ikan/Kerang/Udang dll</td></tr>
    </table>
    <strong>100 g</strong>
    <strong>dapat dimakan 100 %</strong>
    <table>
        <tr><td><i>Water</i></td><td>: 6.4 g</td></tr>
        <tr><td><i>Energy</i></td><td>: 435 Kal</td></tr>
        <tr><td><i>Protein</i></td><td>: 27.2 g</td></tr>
    </table>
    """
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = html_mock
    mock_session.post.return_value = mock_resp

    data = fetch_nutrisi_data("GP054", session=mock_session)
    assert data["Kode"] == "GP054"
    assert data["Nama"] == "Abon ikan"
    assert data["Kategori"] == "Ikan/Kerang/Udang dll"
    assert data["jumlah"] == "100 g"
    assert data["BDD"] == 100
    assert data["Water"] == 6.4
    assert data["Energy"] == 435
    assert data["Protein"] == 27.2


def test_scrape_panganku_with_limit(tmp_path):
    out_file = tmp_path / "latest.json"
    prog_file = tmp_path / "progress.json"

    with patch("indoscraping.scraper.food.panganku.fetch_codes", return_value=["GP054", "GP053"]):
        with patch("indoscraping.scraper.food.panganku.fetch_nutrisi_data") as mock_fetch:
            mock_fetch.side_effect = [
                {"Kode": "GP054", "Nama": "Abon ikan", "Energy": 435},
                {"Kode": "GP053", "Nama": "Abon haruwan", "Energy": 513},
            ]
            results = scrape_panganku(
                limit=2,
                workers=1,
                progress_file=str(prog_file),
                output_path=str(out_file),
            )
            assert len(results) == 2
            assert results[0]["Kode"] == "GP054"
            assert results[1]["Kode"] == "GP053"
