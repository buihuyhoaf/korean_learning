from fastapi import APIRouter

from .login import router as login_router
from .logout import router as logout_router
from .rate_limits import router as rate_limits_router
from .tasks import router as tasks_router
from .tiers import router as tiers_router
from .users import router as users_router
from .google_auth import router as google_auth_router
# from .google_auth_simple import router as google_auth_simple_router
# from .google_auth_working import router as google_auth_working_router
# from .google_auth_new import router as google_auth_new_router

# Korean Learning App API routers
from .course_management import router as course_management_router
from .user_progress import router as user_progress_router
from .mistakes import router as mistakes_router
from .badges import router as badges_router
from .daily_goals import router as daily_goals_router
from .missions import router as missions_router
from .friends import router as friends_router
from .weekly_leaderboard import router as weekly_leaderboard_router
from .upload import router as upload_router
from .predict import router as predict_router
from .grade import router as grade_router
from .pronunciation import router as pronunciation_router
from .routes.notification import router as notification_router
from .user_notifications import router as user_notifications_router
from .push_tokens import router as push_tokens_router
from .writing import router as writing_router
from .health import router as health_router

router = APIRouter(prefix="/v1")

# Core API routers
router.include_router(login_router)
router.include_router(logout_router)
router.include_router(google_auth_router)
router.include_router(users_router)
router.include_router(tasks_router)
router.include_router(tiers_router)
router.include_router(rate_limits_router)

# Korean Learning App API routers
router.include_router(course_management_router)
router.include_router(user_progress_router)
router.include_router(mistakes_router)
router.include_router(badges_router)
router.include_router(daily_goals_router)
router.include_router(missions_router)
router.include_router(friends_router)
router.include_router(weekly_leaderboard_router)
router.include_router(upload_router)
router.include_router(predict_router)
router.include_router(grade_router)
router.include_router(pronunciation_router)
router.include_router(push_tokens_router)
router.include_router(notification_router)
router.include_router(user_notifications_router)
router.include_router(writing_router)
router.include_router(health_router)
