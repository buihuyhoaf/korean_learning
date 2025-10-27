from typing import Annotated

from crudadmin import CRUDAdmin
from crudadmin.admin_interface.model_view import PasswordTransformer
from pydantic import BaseModel, Field

from ..core.security import get_password_hash
from ..models.tier import Tier
from ..models.user import User
from ..models.course import Course, Unit, Lesson
from ..models.quiz import QuestionType, Question, QuestionOption
from ..models.final_quiz import FinalQuiz
from ..models.exercise import Exercise
from ..models.progress import (
    UserCourseProgress, 
    UserUnitProgress, 
    UserLessonProgress, 
    UserQuizAttempt, 
    UserQuestionAttempt, 
    UserQuestionError
)
from ..models.gamification import (
    UserExpLog, 
    Badge, 
    UserBadge, 
    DailyGoal, 
    Challenge, 
    UserChallenge
)
from ..models.social import Friend, Leaderboard
from ..models.ai_log import AiLog
from ..models.notification import Notification
from ..models.entry_test import (
    EntryTest, 
    EntryTestQuestion, 
    EntryTestQuestionOption, 
    UserEntryTestResult, 
    EntryTestResult, 
    UserEntryTestHistory
)

# Import schemas
from ..schemas.user import UserCreate, UserCreateInternal, UserUpdate
from ..schemas.course import CourseCreate, CourseUpdate
from ..schemas.lesson import LessonCreate, LessonUpdate
from ..schemas.final_quiz import FinalQuizCreate, FinalQuizUpdate
from ..schemas.unit import UnitCreate, UnitUpdate
from ..schemas.exercise import ExerciseCreate, ExerciseUpdate
from ..schemas.question import QuestionCreate, QuestionUpdate, QuestionOptionCreate, QuestionOptionResponse, QuestionTypeCreate, QuestionTypeUpdate
from ..schemas.progress import ProgressCreate, ProgressUpdate
from ..schemas.ai_chat_history import AIChatHistoryCreate, AIChatHistoryUpdate
from ..schemas.entry_test import (
    EntryTestCreate, 
    EntryTestUpdate,
    EntryTestQuestionCreateAdmin,
    EntryTestQuestionUpdate,
    EntryTestQuestionOptionCreate,
    EntryTestQuestionOptionUpdate,
    EntryTestScoreRangeCreate,
    EntryTestScoreRangeUpdate,
    EntryTestScoreRangeRead,
    UserEntryTestHistoryRead,
    UserEntryTestHistoryCreate,
    UserEntryTestHistoryUpdate
)


def register_admin_views(admin: CRUDAdmin) -> None:
    """Register all models and their schemas with the admin interface.

    This function adds all available models to the admin interface with appropriate
    schemas and permissions.
    """

    password_transformer = PasswordTransformer(
        password_field="password",
        hashed_field="hashed_password",
        hash_function=get_password_hash,
        required_fields=["username", "email"],
    )

    admin.add_view(
        model=User,
        create_schema=UserCreate,
        update_schema=UserUpdate,
        update_internal_schema=UserCreateInternal,
        password_transformer=password_transformer,
        allowed_actions={"view", "create", "update"},
    )

    # Course Management
    admin.add_view(
        model=Course,
        create_schema=CourseCreate,
        update_schema=CourseUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Unit Management
    admin.add_view(
        model=Unit,
        create_schema=UnitCreate,
        update_schema=UnitUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Lesson Management
    admin.add_view(
        model=Lesson,
        create_schema=LessonCreate,
        update_schema=LessonUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Final Quiz Management
    admin.add_view(
        model=FinalQuiz,
        create_schema=FinalQuizCreate,
        update_schema=FinalQuizUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Exercise Management
    admin.add_view(
        model=Exercise,
        create_schema=ExerciseCreate,
        update_schema=ExerciseUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Question Management
    admin.add_view(
        model=Question,
        create_schema=QuestionCreate,
        update_schema=QuestionUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Question Option Management
    admin.add_view(
        model=QuestionOption,
        create_schema=QuestionOptionCreate,
        update_schema=QuestionOptionResponse,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Question Type Management
    admin.add_view(
        model=QuestionType,
        create_schema=QuestionTypeCreate,
        update_schema=QuestionTypeUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Entry Test Management
    admin.add_view(
        model=EntryTest,
        create_schema=EntryTestCreate,
        update_schema=EntryTestUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Entry Test Question Management
    admin.add_view(
        model=EntryTestQuestion,
        create_schema=EntryTestQuestionCreateAdmin,
        update_schema=EntryTestQuestionUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Entry Test Question Option Management
    admin.add_view(
        model=EntryTestQuestionOption,
        create_schema=EntryTestQuestionOptionCreate,
        update_schema=EntryTestQuestionOptionUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Entry Test Result Management (Score Range Mapping)
    admin.add_view(
        model=EntryTestResult,
        create_schema=EntryTestScoreRangeCreate,
        update_schema=EntryTestScoreRangeUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # User Entry Test History (Read-only)
    admin.add_view(
        model=UserEntryTestHistory,
        create_schema=UserEntryTestHistoryCreate,
        update_schema=UserEntryTestHistoryUpdate,
        allowed_actions={"view"},
    )