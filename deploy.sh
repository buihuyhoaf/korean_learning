#!/usr/bin/env bash
set -euo pipefail

echo "[deploy] Running database migrations..."
alembic upgrade head

MODEL_DIR="/code/src/app/models"
mkdir -p "${MODEL_DIR}"

if [[ -n "${STROKE_MODEL_URL:-}" ]]; then
  echo "[deploy] Downloading stroke model..."
  curl -fSL "${STROKE_MODEL_URL}" -o "${MODEL_DIR}/hangul_stroke_model.tflite"
fi

if [[ -n "${STROKE_LABEL_URL:-}" ]]; then
  echo "[deploy] Downloading stroke labels..."
  curl -fSL "${STROKE_LABEL_URL}" -o "${MODEL_DIR}/2350-common-hangul.txt"
fi

if [[ -n "${FIREBASE_SERVICE_ACCOUNT_B64:-}" ]]; then
  FIREBASE_CREDENTIALS_PATH="/code/firebase-service-account.json"
  echo "[deploy] Writing Firebase service account to ${FIREBASE_CREDENTIALS_PATH}"
  printf '%s' "$FIREBASE_SERVICE_ACCOUNT_B64" | base64 -d > "${FIREBASE_CREDENTIALS_PATH}"
  chmod 600 "${FIREBASE_CREDENTIALS_PATH}"
  export GOOGLE_APPLICATION_CREDENTIALS="${FIREBASE_CREDENTIALS_PATH}"
else
  echo "[deploy] WARNING: FIREBASE_SERVICE_ACCOUNT_B64 is not set. Firebase features will be disabled." >&2
fi

echo "[deploy] Starting application server..."
exec gunicorn src.app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b "0.0.0.0:${PORT:-8000}"


