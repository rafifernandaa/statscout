#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_bigquery.sh
# Provisions BigQuery dataset + 4 tables, then uploads CSVs from data/
# Usage: bash setup/setup_bigquery.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

source "$(dirname "$0")/setup_env.sh"

DATA_DIR="$(dirname "$0")/../data"

echo "==> Creating BigQuery dataset: ${BQ_DATASET} in project ${PROJECT_ID}"
bq --project_id="${PROJECT_ID}" mk \
  --dataset \
  --location="${BQ_LOCATION}" \
  --description="StatScout reference data for bakery market analysis" \
  "${PROJECT_ID}:${BQ_DATASET}" 2>/dev/null || echo "    Dataset already exists, skipping."

# ── Helper: load a CSV into a BQ table ───────────────────────────────────────
load_table() {
  local table="$1"
  local csv_file="$2"
  echo "==> Loading ${csv_file} → ${BQ_DATASET}.${table}"
  bq --project_id="${PROJECT_ID}" load \
    --autodetect \
    --source_format=CSV \
    --skip_leading_rows=1 \
    --replace \
    "${PROJECT_ID}:${BQ_DATASET}.${table}" \
    "${csv_file}"
  echo "    Done. Row count:"
  bq --project_id="${PROJECT_ID}" query --nouse_legacy_sql \
    "SELECT COUNT(*) AS rows FROM \`${PROJECT_ID}.${BQ_DATASET}.${table}\`"
}

load_table "demographics"         "${DATA_DIR}/demographics.csv"
load_table "bakery_prices"        "${DATA_DIR}/bakery_prices.csv"
load_table "sales_history_weekly" "${DATA_DIR}/sales_history_weekly.csv"
load_table "foot_traffic"         "${DATA_DIR}/foot_traffic.csv"

echo ""
echo "✅  BigQuery setup complete."
echo "    Project : ${PROJECT_ID}"
echo "    Dataset : ${BQ_DATASET}"
echo "    Tables  : demographics, bakery_prices, sales_history_weekly, foot_traffic"
