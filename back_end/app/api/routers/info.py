"""
Info router — endpoints used by the frontend to render the landing
greeting, sample-data descriptions, and the live server-status badge.

These endpoints are PUBLIC (no API-key required) so the landing UI can
load them before any user interaction.
"""
import logging
import time
from typing import Any, Dict

from fastapi import APIRouter

from app.services.db_service import describe_database, get_database_overview
from app.services.sample_data_service import LOCAL_SAMPLE_NAME
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
        "Ask questions in natural language about Steam games, reviews, "
        "and users. The AI agent can describe the connected sample data, "
        "query the database directly, and run analysis code in a sandbox "
        "to produce charts and tables for you."
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
        "(thinking, querying the database, running code, ...).",
        "Generated charts and tables appear in the right panel.",
    ],
    "future_work": [
        "Add image and chart understanding so the assistant can interpret "
        "uploaded visuals.",
        "Support more databases and longer chat history.",
    ],
}

_SAMPLE_DATA_DESCRIPTION = {
    "local": {
        "name": LOCAL_SAMPLE_NAME,
        "title": "Sample revenue time series",
        "description": (
            "A small daily revenue series for two years (2024-2025). "
            "Useful for quick demos of time-series charts, monthly "
            "aggregation, and trend analysis."
        ),
        "columns": ["date", "revenue"],
        "kind": "timeseries",
    },
    "database": {
        "title": "Steam games and reviews (Supabase)",
        "description": (
            "Read-only views over a PostgreSQL database hosted on "
            "Supabase. The connected tables are games, users, and "
            "reviews. The AI agent can describe them, run aggregate "
            "queries (counts, averages), and pull sample rows on demand. "
            "It will not modify the data."
        ),
        "tables": [
            {
                "name": "db.games",
                "alias": "games",
                "description": (
                    "One row per Steam game with metadata: name, release "
                    "date, price, supported languages, and flattened "
                    "lists of publishers, developers, categories, and "
                    "genres."
                ),
            },
            {
                "name": "db.users",
                "alias": "users",
                "description": (
                    "Steam user profiles that appear in the reviews "
                    "table, including display name and game count."
                ),
            },
            {
                "name": "db.reviews",
                "alias": "reviews",
                "description": (
                    "User reviews of games, with language, optional "
                    "review text, timestamps, refund and free-copy flags, "
                    "and playtime statistics."
                ),
            },
        ],
    },
}


@router.get("/api/intro", summary="Landing greeting and sample-data description")
async def get_intro() -> Dict[str, Any]:
    """
    Returns the static intro text plus the live database row counts so
    the landing page can show how much sample data is currently in the
    connected database.
    """
    db_overview = await get_database_overview()
    db_schema = describe_database()

    # Per-table columns for the description block on the frontend.
    db_columns = {
        name: [c["name"] for c in info["columns"]]
        for name, info in db_schema.items()
    }

    return {
        "intro": _INTRO,
        "sample_data": {
            **_SAMPLE_DATA_DESCRIPTION,
            "database": {
                **_SAMPLE_DATA_DESCRIPTION["database"],
                "row_counts": db_overview.get("counts", {}),
                "available": db_overview.get("available", False),
                "columns": db_columns,
                "error": db_overview.get("error"),
            },
        },
        "session": {
            "tables": session_manager.get_table_names(),
        },
    }


@router.get("/api/status", summary="Live server connection status")
async def get_status() -> Dict[str, Any]:
    """
    Lightweight endpoint used by the frontend status badge. Pings the
    database, reports uptime, and explains the free-tier behaviour.
    """
    db_overview = await get_database_overview()
    uptime_seconds = int(time.time() - _BOOT_TIME)

    db_ready = bool(db_overview.get("available"))
    db_error = db_overview.get("error")
    counts = db_overview.get("counts", {})

    if db_ready:
        connection_state = "ready"
        status_message = (
            "Connected to Supabase. The AI can describe and query the "
            "Steam games and reviews tables."
        )
    else:
        connection_state = "warming"
        status_message = (
            "Database is not reachable right now. The backend is still "
            "waking up, or the database URL is not configured. The AI "
            "can still answer using any files you upload."
        )

    return {
        "ok": True,
        "connection_state": connection_state,
        "message": status_message,
        "uptime_seconds": uptime_seconds,
        "database": {
            "ready": db_ready,
            "counts": counts,
            "error": db_error,
        },
        "session": {
            "tables": session_manager.get_table_names(),
        },
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
            "Please briefly describe this data: what tables are "
            "available, how many rows each one has, and what kinds of "
            "questions can I ask?"
        ),
    }
