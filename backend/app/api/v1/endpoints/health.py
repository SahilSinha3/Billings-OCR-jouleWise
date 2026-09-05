from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common_dto import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Status",
    description="Returns the operational status of the JouleWise API, queue engine, and OCR adapter.",
)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="1.0.0",
        queue_driver=settings.QUEUE_DRIVER,
        ocr_engine=settings.OCR_ENGINE,
    )
