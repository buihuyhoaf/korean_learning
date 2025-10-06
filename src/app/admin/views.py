from typing import Annotated

from crudadmin import CRUDAdmin
from crudadmin.admin_interface.model_view import PasswordTransformer
from pydantic import BaseModel, Field

from ..core.security import get_password_hash
from ..models.tier import Tier
from ..models.user import User
from ..models.course import Course, Unit, Lesson
from ..models.quiz import Quiz, QuestionType, Question, QuestionOption
from ..models.exercise import ListeningExercise, SpeakingExercise, WritingExercise
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

# Import schemas
from ..schemas.user import UserCreate, UserCreateInternal, UserUpdate
from ..schemas.course import CourseCreate, CourseUpdate
from ..schemas.lesson import LessonCreate, LessonUpdate
from ..schemas.quiz import QuizCreate, QuizUpdate
from ..schemas.unit import UnitCreate, UnitUpdate
from ..schemas.progress import ProgressCreate, ProgressUpdate
from ..schemas.ai_chat_history import AIChatHistoryCreate, AIChatHistoryUpdate


def register_admin_views(admin: CRUDAdmin) -> None:
    """Register all models and their schemas with the admin interface.

    This function adds all available models to the admin interface with appropriate
    schemas and permissions.
    """

    password_transformer = PasswordTransformer(
        password_field="password",
        hashed_field="hashed_password",
        hash_function=get_password_hash,
        required_fields=["name", "username", "email"],
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

    # Quiz Management
    admin.add_view(
        model=Quiz,
        create_schema=QuizCreate,
        update_schema=QuizUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )