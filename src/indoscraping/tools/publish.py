"""Automated Programmatic Dataset Publisher.

Publishes scraped datasets from Indoscraping to public repositories:
- Hugging Face Datasets (via HfApi & HF_TOKEN)
- GitHub Releases CDN (via gh CLI & GH_TOKEN)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import pandas as pd
from huggingface_hub import HfApi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("publisher")

DATASET_METADATA = {
    "panganku": {
        "repo_name": "panganku-indonesian-food-nutrition",
        "pretty_name": "Indonesian Food & Nutrition Composition Database (TKPI - Panganku)",
        "description": "Comprehensive nutritional composition and macro/micronutrient data for 1,146 Indonesian food items scraped from panganku.org (Tabel Komposisi Pangan Indonesia - TKPI, Kementerian Kesehatan RI).",
        "tags": [
            "indonesia",
            "nutrition",
            "food",
            "health",
            "tkpi",
            "kemenkes",
            "calories",
            "tabular",
        ],
        "input_json": "data/food/panganku/latest.json",
        "fields": {
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
        },
    }
}


def generate_hf_readme(config: dict[str, Any], total_records: int, repo_id: str) -> str:
    """Generate Markdown dataset card with valid YAML frontmatter."""
    tags_yaml = "\n".join(f"  - {tag}" for tag in config["tags"])
    fields_table = "\n".join(
        f"| `{col}` | {desc} |" for col, desc in config.get("fields", {}).items()
    )

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
{tags_yaml}
pretty_name: "{config['pretty_name']}"
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

# {config['pretty_name']}

{config['description']}

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
If you use this dataset in your research, applications, or dietary modeling, please cite the original institutional source:

```bibtex
@misc{{tkpi_panganku,
  author = {{Kementerian Kesehatan Republik Indonesia}},
  title = {{Tabel Komposisi Pangan Indonesia (TKPI)}},
  year = {{2026}},
  url = {{https://www.panganku.org}}
}}
```
"""


def publish_to_huggingface(
    scraper_id: str,
    repo_name_override: str | None = None,
    private: bool = False,
) -> str:
    """Upload dataset to Hugging Face Hub using HF_TOKEN."""
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN environment variable is not set. Please set it in ~/.secrets or export HF_TOKEN.")

    api = HfApi(token=token)
    user_info = api.whoami()
    username = user_info["name"]
    logger.info("Authenticated with Hugging Face as: @%s", username)

    cfg = DATASET_METADATA.get(scraper_id, {})
    repo_name = repo_name_override or cfg.get("repo_name", f"indoscraping-{scraper_id}")
    repo_id = f"{username}/{repo_name}"
    input_json = cfg.get("input_json", f"data/{scraper_id}/latest.json")

    if not os.path.exists(input_json):
        raise FileNotFoundError(f"Input data not found at {input_json}. Please run 'indoscraping run {scraper_id}' first.")

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data if isinstance(data, list) else data.get("items", [data])
    total_records = len(records)
    logger.info("Loaded %d records from %s", total_records, input_json)

    # Convert to DataFrame
    df = pd.DataFrame(records)

    with tempfile.TemporaryDirectory() as staging_dir:
        parquet_path = os.path.join(staging_dir, "data.parquet")
        csv_path = os.path.join(staging_dir, "data.csv")
        json_path = os.path.join(staging_dir, "data.json")
        readme_path = os.path.join(staging_dir, "README.md")

        logger.info("Staging export files in %s...", staging_dir)
        df.to_parquet(parquet_path, index=False)
        df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        readme_content = generate_hf_readme(cfg, total_records, repo_id)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        logger.info("Ensuring Hugging Face repository exists: %s (private=%s)", repo_id, private)
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)

        logger.info("Uploading folder to https://huggingface.co/datasets/%s ...", repo_id)
        api.upload_folder(
            folder_path=staging_dir,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"feat(data): automated dataset publish ({total_records} records)",
        )

    url = f"https://huggingface.co/datasets/{repo_id}"
    logger.info("✓ Successfully published to Hugging Face: %s", url)
    return url


def publish_to_github(scraper_id: str, repo: str = "nichsedge/indoscraping") -> str:
    """Create or update a GitHub Release with dataset artifacts using gh CLI."""
    cfg = DATASET_METADATA.get(scraper_id, {})
    input_json = cfg.get("input_json", f"data/{scraper_id}/latest.json")
    if not os.path.exists(input_json):
        raise FileNotFoundError(f"Input data not found at {input_json}")

    tag = f"dataset-{scraper_id}-latest"
    title = f"Dataset: {cfg.get('pretty_name', scraper_id)}"
    notes = f"Automated snapshot export of {scraper_id} dataset ({cfg.get('description', '')})."

    # Ensure parquet and csv exist
    df = pd.read_json(input_json)
    out_dir = os.path.dirname(input_json)
    parquet_path = os.path.join(out_dir, f"{scraper_id}.parquet")
    csv_path = os.path.join(out_dir, f"{scraper_id}.csv")
    json_path = os.path.join(out_dir, f"{scraper_id}.json")

    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    shutil.copyfile(input_json, json_path)

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
    parser = argparse.ArgumentParser(description="Programmatically publish datasets to public hubs")
    parser.add_argument("scraper_id", choices=list(DATASET_METADATA.keys()), help="Scraper ID to publish")
    parser.add_argument("--target", choices=["hf", "github", "all"], default="hf", help="Target platform (default: hf)")
    parser.add_argument("--repo-name", default=None, help="Custom repository name for Hugging Face")
    parser.add_argument("--private", action="store_true", help="Make repository private (default: public)")
    args = parser.parse_args()

    results: list[str] = []

    if args.target in ("hf", "all"):
        hf_url = publish_to_huggingface(args.scraper_id, repo_name_override=args.repo_name, private=args.private)
        results.append(hf_url)

    if args.target in ("github", "all"):
        gh_url = publish_to_github(args.scraper_id)
        results.append(gh_url)

    print("\nPublished URLs:")
    for url in results:
        print(f"  • {url}")


if __name__ == "__main__":
    main()
