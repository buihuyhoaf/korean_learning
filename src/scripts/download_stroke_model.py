"""
Utility script to ensure the Hangul stroke TFLite model is available at runtime.

It supports downloading the model either from a direct HTTP(S) URL or from Supabase
Storage using the official Supabase Python client. The script is intended to run
as part of the deployment process (e.g. via deploy.sh) inside the container.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("download_stroke_model")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def _resolve_target_path() -> Path:
    default_path = Path("/code/src/app/models/hangul_stroke_model.tflite")
    raw_path = os.getenv("STROKE_MODEL_PATH")

    if not raw_path:
        target = default_path
    else:
        parsed = urlparse(raw_path)
        if parsed.scheme in {"http", "https"}:
            logger.info(
                "STROKE_MODEL_PATH is a URL; treating it as download source "
                "and using default local path %s",
                default_path,
            )
            if not os.getenv("STROKE_MODEL_URL"):
                os.environ["STROKE_MODEL_URL"] = raw_path
            target = default_path
        else:
            target = Path(raw_path)
            if not target.is_absolute():
                target = default_path.parent / target

    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _should_force_download() -> bool:
    return os.getenv("STROKE_MODEL_FORCE_DOWNLOAD", "").lower() in {"1", "true", "yes"}


def _download_via_http(url: str, destination: Path) -> None:
    logger.info("Downloading TFLite model from HTTP URL: %s", url)
    timeout = httpx.Timeout(30.0, read=60.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        destination.write_bytes(response.content)
    logger.info("Saved TFLite model to %s", destination)


def _download_via_supabase(destination: Path) -> bool:
    bucket = os.getenv("STROKE_MODEL_BUCKET")
    object_path = os.getenv("STROKE_MODEL_OBJECT")
    if not bucket or not object_path:
        logger.info(
            "Supabase download skipped: STROKE_MODEL_BUCKET or STROKE_MODEL_OBJECT not set."
        )
        return False

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error(
            "Supabase credentials missing. Ensure SUPABASE_URL and SUPABASE_KEY or "
            "SUPABASE_SERVICE_ROLE_KEY are set."
        )
        return False

    logger.info(
        "Downloading TFLite model from Supabase bucket '%s', object '%s'.",
        bucket,
        object_path,
    )

    try:
        from supabase import create_client  # Lazy import to avoid startup cost
    except ImportError as exc:
        logger.error("supabase package is not available: %s", exc)
        return False

    client = create_client(supabase_url, supabase_key)

    try:
        data: bytes = client.storage.from_(bucket).download(object_path)
    except Exception as exc:  # pragma: no cover - Supabase errors are runtime-specific
        logger.error("Failed to download model from Supabase: %s", exc)
        return False

    destination.write_bytes(data)
    logger.info("Saved TFLite model to %s", destination)
    return True


def ensure_model() -> Optional[Path]:
    destination = _resolve_target_path()

    if destination.exists() and not _should_force_download():
        logger.info("Model already present at %s. Skipping download.", destination)
        return destination

    http_url = os.getenv("STROKE_MODEL_URL")
    if http_url:
        try:
            _download_via_http(http_url, destination)
            return destination
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("HTTP download failed: %s", exc)
            return None

    if _download_via_supabase(destination):
        return destination

    logger.warning(
        "Model download skipped. Provide STROKE_MODEL_URL or "
        "STROKE_MODEL_BUCKET/STROKE_MODEL_OBJECT."
    )
    return None


def main() -> int:
    path = ensure_model()
    if path is None:
        logger.warning("TFLite model is not available after download attempt.")
        return 1  # Non-zero so deploy script can surface the warning.
    logger.info("TFLite model ensured at %s", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())


