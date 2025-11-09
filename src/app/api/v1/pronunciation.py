from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ...api.dependencies import get_current_user
from ...services.pronunciation_service import PronunciationServiceError, evaluate_pronunciation

router = APIRouter(prefix="/pronunciation", tags=["pronunciation"])


class PronunciationEvaluationResponse(BaseModel):
    transcript: str = Field(..., description="Transcribed text from the recording")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score between 0 and 1")
    passed: bool = Field(..., description="Whether score meets configured threshold")


@router.post(
    "",
    response_model=PronunciationEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate pronunciation recording",
)
async def evaluate_user_pronunciation(
    file: UploadFile = File(..., description="Recorded audio in wav or PCM16"),
    sentence: str = Form(..., description="Target sentence the learner attempted"),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio is empty",
            )

        evaluation = evaluate_pronunciation(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            sentence=sentence,
        )
        return JSONResponse(PronunciationEvaluationResponse(**evaluation).model_dump())
    except PronunciationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate pronunciation: {exc}",
        ) from exc

