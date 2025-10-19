# Import all models to ensure they are registered with SQLAlchemy
from .user import User
from .user_refresh_token import UserRefreshToken
from .course import Course, Unit, Lesson
from .quiz import Quiz, QuestionType, Question, QuestionOption
from .entry_test import EntryTest, EntryTestQuestion, EntryTestQuestionOption, UserEntryTestResult, EntryTestResult, UserEntryTestHistory

# Import TokenBlacklist model
from ..core.db.token_blacklist import TokenBlacklist
from .exercise import ListeningExercise, SpeakingExercise, WritingExercise
from .progress import (
    UserCourseProgress, 
    UserUnitProgress, 
    UserLessonProgress, 
    UserQuizAttempt, 
    UserQuestionAttempt, 
    UserQuestionError
)
from .gamification import (
    UserExpLog, 
    Badge, 
    UserBadge, 
    DailyGoal, 
    Challenge, 
    UserChallenge
)
from .social import Friend, Leaderboard
from .ai_log import AiLog
from .notification import Notification

# Keep old models for backward compatibility (can be removed later)
from .rate_limit import RateLimit
from .tier import Tier
