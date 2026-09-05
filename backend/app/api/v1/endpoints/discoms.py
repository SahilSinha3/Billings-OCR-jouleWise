from typing import Any

from fastapi import APIRouter

from app.core.constants import DISCOMS_LIST

router = APIRouter()


@router.get(
    "/discoms",
    response_model=list[dict[str, Any]],
    summary="List Supported DISCOMs",
    description="Returns all registered state electricity distribution companies loaded from external JSON configuration.",
)
async def list_discoms() -> list[dict[str, Any]]:
    return DISCOMS_LIST
