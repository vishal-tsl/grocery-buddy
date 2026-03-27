#!/usr/bin/env bash
# Step 4: Create Artifact Registry Docker repository.
# Usage: export PROJECT_ID=... REGION=us-central1 AR_REPO=backend && ./scripts/gcp/03-artifact-registry.sh
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:?Set REGION}"
: "${AR_REPO:?Set AR_REPO (e.g. backend)}"

gcloud artifacts repositories create "${AR_REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Backend container images" \
  --project="${PROJECT_ID}" 2>/dev/null || echo "Repository may already exist; continuing."

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "Docker repo: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"
