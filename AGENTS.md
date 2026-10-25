# Indoscraping — Developer & Agent Guide

Welcome to the modernized **Indoscraping** developer manual. This document guides developers and autonomous agents on how to execute, maintain, test, and expand the dual-engine scraper suite.

---

## 1. Dual-Engine Architecture (Python + Go)

Indoscraping features a unified, polyglot architecture designed for both interactive desktop development and high-performance server/mobile execution:

| Engine | Primary Role | Tech Stack | Entry Point |
| :--- | :--- | :--- | :--- |
| **Python Engine** | Interactive Rich TUI, Playwright stream interception, modular packages | Python 3.14+, `uv`, `curl_cffi`, Playwright, Rich, Pydantic | `uv run indoscraping` |
| **Go Native Engine** | High-concurrency semaphore pool, native Termux (aarch64), zero-python servers | Go 1.22+, `net/http`, Goroutines, CDP | `bin/indoscraping` or `--engine go` |

Both engines adhere to the **exact same standardized output contracts** (`latest.json`, `history/YYYY-MM-DD.json`, and `.meta.json` lineage sidecars) under the `data/` directory.

---

## 2. Unified CLI Dashboard & Execution

The central CLI dashboard (`indoscraping`) is built with `rich` and can orchestrate both Python and Go executions.

### Interactive Dashboard
```bash
uv run indoscraping
```

### Direct CLI Commands (Headless / Automation / CRONs)
```bash
# 1. List all available scrapers, categories, and dual-engine support
uv run indoscraping list

# 2. View data volume stats, file formats, and last-modified dates
uv run indoscraping status

# 3. Inspect scraped records directly in terminal
uv run indoscraping inspect <scraper_id>

# 4. Check system Chromium/Chrome detection & Playwright environment
uv run indoscraping check-browser

# 5. Execute a specific scraper (Python engine by default)
uv run indoscraping run <scraper_id> [optional_arguments]

# 6. Execute a specific scraper using the Go native engine
uv run indoscraping run <scraper_id> --engine go [optional_arguments]

# 7. Batch execute scrapers sequentially
uv run indoscraping run-all [--category <news|ecommerce|property>] [--engine py|go] [--limit-articles <N>]

# 8. Export Scraped Datasets (Parquet or CSV)
uv run indoscraping export <scraper_id> [--format parquet|csv] [--output <path>]

# 9. Extract nutrition facts from product images via RapidOCR
uv run indoscraping ocr-nutrition --input <image_path_or_json> --output <result_path>
```

### Common Command Examples:
```bash
# News
uv run indoscraping run cnbc --limit-categories 1 --limit-articles 3
uv run indoscraping run detik --limit-articles 5
uv run indoscraping run bisnis --limit-articles 2
uv run indoscraping run narasi --limit-articles 3

# E-Commerce (canonical keys: tokopedia, blibli, alfagift, indomaret)
uv run indoscraping run tokopedia --query "kopi"
uv run indoscraping run blibli --query "susu"
uv run indoscraping run alfagift --limit-categories 1 --limit-articles 5
uv run indoscraping run indomaret --limit-categories 1 --limit-articles 5

# Real Estate & Boarding Houses (Kost)
uv run indoscraping run sewakost --area jakarta/jakarta-barat/palmerah --limit-pages 1
uv run indoscraping run jendela360 --limit-pages 1
uv run indoscraping run rumah123 --limit-articles 5 --deal-type jual --category rumah

# Go Engine Direct Execution
./bin/indoscraping run cnbc --limit-articles 5
./bin/indoscraping run sewakost --limit-pages 1
./bin/indoscraping run all --limit-items 3
./bin/indoscraping export csv
```

---

## 3. Environment & Tooling Standards

- **Python Env Manager (`uv`)**: We use `uv` exclusively.
  - Strict syntax: NEVER write `uv run python <script.py>`. Always use direct execution: `uv run indoscraping` or `uv run pytest`.
  - Restore dependencies: `uv sync`
  - Add workspace dependency: `uv add <pkg>`
- **Go Toolchain**:
  - Compile native binary: `go build -o bin/indoscraping ./cmd/indoscraping` (or `make build-go`).
  - Run Go tests: `go test ./...` (or `make test-go`).
- **Make Shortcuts**:
  - `make test`: Runs both Python (`pytest`) and Go test suites.
  - `make build-go`: Compiles `bin/indoscraping`.
  - `make check-browser`: Verifies browser environment.
- **Playwright Bypass**:
  - Always use system-installed Chrome: `channel='chrome'`, `headless=True`.
  - Ensure `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` is set to skip runtime browser downloads.

---

## 4. Standardized Output & Data Topology

Scraped data is systematically stored under the `data/` tree. Each scraper produces `latest.json` for rapid CLI dashboard access, chronological snapshots under `history/YYYY-MM-DD.json`, and `.meta.json` lineage sidecars:

