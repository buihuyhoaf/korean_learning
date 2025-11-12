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


def _resolve_target_path(
    *,
    path_env: str,
    default_path: Path,
    url_env: str,
    asset_name: str,
) -> Path:
    raw_path = os.getenv(path_env)

    if not raw_path:
        target = default_path
    else:
        parsed = urlparse(raw_path)
        if parsed.scheme in {"http", "https"}:
            logger.info(
                "%s is a URL; treating it as download source and using default local path %s for %s",
                path_env,
                default_path,
                asset_name,
            )
            if not os.getenv(url_env):
                os.environ[url_env] = raw_path
            target = default_path
        else:
            target = Path(raw_path)
            if not target.is_absolute():
                target = default_path.parent / target

    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _should_force_download(force_env: str) -> bool:
    return os.getenv(force_env, "").lower() in {"1", "true", "yes"}


def _download_via_http(asset_name: str, url: str, destination: Path) -> None:
    logger.info("Downloading %s from HTTP URL: %s", asset_name, url)
    timeout = httpx.Timeout(30.0, read=60.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        destination.write_bytes(response.content)
    logger.info("Saved %s to %s", asset_name, destination)


def _download_via_supabase(
    asset_name: str,
    destination: Path,
    *,
    bucket_env: str,
    object_env: str,
) -> bool:
    bucket = os.getenv(bucket_env)
    object_path = os.getenv(object_env)
    if not bucket or not object_path:
        logger.info(
            "Supabase download skipped for %s: %s or %s not set.",
            asset_name,
            bucket_env,
            object_env,
        )
        return False

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error(
            "Supabase credentials missing for %s. Ensure SUPABASE_URL and SUPABASE_KEY or "
            "SUPABASE_SERVICE_ROLE_KEY are set.",
            asset_name,
        )
        return False

    logger.info(
        "Downloading %s from Supabase bucket '%s', object '%s'.",
        asset_name,
        bucket,
        object_path,
    )

    try:
        from supabase import create_client  # Lazy import to avoid startup cost
    except ImportError as exc:
        logger.error("supabase package is not available (%s) while fetching %s", exc, asset_name)
        return False

    client = create_client(supabase_url, supabase_key)

    try:
        data: bytes = client.storage.from_(bucket).download(object_path)
    except Exception as exc:  # pragma: no cover - Supabase errors are runtime-specific
        logger.error("Failed to download %s from Supabase: %s", asset_name, exc)
        return False

    destination.write_bytes(data)
    logger.info("Saved %s to %s", asset_name, destination)
    return True


def ensure_asset(
    *,
    asset_name: str,
    default_path: Path,
    path_env: str,
    url_env: str,
    bucket_env: str,
    object_env: str,
    force_env: str,
) -> Optional[Path]:
    destination = _resolve_target_path(
        path_env=path_env,
        default_path=default_path,
        url_env=url_env,
        asset_name=asset_name,
    )
    logger.info("Resolved target path for %s: %s", asset_name, destination)

    if destination.exists() and not _should_force_download(force_env):
        logger.info("%s already present at %s. Skipping download.", asset_name, destination)
        return destination

    http_url = os.getenv(url_env)
    if http_url:
        try:
            _download_via_http(asset_name, http_url, destination)
            logger.info("HTTP download completed successfully for %s.", asset_name)
            return destination
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("HTTP download failed for %s: %s", asset_name, exc)
            return None

    if _download_via_supabase(
        asset_name,
        destination,
        bucket_env=bucket_env,
        object_env=object_env,
    ):
        return destination

    logger.warning(
        "%s download skipped. Provide %s or %s/%s.",
        asset_name,
        url_env,
        bucket_env,
        object_env,
    )
    return None


def main() -> int:
    status = 0

    model_path = ensure_asset(
        asset_name="TFLite model",
        default_path=Path("/code/src/app/models/hangul_stroke_model.tflite"),
        path_env="STROKE_MODEL_PATH",
        url_env="STROKE_MODEL_URL",
        bucket_env="STROKE_MODEL_BUCKET",
        object_env="STROKE_MODEL_OBJECT",
        force_env="STROKE_MODEL_FORCE_DOWNLOAD",
    )
    if model_path is None:
        logger.warning("TFLite model is not available after download attempt.")
        status = 1
    else:
        logger.info("TFLite model ensured at %s", model_path)

    label_path = ensure_asset(
        asset_name="stroke label file",
        default_path=Path("/code/src/app/models/hangul_labels.txt"),
        path_env="STROKE_LABEL_PATH",
        url_env="STROKE_LABEL_URL",
        bucket_env="STROKE_LABEL_BUCKET",
        object_env="STROKE_LABEL_OBJECT",
        force_env="STROKE_LABEL_FORCE_DOWNLOAD",
    )
    if label_path is None:
        logger.warning(
            "Stroke label file not available. Falling back to built-in labels if provided."
        )
    else:
        logger.info("Stroke label file ensured at %s", label_path)

    return status


if __name__ == "__main__":
    sys.exit(main())


