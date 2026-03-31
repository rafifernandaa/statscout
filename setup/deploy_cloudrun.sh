#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy_cloudrun.sh
# Builds and deploys StatScout to Google Cloud Run.
# Usage: bash setup/deploy_cloudrun.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

source "$(dirname "$0")/setup_env.sh"

SA_EMAIL="statscout-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo "═══════════════════════════════════════════"
echo "  StatScout — Cloud Run Deployment"
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "  Service : ${SERVICE_NAME}"
echo "═══════════════════════════════════════════"
echo ""

# ── Step 1: Enable required APIs ─────────────────────────────────────────────
echo "==> [1/5] Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  --project="${PROJECT_ID}"
echo "    Done."

# ── Step 2: Create service account (idempotent) ───────────────────────────────
echo "==> [2/5] Setting up service account: ${SA_EMAIL}"
gcloud iam service-accounts create statscout-sa \
  --display-name="StatScout Service Account" \
  --project="${PROJECT_ID}" 2>/dev/null \
  || echo "    Service account already exists, skipping creation."

# Grant Vertex AI + BigQuery access
echo "    Granting roles..."
for ROLE in \
  roles/aiplatform.user \
  roles/bigquery.user \
  roles/bigquery.jobUser \
  roles/bigquery.dataViewer; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --quiet
done
echo "    Roles granted."

# ── Step 3: Load BigQuery data (idempotent) ───────────────────────────────────
echo "==> [3/5] Loading data into BigQuery..."
bash "$(dirname "$0")/setup_bigquery.sh"

# ── Step 4: Deploy to Cloud Run ───────────────────────────────────────────────
echo "==> [4/5] Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --source "$(dirname "$0")/.." \
  --region "${REGION}" \
  --service-account "${SA_EMAIL}" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},BQ_DATASET=${BQ_DATASET},GOOGLE_GENAI_USE_VERTEXAI=true" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --project "${PROJECT_ID}" \ 
  --concurrency 1

# ── Step 5: Smoke test ────────────────────────────────────────────────────────
echo "==> [5/5] Running smoke test..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format "value(status.url)")

echo "    Service URL: ${SERVICE_URL}"

# Health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health")
if [[ "${HTTP_STATUS}" == "200" ]]; then
  echo "    Health check passed (HTTP 200)"
else
  echo "    WARNING: Health check returned HTTP ${HTTP_STATUS}"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅  Deployment complete!"
echo "  URL: ${SERVICE_URL}"
echo ""
echo "  Test with:"
echo "  curl -X POST ${SERVICE_URL}/analyze \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"query\": \"what are the top selling products?\"}'"
echo "═══════════════════════════════════════════"
