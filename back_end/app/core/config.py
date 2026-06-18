
"""
Application configuration loaded from environment variables.
Uses Pydantic BaseSettings for type-safe, validated config.
"""
import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings


# Load .env file from project root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
class Settings(BaseSettings):
    # ── API Keys ──────────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    HF_TOKEN: str = ""
    E2B_API_KEY: str = ""
    PINECONE_API_KEY: str = ""
    BACKEND_SECRET_TOKEN: str = ""

    # ── Database (Supabase PostgreSQL) ────────────────────────────────
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DEBUG: bool = False

    # ── Paths ─────────────────────────────────────────────────────────
    TEMP_DATA_DIR: str = "temp_data"

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton settings instance
settings = Settings()

# ── Ensure temp directory exists ────────────────────────────────────
os.makedirs(settings.TEMP_DATA_DIR, exist_ok=True)

# ── Quick logging setup ──────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(name)-25s | %(levelname)-5s | %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
