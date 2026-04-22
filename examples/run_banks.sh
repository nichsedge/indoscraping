#!/bin/bash
# Script to run the bank scraper monthly
# You can add this to your crontab: 0 0 1 * * /path/to/run.sh

# Ensure we are in the project root directory
cd "$(dirname "$0")/.."

# Set Playwright environment variables
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Run the scraper using uv
uv run python -m src.indoscraping.scraper.finance.index
