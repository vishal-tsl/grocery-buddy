#!/usr/bin/env bash
# Step 5: Deploy to Cloud Run (public by default).
# Prerequisites: IMAGE from 04-build-push.sh, bucket + SA from 02-iam-bucket.sh
# Usage:
#   export PROJECT_ID=... REGION=us-central1 SERVICE_NAME=slai-api IMAGE=...region-docker.pkg.dev/... SA_EMAIL=...
#   export BUCKET_NAME=...
#   export GEMINI_API_KEY=...   # required by app Settings
#   ./scripts/gcp/05-deploy-cloud-run.sh
#
# Optional: AUTH_FLAG="--no-allow-unauthenticated" for private service; then grant run.invoker.
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:?Set REGION}"
: "${SERVICE_NAME:?Set SERVICE_NAME}"
: "${IMAGE:?Set IMAGE (full Artifact Registry URL with tag)}"
: "${SA_EMAIL:?Set SA_EMAIL (backend-run-sa@...)}"
: "${BUCKET_NAME:?Set BUCKET_NAME}"
: "${GEMINI_API_KEY:?Set GEMINI_API_KEY for the app}"

AUTH_FLAG="${AUTH_FLAG:---allow-unauthenticated}"

gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --platform=managed \
  --service-account="${SA_EMAIL}" \
  ${AUTH_FLAG} \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --timeout=300 \
  --set-env-vars="GCS_BUCKET=${BUCKET_NAME},ENV=production,GEMINI_API_KEY=${GEMINI_API_KEY}"

echo "Deployed ${SERVICE_NAME}. Set other secrets (autocomplete, supabase) via Console or --set-secrets as needed."
