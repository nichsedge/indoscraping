from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

from indoscraping.tools.publish import (
    generate_hf_readme,
    DATASET_METADATA,
    publish_to_huggingface,
)


def test_generate_hf_readme():
    cfg = DATASET_METADATA["panganku"]
    readme = generate_hf_readme(cfg, total_records=1146, repo_id="testuser/panganku-nutrition")
    assert "---" in readme
    assert "license: cc-by-4.0" in readme
    assert "testuser/panganku-nutrition" in readme
    assert "Kode" in readme
    assert "1146" in readme


def test_publish_to_hf_missing_token(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(ValueError, match="HF_TOKEN environment variable is not set"):
        publish_to_huggingface("panganku")
