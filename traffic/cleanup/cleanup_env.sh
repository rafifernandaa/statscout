#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# cleanup_env.sh
# Tears down all GCP resources provisioned by setup scripts.
# Usage: bash cleanup/cleanup_env.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

source "$(dirname "$0")/../setup/setup_env.sh"

echo ""
echo "⚠️  This will permanently delete:"
echo "    - Cloud Run service  : ${SERVICE_NAME} (${REGION})"
echo "    - BigQuery dataset   : ${BQ_DATASET} (all tables)"
echo "    - Service account    : statscout-sa@${PROJECT_ID}.iam.gserviceaccount.com"
echo ""
read -rp "Type 'yes' to confirm: " CONFIRM
if [[ "${CONFIRM}" != "yes" ]]; then
  echo "Aborted."
  exit 0
fi

# ── Cloud Run ─────────────────────────────────────────────────────────────────
echo "==> Deleting Cloud Run service: ${SERVICE_NAME}"
gcloud run services delete "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet 2>/dev/null && echo "    Deleted." || echo "    Not found, skipping."

# ── BigQuery ──────────────────────────────────────────────────────────────────
echo "==> Deleting BigQuery dataset: ${BQ_DATASET}"
bq --project_id="${PROJECT_ID}" rm \
  --recursive \
  --force \
  "${PROJECT_ID}:${BQ_DATASET}" 2>/dev/null && echo "    Deleted." || echo "    Not found, skipping."

# ── Service account ───────────────────────────────────────────────────────────
SA_EMAIL="statscout-sa@${PROJECT_ID}.iam.gserviceaccount.com"
echo "==> Deleting service account: ${SA_EMAIL}"
gcloud iam service-accounts delete "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --quiet 2>/dev/null && echo "    Deleted." || echo "    Not found, skipping."

echo ""
echo "✅  Cleanup complete."
