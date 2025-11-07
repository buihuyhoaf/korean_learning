#!/usr/bin/env bash
set -euo pipefail

echo "[deploy] Running database migrations..."
alembic upgrade head

echo "[deploy] Starting application server..."
exec gunicorn src.app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b "0.0.0.0:${PORT:-8000}"


