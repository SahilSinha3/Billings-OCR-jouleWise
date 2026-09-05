from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Overall system health status")
    version: str = Field(default="1.0.0", description="API version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Current server UTC timestamp",
    )
    queue_driver: str = Field(..., description="Active task queue driver")
    ocr_engine: str = Field(..., description="Active OCR engine")


class ErrorResponse(BaseModel):
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable error explanation")
    details: dict[str, Any] | None = Field(default=None, description="Granular error attributes and context")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when error occurred",
    )
