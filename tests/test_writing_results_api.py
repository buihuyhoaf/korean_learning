import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app.api.v1.writing import get_writing_results
from src.app.core.db.database import Base
from src.app.crud.writing import WritingSubmissionCRUD
from src.app.models.course import Course, Unit, Lesson
from src.app.models.exercise import Exercise, ExerciseType
from src.app.models.user import User
from src.app.models.writing_submission import WritingSubmissionStatus
from src.app.schemas.writing import WritingSubmissionMode


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provide an in-memory SQLite session for writing results API tests."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_lesson(db: AsyncSession) -> tuple[User, Lesson, Exercise, Exercise]:
    """Create a user, lesson, and two writing exercises."""

    user = User(
        username="student",
        email="student@example.com",
        password="hashed",
        role="student",
    )
    course = Course(title="Course", description="Desc")
    unit = Unit(title="Unit", description="Desc", course=course)
    lesson = Lesson(title="Lesson", description="Desc", unit=unit)
    exercise_ai = Exercise(
        lesson=lesson,
        type=ExerciseType.WRITING,
        title="AI prompt",
        content="Prompt 1",
    )
    exercise_teacher = Exercise(
        lesson=lesson,
        type=ExerciseType.WRITING,
        title="Teacher prompt",
        content="Prompt 2",
    )

    db.add_all([user, course, unit, lesson, exercise_ai, exercise_teacher])
    await db.commit()

    await db.refresh(user)
    await db.refresh(lesson)
    await db.refresh(exercise_ai)
    await db.refresh(exercise_teacher)
    return user, lesson, exercise_ai, exercise_teacher


@pytest.mark.asyncio
async def test_get_writing_results_returns_ai_and_teacher_entries(db_session: AsyncSession) -> None:
    """Endpoint aggregates AI and teacher results for a lesson."""

    user, lesson, exercise_ai, exercise_teacher = await _seed_lesson(db_session)

    ai_submission = await WritingSubmissionCRUD.create_submission(
        db=db_session,
        user_id=user.id,
        exercise_id=exercise_ai.id,
        text="AI bài viết",
    )
    await WritingSubmissionCRUD.update_ai_result(
        db=db_session,
        submission_id=ai_submission.id,
        score=9.2,
        feedback="AI feedback",
        status=WritingSubmissionStatus.AI_GRADED,
    )

    teacher_submission = await WritingSubmissionCRUD.create_submission(
        db=db_session,
        user_id=user.id,
        exercise_id=exercise_teacher.id,
        text="Teacher bài viết",
    )
    await WritingSubmissionCRUD.update_teacher_result(
        db=db_session,
        submission_id=teacher_submission.id,
        spelling_score=8.0,
        grammar_score=8.5,
        structure_score=9.0,
        vocabulary_score=8.5,
        feedback="Chấm giáo viên",
        final_score=8.5,
        status=WritingSubmissionStatus.TEACHER_GRADED,
    )
    await db_session.commit()

    response = await get_writing_results(
        lesson_id=lesson.id,
        db=db_session,
        current_user={"id": str(user.id)},
    )

    assert response.lesson_id == lesson.id
    assert len(response.submissions) == 2

    ai_entry = next(item for item in response.submissions if item.exercise_id == exercise_ai.id)
    assert ai_entry.mode == WritingSubmissionMode.AI
    assert ai_entry.ai_score == 9.2
    assert ai_entry.teacher_feedback is None

    teacher_entry = next(item for item in response.submissions if item.exercise_id == exercise_teacher.id)
    assert teacher_entry.mode == WritingSubmissionMode.TEACHER
    assert teacher_entry.final_score == 8.5
    assert teacher_entry.teacher_feedback == "Chấm giáo viên"


@pytest.mark.asyncio
async def test_get_writing_results_missing_user_id_raises(db_session: AsyncSession) -> None:
    """Invalid user id should raise HTTP 400."""

    _, lesson, _, _ = await _seed_lesson(db_session)

    with pytest.raises(HTTPException):
        await get_writing_results(
            lesson_id=lesson.id,
            db=db_session,
            current_user={"id": "not-a-uuid"},
        )

