"""Utilities for interacting with Supabase Storage via direct HTTP calls."""

import uuid
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile, status

from ..config import settings


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _resolve_supabase_credentials() -> tuple[str, str]:
    """Return the Supabase URL and API key or raise if they are missing."""
    supabase_url = settings.SUPABASE_URL
    if not supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase URL is not configured",
        )

    has_service_role = bool(
        getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
        and settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()
    )
    supabase_key = (
        settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()
        if has_service_role
        else settings.SUPABASE_KEY.get_secret_value()
    )
    if not supabase_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase API key is not configured",
        )

    return supabase_url, supabase_key


def get_file_extension(filename: str) -> str:
    """Extract the filename extension (including the dot) in lowercase."""
    return Path(filename).suffix.lower()


def generate_unique_filename(original_filename: str) -> str:
    """Return a UUID-based filename while preserving the original extension."""
    file_ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{file_ext}"


async def upload_image_to_supabase(file: UploadFile, bucket_name: str = "questions-images") -> str:
    """Upload an image to Supabase Storage and return its public URL."""
    file_ext = get_file_extension(file.filename or "")
    content_type = file.content_type or ""

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type. Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )

    unique_filename = generate_unique_filename(file.filename or "image")
    file_path = f"{unique_filename}"

    try:
        file_content = await file.read()
    except Exception as exc:  # pragma: no cover - IO edge cases
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {exc}",
        ) from exc

    supabase_url, supabase_key = _resolve_supabase_credentials()
    upload_url = f"{supabase_url}/storage/v1/object/{bucket_name}/{file_path}"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(upload_url, content=file_content, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error connecting to Supabase: {exc}",
        ) from exc

    if response.status_code in (200, 201):
        public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{file_path}"
        return public_url

    try:
        error_detail = response.json()
    except ValueError:  # pragma: no cover - non JSON responses
        error_detail = {"status": response.status_code, "text": response.text}

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error uploading file to Supabase: {error_detail}",
    )

