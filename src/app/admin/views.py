from typing import Annotated, Any, cast

from crudadmin import CRUDAdmin
from crudadmin.admin_interface.model_view import PasswordTransformer

from ..core.security import get_password_hash
from ..core.db.token_blacklist import TokenBlacklist
from ..models.tier import Tier
from ..models.user import User
from ..models.user_refresh_token import UserRefreshToken
from ..models.course import Course, Unit, Lesson
from ..models.question_type import QuestionType
from ..models.question import Question
from ..models.question_option import QuestionOption
from ..models.question_matching_pair import QuestionMatchingPair
from ..models.question_sentence_order import QuestionSentenceOrder
from ..models.question_audio_comprehension import QuestionAudioComprehension
from ..models.question_pronunciation import QuestionPronunciation
from ..models.question_blank import QuestionBlank
from ..models.exercise import Exercise, ExerciseQuestion, ExerciseQuestionOption
from ..models.progress import (
    UserCourseProgress, 
    UserUnitProgress, 
    UserLessonProgress, 
    UserQuestionError
)
from ..models.gamification import (
    UserExpLog, 
    Badge, 
    UserBadge, 
    DailyGoal
)
from ..models.social import Friend, Leaderboard
from ..models.ai_log import AiLog
from ..models.notification import Notification
from ..models.user_push_token import UserPushToken
from ..models.rate_limit import RateLimit
from ..models.user_answer import UserAnswer

# Import schemas
from ..schemas.user import UserCreate, UserCreateInternal, UserUpdate
from ..schemas.course import CourseCreate, CourseUpdate
from ..schemas.lesson import LessonCreate, LessonUpdate
from ..schemas.unit import UnitCreate, UnitUpdate
from ..schemas.exercise import (
    ExerciseCreate, 
    ExerciseUpdate, 
    ExerciseQuestionCreate, 
    ExerciseQuestionUpdate,
    ExerciseQuestionOptionCreate,
    ExerciseQuestionOptionUpdate
)
from ..schemas.question_schemas import (
    QuestionCreate,
    QuestionCreateAdmin,
    QuestionUpdate,
    QuestionOptionCreate,
    QuestionOptionUpdate,
    QuestionOptionResponse,
    QuestionTypeCreate,
    QuestionTypeUpdate,
    MatchingPairCreate,
    MatchingPairResponse,
    MatchingPairUpdate,
    SentenceOrderCreate,
    SentenceOrderResponse,
    SentenceOrderUpdate,
    AudioComprehensionCreate,
    AudioComprehensionResponse,
    AudioComprehensionUpdate,
    PronunciationCreate,
    PronunciationResponse,
    PronunciationUpdate,
    BlankCreate,
    BlankResponse,
    BlankUpdate
)
from ..schemas.progress import ProgressCreate, ProgressUpdate
from ..schemas.ai_chat_history import AIChatHistoryCreate, AIChatHistoryUpdate
from ..schemas.tier import TierCreate, TierUpdate
from ..schemas.rate_limit import RateLimitCreate, RateLimitUpdate
from ..schemas.user_refresh_token import UserRefreshTokenCreate, UserRefreshTokenUpdate
from ..schemas.answer_schemas import AnswerResponse
from ..core.schemas import TokenBlacklistCreate, TokenBlacklistUpdate
from ..schemas.gamification_schemas import (
    BadgeCreate,
    BadgeUpdate,
    UserBadgeCreate,
    UserBadgeUpdate,
    DailyGoalCreate,
    DailyGoalUpdate,
    UserExpLogCreate,
    UserExpLogUpdate
)
from ..schemas.notification_schemas import (
    NotificationCreate,
    NotificationUpdate,
    AdminPushNotificationRequest,
)


