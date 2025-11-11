import uuid

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app.api.dependencies import get_current_admin_or_teacher, get_current_user
from src.app.api.v1.writing import router as writing_router
from src.app.core.db.database import Base
from src.app.models.course import Course, Lesson, Unit
from src.app.models.exercise import Exercise, ExerciseType
from src.app.models.user import User
from src.app.models.writing_submission import WritingSubmission, WritingSubmissionStatus
from src.app.schemas.writing import TeacherGradeSchema


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provide an in-memory SQLite session for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def _make_app(db_session: AsyncSession, user_payload: dict) -> FastAPI:
    """Create a FastAPI app with dependency overrides for testing."""
    app = FastAPI()
    app.include_router(writing_router, prefix="/v1")

    async def override_db():
        yield db_session

    def override_current_user():
        return user_payload

    def override_admin_or_teacher():
        allowed_roles = {"admin", "teacher"}
        if user_payload.get("is_superuser") or user_payload.get("role") in allowed_roles:
            return user_payload
        from src.app.core.exceptions.http_exceptions import ForbiddenException

        raise ForbiddenException("You do not have enough privileges.")

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_current_admin_or_teacher] = override_admin_or_teacher
    from src.app.core.db.database import async_get_db

    app.dependency_overrides[async_get_db] = override_db
    return app


async def _seed_writing_submission(db_session: AsyncSession) -> tuple[WritingSubmission, Lesson, User, User]:
    """Insert the minimal graph required for grading."""
    teacher = User(
        id=uuid.uuid4(),
        username="teacher1",
        email="teacher@example.com",
        password="hashed",
        role="teacher",
    )
    student = User(
        id=uuid.uuid4(),
        username="student1",
        email="student@example.com",
        password="hashed",
        role="student",
    )

    course = Course(id=uuid.uuid4(), title="Course", description="Desc", order_index=0)
    unit = Unit(id=uuid.uuid4(), course_id=course.id, title="Unit", description="Desc", order_index=0)
    lesson = Lesson(
        id=uuid.uuid4(),
        unit_id=unit.id,
        title="Lesson",
        description="Desc",
        order_index=0,
        max_exp=120,
    )
    exercise = Exercise(
        id=uuid.uuid4(),
        lesson_id=lesson.id,
        type=ExerciseType.WRITING,
        title="Write",
        content="N/A",
        order_index=0,
    )

    submission = WritingSubmission(
        id=uuid.uuid4(),
        user_id=student.id,
        exercise_id=exercise.id,
        text="테스트 문장 입니다.",
        status=WritingSubmissionStatus.SUBMITTED,
    )

    db_session.add_all([teacher, student, course, unit, lesson, exercise, submission])
    await db_session.commit()
    await db_session.refresh(submission)
    return submission, lesson, teacher, student


@pytest.mark.asyncio
async def test_grade_writing_submission_success(db_session: AsyncSession) -> None:
    submission, lesson, teacher, _ = await _seed_writing_submission(db_session)

    app = _make_app(
        db_session=db_session,
        user_payload={"id": teacher.id, "role": "teacher", "is_superuser": False},
    )

    payload = TeacherGradeSchema(
        spelling_score=8.0,
        grammar_score=7.0,
        structure_score=7.0,
        vocabulary_score=8.0,
        feedback="Great improvements!",
    ).model_dump()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/v1/writing/grade/{submission.id}", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["final_score"] == pytest.approx(7.5)
    assert data["feedback"] == "Great improvements!"
    assert data["status"] == WritingSubmissionStatus.TEACHER_GRADED.value

    refreshed = await db_session.get(WritingSubmission, submission.id)
    assert refreshed is not None
    assert refreshed.status == WritingSubmissionStatus.TEACHER_GRADED
    assert refreshed.final_score == pytest.approx(7.5)
    assert refreshed.teacher_feedback == "Great improvements!"
    assert refreshed.teacher_spelling_score == pytest.approx(8.0)


@pytest.mark.asyncio
async def test_grade_writing_submission_requires_teacher(db_session: AsyncSession) -> None:
    submission, _, _, student = await _seed_writing_submission(db_session)

    app = _make_app(
        db_session=db_session,
        user_payload={"id": student.id, "role": "student", "is_superuser": False},
    )

    payload = TeacherGradeSchema(
        spelling_score=8.0,
        grammar_score=7.0,
        structure_score=7.0,
        vocabulary_score=8.0,
        feedback="Attempted feedback",
    ).model_dump()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/v1/writing/grade/{submission.id}", json=payload)

    assert response.status_code == 403
    refreshed = await db_session.get(WritingSubmission, submission.id)
    assert refreshed is not None
    assert refreshed.status == WritingSubmissionStatus.SUBMITTED
    assert refreshed.teacher_feedback is None

