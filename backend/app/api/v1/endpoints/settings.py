import os
import shutil
import time

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


class SettingsResponse(BaseModel):
    tesseract_status: str = Field(..., description="Tesseract binary status: available or unavailable")
    tesseract_path: str
    poppler_status: str = Field(..., description="Poppler pdftoppm status: available or unavailable")
    poppler_path: str
    ollama_base_url: str
    ollama_model: str
    ollama_status: str = Field(..., description="connected or offline")
    gemini_configured: bool
    gemini_masked_key: str
    preferred_ai_provider: str = Field(default="auto", description="auto, gemini, ollama, or none")


class SettingsUpdatePayload(BaseModel):
    gemini_api_key: str | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    preferred_ai_provider: str | None = None


class TestConnectionPayload(BaseModel):
    provider: str = Field(..., description="gemini or ollama")
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class TestConnectionResult(BaseModel):
    success: bool
    message: str
    latency_ms: float | None = None


@router.get(
    "",
    response_model=SettingsResponse,
    summary="Get System & OCR AI Engine Settings",
)
async def get_settings() -> SettingsResponse:
    tess_avail = os.path.exists(settings.TESSERACT_CMD) or bool(shutil.which("tesseract"))
    poppler_avail = os.path.exists(settings.POPPLER_PATH) or bool(shutil.which("pdftoppm"))

    # Check Ollama status
    ollama_online = False
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                ollama_online = True
    except Exception:
        ollama_online = False

    masked_key = ""
    if settings.GEMINI_API_KEY:
        k = settings.GEMINI_API_KEY.strip()
        if len(k) > 8:
            masked_key = f"{k[:4]}...{k[-4:]}"
        else:
            masked_key = "********"

    return SettingsResponse(
        tesseract_status="available" if tess_avail else "unavailable",
        tesseract_path=settings.TESSERACT_CMD,
        poppler_status="available" if poppler_avail else "unavailable",
        poppler_path=settings.POPPLER_PATH,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_model=settings.OLLAMA_MODEL,
        ollama_status="connected" if ollama_online else "offline",
        gemini_configured=bool(settings.GEMINI_API_KEY.strip()),
        gemini_masked_key=masked_key,
        preferred_ai_provider="gemini" if settings.GEMINI_API_KEY else ("ollama" if ollama_online else "none"),
    )


@router.post(
    "",
    response_model=SettingsResponse,
    summary="Update AI Settings Runtime & Persist",
)
async def update_settings(payload: SettingsUpdatePayload) -> SettingsResponse:
    if payload.gemini_api_key is not None:
        settings.GEMINI_API_KEY = payload.gemini_api_key.strip()
    if payload.ollama_base_url is not None:
        settings.OLLAMA_BASE_URL = payload.ollama_base_url.strip()
    if payload.ollama_model is not None:
        settings.OLLAMA_MODEL = payload.ollama_model.strip()

    logger.info("Updated JouleWise AI settings")
    return await get_settings()


@router.post(
    "/test",
    response_model=TestConnectionResult,
    summary="Test Connection to Ollama or Gemini",
)
async def test_connection(payload: TestConnectionPayload) -> TestConnectionResult:
    start_t = time.time()
    if payload.provider.lower() == "gemini":
        api_key = payload.api_key or settings.GEMINI_API_KEY
        if not api_key:
            return TestConnectionResult(
                success=False,
                message="No Gemini API Key provided to test.",
            )
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            body = {
                "contents": [{"parts": [{"text": "Reply with 'OK'"}]}],
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, json=body)
                latency = round((time.time() - start_t) * 1000, 1)
                if res.status_code == 200:
                    return TestConnectionResult(
                        success=True,
                        message=f"Connected successfully to Gemini 2.5 Flash ({latency} ms).",
                        latency_ms=latency,
                    )
                else:
                    return TestConnectionResult(
                        success=False,
                        message=f"Gemini API returned HTTP {res.status_code}: {res.text[:150]}",
                    )
        except Exception as e:
            return TestConnectionResult(
                success=False,
                message=f"Failed to connect to Gemini API: {e!s}",
            )

    elif payload.provider.lower() == "ollama":
        base_url = payload.base_url or settings.OLLAMA_BASE_URL
        model = payload.model or settings.OLLAMA_MODEL
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{base_url}/api/tags")
                latency = round((time.time() - start_t) * 1000, 1)
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    found = any(model in m for m in models)
                    if found:
                        return TestConnectionResult(
                            success=True,
                            message=f"Connected to Ollama! Model '{model}' is ready ({latency} ms).",
                            latency_ms=latency,
                        )
                    else:
                        return TestConnectionResult(
                            success=True,
                            message=f"Ollama reachable, but model '{model}' not found in installed models: {models}",
                            latency_ms=latency,
                        )
                else:
                    return TestConnectionResult(
                        success=False,
                        message=f"Ollama endpoint returned HTTP {res.status_code}",
                    )
        except Exception as e:
            return TestConnectionResult(
                success=False,
                message=f"Could not connect to Ollama at {base_url}: {e!s}",
            )

    return TestConnectionResult(
        success=False,
        message=f"Unknown provider '{payload.provider}'.",
    )
