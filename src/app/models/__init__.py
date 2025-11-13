# Import all models to ensure they are registered with SQLAlchemy
from .user import User
from .user_refresh_token import UserRefreshToken
from .course import Course, Unit, Lesson
from .question_type import QuestionType
from .question import Question
from .question_option import QuestionOption
from .question_matching_pair import QuestionMatchingPair
from .question_sentence_order import QuestionSentenceOrder
from .question_audio_comprehension import QuestionAudioComprehension
from .question_pronunciation import QuestionPronunciation
from .question_blank import QuestionBlank
from .user_answer import UserAnswer
from .exercise import Exercise, ExerciseQuestion, ExerciseQuestionOption  # New unified exercise model

# Import TokenBlacklist model
from ..core.db.token_blacklist import TokenBlacklist
from .progress import (
    UserCourseProgress, 
    UserUnitProgress, 
    UserLessonProgress, 
    UserQuestionError
)
from .gamification import (
    UserExpLog, 
    Badge, 
    UserBadge, 
    DailyGoal,
    DailyMission
)
from .social import Friend, Leaderboard
from .ai_log import AiLog
from .notification import Notification
from .user_push_token import UserPushToken
from .writing_submission import WritingSubmission, WritingSubmissionStatus

# Keep old models for backward compatibility (can be removed later)
from .rate_limit import RateLimit
from .tier import Tier
