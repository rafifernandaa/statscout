#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_env.sh
# Exports all environment variables needed by StatScout.
# Source this file — do NOT execute it directly.
# Usage: source setup/setup_env.sh
# ─────────────────────────────────────────────────────────────────────────────

# ── GCP Core ─────────────────────────────────────────────────────────────────
export PROJECT_ID="${PROJECT_ID:-your-gcp-project-id}"
export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

# ── BigQuery ──────────────────────────────────────────────────────────────────
export BQ_DATASET="${BQ_DATASET:-statscout_data}"
export BQ_LOCATION="${BQ_LOCATION:-US}"

# ── Cloud Run ─────────────────────────────────────────────────────────────────
export SERVICE_NAME="${SERVICE_NAME:-statscout}"
export REGION="${GOOGLE_CLOUD_LOCATION}"

# ── App ───────────────────────────────────────────────────────────────────────
export PORT="${PORT:-8080}"

echo "Environment loaded:"
echo "  PROJECT_ID            = ${PROJECT_ID}"
echo "  GOOGLE_CLOUD_LOCATION = ${GOOGLE_CLOUD_LOCATION}"
echo "  BQ_DATASET            = ${BQ_DATASET}"
echo "  SERVICE_NAME          = ${SERVICE_NAME}"
