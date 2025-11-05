from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from starlette.types import ASGIApp, Receive, Scope, Send
from typing import Callable

from .admin.initialize import create_admin_interface
from .admin.custom_assets import serve_custom_css, serve_custom_js
from .api import router
from .core.config import settings
from .core.setup import create_application, lifespan_factory
from .core import logger  # Import logger configuration

admin = create_admin_interface()


class AdminAssetInjectorMiddleware(BaseHTTPMiddleware):
    """Middleware to inject custom CSS/JS into admin HTML responses."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Inject custom assets into admin HTML responses."""
        response = await call_next(request)
        
        # Only process admin requests
        if not request.url.path.startswith(settings.CRUD_ADMIN_MOUNT_PATH):
            return response
        
        # Check if response is HTML by content type
        content_type = response.headers.get('content-type', '')
        if 'text/html' not in content_type:
            return response
        
        # Inject CSS and JS before </body> tag
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        body_str = body.decode('utf-8')
        if '</body>' in body_str:
            # Inject custom assets before closing body tag
            injection = '''
    <link rel="stylesheet" href="/admin-static/custom.css">
    <script src="/admin-static/custom.js"></script>
    '''
            body_str = body_str.replace('</body>', injection + '</body>', 1)
            body = body_str.encode('utf-8')
        
        # Create new response with updated content and headers (remove old content-length)
        new_headers = dict(response.headers)
        new_headers.pop('content-length', None)
        return HTMLResponse(
            content=body, 
            status_code=response.status_code,
            headers=new_headers,
            media_type=response.media_type
        )


@asynccontextmanager
async def lifespan_with_admin(app: FastAPI) -> AsyncGenerator[None, None]:
    """Custom lifespan that includes admin initialization."""
    # Get the default lifespan
    default_lifespan = lifespan_factory(settings)

    # Run the default lifespan initialization and our admin initialization
    async with default_lifespan(app):
        # Initialize admin interface if it exists
        if admin:
            # Initialize admin database and setup
            await admin.initialize()

        yield


app = create_application(router=router, settings=settings, lifespan=lifespan_with_admin)

# Add admin asset injector middleware
app.add_middleware(AdminAssetInjectorMiddleware)

# Add global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to catch all unhandled exceptions"""
    print(f"[GLOBAL_EXCEPTION_HANDLER] Caught exception: {exc}")
    print(f"[GLOBAL_EXCEPTION_HANDLER] Exception type: {type(exc).__name__}")
    print(f"[GLOBAL_EXCEPTION_HANDLER] Full traceback:")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Register admin static assets on main app (accessible without admin auth)
if admin:
    app.get("/admin-static/custom.css")(serve_custom_css)
    app.get("/admin-static/custom.js")(serve_custom_js)
    print(f"[MAIN] ✅ Registered admin static assets on main app")
    
    # Mount admin interface if enabled (after routes)
    app.mount(settings.CRUD_ADMIN_MOUNT_PATH, admin.app)

# --- Health endpoints ---
@app.get("/", include_in_schema=False)
async def root_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}
