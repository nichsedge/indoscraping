"""Programmatic Publisher for Panganku.org Indonesian Food & Nutrition Dataset (TKPI).

Publishes the validated Panganku TKPI dataset across open data platforms:
- Hugging Face Datasets (via HfApi & HF_TOKEN)
- Kaggle Datasets (via KaggleApi & modern KAGGLE_API_TOKEN)
- GitHub Releases CDN (via gh CLI & GH_TOKEN)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any

import pandas as pd
from huggingface_hub import HfApi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("publish_panganku")

DEFAULT_INPUT_JSON = "data/food/panganku/latest.json"
HF_REPO_NAME = "panganku-indonesian-food-nutrition"
KAGGLE_SLUG = "panganku-food-nutrition"
GITHUB_REPO = "nichsedge/indoscraping"
GITHUB_TAG = "dataset-panganku-latest"


def _ensure_secrets(secrets_file: str | None = None) -> None:
    """Auto-load secrets file if keys are not already in environment."""
    target_file = secrets_file or os.path.expanduser("~/.secrets")
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export "):
                        line = line[7:]
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ and v:
                            os.environ[k] = v
        except Exception:
            pass

DATASET_FIELDS = {
    "Kode": "Unique national food code (e.g. GP054)",
    "Nama": "General food name in Indonesian",
    "Nama Latin": "Scientific / Latin taxonomic name",
    "Asal": "Regional origin / province in Indonesia",
    "Kategori": "Food category (e.g. Ikan/Kerang/Udang, Serealia, Sayuran)",
    "Tipe Bahan": "State of item (Mentah / Olahan)",
    "Keterangan": "Additional descriptions or processing notes",
    "jumlah": "Reference sample weight (default: 100 g)",
    "BDD": "Berat Dapat Dimakan (Edible portion percentage, %)",
    "Water": "Water content (Air) in grams (g)",
    "Energy": "Energy in Kal / kcal",
    "Protein": "Protein content in grams (g)",
    "Fat": "Total lipid/fat content in grams (g)",
    "CHO": "Carbohydrates (Karbohidrat) in grams (g)",
    "Fibre": "Dietary fibre (Serat) in grams (g)",
    "ASH": "Mineral Ash (Abu) in grams (g)",
    "Ca": "Calcium (Kalsium) in milligrams (mg)",
    "P": "Phosphorus (Fosfor) in milligrams (mg)",
    "Fe": "Iron (Besi) in milligrams (mg)",
    "Na": "Sodium (Natrium) in milligrams (mg)",
    "K": "Potassium (Kalium) in milligrams (mg)",
    "Cu": "Copper (Tembaga) in milligrams (mg)",
    "Zn": "Zinc (Seng) in milligrams (mg)",
    "Vit. A": "Vitamin A in micrograms (mcg)",
    "Carotenes": "Carotenes in micrograms (mcg)",
    "Re": "Retinol in micrograms (mcg)",
    "Vit. B1": "Thiamine (Vitamin B1) in milligrams (mg)",
    "Vit. B2": "Riboflavin (Vitamin B2) in milligrams (mg)",
    "Niacin": "Niacin in milligrams (mg)",
    "Vit. C": "Vitamin C in milligrams (mg)",
}


def generate_hf_readme(total_records: int, repo_id: str) -> str:
    """Generate Markdown dataset card with valid YAML frontmatter for Hugging Face."""
    fields_table = "\n".join(f"| `{col}` | {desc} |" for col, desc in DATASET_FIELDS.items())

    return f"""---
language:
  - id
  - en
license: cc-by-4.0
size_categories:
  - 1K<n<10K
task_categories:
  - tabular-classification
  - tabular-regression
tags:
  - indonesia
  - nutrition
  - food
  - health
  - tkpi
  - kemenkes
  - calories
  - tabular
pretty_name: "Indonesian Food & Nutrition Composition Database (TKPI - Panganku)"
dataset_info:
  features:
    - name: Kode
      dtype: string
    - name: Nama
      dtype: string
    - name: Kategori
      dtype: string
    - name: Energy
      dtype: float64
    - name: Protein
      dtype: float64
    - name: Fat
      dtype: float64
    - name: CHO
      dtype: float64
  splits:
    - name: train
      num_bytes: 107616
      num_examples: {total_records}
configs:
  - config_name: default
    data_files:
      - split: train
        path: "data.parquet"
