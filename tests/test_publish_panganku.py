from __future__ import annotations

import os
from unittest.mock import patch
import pytest

from indoscraping.tools.publish_panganku import (
    generate_hf_readme,
    publish_to_huggingface,
    publish_to_kaggle,
)


def test_generate_hf_readme():
    readme = generate_hf_readme(total_records=1146, repo_id="testuser/panganku-nutrition")
    assert "---" in readme
    assert "license: cc-by-4.0" in readme
    assert "testuser/panganku-nutrition" in readme
    assert "Kode" in readme
    assert "1146" in readme


def test_publish_to_hf_missing_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with patch("indoscraping.tools.publish_panganku._ensure_secrets"):
        with pytest.raises(ValueError, match="HF_TOKEN environment variable is not set"):
            publish_to_huggingface()


def test_publish_to_kaggle_missing_token(monkeypatch):
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    with patch("indoscraping.tools.publish_panganku._ensure_secrets"):
        with pytest.raises(ValueError, match="KAGGLE_API_TOKEN environment variable is not set"):
            publish_to_kaggle()
