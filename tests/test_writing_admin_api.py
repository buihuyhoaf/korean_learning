import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app.api.v1.writing import list_pending_submissions
from src.app.core.db.database import Base
from src.app.crud.writing import WritingSubmissionCRUD
from src.app.models.course import Course, Unit, Lesson
from src.app.models.exercise import Exercise, ExerciseType
from src.app.models.user import User
from src.app.schemas.writing import WritingSubmissionMode


@pytest.fixture
async def db_session() -> AsyncSession:
    """Yield an in-memory SQLite session for admin API tests."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _create_writing_submission(db: AsyncSession) -> None:
    """Seed database with a pending writing submission."""

    user = User(
        username="learner",
        email="learner@example.com",
        password="hashed",
        role="student",
    )
    course = Course(title="Course", description="Desc")
    unit = Unit(title="Unit", description="Desc", course=course)
    lesson = Lesson(title="Lesson", description="Desc", unit=unit)
    exercise = Exercise(
        lesson=lesson,
        type=ExerciseType.WRITING,
        title="Teacher prompt",
        content="Prompt",
    )

    db.add_all([user, course, unit, lesson, exercise])
    await db.commit()

    await db.refresh(user)
    await db.refresh(exercise)

    await WritingSubmissionCRUD.create_submission(
        db=db,
        user_id=user.id,
        exercise_id=exercise.id,
        text="Bài viết chờ chấm",
    )
    await db.commit()


@pytest.mark.asyncio
async def test_list_pending_submissions_returns_queue(db_session: AsyncSession) -> None:
    """Admin endpoint should surface submissions waiting for teacher grading."""

    await _create_writing_submission(db_session)

    response = await list_pending_submissions(
        skip=0,
        limit=10,
        db=db_session,
        current_user={"id": "admin", "role": "admin", "is_superuser": True},
    )

    assert response.total == 1
    assert len(response.submissions) == 1

    item = response.submissions[0]
    assert item.mode == WritingSubmissionMode.TEACHER
    assert item.text == "Bài viết chờ chấm"
    assert item.exercise_title == "Teacher prompt"
    assert item.lesson_title == "Lesson"

