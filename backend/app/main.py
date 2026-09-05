from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import JouleWiseBaseException
from app.core.logging import logger
from app.db.session import Base, engine
from app.workers.queue import task_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing JouleWise database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Starting JouleWise background task queue worker...")
    task_queue.start()
    yield
    logger.info("Shutting down JouleWise...")


app = FastAPI(
    title="JouleWise: Enterprise State Electricity Bill OCR & Tariff API",
    description="Automated state electricity bill data ingestion, multi-engine OCR extraction, deterministic math verification, and tariff audit.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(JouleWiseBaseException)
async def joulewise_exception_handler(request: Request, exc: JouleWiseBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


app.include_router(api_router)
