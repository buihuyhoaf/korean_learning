from fastapi import APIRouter

from ..api.v1 import router as v1_router
from ..api.routes import stroke_api

router = APIRouter(prefix="/api")
router.include_router(v1_router)
router.include_router(stroke_api.router)
