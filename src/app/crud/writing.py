"""
CRUD helpers for writing submissions.

Only skeleton implementations are provided for Phase 1. Extend as business
rules mature (e.g. teacher grading workflow, pagination, filtering).
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.writing_submission import WritingSubmission, WritingSubmissionStatus


class WritingSubmissionCRUD:
    """Utility CRUD methods for ``WritingSubmission`` records."""

    @staticmethod
    async def create_submission(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        exercise_id: uuid.UUID,
        text: str,
        status: WritingSubmissionStatus = WritingSubmissionStatus.SUBMITTED,
    ) -> WritingSubmission:
        """
        Persist a new writing submission.

        Parameters
        ----------
        user_id:
            Author of the submission.
        exercise_id:
            Target writing exercise identifier.
        text:
            Raw learner response.
        status:
            Initial workflow status (defaults to ``submitted``).
        """

        submission = WritingSubmission(
            user_id=user_id,
            exercise_id=exercise_id,
            text=text,
            status=status,
        )
        db.add(submission)
        await db.flush()
        return submission

    @staticmethod
    async def update_ai_result(
        db: AsyncSession,
        *,
        submission_id: uuid.UUID,
        score: float | None,
        feedback: str | None,
        status: WritingSubmissionStatus = WritingSubmissionStatus.AI_GRADED,
    ) -> WritingSubmission | None:
        """
        Attach AI evaluation results to an existing submission.

        Returns the updated ``WritingSubmission`` or ``None`` if not found.
        """

        query = select(WritingSubmission).where(WritingSubmission.id == submission_id)
        result = await db.execute(query)
        submission = result.scalar_one_or_none()
        if not submission:
            return None

        submission.ai_score = score
        submission.ai_feedback = feedback
        submission.status = status
        await db.flush()
        return submission

    @staticmethod
    async def update_teacher_result(
        db: AsyncSession,
        *,
        submission_id: uuid.UUID,
        spelling_score: float,
        grammar_score: float,
        structure_score: float,
        vocabulary_score: float,
        feedback: str,
        final_score: float,
        status: WritingSubmissionStatus = WritingSubmissionStatus.TEACHER_GRADED,
    ) -> WritingSubmission | None:
        """
        Persist teacher-provided evaluation metrics.

        Intended to be called from the admin grading endpoint once a teacher
        submits the rubric. Returns the updated submission or ``None`` if the
        record cannot be found.
        """

        query = select(WritingSubmission).where(WritingSubmission.id == submission_id)
        result = await db.execute(query)
        submission = result.scalar_one_or_none()
        if not submission:
            return None

        submission.teacher_spelling_score = spelling_score
        submission.teacher_grammar_score = grammar_score
        submission.teacher_structure_score = structure_score
        submission.teacher_vocabulary_score = vocabulary_score
        submission.teacher_feedback = feedback
        submission.final_score = final_score
        submission.status = status
        await db.flush()
        return submission

    @staticmethod
    async def get_submission(
        db: AsyncSession,
        submission_id: uuid.UUID,
    ) -> WritingSubmission | None:
        """Fetch a submission by primary key."""

        query = select(WritingSubmission).where(WritingSubmission.id == submission_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_submissions(
        db: AsyncSession,
        *,
        user_id: uuid.UUID | None = None,
        exercise_id: uuid.UUID | None = None,
    ) -> Sequence[WritingSubmission]:
        """
        Retrieve submissions filtered by user and/or exercise.

        This skeleton version performs a simple SELECT without pagination.
        """

        query = select(WritingSubmission)
        if user_id is not None:
            query = query.where(WritingSubmission.user_id == user_id)
        if exercise_id is not None:
            query = query.where(WritingSubmission.exercise_id == exercise_id)

        result = await db.execute(query)
        return result.scalars().all()


