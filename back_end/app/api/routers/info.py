"""
Info router - endpoints used by the frontend to render the landing
greeting, sample-data descriptions, and the live server-status badge.

These endpoints are PUBLIC (no API-key required) so the landing UI can
load them before any user interaction.
"""
import logging
import time
from typing import Any, Dict

from fastapi import APIRouter

from app.services.sample_data_service import SAMPLE_FILES
from app.services.session_service import session_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Info"])

# Server boot time (used for uptime reporting).
_BOOT_TIME = time.time()


# Static copy used for the frontend intro. Plain English only,
# no emoji or special characters.
_INTRO = {
    "title": "Steam Game Data Analyst",
    "tagline": (
        "Ask questions in natural language about Steam games and "
        "user reviews. The AI agent can describe the sample data, run "
        "Python analysis code in a sandbox, and produce charts and "
        "tables for you."
    ),
    "system_notes": [
        "Backend runs on the Render free tier, so the server may take "
        "30 to 60 seconds to wake up after a period of inactivity.",
        "The E2B code interpreter runs on the free tier as well, which "
        "limits computation time per request.",
        "This is a single-user demo, so all sample data is shared.",
    ],
    "how_to_use": [
        "Open the chat box below and type a question about games, "
        "reviews, or your own uploaded files.",
        "Click 'Tell me about this data' on a sample to send a pre-filled "
        "query to the backend.",
        "Watch the workflow panel to see what step the system is on "
        "(thinking, running code, ...).",
        "Generated charts and tables appear in the right panel.",
    ],
    "future_work": [
        "Add image and chart understanding so the assistant can interpret "
        "uploaded visuals.",
        "Support more data sources and longer chat history.",
    ],
}


def _build_sample_data_payload() -> Dict[str, Any]:
    """Describe every bundled CSV sample (columns + friendly text)."""
    samples: Dict[str, Any] = {}
    for name, meta in SAMPLE_FILES.items():
        samples[name] = {
            "name": name,
            "title": meta.get("description", "").split(".")[0],
            "description": meta.get("description", ""),
            "columns": meta.get("columns", []),
            "kind": meta.get("kind", "sample"),
        }
    return samples


@router.get("/api/intro", summary="Landing greeting and sample-data description")
async def get_intro() -> Dict[str, Any]:
    """
    Returns the static intro text plus a description of every bundled
    sample CSV so the landing page can render the greeting and the
    sample-data cards without waiting for a database.
    """
    return {
        "intro": _INTRO,
        "sample_data": _build_sample_data_payload(),
        "session": {
            "tables": session_manager.get_table_names(),
        },
    }


@router.get("/api/status", summary="Live server connection status")
async def get_status() -> Dict[str, Any]:
    """
    Lightweight endpoint used by the frontend status badge. Reports
    uptime, the list of loaded sample files, and the free-tier note.
    No external database connection is required.
    """
    uptime_seconds = int(time.time() - _BOOT_TIME)
    tables = session_manager.get_table_names()

    return {
        "ok": True,
        "connection_state": "ready",
        "message": (
            "Server is up. The bundled CSV samples are loaded and ready "
            "to be queried."
        ),
        "uptime_seconds": uptime_seconds,
        "database": {
            "ready": True,
            "engine": "bundled-csv",
            "row_counts": {},
        },
        "session": {"tables": tables},
        "free_tier_notes": (
            "Backend is hosted on the Render free tier. The first "
            "request after a period of inactivity can take up to a "
            "minute while the service spins up. Subsequent requests "
            "are fast."
        ),
    }


@router.get("/api/sample-data/tell-me", summary="Pre-built query for the sample data")
async def sample_data_tell_me() -> Dict[str, Any]:
    """
    Returns a pre-filled user query suitable for the 'Tell me about
    this data' button on the frontend. The frontend posts it to /chat
    just like any other user query.
    """
    return {
        "query": (
            "Please briefly describe the sample data: what files are "
            "available, what columns they have, and what kinds of "
            "questions can I ask?"
        ),
    }