---

# Indonesian Food & Nutrition Composition Database (TKPI - Panganku)

Comprehensive nutritional composition and macro/micronutrient data for {total_records} Indonesian food items scraped from panganku.org (Tabel Komposisi Pangan Indonesia - TKPI, Kementerian Kesehatan RI).

- **Source**: [panganku.org](https://panganku.org) (Tabel Komposisi Pangan Indonesia / TKPI)
- **Institution**: Kementerian Kesehatan Republik Indonesia (Ministry of Health)
- **Total Records**: {total_records} food items
- **Scraper & Pipeline**: [indoscraping](https://github.com/nichsedge/indoscraping)

---

## 🚀 Quick Usage

### Python (`datasets`)
```python
from datasets import load_dataset

dataset = load_dataset("{repo_id}")
print(dataset["train"][0])
```

### Python (`pandas` / `polars` / `duckdb`)
```python
import pandas as pd

# Load direct Parquet from Hugging Face CDN
df = pd.read_parquet("https://huggingface.co/datasets/{repo_id}/resolve/main/data.parquet")
print(df.head())
```

---

## 📊 Data Fields & Schema

| Column Name | Description / Unit |
| :--- | :--- |
{fields_table}

---

## 📜 Citation & Attribution
```bibtex
@misc{{tkpi_panganku,
  author = {{Kementerian Kesehatan Republik Indonesia}},
  title = {{Tabel Komposisi Pangan Indonesia (TKPI)}},
  year = {{2026}},
  url = {{https://www.panganku.org}}
}}
```
"""


def load_panganku_records(input_path: str = DEFAULT_INPUT_JSON) -> list[dict[str, Any]]:
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Input dataset not found at {input_path}. Please run 'uv run indoscraping run panganku' first."
        )
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("items", [data])


def publish_to_huggingface(
    input_path: str = DEFAULT_INPUT_JSON,
    repo_name: str = HF_REPO_NAME,
    private: bool = False,
) -> str:
    """Upload Panganku dataset to Hugging Face Hub using HF_TOKEN."""
    _ensure_secrets()
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN environment variable is not set. Please set it in ~/.secrets or export HF_TOKEN.")

    api = HfApi(token=token)
    user_info = api.whoami()
    username = user_info["name"]
    logger.info("Authenticated with Hugging Face as: @%s", username)

    repo_id = f"{username}/{repo_name}"
    records = load_panganku_records(input_path)
    total_records = len(records)
    logger.info("Loaded %d records for Hugging Face upload.", total_records)

    df = pd.DataFrame(records)

    with tempfile.TemporaryDirectory() as staging_dir:
        parquet_path = os.path.join(staging_dir, "data.parquet")
        csv_path = os.path.join(staging_dir, "data.csv")
        json_path = os.path.join(staging_dir, "data.json")
        readme_path = os.path.join(staging_dir, "README.md")

        df.to_parquet(parquet_path, index=False)
        df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        readme_content = generate_hf_readme(total_records, repo_id)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
        api.upload_folder(
            folder_path=staging_dir,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"feat(data): automated panganku publish ({total_records} records)",
        )

    url = f"https://huggingface.co/datasets/{repo_id}"
    logger.info("✓ Successfully published to Hugging Face: %s", url)
    return url


def publish_to_kaggle(
    input_path: str = DEFAULT_INPUT_JSON,
    slug: str = KAGGLE_SLUG,
) -> str:
    """Upload or update Panganku dataset on Kaggle using modern KAGGLE_API_TOKEN."""
    _ensure_secrets()
    token = os.environ.get("KAGGLE_API_TOKEN")
    if not token:
        raise ValueError(
            "KAGGLE_API_TOKEN environment variable is not set. Please set it in ~/.secrets or export KAGGLE_API_TOKEN."
        )

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    username = api.config_values.get("username")
    logger.info("Authenticated with Kaggle as: @%s", username)

    records = load_panganku_records(input_path)
    total_records = len(records)
    df = pd.DataFrame(records)

    dataset_id = f"{username}/{slug}" if "/" not in slug else slug

    with tempfile.TemporaryDirectory() as staging_dir:
        csv_path = os.path.join(staging_dir, "data.csv")
        parquet_path = os.path.join(staging_dir, "data.parquet")
        json_path = os.path.join(staging_dir, "data.json")
        meta_path = os.path.join(staging_dir, "dataset-metadata.json")

        df.to_csv(csv_path, index=False)
        df.to_parquet(parquet_path, index=False)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        meta = {
            "title": "Indonesian Food Nutrition Database (Panganku TKPI)",
            "id": dataset_id,
            "licenses": [{"name": "CC-BY-4.0"}],
            "description": "Comprehensive nutritional composition for Indonesian food items from panganku.org (Kementerian Kesehatan RI).",
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        logger.info("Checking if Kaggle dataset '%s' exists...", dataset_id)
        try:
            api.dataset_list_files(dataset_id)
            exists = True
        except Exception:
            exists = False

        if exists:
            logger.info("Creating new Kaggle version for %s (%d records)...", dataset_id, total_records)
            api.dataset_create_version(
                staging_dir,
                version_notes=f"Automated update: {total_records} validated food items (CSV, Parquet, JSON)",
                dir_mode="skip",
            )
        else:
            logger.info("Creating new Kaggle dataset: %s...", dataset_id)
            api.dataset_create_new(
                staging_dir,
                public=True,
                dir_mode="skip",
            )

    url = f"https://www.kaggle.com/datasets/{dataset_id}"
    logger.info("✓ Successfully published to Kaggle: %s", url)
    return url


def publish_to_github(
    input_path: str = DEFAULT_INPUT_JSON,
    repo: str = GITHUB_REPO,
    tag: str = GITHUB_TAG,
) -> str:
    """Create or update GitHub Release assets on nichsedge/indoscraping."""
    records = load_panganku_records(input_path)
    df = pd.DataFrame(records)

    out_dir = os.path.dirname(input_path)
    parquet_path = os.path.join(out_dir, "panganku.parquet")
    csv_path = os.path.join(out_dir, "panganku.csv")
    json_path = os.path.join(out_dir, "panganku.json")

    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    shutil.copyfile(input_path, json_path)

    title = "Dataset: Indonesian Food & Nutrition Composition Database (TKPI - Panganku)"
    notes = "Automated snapshot export of panganku dataset from panganku.org (Kementerian Kesehatan RI)."

    logger.info("Checking if GitHub Release '%s' exists on %s...", tag, repo)
    view_proc = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if view_proc.returncode == 0:
        logger.info("Release exists. Uploading/overwriting assets to '%s'...", tag)
        subprocess.check_call(
            ["gh", "release", "upload", tag, parquet_path, csv_path, json_path, "--repo", repo, "--clobber"]
        )
    else:
        logger.info("Creating new release '%s' on %s...", tag, repo)
        subprocess.check_call(
            [
                "gh",
                "release",
                "create",
                tag,
                parquet_path,
                csv_path,
                json_path,
                "--repo",
                repo,
                "--title",
                title,
                "--notes",
                notes,
            ]
        )

    release_url = f"https://github.com/{repo}/releases/tag/{tag}"
    logger.info("✓ Successfully uploaded dataset assets to GitHub Release: %s", release_url)
    return release_url


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Programmatically publish Panganku TKPI dataset to Hugging Face, Kaggle, or GitHub Releases"
    )
    parser.add_argument(
        "--target",
        choices=["hf", "github", "kaggle", "all"],
        default="all",
        help="Target platform: hf, github, kaggle, or all (default: all)",
    )
    parser.add_argument("--input", default=DEFAULT_INPUT_JSON, help="Input JSON file path")
    parser.add_argument("--hf-repo", default=HF_REPO_NAME, help="Custom Hugging Face repo name")
    parser.add_argument("--kaggle-slug", default=KAGGLE_SLUG, help="Custom Kaggle dataset slug")
    parser.add_argument("--private", action="store_true", help="Make repository private (HF only)")
    args = parser.parse_args()

    results: list[str] = []

    if args.target in ("hf", "all"):
        hf_url = publish_to_huggingface(input_path=args.input, repo_name=args.hf_repo, private=args.private)
        results.append(hf_url)

    if args.target in ("kaggle", "all"):
        kg_url = publish_to_kaggle(input_path=args.input, slug=args.kaggle_slug)
        results.append(kg_url)

    if args.target in ("github", "all"):
        gh_url = publish_to_github(input_path=args.input)
        results.append(gh_url)

    print("\nPublished URLs:")
    for url in results:
        print(f"  • {url}")


if __name__ == "__main__":
    main()
