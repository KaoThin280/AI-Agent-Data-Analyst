"""
FastAPI application entry point for the Steam Game Data Analyst.

Registers all core routers, applies CORS middleware, exposes the
interactive Swagger docs, and bootstraps the bundled CSV samples on
startup. Public endpoints (info, status, health) do not require an
API key so the landing UI can render the greeting immediately.
"""
import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import upload, chat, manual_plot, reviews, download, info
from app.core.config import settings
from app.services.sample_data_service import bootstrap_sample_data

logger = logging.getLogger(__name__)

_BOOT_TIME = time.time()


os.makedirs(settings.TEMP_DATA_DIR, exist_ok=True)


app = FastAPI(
    title="Steam Game Data Analyst",
    description=(
        "Agentic AI-powered data analysis backend. The system ships "
        "with three bundled CSV samples (sample_timeseries, metadata, "
        "reviews) and an E2B code sandbox. The AI can describe the "
        "data, run read-only CSV queries, and produce Python "
        "visualisations on demand."
    ),
    version="2.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/temp_data", StaticFiles(directory="temp_data"), name="temp_data")
logger.info("Static files mounted: /temp_data -> %s", settings.TEMP_DATA_DIR)
logger.info("CORS configured (allow_origins=*). Set specific origins for production.")


# Register public routers first (no API key required)
app.include_router(info.router, prefix="", tags=["0. Info & Status"])


# Register core protected routers
app.include_router(upload.router, prefix="", tags=["1. File Upload & Analysis"])
app.include_router(chat.router, prefix="", tags=["2. AI Chat & Workflow"])
app.include_router(manual_plot.router, prefix="", tags=["3. Manual Charting Data"])
app.include_router(reviews.router, prefix="", tags=["4. User Feedback"])
app.include_router(download.router, prefix="", tags=["5. File Download & Management"])

logger.info(
    "Routers registered: info, upload, chat, manual_plot, reviews, download"
)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to the interactive Swagger documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check. Reports server uptime, sample-data status, and
    whether the CSV samples are present on disk.
    """
    sample_files = []
    if os.path.isdir(settings.TEMP_DATA_DIR):
        sample_files = sorted(
            f for f in os.listdir(settings.TEMP_DATA_DIR)
            if f.endswith(".csv")
        )
    return {
        "status": "healthy",
        "version": "2.4.0",
        "uptime_seconds": int(time.time() - _BOOT_TIME),
        "temp_data_dir": settings.TEMP_DATA_DIR,
        "sample_files": sample_files,
    }


# Startup / shutdown hooks
@app.on_event("startup")
async def _on_startup() -> None:
    """Register the bundled CSV samples."""
    try:
        status = await bootstrap_sample_data()
        logger.info(
            "Sample data bootstrap: samples=%s, tables=%s",
            status.get("samples"),
            status.get("tables"),
        )
    except Exception as exc:
        logger.warning("Sample data bootstrap failed: %s", exc)


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    """Cleanup on shutdown (no DB connections to close in CSV-only mode)."""
    return None
