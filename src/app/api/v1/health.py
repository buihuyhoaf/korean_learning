"""Health check endpoints for various services."""

from fastapi import APIRouter

from ...core.config import settings
from ...services.languagetool_server import get_languagetool_status

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/languagetool")
async def check_languagetool_health():
    """Check LanguageTool server health status."""
    if not settings.LANGUAGETOOL_USE_LOCAL:
        return {
            "mode": "public_api",
            "status": "ok"
        }
    
    status = get_languagetool_status()
    return {
        "mode": "local_server",
        "status": "ready" if status["ready"] else "not_ready",
        "running": status["running"],
        "port": status["port"]
    }

