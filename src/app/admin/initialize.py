from typing import Optional, Annotated, Any
from pathlib import Path
import os
from urllib.parse import quote, urlparse, urlunparse

from crudadmin import CRUDAdmin
from crudadmin.core.db import get_default_db_path
from fastapi import Request, Depends, HTTPException, Query, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from ..core.config import EnvironmentOption, settings
from ..core.db.database import async_get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

import logging
from .views import register_admin_views
from .custom_assets import serve_custom_css, serve_custom_js
from ..api.v1.user_progress import (
    fetch_progress_tracker_users,
    build_exp_series_response,
)
from ..schemas.progress_tracking import ExpSeriesResponse
from ..core.exceptions.http_exceptions import NotFoundException
from ..schemas.user import UserSummary
from ..schemas.notification_schemas import AdminPushNotificationRequest
from ..schemas.writing import TeacherGradeSchema
from ..api.v1 import writing as writing_api
from ..services.push_service import FirebaseNotInitializedError, PushSendResult, send_push_notification

logger = logging.getLogger(__name__)

templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))


def create_admin_interface() -> Optional[CRUDAdmin]:
    """Create and configure the admin interface."""
    if not settings.CRUD_ADMIN_ENABLED:
        return None

    session_backend = "memory"
    redis_config = None

    if settings.CRUD_ADMIN_REDIS_ENABLED:
        session_backend = "redis"
        redis_config = {}

        redis_url = settings.CRUD_ADMIN_REDIS_URL
        raw_password = settings.CRUD_ADMIN_REDIS_PASSWORD
        password_clean: str | None
        if isinstance(raw_password, str):
            password_clean = raw_password.strip()
            if not password_clean or password_clean.lower() == "none":
                password_clean = None
        else:
            password_clean = str(raw_password) if raw_password else None

        if isinstance(redis_url, str) and redis_url.strip() and redis_url.lower() != "none":
            redis_config["url"] = redis_url.strip()
        else:
            redis_config.update(
                {
                    "host": settings.CRUD_ADMIN_REDIS_HOST,
                    "port": settings.CRUD_ADMIN_REDIS_PORT,
                    "db": settings.CRUD_ADMIN_REDIS_DB,
                }
            )
            if password_clean is not None:
                redis_config["password"] = password_clean

        if settings.CRUD_ADMIN_REDIS_SSL:
            tls_port = settings.CRUD_ADMIN_REDIS_PORT
            forced_tls_port = False
            force_tls_port_env = os.getenv("CRUD_ADMIN_REDIS_FORCE_TLS_PORT", "true").lower() == "true"
            if force_tls_port_env and tls_port == 6379:
                tls_port = 6380
                forced_tls_port = True
                logger.warning(
                    "[ADMIN_INIT] CRUD_ADMIN_REDIS_PORT was 6379 with SSL enabled; using 6380 for Upstash-compatible TLS"
                )

            if "port" in redis_config:
                redis_config["port"] = tls_port
            if "host" in redis_config and forced_tls_port:
                redis_config["host"] = settings.CRUD_ADMIN_REDIS_HOST

            if "url" in redis_config:
                parsed = urlparse(redis_config["url"])

                scheme = "rediss"
                hostname = parsed.hostname or settings.CRUD_ADMIN_REDIS_HOST
                port = parsed.port or tls_port
                if forced_tls_port and (parsed.port in (None, 6379)):
                    port = tls_port

                path = parsed.path or f"/{settings.CRUD_ADMIN_REDIS_DB}"

                raw_username = parsed.username
                password_in_url = parsed.password or password_clean

                username = raw_username
                if not username and (password_in_url or password_clean):
                    username = "default"

                if password_in_url:
                    password_in_url = quote(password_in_url)

                netloc_parts: list[str] = []
                if username:
                    creds = username
                    if password_in_url is not None:
                        creds = f"{creds}:{password_in_url}"
                    netloc_parts.append(f"{creds}@")
                elif password_in_url is not None:
                    netloc_parts.append(f":{password_in_url}@")

                if hostname:
                    netloc_parts.append(hostname)

                if port:
                    netloc_parts.append(f":{port}")

                redis_config["url"] = urlunparse(
                    (
                        scheme,
                        "".join(netloc_parts),
                        path if path else f"/{settings.CRUD_ADMIN_REDIS_DB}",
                        "",
                        "",
                        "",
                    )
                )
            else:
                password = password_clean or ""
                auth_segment = f"default:{quote(password)}@" if password else ""
                redis_config["url"] = (
                    f"rediss://{auth_segment}"
                    f"{settings.CRUD_ADMIN_REDIS_HOST}:{tls_port}/"
                    f"{settings.CRUD_ADMIN_REDIS_DB}"
                )


        if redis_config:
            sanitized_config = {}
            for key, value in redis_config.items():
                if key == "password" and value is not None:
                    sanitized_config[key] = "***"
                elif key == "url" and isinstance(value, str):
                    masked = value
                    if '://default:' in masked:
                        masked = masked.replace('://default:', '://default:***')
                    if '@' in masked:
                        parts = masked.split('@', 1)
                        masked = parts[0] + '@***@' + parts[1] if len(parts) > 1 else masked
                    sanitized_config[key] = masked
                else:
                    sanitized_config[key] = value
            logger.info("[ADMIN_INIT] Redis session config prepared: %s", sanitized_config)

    # Only set initial_admin if explicitly provided via env vars (not defaults)
    # This prevents CRUDAdmin from trying to seed admin on every request
    initial_admin = None
    
    # Check if we should force seed (even with defaults)
    force_seed = os.getenv("CRUDADMIN_FORCE_SEED", "false").lower() == "true"
    should_reset = os.getenv("CRUDADMIN_RESET", "false").lower() == "true"
    
    admin_db_path_env = os.getenv("CRUDADMIN_DB_PATH")
    if admin_db_path_env and admin_db_path_env.lower() != "none":
        admin_db_path = Path(admin_db_path_env)
    else:
        admin_db_path = Path(get_default_db_path())
    admin_db_exists = admin_db_path.exists()

    seed_requested = not admin_db_exists or force_seed or should_reset

    if seed_requested:
        if settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD:
            initial_admin = {
                "username": settings.ADMIN_USERNAME,
                "password": settings.ADMIN_PASSWORD,
            }
            logger.info(
                f"[ADMIN_INIT] Initial admin will be seeded (requested={seed_requested}, "
                f"db_exists={admin_db_exists})"
            )
        else:
            logger.warning("[ADMIN_INIT] Seed requested but admin credentials are missing; skipping")
    else:
        logger.info(
            f"[ADMIN_INIT] Admin DB already present at {admin_db_path}. Skipping initial admin seed"
        )

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

    @admin.app.get("/progress-tracker", response_class=HTMLResponse)
    async def teacher_progress_tracker(request: Request) -> HTMLResponse:
        admin_mount = settings.CRUD_ADMIN_MOUNT_PATH.rstrip("/") or "/admin"
        return templates.TemplateResponse(
            "progress_tracker.html",
            {
                "request": request,
                "admin_mount": admin_mount,
                "api_prefix": f"{admin_mount}/progress-tracker/api",
                "current_user": getattr(request.state, "user", None),
            },
        )

    @admin.app.get(
        "/progress-tracker/api/users",
        response_model=list[UserSummary],
    )
    async def admin_progress_tracker_users(
        request: Request,
        search: Annotated[str, Query(min_length=1, description="Username or email fragment to search for")],
        limit: Annotated[int, Query(ge=1, le=25)] = 10,
        db: AsyncSession = Depends(async_get_db),
        current_admin: dict = Depends(admin.admin_authentication.get_current_user),
    ) -> list[UserSummary]:
        return await fetch_progress_tracker_users(db=db, search_term=search, limit=limit)

    @admin.app.get(
        "/progress-tracker/api/exp-series",
        response_model=ExpSeriesResponse,
    )
    async def admin_progress_tracker_exp_series(
        request: Request,
        user_ids: Annotated[str, Query(min_length=1, description="Comma separated list of user UUIDs")],
        days: Annotated[int, Query(ge=1, le=365)] = 30,
        db: AsyncSession = Depends(async_get_db),
        current_admin: dict = Depends(admin.admin_authentication.get_current_user),
    ) -> ExpSeriesResponse:
        raw_ids = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
        if not raw_ids:
            return await build_exp_series_response(db=db, target_ids=[], days=days)

        try:
            target_ids = [UUID(uid) for uid in raw_ids]
        except ValueError as exc:
            raise NotFoundException("One or more user IDs are invalid") from exc

        return await build_exp_series_response(db=db, target_ids=target_ids, days=days)

    @admin.app.get("/writing-submissions", response_class=HTMLResponse)
    async def admin_writing_submissions_page(
        request: Request,
        current_admin: dict = Depends(admin.admin_authentication.get_current_user),
    ) -> HTMLResponse:
        admin_mount = settings.CRUD_ADMIN_MOUNT_PATH.rstrip("/") or "/admin"
        return templates.TemplateResponse(
            "writing_submissions.html",
            {
                "request": request,
                "admin_mount": admin_mount,
            },
        )

    @admin.app.get("/writing-submissions/api/pending")
    async def admin_writing_submissions_pending(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        db: AsyncSession = Depends(async_get_db),
        current_admin: dict = Depends(admin.admin_authentication.get_current_user),
    ) -> JSONResponse:
        response = await writing_api.list_pending_submissions(
            skip=skip,
            limit=limit,
            db=db,
            current_user=current_admin,
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content=response.model_dump())

    @admin.app.post("/writing-submissions/api/grade/{submission_id}")
    async def admin_writing_submission_grade(
        submission_id: UUID,
        payload: TeacherGradeSchema,
        db: AsyncSession = Depends(async_get_db),
        current_admin: dict = Depends(admin.admin_authentication.get_current_user),
    ) -> JSONResponse:
        result = await writing_api.grade_writing_submission(
            submission_id=submission_id,
            payload=payload,
            db=db,
            current_user=current_admin,
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content=result.model_dump())

    @admin.app.get("/push-notifications", response_class=HTMLResponse)
    async def admin_push_notifications_page(
        request: Request,
        current_admin: dict = Depends(admin.admin_authentication.get_current_user),
    ) -> HTMLResponse:
        admin_mount = settings.CRUD_ADMIN_MOUNT_PATH.rstrip("/") or "/admin"
        api_base = "/api/v1"
        return templates.TemplateResponse(
            "push_notifications.html",
            {
                "request": request,
                "admin_mount": admin_mount,
                "api_notifications_endpoint": f"{api_base}/notifications/send",
            },
        )

    @admin.app.post("/push-notifications/api/send")
    async def admin_push_notifications_send(
        payload: AdminPushNotificationRequest,
        db: AsyncSession = Depends(async_get_db),
        current_admin: dict = Depends(admin.admin_authentication.get_current_user),
    ) -> JSONResponse:
        try:
            target_ids = [UUID(str(user_id)) for user_id in payload.user_ids]
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user ID format") from exc

        try:
            result: PushSendResult = await send_push_notification(
                db=db,
                user_ids=target_ids,
                title=payload.title,
                body=payload.body,
            )
        except FirebaseNotInitializedError as exc:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": str(exc)},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Notifications dispatched",
                "stats": result.as_dict(),
            },
        )

    return admin

