from fastapi import APIRouter

from app.api.v1.endpoints import bills, discoms, health
from app.api.v1.endpoints import settings as settings_endpoint

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["System Health"])
api_router.include_router(discoms.router, tags=["DISCOMs"])
api_router.include_router(bills.router, prefix="/bills", tags=["Bills & OCR"])
api_router.include_router(settings_endpoint.router, prefix="/settings", tags=["Settings & AI Configuration"])
