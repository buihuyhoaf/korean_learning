"""
Endpoints dedicated to writing submission management.

This module currently exposes the teacher grading endpoint. Future phases can
extend it with additional CRUD and reporting handlers.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...crud.writing import WritingSubmissionCRUD
from ...models.writing_submission import WritingSubmissionStatus
from ...schemas.writing import (
    TeacherGradeSchema,
    TeacherGradeResponseSchema,
)

router = APIRouter(prefix="/writing", tags=["writing"])


@router.post("/grade/{submission_id}", response_model=TeacherGradeResponseSchema)
async def grade_writing_submission(
    submission_id: UUID,
    payload: TeacherGradeSchema,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> TeacherGradeResponseSchema:
    """
    Record teacher grading results for a writing submission.

    Notes
    -----
    - Caller authentication/authorization is delegated to ``get_current_user``.
      Add explicit role checks (e.g. teacher vs. admin) once the account model
      supports it.
    - After this endpoint succeeds, Phase 6 should trigger notification delivery
      (FCM + in-app notification).
    """

    submission = await WritingSubmissionCRUD.get_submission(db, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    final_score = (
        payload.spelling_score
        + payload.grammar_score
        + payload.structure_score
        + payload.vocabulary_score
    ) / 4.0

    updated_submission = await WritingSubmissionCRUD.update_teacher_result(
        db=db,
        submission_id=submission_id,
        spelling_score=payload.spelling_score,
        grammar_score=payload.grammar_score,
        structure_score=payload.structure_score,
        vocabulary_score=payload.vocabulary_score,
        feedback=payload.feedback,
        final_score=final_score,
        status=WritingSubmissionStatus.TEACHER_GRADED,
    )

    if updated_submission is None:
        # Safety net: record could have been deleted concurrently.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    # TODO(Phase 6): Call notification service (FCM + persist notification record).

    return TeacherGradeResponseSchema(
        final_score=final_score,
        feedback=payload.feedback,
        status=updated_submission.status,
    )


