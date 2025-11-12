import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app.api.v1.exercises import submit_exercise
from src.app.core.db.database import Base
from src.app.models.course import Course, Unit, Lesson
from src.app.models.exercise import Exercise, ExerciseType
from src.app.models.user import User
from src.app.models.writing_submission import WritingSubmission, WritingSubmissionStatus
from src.app.services.writing_ai import WritingAiEvaluationResult


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provide an in-memory SQLite session for API tests."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_lesson_with_writing_exercise(db: AsyncSession) -> tuple[User, Lesson, Exercise]:
    """Create minimal user/lesson/exercise records for tests."""

    user = User(
        username="student",
        email="student@example.com",
        password="hashed",
        role="student",
    )
    course = Course(title="Course", description="Desc")
    unit = Unit(title="Unit", description="Desc", course=course)
    lesson = Lesson(title="Lesson", description="Desc", unit=unit)
    exercise = Exercise(
        lesson=lesson,
        type=ExerciseType.WRITING,
        title="Write something",
        content="Prompt",
    )

    db.add_all([user, course, unit, lesson, exercise])
    await db.commit()
    await db.refresh(user)
    await db.refresh(lesson)
    await db.refresh(exercise)
    return user, lesson, exercise


@pytest.mark.asyncio
async def test_submit_writing_ai_success(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession) -> None:
    """Submitting in AI mode should store scores and mark submission ai_graded."""

    user, _lesson, exercise = await _seed_lesson_with_writing_exercise(db_session)

    async def fake_ai_service(text: str) -> WritingAiEvaluationResult:
        assert text == "Xin chào"
        return WritingAiEvaluationResult(
            score=9.5,
            feedback="Great job!",
            spelling_score=9.0,
            grammar_score=10.0,
            spelling_errors=1,
            grammar_errors=0,
            total_tokens=2,
            is_fallback=False,
        )

    monkeypatch.setattr("src.app.api.v1.exercises.evaluate_writing_with_ai", fake_ai_service)

    result = await submit_exercise(
        exercise_id=exercise.id,
        submission_data={"response": "Xin chào", "mode": "AI"},
        db=db_session,
        current_user={"id": str(user.id)},
    )

    assert result["status"] == "ai_graded"
    assert result["ai_result"]["score"] == 9.5
    assert result["submission"]["status"] == WritingSubmissionStatus.AI_GRADED.value

    stored = await db_session.get(WritingSubmission, uuid.UUID(result["submission"]["id"]))
    assert stored is not None
    assert stored.ai_score == 9.5
    assert stored.status == WritingSubmissionStatus.AI_GRADED


@pytest.mark.asyncio
async def test_submit_writing_ai_fallback(monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession) -> None:
    """If AI service falls back, submission remains in submitted state and feedback is returned."""

    user, _lesson, exercise = await _seed_lesson_with_writing_exercise(db_session)

    async def fake_ai_service(_text: str) -> WritingAiEvaluationResult:
        return WritingAiEvaluationResult(
            score=None,
            feedback="Fallback message",
            spelling_score=None,
            grammar_score=None,
            spelling_errors=0,
            grammar_errors=0,
            total_tokens=0,
            is_fallback=True,
        )

    monkeypatch.setattr("src.app.api.v1.exercises.evaluate_writing_with_ai", fake_ai_service)

    result = await submit_exercise(
        exercise_id=exercise.id,
        submission_data={"response": "Xin chào", "mode": "AI"},
        db=db_session,
        current_user={"id": str(user.id)},
    )

    assert result["status"] == WritingSubmissionStatus.SUBMITTED.value
    assert result["ai_result"]["is_fallback"] is True

    stored = await db_session.get(WritingSubmission, uuid.UUID(result["submission"]["id"]))
    assert stored is not None
    assert stored.ai_score is None
    assert stored.status == WritingSubmissionStatus.SUBMITTED