def register_admin_views(admin: CRUDAdmin) -> None:
    """Register all models and their schemas with the admin interface.

    This function adds all available models to the admin interface with appropriate
    schemas and permissions.
    """

    password_transformer = PasswordTransformer(
        password_field="password",
        hashed_field="password",
        hash_function=get_password_hash,
        required_fields=["username", "email", "password"],
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

    # Final Quiz Management - REMOVED (no longer using quizzes)

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
        update_schema=QuestionOptionUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Question Type Management (View-only)
    admin.add_view(
        model=QuestionType,
        create_schema=QuestionTypeCreate,
        update_schema=QuestionTypeUpdate,
        allowed_actions={"view"},
    )

    # ============================================================================
    # Authentication & Users (Additional)
    # ============================================================================
    
    # User Refresh Token Management (View-only)
    admin.add_view(
        model=UserRefreshToken,
        create_schema=UserRefreshTokenCreate,
        update_schema=UserRefreshTokenUpdate,
        allowed_actions={"view"},
    )

    # Token Blacklist Management (View-only)
    admin.add_view(
        model=TokenBlacklist,
        create_schema=TokenBlacklistCreate,
        update_schema=TokenBlacklistUpdate,
        allowed_actions={"view"},
    )

    # ============================================================================
    # Specialized Question Types
    # ============================================================================
    
    # Question Blank Management
    admin.add_view(
        model=QuestionBlank,
        create_schema=BlankCreate,
        update_schema=BlankUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Question Matching Pair Management
    admin.add_view(
        model=QuestionMatchingPair,
        create_schema=MatchingPairCreate,
        update_schema=MatchingPairUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Question Sentence Order Management
    admin.add_view(
        model=QuestionSentenceOrder,
        create_schema=SentenceOrderCreate,
        update_schema=SentenceOrderUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Question Audio Comprehension Management
    admin.add_view(
        model=QuestionAudioComprehension,
        create_schema=AudioComprehensionCreate,
        update_schema=AudioComprehensionUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Question Pronunciation Management
    admin.add_view(
        model=QuestionPronunciation,
        create_schema=PronunciationCreate,
        update_schema=PronunciationUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # ============================================================================
    # Exercises (Additional)
    # ============================================================================
    
    # Exercise Question Management
    admin.add_view(
        model=ExerciseQuestion,
        create_schema=ExerciseQuestionCreate,
        update_schema=ExerciseQuestionUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Exercise Question Option Management
    admin.add_view(
        model=ExerciseQuestionOption,
        create_schema=ExerciseQuestionOptionCreate,
        update_schema=ExerciseQuestionOptionUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # ============================================================================
    # User Progress Tracking (View-only)
    # ============================================================================
    
    # User Course Progress
    admin.add_view(
        model=UserCourseProgress,
        create_schema=ProgressCreate,
        update_schema=ProgressUpdate,
        allowed_actions={"view"},
    )

    # User Unit Progress
    admin.add_view(
        model=UserUnitProgress,
        create_schema=ProgressCreate,
        update_schema=ProgressUpdate,
        allowed_actions={"view"},
    )

    # User Lesson Progress
    admin.add_view(
        model=UserLessonProgress,
        create_schema=ProgressCreate,
        update_schema=ProgressUpdate,
        allowed_actions={"view"},
    )

    # User Question Errors
    admin.add_view(
        model=UserQuestionError,
        create_schema=ProgressCreate,
        update_schema=ProgressUpdate,
        allowed_actions={"view"},
    )

    # ============================================================================
    # User Answers
    # ============================================================================
    
    # User Answers (View-only)
    admin.add_view(
        model=UserAnswer,
        create_schema=AnswerResponse,
        update_schema=AnswerResponse,
        allowed_actions={"view"},
    )

    # ============================================================================
    # Gamification
    # ============================================================================
    
    # User Exp Log (View-only)
    admin.add_view(
        model=UserExpLog,
        create_schema=UserExpLogCreate,
        update_schema=UserExpLogUpdate,
        allowed_actions={"view"},
    )

    # Badge Management
    admin.add_view(
        model=Badge,
        create_schema=BadgeCreate,
        update_schema=BadgeUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # User Badge (View-only)
    admin.add_view(
        model=UserBadge,
        create_schema=UserBadgeCreate,
        update_schema=UserBadgeUpdate,
        allowed_actions={"view"},
    )

    # Daily Goal Management
    admin.add_view(
        model=DailyGoal,
        create_schema=DailyGoalCreate,
        update_schema=DailyGoalUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # ============================================================================
    # Writing Evaluation (Teacher Grading) - Skeleton
    # ============================================================================
    #
    # Future admin screen should:
    #   * Fetch `WritingSubmission` rows where status in {"submitted", "ai_graded"}.
    #   * Render a grading form with fields from `TeacherGradeSchema`.
    #   * Submit the form to POST /api/v1/writing/grade/{submission_id}.
    #   * Refresh the list when status transitions to `teacher_graded`.
    #
    # Compose / React admin clients can hook into this router by building a custom
    # page; CRUDAdmin view registration is omitted intentionally until design is ready.
    #
    # Example (pseudocode):
    #
    # admin.add_custom_view(
    #     name="Writing Submissions",
    #     path="/writing-submissions",
    #     template="writing_submissions.html",
    # )
    #

    # ============================================================================
    # Social Features (View-only)
    # ============================================================================
    
    # Friends
    admin.add_view(
        model=Friend,
        create_schema=ProgressCreate,
        update_schema=ProgressUpdate,
        allowed_actions={"view"},
    )

    # Leaderboard
    admin.add_view(
        model=Leaderboard,
        create_schema=ProgressCreate,
        update_schema=ProgressUpdate,
        allowed_actions={"view"},
    )

    # ============================================================================
    # System & Logs
    # ============================================================================
    
    # AI Logs (View-only)
    admin.add_view(
        model=AiLog,
        create_schema=ProgressCreate,
        update_schema=ProgressUpdate,
        allowed_actions={"view"},
    )

    # Notification Management
    admin.add_view(
        model=Notification,
        create_schema=NotificationCreate,
        update_schema=NotificationUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # ============================================================================
    # Tier & Rate Limiting
    # ============================================================================
    
    # Tier Management
    admin.add_view(
        model=Tier,
        create_schema=TierCreate,
        update_schema=TierUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # Rate Limit Management
    admin.add_view(
        model=RateLimit,
        create_schema=RateLimitCreate,
        update_schema=RateLimitUpdate,
        allowed_actions={"view", "create", "update", "delete"},
    )

    # ============================================================================
    # Entry Test Results (Additional)
    # ============================================================================
    
    # User Entry Test Results (View-only)
    admin.add_view(
        model=UserEntryTestResult,
        create_schema=EntryTestScoreRangeCreate,
        update_schema=EntryTestScoreRangeUpdate,
        allowed_actions={"view"},
    )