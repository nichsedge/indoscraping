# Indoscraping — Agent Notes

## Run scrapers (unified interface)
- All scrapers are run via npm scripts in package.json:
  - `npm run scrape:detik` — news scraper (Python/uv)
  - `npm run scrape:banks` — digital bank rates (Python/uv + Playwright; requires `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`)
  - `npm run scrape:alfagift` / `npm run scrape:indomaret` — retail scrapers (Node)
  - `npm run list:scrapers` — list available scrapers

## Environment & tooling
- Use `uv` for Python dependency/env management. Run `uv sync` if needed.
- Node.js is required for retail scrapers; `npm install` in repo root if needed.
- The `data/` directory holds `latest.json` and dated snapshots under `data/history/` for bank-rate runs.

## Project structure
- Python scraper modules: `src/indoscraping/scraper/` → `news/`, `finance/`, `retail/`
- Finance scrapers use Playwright async; configured via `src/indoscraping/scraper/finance/index.py` and models in `models.py`.
- The `examples/run_banks.sh` script runs the bank scraper monthly (ensure env `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`).

## Workflow conventions
- No tests directory present; rely on the npm scripts above for verification.
- For bank-rate scraper, ensure `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` is set to avoid browser downloads.