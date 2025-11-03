"""Supabase client utility for file storage operations."""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException, status
import httpx
from supabase import create_client, Client
from supabase import SupabaseException, StorageException

from ..config import settings

# Use SupabaseException and StorageException from supabase module
# These are the actual exception classes available in supabase-py
APIError = SupabaseException  # Alias for compatibility

# Global Supabase client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create a Supabase client instance.

    Returns
    -------
    Client
        Supabase client instance.

    Raises
    ------
    HTTPException
        If Supabase credentials are not configured.
    """
    global _supabase_client

    if _supabase_client is None:
        if not settings.SUPABASE_URL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase URL is not configured",
            )

        # Prefer service role key when available (server-side privileged operations)
        has_service_role = bool(
            getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
            and settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()
        )
        supabase_key = (
            settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value() if has_service_role else settings.SUPABASE_KEY.get_secret_value()
        )
        if not supabase_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase API key is not configured",
            )

        # Debug line to confirm which key type is used (safe: does not print actual keys)
        print(f"[SUPABASE] Using service role key: {has_service_role}")

        _supabase_client = create_client(settings.SUPABASE_URL, supabase_key)

    return _supabase_client



def get_file_extension(filename: str) -> str:
    """
    Extract file extension from filename.

    Parameters
    ----------
    filename : str
        The filename to extract extension from.

    Returns
    -------
    str
        The file extension (including the dot), or empty string if no extension.
    """
    return Path(filename).suffix.lower()


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename with UUID and preserve original extension.

    Parameters
    ----------
    original_filename : str
        The original filename.

    Returns
    -------
    str
        A unique filename with UUID prefix.
    """
    file_ext = get_file_extension(original_filename)
    unique_id = uuid.uuid4().hex
    return f"{unique_id}{file_ext}"


async def upload_image_to_supabase(file: UploadFile, bucket_name: str = "questions-images") -> str:
    """
    Upload an image file to Supabase Storage and return the public URL.

    Parameters
    ----------
    file : UploadFile
        The image file to upload.
    bucket_name : str, optional
        The name of the Supabase Storage bucket, by default "question_images".

    Returns
    -------
    str
        The public URL of the uploaded image.

    Raises
    ------
    HTTPException
        If file validation fails, upload fails, or bucket operations fail.
    """
    # Validate file type
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    file_ext = get_file_extension(file.filename or "")
    content_type = file.content_type or ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}",
        )

    # Validate content type
    allowed_mime_types = {"image/jpeg", "image/png", "image/webp"}
    if content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type. Allowed types: {', '.join(allowed_mime_types)}",
        )

    # Assume bucket already exists (no ensure here to avoid 403 with anon keys)

    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename or "image")
    file_path = f"{unique_filename}"

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}",
        )

    # Prefer direct REST upload with service role to avoid RLS issues in client
    try:
        has_service_role = bool(
            getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
            and settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()
        )
        api_key = (
            settings.SUPABASE_SERVICE_ROLE_KEY.get_secret_value() if has_service_role else settings.SUPABASE_KEY.get_secret_value()
        )

        upload_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket_name}/{file_path}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "apikey": api_key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(upload_url, content=file_content, headers=headers)

        if resp.status_code in (200, 201):
            public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{file_path}"
            return public_url

        # Try to parse error
        try:
            err = resp.json()
        except Exception:
            err = {"status": resp.status_code, "text": resp.text}
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error uploading file to Supabase: {err}")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during upload: {str(e)}",
        )

