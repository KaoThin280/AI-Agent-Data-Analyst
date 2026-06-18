"""Application configuration loaded from environment variables."""
import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings


env_path = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    OPENROUTER_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    HF_TOKEN: str = ""
    E2B_API_KEY: str = ""
    BACKEND_SECRET_TOKEN: str = ""
    TEMP_DATA_DIR: str = "temp_data"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True
        # The .env may still contain legacy keys (DATABASE_URL, PINECONE_API_KEY,
        # REDIS_URL, ...). Ignore them instead of failing the boot.
        extra = "ignore"


settings = Settings()

os.makedirs(settings.TEMP_DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(name)-25s | %(levelname)-5s | %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
