#!/usr/bin/env bash
set -euo pipefail

echo "[deploy] Running database migrations..."
alembic upgrade head

echo "[deploy] Ensuring TFLite stroke model is available..."
python /code/src/scripts/download_stroke_model.py || {
  echo "[deploy] WARNING: Failed to download TFLite model." >&2
}

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
WORKERS="${WEB_CONCURRENCY:-2}"
echo "[deploy] Using ${WORKERS} worker(s)"
exec gunicorn src.app.main:app \
  -w "${WORKERS}" \
  -k uvicorn.workers.UvicornWorker \
  --forwarded-allow-ips="*" \
  -b "0.0.0.0:${PORT:-8000}"


