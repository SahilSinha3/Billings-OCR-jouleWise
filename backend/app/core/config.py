from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "JouleWise Enterprise OCR"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    DATABASE_URL: str = "postgresql+asyncpg://sahilsinha@localhost:5432/joulewise_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    TESSERACT_CMD: str = "/opt/homebrew/bin/tesseract"
    POPPLER_PATH: str = "/opt/homebrew/bin"
    OCR_ENGINE: str = "Tesseract"
    QUEUE_DRIVER: str = "asyncio.Queue"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    GEMINI_API_KEY: str = ""

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    JWT_SECRET_KEY: str = "dev_secret_key_change_in_production_983719471928471"


settings = Settings()