```
data/
├── news/
│   ├── detik/latest.json & history/YYYY-MM-DD.json
│   ├── bisnis/latest.json & history/YYYY-MM-DD.json
│   ├── cnbc/latest.json & history/YYYY-MM-DD.json
│   ├── cnn/latest.json & history/YYYY-MM-DD.json
│   ├── kompas/latest.json & history/YYYY-MM-DD.json
│   └── narasi/latest.json & history/YYYY-MM-DD.json
├── ecommerce/
│   ├── alfagift/latest.json & history/YYYY-MM-DD.json
│   ├── indomaret/latest.json & history/YYYY-MM-DD.json
│   ├── blibli/latest.json & history/YYYY-MM-DD.json
│   └── tokopedia/latest.json & history/YYYY-MM-DD.json
├── property/
│   ├── jendela360/latest.json & history/YYYY-MM-DD.json
│   ├── rumah123/latest.json & history/YYYY-MM-DD.json
│   └── sewakost/latest.json & history/YYYY-MM-DD.json
└── hardware/
    ├── enterkomputer/latest.json & history/YYYY-MM-DD.json
    └── viraindo/latest.json & history/YYYY-MM-DD.json
```

---

## 5. Complete Scraper Catalog & Code Map

### Canonical Scraper IDs & Supported Engines

| Canonical ID | Aliases | Scraper Name | Category | Python Engine | Go Engine |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `detik` | — | Detik.com News | News | `src/indoscraping/scraper/news/detik.py` | `pkg/scrapers/news/detik.go` |
| `bisnis` | — | Bisnis.com News | News | `src/indoscraping/scraper/news/bisnis.py` | — |
| `cnbc` | — | CNBC Indonesia | News | `src/indoscraping/scraper/news/cnbc.py` | `pkg/scrapers/news/cnbc.go` |
| `cnn` | — | CNN Indonesia | News | `src/indoscraping/scraper/news/cnn.py` | `pkg/scrapers/news/cnn.go` |
| `kompas` | — | Kompas.com | News | `src/indoscraping/scraper/news/kompas.py` | `pkg/scrapers/news/kompas.go` |
| `narasi` | — | Narasi.tv | News | `src/indoscraping/scraper/news/narasi.py` | — |
| `alfagift` | — | Alfamart Alfagift | E-Commerce | `packages/alfagift-scraper/` | `pkg/scrapers/ecommerce/alfagift.go` |
| `indomaret` | — | Klik Indomaret | E-Commerce | `packages/indomaret-scraper/` | `pkg/scrapers/ecommerce/indomaret.go` |
| `blibli` | `blibli-search` | Blibli Products | E-Commerce | `packages/blibli-scraper/` | `pkg/scrapers/ecommerce/blibli.go` |
| `tokopedia` | `tokped` | Tokopedia Marketplace | E-Commerce | `packages/tokopedia-scraper/` | `pkg/scrapers/ecommerce/tokopedia.go` |
| `jendela360`| — | Jendela360 Property | Property | `src/indoscraping/scraper/property/jendela360.py` | `pkg/scrapers/property/jendela360.go` |
| `sewakost` | — | SewaKost Boarding Rooms | Property | `src/indoscraping/scraper/property/sewakost.py` | `pkg/scrapers/property/sewakost.go` |
| `rumah123` | — | Rumah123 Listings | Property | `src/indoscraping/scraper/property/rumah123.py` | — |
| `enterkomputer` | — | EnterKomputer Hardware | Hardware | `src/indoscraping/scraper/hardware/enterkomputer.py` | — |
| `viraindo` | — | Viraindo PC Hardware | Hardware | `src/indoscraping/scraper/hardware/viraindo.py` | — |

---

## 6. Monorepo Structure & Package Boundaries

```
indoscraping/
├── pyproject.toml               # Root uv monorepo workspace definition
├── Makefile                     # Cross-engine build & test orchestrator
├── cmd/indoscraping/            # Go native CLI entry point (main.go)
├── pkg/                         # Go scraper engines & HTTP/browser packages
├── src/indoscraping/            # Python CLI dashboard (`cli.py`), news, property & hardware crawlers
│   ├── cli.py                   # Central interactive Rich dashboard & CLI dispatcher
│   ├── scraper/
│   │   ├── news/                # Detik, Bisnis, CNBC, CNN, Kompas, Narasi crawlers
│   │   ├── property/            # Rumah123, Jendela360, SewaKost crawlers
│   │   └── hardware/            # EnterKomputer, Viraindo PC hardware price scrapers
│   └── tools/
│       └── indomaret_nutrition.py # OCR-based nutrition fact extraction tool
├── packages/                    # Standalone publishable Python packages
│   ├── indoscraping-core/       # Shared DQ, schema drift, lineage & atomic output engine
│   ├── blibli-scraper/          # Standalone Blibli search package
│   ├── tokopedia-scraper/       # Standalone Tokopedia Playwright interceptor package
│   ├── alfagift-scraper/        # Standalone Alfagift TLS impersonation package
│   └── indomaret-scraper/       # Standalone Klik Indomaret package
└── tests/                       # Python test suite (49+ tests across CLI, DQ, & scrapers)
```

---

## 7. Developer & Agent Contribution Rules

> [!IMPORTANT]
> 1. **No Backward Compatibility / Modern Only**: Never write compatibility shims or obsolete patterns. Target latest standards.
> 2. **Canonical Keys First**: Always use canonical scraper IDs (`tokopedia`, `blibli`, `detik`, etc.). Aliases (`tokped`, `blibli-search`) exist only for user CLI convenience.
> 3. **Dual Engine Synchronization**: When modifying shared data contracts or adding scrapers, verify output compatibility between Python and Go.
> 4. **Testing Before Completion**: Run `make test` (or `uv run pytest` and `go test ./...`) before declaring tasks complete. All tests must pass.
> 5. **Documentation Sync**: When adding, modifying, or removing scrapers, CLI flags, or packages, update both `README.md` and `AGENTS.md` in the same turn.
