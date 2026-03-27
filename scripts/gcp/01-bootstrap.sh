#!/usr/bin/env bash
# Step 1: GCP project + APIs (Cloud Run + GCS playbook).
# Usage: export PROJECT_ID=your-project-id && ./scripts/gcp/01-bootstrap.sh
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID (e.g. export PROJECT_ID=my-proj)}"

echo "Creating project (ignore error if it already exists)..."
gcloud projects create "${PROJECT_ID}" --name="Backend (Cloud Run)" 2>/dev/null || true
gcloud config set project "${PROJECT_ID}"

echo "Link billing (uncomment and set BILLING_ACCOUNT_ID if needed):"
echo "  gcloud billing accounts list"
echo "  gcloud billing projects link ${PROJECT_ID} --billing-account=BILLING_ACCOUNT_ID"

read -r -p "Press Enter after billing is attached (or if already attached)..."

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  --project="${PROJECT_ID}"

echo "Done. APIs enabled for ${PROJECT_ID}."
