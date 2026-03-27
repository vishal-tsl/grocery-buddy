#!/usr/bin/env bash
# Step 2 & 6: Runtime service account, logging, GCS bucket, bucket IAM (least privilege on bucket).
# Usage:
#   export PROJECT_ID=...
#   export REGION=us-central1
#   export BUCKET_NAME=your-unique-bucket-name
#   ./scripts/gcp/02-iam-bucket.sh
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:?Set REGION (e.g. us-central1)}"
: "${BUCKET_NAME:?Set BUCKET_NAME (globally unique)}"

SA_ID="backend-run-sa"
SA_EMAIL="${SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create "${SA_ID}" \
  --display-name="Cloud Run backend (GCS)" \
  --project="${PROJECT_ID}" 2>/dev/null || echo "Service account may already exist; continuing."

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter"

gcloud storage buckets create "gs://${BUCKET_NAME}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --uniform-bucket-level-access 2>/dev/null || echo "Bucket may already exist; continuing."

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

echo "Runtime SA: ${SA_EMAIL}"
echo "Bucket: gs://${BUCKET_NAME}"
echo "Bind this SA to Cloud Run with: --service-account=${SA_EMAIL}"
