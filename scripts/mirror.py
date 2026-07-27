#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import tempfile
from typing import Dict, List

# Define the scraper categories and their configurations
CATEGORIES: Dict[str, Dict[str, any]] = {
    "news": {
        "description": "Indonesian news scrapers split from indoscraping suite",
        "dependencies": [
            "beautifulsoup4>=4.13.4",
            "curl-cffi>=0.15.0",
            "fake-useragent>=2.2.0",
            "pendulum>=3.1.0",
            "requests>=2.32.4",
        ],
        "scrapers": [
            "Detik.com (src/indoscraping/scraper/news/detik.py)",
            "Bisnis.com (src/indoscraping/scraper/news/bisnis.py)",
            "CNBC Indonesia (src/indoscraping/scraper/news/cnbc.py)",
            "CNN Indonesia (src/indoscraping/scraper/news/cnn.py)",
            "Kompas.com (src/indoscraping/scraper/news/kompas.py)",
            "Narasi.tv (src/indoscraping/scraper/news/narasi.py)",
        ],
        "instructions": "python src/indoscraping/scraper/news/detik.py",
    },
    "ecommerce": {
        "description": "Indonesian e-commerce and retail scrapers (Tokopedia, Blibli, Alfagift, Klik Indomaret) split from indoscraping suite",
        "dependencies": [
            "beautifulsoup4>=4.13.4",
            "curl-cffi>=0.15.0",
            "pandas>=3.0.2",
            "playwright>=1.58.0",
            "requests>=2.32.4",
        ],
        "scrapers": [
            "Alfagift (src/indoscraping/scraper/ecommerce/alfagift.py)",
            "Klik Indomaret (src/indoscraping/scraper/ecommerce/indomaret.py)",
            "Blibli Search (src/indoscraping/scraper/ecommerce/blibli_search.py)",
            "Blibli Holistic (src/indoscraping/scraper/ecommerce/blibli_holistic.py)",
            "Tokopedia (src/indoscraping/scraper/ecommerce/tokopedia.py)",
        ],
        "instructions": "python src/indoscraping/scraper/ecommerce/alfagift.py",
    },
    "finance": {
        "description": "Indonesian digital bank rates scraper split from indoscraping suite",
        "dependencies": [
            "beautifulsoup4>=4.13.4",
            "playwright>=1.58.0",
            "playwright-stealth>=2.0.3",
            "pydantic>=2.13.3",
            "requests>=2.32.4",
            "rich>=15.0.0",
        ],
        "scrapers": [
            "Digital Bank Rates (src/indoscraping/scraper/finance/rates.py)",
        ],
        "instructions": "python -m src.indoscraping.scraper.finance.rates",
    },
}

PYPROJECT_TEMPLATE = """[project]
name = "indoscraping-{name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
{dependencies}
]

[build-system]
requires = ["setuptools>=61.0.0"]
build-backend = "setuptools.build_meta"
"""

README_TEMPLATE = """# Indoscraping {title}

This repository contains the {name} scrapers from the **Indoscraping** suite. It is automatically mirrored from the main [indoscraping](https://github.com/{owner}/indoscraping) monorepo.

> [!NOTE]
> Active development happens in the main monorepo. Please submit all PRs and issues there.

## Included Scrapers
{scrapers_list}

## Running a Scraper
```bash
{instructions}
```
"""

GITIGNORE_CONTENT = """# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
ENV/
env/
.pytest_cache/

# Local data
data/
*.json
*.csv
*.tmp
"""


