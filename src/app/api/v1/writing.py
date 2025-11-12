"""
Endpoints dedicated to writing submission management.

This module currently exposes the teacher grading endpoint. Future phases can
extend it with additional CRUD and reporting handlers.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_admin_or_teacher, get_current_user
from ...core.db.database import async_get_db
from ...crud.writing import WritingSubmissionCRUD
from ...models.exercise import Exercise
from ...models.course import Lesson
from ...models.user import User
from ...models.writing_submission import WritingSubmission, WritingSubmissionStatus
from ...schemas.writing import (
    TeacherGradeSchema,
    TeacherGradeResponseSchema,
    WritingAdminPendingResponse,
    WritingAdminSubmissionItem,
    WritingLessonResultItem,
    WritingLessonResultsResponse,
    WritingSubmissionMode,
    WritingSubmissionCreate,
)

router = APIRouter(prefix="/writing", tags=["writing"])

logger = logging.getLogger(__name__)


@router.post("/{exercise_id}/submit", status_code=status.HTTP_200_OK)
async def submit_writing_exercise(
    exercise_id: UUID,
    payload: WritingSubmissionCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Submit a writing exercise. This forwards the request to the generic exercise
    submission handler but ensures the payload structure aligns with writing requirements.
    """

    submission_data = {
        "text": payload.text,
        "mode": payload.mode.value,
        "response": payload.text,  # Backward compatibility for older clients
    }

    from .exercises import submit_exercise as submit_exercise_handler

    return await submit_exercise_handler(
        exercise_id=exercise_id,
        submission_data=submission_data,
        db=db,
        current_user=current_user,
    )


@router.post("/grade/{submission_id}", response_model=TeacherGradeResponseSchema)
async def grade_writing_submission(
    submission_id: UUID,
    payload: TeacherGradeSchema,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_admin_or_teacher)],
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

    await db.commit()
    await db.refresh(updated_submission)

    # Send FCM notification and save notification record
    try:
        from ...services.writing_notifications import notify_writing_graded
        from ...models.exercise import Exercise
        from sqlalchemy import select
        
        # Get lesson_id from exercise
        exercise_query = select(Exercise).where(Exercise.id == updated_submission.exercise_id)
        exercise_result = await db.execute(exercise_query)
        exercise = exercise_result.scalar_one_or_none()
        
        if exercise:
            await notify_writing_graded(
                db=db,
                user_id=updated_submission.user_id,
                submission_id=updated_submission.id,
                lesson_id=exercise.lesson_id,
                title="Bài viết đã được chấm",
                body="Giáo viên đã chấm bài viết của bạn",
            )
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        # Log error but don't fail the grading request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            "Failed to send writing graded notification (submission_id=%s): %s",
            updated_submission.id,
            exc,
            exc_info=True,
        )

    return TeacherGradeResponseSchema(
        final_score=final_score,
        feedback=payload.feedback,
        status=updated_submission.status,
    )


@router.get("/admin/pending", response_model=WritingAdminPendingResponse)
async def list_pending_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_admin_or_teacher)] = None,
) -> WritingAdminPendingResponse:
    """
    Retrieve writing submissions awaiting teacher grading.

    Returns learner/exercise context so the admin interface can render a queue
    without issuing additional API calls.
    """

    status_filter = WritingSubmission.status.in_(
        (
            WritingSubmissionStatus.SUBMITTED,
            WritingSubmissionStatus.AI_GRADED,
        )
    )

    total_query = (
        select(func.count())
        .select_from(WritingSubmission)
        .join(Exercise, WritingSubmission.exercise_id == Exercise.id)
        .where(status_filter)
    )
    total = (await db.execute(total_query)).scalar_one()

    if total == 0:
        return WritingAdminPendingResponse(total=0, submissions=[])

    pending_query = (
        select(WritingSubmission, Exercise, Lesson, User)
        .join(Exercise, WritingSubmission.exercise_id == Exercise.id)
        .join(Lesson, Exercise.lesson_id == Lesson.id)
        .join(User, WritingSubmission.user_id == User.id)
        .where(status_filter)
        .order_by(WritingSubmission.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    rows = (await db.execute(pending_query)).all()

    submissions: list[WritingAdminSubmissionItem] = []
    for submission, exercise, lesson, user in rows:
        submissions.append(
            WritingAdminSubmissionItem(
                submission_id=submission.id,
                user_id=user.id,
                learner_name=getattr(user, "username", None),
                learner_email=getattr(user, "email", None),
                exercise_id=exercise.id,
                exercise_title=exercise.title or "",
                lesson_id=lesson.id,
                lesson_title=lesson.title,
                text=submission.text,
                status=submission.status,
                mode=_infer_submission_mode(submission),
                ai_score=submission.ai_score,
                ai_feedback=submission.ai_feedback,
                created_at=submission.created_at,
                updated_at=submission.updated_at,
            )
        )

    return WritingAdminPendingResponse(total=total, submissions=submissions)


@router.get("/results/{lesson_id}", response_model=WritingLessonResultsResponse)
async def list_writing_results(
    lesson_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> WritingLessonResultsResponse:
    """Return all writing submissions for the current user within a lesson."""

    user_id = UUID(str(current_user["id"]))
    submissions = await WritingSubmissionCRUD.list_for_lesson(
        db=db,
        user_id=user_id,
        lesson_id=lesson_id,
    )

    items = [
        WritingLessonResultItem(
            submission_id=submission.id,
            exercise_id=submission.exercise_id,
            mode=_infer_submission_mode(submission),
            status=submission.status,
            ai_score=submission.ai_score,
            ai_feedback=submission.ai_feedback,
            teacher_spelling_score=submission.teacher_spelling_score,
            teacher_grammar_score=submission.teacher_grammar_score,
            teacher_structure_score=submission.teacher_structure_score,
            teacher_vocabulary_score=submission.teacher_vocabulary_score,
            teacher_feedback=submission.teacher_feedback,
            final_score=submission.final_score,
            submitted_at=submission.created_at,
            updated_at=submission.updated_at,
        )
        for submission in submissions
    ]

    return WritingLessonResultsResponse(
        lesson_id=lesson_id,
        submissions=items,
    )


def _infer_submission_mode(submission) -> WritingSubmissionMode:
    """Best-effort classification of submission mode."""

    if submission.final_score is not None or submission.status == WritingSubmissionStatus.TEACHER_GRADED:
        return WritingSubmissionMode.TEACHER

    if submission.status == WritingSubmissionStatus.AI_GRADED or submission.ai_score is not None:
        return WritingSubmissionMode.AI

    # Default to teacher when waiting for manual grading.
    return WritingSubmissionMode.TEACHER


