"""Image upload endpoints using Supabase Storage."""

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel

from ...core.utils.supabase import upload_image_to_supabase

router = APIRouter(tags=["upload"])


class ImageUploadResponse(BaseModel):
    """Response model for image upload endpoint."""

    url: str
    message: str = "Image uploaded successfully"


@router.post("/upload-image", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...)) -> ImageUploadResponse:
    """
    Upload an image file to Supabase Storage.

    This endpoint accepts image files (jpg, png, or webp) and uploads them to
    a Supabase Storage bucket named 'question_images'. The file is stored with
    a unique UUID-based filename to prevent collisions.

    Parameters
    ----------
    file : UploadFile
        The image file to upload. Must be jpg, png, or webp format.

    Returns
    -------
    ImageUploadResponse
        Response containing the public URL of the uploaded image.

    Raises
    ------
    HTTPException
        - 400: If file type or content type is invalid
        - 500: If upload fails or Supabase is not configured
    """
    try:
        # Upload directly to the configured public bucket (no ensure step)
        public_url = await upload_image_to_supabase(file, bucket_name="questions-images")

        return ImageUploadResponse(
            url=public_url,
            message="Image uploaded successfully",
        )
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}",
        )