def run_cmd(cmd: List[str], cwd: str = None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running: {' '.join(cmd)}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        raise RuntimeError(f"Command failed with exit code {result.returncode}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Mirror indoscraping scrapers to downstream repositories.")
    parser.add_argument("--owner", default="nichsedge", help="GitHub repository owner/organization name")
    parser.add_argument("--dry-run", action="store_true", help="Prepare repositories locally without pushing")
    parser.add_argument("--output-dir", help="Directory to save repositories in dry-run mode (defaults to temp)")
    args = parser.parse_args()

    token = os.environ.get("MIRROR_PAT") or os.environ.get("GITHUB_TOKEN")
    if not args.dry_run and not token:
        print("Warning: Neither MIRROR_PAT nor GITHUB_TOKEN environment variable is set. Push might fail.")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Monorepo Root: {base_dir}")

    # Determine latest monorepo commit message to reuse for mirrors
    try:
        commit_msg = run_cmd(["git", "log", "-1", "--pretty=%B"], cwd=base_dir)
    except Exception:
        commit_msg = "Mirror update from indoscraping monorepo"

    for category, config in CATEGORIES.items():
        print(f"\n--- Processing '{category}' Scraper Repository ---")
        
        # Setup workspace
        if args.dry_run and args.output_dir:
            repo_dir = os.path.join(args.output_dir, f"indoscraping-{category}")
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)
            os.makedirs(repo_dir)
        else:
            repo_dir = tempfile.mkdtemp(prefix=f"indoscraping-{category}-")

        print(f"Staging files in: {repo_dir}")

        # Recreate directory layout
        src_dir = os.path.join(repo_dir, "src", "indoscraping")
        scraper_dest = os.path.join(src_dir, "scraper", category)
        core_dest = os.path.join(src_dir, "core")
        
        os.makedirs(scraper_dest, exist_ok=True)
        os.makedirs(core_dest, exist_ok=True)

        # Copy Scrapers
        scraper_src = os.path.join(base_dir, "src", "indoscraping", "scraper", category)
        for item in os.listdir(scraper_src):
            s_path = os.path.join(scraper_src, item)
            d_path = os.path.join(scraper_dest, item)
            if os.path.isdir(s_path):
                shutil.copytree(s_path, d_path)
            else:
                shutil.copy2(s_path, d_path)

        # Copy Core shared package
        core_src = os.path.join(base_dir, "src", "indoscraping", "core")
        for item in os.listdir(core_src):
            s_path = os.path.join(core_src, item)
            d_path = os.path.join(core_dest, item)
            if os.path.isdir(s_path):
                shutil.copytree(s_path, d_path)
            else:
                shutil.copy2(s_path, d_path)

        # Generate pyproject.toml
        deps_str = "\n".join([f'    "{d}",' for d in config["dependencies"]])
        pyproject_content = PYPROJECT_TEMPLATE.format(
            name=category,
            description=config["description"],
            dependencies=deps_str
        )
        with open(os.path.join(repo_dir, "pyproject.toml"), "w") as f:
            f.write(pyproject_content)

        # Generate README.md
        scrapers_list = "\n".join([f"- {s}" for s in config["scrapers"]])
        readme_content = README_TEMPLATE.format(
            title=category.capitalize(),
            name=category,
            owner=args.owner,
            scrapers_list=scrapers_list,
            instructions=config["instructions"]
        )
        with open(os.path.join(repo_dir, "README.md"), "w") as f:
            f.write(readme_content)

        # Generate .gitignore
        with open(os.path.join(repo_dir, ".gitignore"), "w") as f:
            f.write(GITIGNORE_CONTENT)

        # Initialize and commit
        run_cmd(["git", "init"], cwd=repo_dir)
        run_cmd(["git", "config", "user.name", "github-actions[bot]"], cwd=repo_dir)
        run_cmd(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], cwd=repo_dir)
        run_cmd(["git", "add", "."], cwd=repo_dir)
        
        # Commit using monorepo author/message
        run_cmd(["git", "commit", "-m", commit_msg], cwd=repo_dir)
        run_cmd(["git", "branch", "-M", "main"], cwd=repo_dir)

        # Push if not dry-run
        if not args.dry_run:
            remote_url = f"https://x-access-token:{token}@github.com/{args.owner}/indoscraping-{category}.git"
            print(f"Pushing to github.com/{args.owner}/indoscraping-{category}.git...")
            try:
                run_cmd(["git", "push", remote_url, "main", "--force"], cwd=repo_dir)
                print(f"Successfully pushed indoscraping-{category}!")
            except Exception as e:
                print(f"Failed to push to remote: {e}")
        else:
            print(f"Dry-run mode: Skipping push for indoscraping-{category}")

        # Clean up if not saving dry-run
        if not (args.dry_run and args.output_dir):
            shutil.rmtree(repo_dir)

    print("\nMirror processing finished!")


if __name__ == "__main__":
    main()
