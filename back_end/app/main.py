"""
FastAPI application entry point for the Data Analyst AI System.

Registers all core routers, applies CORS middleware, and exposes root
redirect to the interactive API documentation. All protected endpoints
use X-API-Key authentication.
"""
import os
import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.api.routers import upload, chat, manual_plot, reviews, download
from app.core.config import settings
from app.core.security import get_api_key
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# ── Ensure required directories exist ────────────────────────────────
os.makedirs(settings.TEMP_DATA_DIR, exist_ok=True)

# ── Application instance ─────────────────────────────────────────────

app = FastAPI(
    title="Data Analyst AI System",
    description=(
        "Agentic AI-powered data analysis backend. Upload your CSV/Excel "
        "files, ask natural-language questions, and get auto-generated "
        "Python code, interactive charts, and business insights."
    ),
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (permissive for development; lock down origins in production) ─
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
  # Cấu hình cung cấp quyền truy cập qua HTTP cho thư mục temp_data
app.mount("/temp_data", StaticFiles(directory="temp_data"), name="temp_data")
# Thêm mount cho /tables (cùng thư mục temp_data)
#app.mount("/tables", StaticFiles(directory=settings.TEMP_DATA_DIR), name="tables")
logger.info("Static files mounted: /temp_data and /tables → %s", settings.TEMP_DATA_DIR)
logger.info("CORS configured (allow_origins=*). Set specific origins for production.")

# ── Register core routers ────────────────────────────────────────────
# All protected endpoints use X-API-Key via dependency injection in each router.
app.include_router(upload.router, prefix="", tags=["1. File Upload & Analysis"])
app.include_router(chat.router, prefix="", tags=["2. AI Chat & Workflow"])
app.include_router(manual_plot.router, prefix="", tags=["3. Manual Charting Data"])
app.include_router(reviews.router, prefix="", tags=["4. User Feedback"])

app.include_router(download.router, prefix="", tags=["5. File Download & Management"])

logger.info("Routers registered: upload, chat, manual_plot, reviews, download")
# ── Root endpoint ────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to the interactive Swagger documentation."""
    return RedirectResponse(url="/docs")

# ── Health check ─────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """
    Simple health check endpoint. Returns 200 OK if the server is running.
    """
    return {
        "status": "healthy",
        "version": "2.2.0",
        "temp_data_dir": settings.TEMP_DATA_DIR,
    }

