from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from indoscraping.scraper.governance.lhkpn import (
    parse_detail,
    parse_max_results,
    save_lhkpn_results,
    CATEGORY_MAP,
)


SAMPLE_MODAL_HTML = """
<div id="modal-perbandingan-announcement-lhkpn">
  <table class="table">
    <tbody class="data_perbandingan_lhkpn">
      <tr>
        <th>A.</th>
        <th>TANAH DAN BANGUNAN</th>
        <th>Rp. 200.000.000</th>
      </tr>
      <tr>
        <td>1.</td>
        <td>Tanah dan Bangunan Seluas 500 m2 di JAKARTA SELATAN</td>
        <td>150.000.000</td>
      </tr>
      <tr>
        <td>2.</td>
        <td>Tanah Seluas 1000 m2 di BOGOR</td>
        <td>50.000.000</td>
      </tr>
      <tr>
        <th>B.</th>
        <th>ALAT TRANSPORTASI DAN MESIN</th>
        <th>Rp. 50.000.000</th>
      </tr>
      <tr>
        <td>1.</td>
        <td>Mobil Toyota Alphard Tahun 2022</td>
        <td>50.000.000</td>
      </tr>
      <tr>
        <th>C.</th>
        <th>KAS DAN SETARA KAS</th>
        <th>Rp. 10.000.000</th>
      </tr>
      <tr>
        <td colspan="3">KAS DAN SETARA KAS 10.000.000</td>
      </tr>
    </tbody>
  </table>
</div>
"""


def test_parse_detail_modal():
    details = parse_detail(SAMPLE_MODAL_HTML)
    assert "tanah_bangunan" in details
    assert "transportasi" in details
    assert "kas" in details

    # Tanah dan Bangunan items
    tb = details["tanah_bangunan"]
    assert len(tb) == 2
    assert "JAKARTA SELATAN" in tb[0]["description"]
    assert tb[0]["value"] == "150.000.000"
    assert "BOGOR" in tb[1]["description"]
    assert tb[1]["value"] == "50.000.000"

    # Transportasi
    tr = details["transportasi"]
    assert len(tr) == 1
    assert "Alphard" in tr[0]["description"]
    assert tr[0]["value"] == "50.000.000"

    # Kas fallback
    kas = details["kas"]
    assert len(kas) >= 1
    assert kas[0]["value"] == "10.000.000"


def test_parse_max_results():
    assert parse_max_results("5") == 5
    assert parse_max_results("inf") == float("inf")
    assert parse_max_results("INF") == float("inf")

    with pytest.raises(Exception):
        parse_max_results("invalid")


def test_save_lhkpn_results(tmp_path):
    out_file = tmp_path / "latest.json"
    sample_data = [
        {
            "name": "TEST OFFICIAL",
            "lembaga": "KPK",
            "unit_kerja": "PIMPINAN",
            "jabatan": "KETUA",
            "tanggal_lapor": "2026-01-01",
            "jenis_laporan": "Khusus",
            "total_harta": "Rp.10.000.000.000",
            "tanah_bangunan": [],
        }
    ]

    save_lhkpn_results(
        sample_data,
        output_path=str(out_file),
        format_type="csv",
        date_str="2026-10-25",
    )

    assert out_file.exists()
    assert (tmp_path / "latest.meta.json").exists()
    assert (tmp_path / "history" / "2026-10-25.json").exists()
    assert (tmp_path / "latest.csv").exists()

    with open(out_file) as f:
        loaded = json.load(f)
    assert len(loaded) == 1
    assert loaded[0]["name"] == "TEST OFFICIAL"
