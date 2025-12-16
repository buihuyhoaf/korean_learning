from arq.connections import RedisSettings
from arq.cron import CronJob

from ...core.config import settings
from .functions import (
    sample_background_task,
    shutdown,
    startup,
    update_weekly_leaderboard_dummy_xp
)

REDIS_QUEUE_HOST = settings.REDIS_QUEUE_HOST
REDIS_QUEUE_PORT = settings.REDIS_QUEUE_PORT


class WorkerSettings:
    functions = [sample_background_task]
    redis_settings = RedisSettings(host=REDIS_QUEUE_HOST, port=REDIS_QUEUE_PORT)
    on_startup = startup
    on_shutdown = shutdown
    handle_signals = False
    
    # Cron jobs - run daily at 00:00 UTC
    cron_jobs = [
        CronJob(
            # arq CronJob signature in this project requires these args
            name="update_weekly_leaderboard_dummy_xp",
            coroutine=update_weekly_leaderboard_dummy_xp,
            month=None,
            day=None,
            weekday=None,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            unique=False,
            job_id=None,
            timeout_s=300,
            keep_result_s=3600,
            keep_result_forever=False,
            max_tries=5,
            run_at_startup=False
        )
    ]
