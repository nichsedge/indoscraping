#!/usr/bin/env bash
set -euo pipefail

# Daily D-1 CNBC Indonesia alpha scraper -> GCS (Hive-partitioned JSON)
# Designed for GCP Always Free e2-micro VM using attached Service Account (ADC).
#
# Required env:
#   GCS_BUCKET               Target GCS bucket name (without gs://)
# Optional env:
#   CNBC_CATEGORIES          Comma-separated slugs (default: market,research,news)
#   TARGET_DATE              Override D-1 date in YYYY-MM-DD (default: yesterday Asia/Jakarta)
#   BIN_PATH                 Path to indoscraping Go binary (default: ./bin/indoscraping)
#   TELEGRAM_BOT_TOKEN       Telegram bot token for alerts
#   TELEGRAM_CHAT_ID         Telegram chat/user ID for alerts
#   TELEGRAM_NOTIFY_SUCCESS  Send 1-line summary on success (1=yes, 0=no; default: 1)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f "${REPO_ROOT}/.env.telegram" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env.telegram"
fi

: "${GCS_BUCKET:?GCS_BUCKET environment variable must be set}"

BIN_PATH="${BIN_PATH:-./bin/indoscraping}"
CNBC_CATEGORIES="${CNBC_CATEGORIES:-market,research,news}"
TARGET_DATE="${TARGET_DATE:-$(TZ=Asia/Jakarta date -d "yesterday" +%Y-%m-%d)}"
TELEGRAM_NOTIFY_SUCCESS="${TELEGRAM_NOTIFY_SUCCESS:-1}"

send_telegram() {
  local msg="$1"
  if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
    return 0
  fi
  curl -fsS --max-time 10 -X POST \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${msg}" >/dev/null || true
}

on_error() {
  local exit_code=$?
  local line_no=$1
  send_telegram "❌ [always-free-vm] CNBC D-1 FAILED (${TARGET_DATE}) at line ${line_no} (exit ${exit_code}). Check ~/indoscraping/cnbc_daily.log"
  exit "$exit_code"
}
trap 'on_error $LINENO' ERR

if [[ ! -x "$BIN_PATH" ]]; then
  echo "Error: Go binary not found or not executable at $BIN_PATH" >&2
  exit 1
fi

"$BIN_PATH" run cnbc \
  --categories "$CNBC_CATEGORIES" \
  --date "$TARGET_DATE" \
  --limit-articles -1

LOCAL_FILE="data/news/cnbc/history/${TARGET_DATE}.json"
if [[ ! -s "$LOCAL_FILE" ]]; then
  echo "Error: expected output file not found or empty: $LOCAL_FILE" >&2
  exit 1
fi

GCS_URI="gs://${GCS_BUCKET}/news/cnbc/date=${TARGET_DATE}/data.json"
gcloud storage cp "$LOCAL_FILE" "$GCS_URI"
SIZE_BYTES=$(wc -c < "$LOCAL_FILE")
echo "Uploaded ${LOCAL_FILE} (${SIZE_BYTES} bytes) -> ${GCS_URI}"

if [[ "$TELEGRAM_NOTIFY_SUCCESS" == "1" ]]; then
  send_telegram "✅ [always-free-vm] CNBC D-1 (${TARGET_DATE}) uploaded: ${SIZE_BYTES} bytes -> ${GCS_URI}"
fi
