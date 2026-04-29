from fastapi import APIRouter

from app.api.endpoints.health import router as health_router
from app.api.endpoints.video_records import router as video_records_router
from app.api.endpoints.sheets import router as sheets_router
from app.api.endpoints.admin import router as admin_router
from app.api.endpoints.presets import router as presets_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(video_records_router)
api_router.include_router(sheets_router)
api_router.include_router(admin_router)
api_router.include_router(presets_router)