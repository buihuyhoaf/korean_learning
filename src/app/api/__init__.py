from fastapi import APIRouter

from ..api.v1 import router as v1_router
# DISABLED: Stroke API - inference now runs locally on Android device
# from ..api.routes import stroke_api

router = APIRouter(prefix="/api")
router.include_router(v1_router)
# DISABLED: Stroke API router - inference now runs locally on Android device
# router.include_router(stroke_api.router)
