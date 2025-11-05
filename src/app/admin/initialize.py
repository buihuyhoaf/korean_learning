from typing import Optional
from pathlib import Path

from crudadmin import CRUDAdmin
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from ..core.config import EnvironmentOption, settings
from ..core.db.database import async_get_db
import logging
from .views import register_admin_views
from .custom_assets import serve_custom_css, serve_custom_js

logger = logging.getLogger(__name__)


def create_admin_interface() -> Optional[CRUDAdmin]:
    """Create and configure the admin interface."""
    if not settings.CRUD_ADMIN_ENABLED:
        return None

    session_backend = "memory"
    redis_config = None

    if settings.CRUD_ADMIN_REDIS_ENABLED:
        session_backend = "redis"
        redis_config = {
            "host": settings.CRUD_ADMIN_REDIS_HOST,
            "port": settings.CRUD_ADMIN_REDIS_PORT,
            "db": settings.CRUD_ADMIN_REDIS_DB,
            "password": settings.CRUD_ADMIN_REDIS_PASSWORD if settings.CRUD_ADMIN_REDIS_PASSWORD != "None" else None,
        }

    # Only set initial_admin if explicitly provided via env vars (not defaults)
    # This prevents CRUDAdmin from trying to seed admin on every request
    initial_admin = None
    import os
    
    # Check if we should force seed (even with defaults)
    force_seed = os.getenv("CRUDADMIN_FORCE_SEED", "false").lower() == "true"
    should_reset = os.getenv("CRUDADMIN_RESET", "false").lower() == "true"
    
    if settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD:
        # Check if values are not the defaults (to avoid auto-seeding in production)
        default_username = "admin"
        default_password = "!Ch4ng3Th1sP4ssW0rd!"
        
        # Only set initial_admin if:
        # 1. Values are explicitly different from defaults, OR
        # 2. CRUDADMIN_FORCE_SEED=true (to force seed even with defaults), OR  
        # 3. CRUDADMIN_RESET=true (to seed after reset)
        if (settings.ADMIN_USERNAME != default_username or 
            settings.ADMIN_PASSWORD != default_password or
            force_seed or
            should_reset):
            initial_admin = {
                "username": settings.ADMIN_USERNAME,
                "password": settings.ADMIN_PASSWORD,
            }
            logger.info(f"[ADMIN_INIT] Initial admin will be seeded: username={settings.ADMIN_USERNAME}")
        else:
            logger.info(f"[ADMIN_INIT] Skipping initial admin seed (using defaults without force_seed)")
    else:
        logger.info(f"[ADMIN_INIT] No initial admin credentials provided, skipping seed")

    admin = CRUDAdmin(
        session=async_get_db,
        SECRET_KEY=settings.SECRET_KEY.get_secret_value(),
        mount_path=settings.CRUD_ADMIN_MOUNT_PATH,
        session_backend=session_backend,
        redis_config=redis_config,
        allowed_ips=settings.CRUD_ADMIN_ALLOWED_IPS_LIST if settings.CRUD_ADMIN_ALLOWED_IPS_LIST else None,
        allowed_networks=settings.CRUD_ADMIN_ALLOWED_NETWORKS_LIST
        if settings.CRUD_ADMIN_ALLOWED_NETWORKS_LIST
        else None,
        max_sessions_per_user=settings.CRUD_ADMIN_MAX_SESSIONS,
        session_timeout_minutes=settings.CRUD_ADMIN_SESSION_TIMEOUT,
        secure_cookies=settings.SESSION_SECURE_COOKIES,
        enforce_https=settings.ENVIRONMENT == EnvironmentOption.PRODUCTION,
        track_events=settings.CRUD_ADMIN_TRACK_EVENTS,
        track_sessions_in_db=settings.CRUD_ADMIN_TRACK_SESSIONS,
        initial_admin=initial_admin,
    )

    # Mount static files for widgets in admin app
    custom_static_dir = Path(__file__).parent.parent / "static"
    if custom_static_dir.exists():
        admin.app.mount("/static/widgets", StaticFiles(directory=str(custom_static_dir)), name="admin_widgets_static")
        print(f"[ADMIN_INIT] ✅ Mounted widgets static at /admin/static/widgets from {custom_static_dir}")
    
    # Register custom CSS and JS routes
    admin.app.get("/custom.css")(serve_custom_css)
    admin.app.get("/custom.js")(serve_custom_js)
    print(f"[ADMIN_INIT] ✅ Registered custom CSS and JS routes")

    register_admin_views(admin)

    return admin

