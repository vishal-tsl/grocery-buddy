#!/usr/bin/env bash
# Step 4: Build and push image from repo root.
# Usage from repository root:
#   export PROJECT_ID=... REGION=us-central1 AR_REPO=backend IMAGE_NAME=slai-api TAG=v1
#   ./scripts/gcp/04-build-push.sh
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:?Set REGION}"
: "${AR_REPO:?Set AR_REPO}"
: "${IMAGE_NAME:?Set IMAGE_NAME}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAG="${TAG:-$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo latest)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${IMAGE_NAME}:${TAG}"

cd "$ROOT"
docker build -t "${IMAGE}" .
docker push "${IMAGE}"
echo "Pushed: ${IMAGE}"
echo "export IMAGE=${IMAGE}"
