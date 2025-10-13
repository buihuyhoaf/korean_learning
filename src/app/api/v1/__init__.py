from fastapi import APIRouter

from .login import router as login_router
from .logout import router as logout_router
from .rate_limits import router as rate_limits_router
from .tasks import router as tasks_router
from .tiers import router as tiers_router
from .users import router as users_router
from .google_auth import router as google_auth_router

# Korean Learning App API routers
from .course_management import router as course_management_router
from .quiz_management import router as quiz_management_router
from .user_progress import router as user_progress_router
from .mistakes import router as mistakes_router
from .badges import router as badges_router
from .daily_goals import router as daily_goals_router
from .challenges import router as challenges_router
from .friends import router as friends_router
from .leaderboard import router as leaderboard_router

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
router.include_router(quiz_management_router)
router.include_router(user_progress_router)
router.include_router(mistakes_router)
router.include_router(badges_router)
router.include_router(daily_goals_router)
router.include_router(challenges_router)
router.include_router(friends_router)
router.include_router(leaderboard_router)
