import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app.api.v1.writing import grade_writing_submission
from src.app.core.db.database import Base
from src.app.crud.writing import WritingSubmissionCRUD
from src.app.models.course import Course, Unit, Lesson
from src.app.models.exercise import Exercise, ExerciseType
from src.app.models.user import User
from src.app.models.writing_submission import WritingSubmission, WritingSubmissionStatus
from src.app.schemas.writing import TeacherGradeSchema


@pytest.fixture
async def db_session() -> AsyncSession:
    """Provide an in-memory SQLite session for grading tests."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_submission(db: AsyncSession) -> tuple[User, WritingSubmission]:
    """Create a teacher user and a pending writing submission."""

    teacher = User(
        username="teacher",
        email="teacher@example.com",
        password="hashed",
        role="teacher",
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

    db.add_all([teacher, course, unit, lesson, exercise])
    await db.commit()
    await db.refresh(teacher)
    await db.refresh(exercise)

    submission = await WritingSubmissionCRUD.create_submission(
        db=db,
        user_id=teacher.id,  # reuse teacher id just for fixture simplicity
        exercise_id=exercise.id,
        text="Bài viết của học viên",
        status=WritingSubmissionStatus.SUBMITTED,
    )
    await db.commit()
    await db.refresh(submission)

    return teacher, submission


@pytest.mark.asyncio
async def test_grade_submission_success(db_session: AsyncSession) -> None:
    """Teacher can grade a submission and results are stored."""

    teacher, submission = await _seed_submission(db_session)

    payload = TeacherGradeSchema(
        spelling_score=9.0,
        grammar_score=8.5,
        structure_score=8.0,
        vocabulary_score=9.5,
        feedback="Bài viết khá tốt, chú ý thêm cấu trúc câu.",
    )

    response = await grade_writing_submission(
        submission_id=submission.id,
        payload=payload,
        db=db_session,
        current_user={"id": str(teacher.id), "role": "teacher", "is_superuser": False},
    )

    assert round(response.final_score, 2) == pytest.approx(8.75, rel=1e-3)
    assert response.status == WritingSubmissionStatus.TEACHER_GRADED

    stored = await db_session.get(WritingSubmission, submission.id)
    assert stored is not None
    assert stored.final_score == pytest.approx(8.75, rel=1e-3)
    assert stored.teacher_feedback == payload.feedback
    assert stored.status == WritingSubmissionStatus.TEACHER_GRADED


@pytest.mark.asyncio
async def test_grade_submission_forbidden_for_student(db_session: AsyncSession) -> None:
    """Students are not allowed to call the grading endpoint."""

    _, submission = await _seed_submission(db_session)

    payload = TeacherGradeSchema(
        spelling_score=8.0,
        grammar_score=8.0,
        structure_score=8.0,
        vocabulary_score=8.0,
        feedback="Feedback",
    )

    with pytest.raises(HTTPException) as exc_info:
        await grade_writing_submission(
            submission_id=submission.id,
            payload=payload,
            db=db_session,
            current_user={"id": str(uuid.uuid4()), "role": "student", "is_superuser": False},
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_grade_submission_not_found(db_session: AsyncSession) -> None:
    """Grading a non-existent submission returns 404."""

    teacher, _ = await _seed_submission(db_session)

    payload = TeacherGradeSchema(
        spelling_score=7.0,
        grammar_score=7.0,
        structure_score=7.0,
        vocabulary_score=7.0,
        feedback="Feedback",
    )

    with pytest.raises(HTTPException) as exc_info:
        await grade_writing_submission(
            submission_id=uuid.uuid4(),
            payload=payload,
            db=db_session,
            current_user={"id": str(teacher.id), "role": "teacher", "is_superuser": False},
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_grade_submission_already_graded(db_session: AsyncSession) -> None:
    """Cannot grade the same submission twice."""

    teacher, submission = await _seed_submission(db_session)

    submission.status = WritingSubmissionStatus.TEACHER_GRADED
    await db_session.commit()

    payload = TeacherGradeSchema(
        spelling_score=8.0,
        grammar_score=8.0,
        structure_score=8.0,
        vocabulary_score=8.0,
        feedback="Feedback",
    )

    with pytest.raises(HTTPException) as exc_info:
        await grade_writing_submission(
            submission_id=submission.id,
            payload=payload,
            db=db_session,
            current_user={"id": str(teacher.id), "role": "teacher", "is_superuser": False},
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
def test_teacher_grade_schema_validation() -> None:
    """Schema enforces 0-10 scoring bounds."""

    with pytest.raises(ValidationError):
        TeacherGradeSchema(
            spelling_score=11.0,
            grammar_score=9.0,
            structure_score=9.0,
            vocabulary_score=9.0,
            feedback="Feedback",
        )

