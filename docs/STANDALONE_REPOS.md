# 🌐 IndoScraping Standalone & SEO Repository Guide

This guide explains how to maintain standalone GitHub repositories (e.g. `blibli-scraper`, `tokopedia-scraper`, `idx-bei`) alongside the central `indoscraping` monorepo for maximum search discoverability and package isolation.

---

## 🎯 The Discoverability Strategy

Most developers search GitHub or Google for specific target keywords like:
- `blibli-scraper python`
- `tokopedia scraper api`
- `idx-bei financial data`
- `detik news scraper`

By publishing standalone PyPI packages (`pip install blibli-scraper`) and linking them with standalone GitHub repositories, you capture target-specific search traffic while keeping a shared core engine (`indoscraping-core`).

---

## 🏗️ Architecture Overview

```
                      ┌─────────────────────────┐
                      │    indoscraping-core    │  <-- PyPI: indoscraping-core
                      │ (Shared Engine & Utils) │
                      └────────────┬────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐
│   blibli-scraper   │   │ tokopedia-scraper  │   │      idx-bei       │  <-- Standalone PyPI & GitHub Repos
└──────────┬─────────┘   └──────────┬─────────┘   └──────────┬─────────┘
           │                        │                        │
           └────────────────────────┼────────────────────────┘
                                    ▼
                      ┌─────────────────────────┐
                      │      indoscraping       │  <-- Monorepo & Visual CLI Hub
                      └─────────────────────────┘
```

---

## 🚀 Setting Up a Standalone Repo (e.g. `blibli-scraper`)

### 1. Create standalone GitHub repository
Create a dedicated public repo on GitHub named `blibli-scraper` with descriptive topics/tags:
- **Topics**: `blibli`, `blibli-scraper`, `ecommerce-scraper`, `indonesia`, `python-scraping`, `indoscraping`

### 2. Standalone `pyproject.toml` Template
```toml
[project]
name = "blibli-scraper"
version = "0.1.0"
description = "Standalone Blibli e-commerce product search & category scraper for Python."
readme = "README.md"
requires-python = ">=3.12"
keywords = ["blibli", "blibli-scraper", "ecommerce-scraper", "indonesia", "indoscraping"]
dependencies = [
    "indoscraping-core>=0.1.0",
    "playwright>=1.58.0",
    "playwright-stealth>=2.0.3",
    "beautifulsoup4>=4.13.4",
]

[project.scripts]
blibli-scraper = "blibli_scraper.cli:main"

[project.entry-points."indoscraping.scrapers"]
blibli = "blibli_scraper.cli:main"

[build-system]
requires = ["uv_build>=0.8.2,<0.9.0"]
build-backend = "uv_build"
```

### 3. Publishing to PyPI using `uv`
```bash
# Build standalone package wheel and sdist
uv build --package blibli-scraper

# Publish to PyPI
uv publish dist/*
```

---

## ⚡ Monorepo Workspace Development (`uv workspace`)

Inside the main `indoscraping` repository, all subpackages live under `packages/`:
- `packages/indoscraping-core`
- `packages/blibli-scraper`
- `packages/tokopedia-scraper`

Run `uv sync` from the monorepo root to link all workspace packages in editable mode automatically!
