"""
Sample data service - registers pre-loaded sample tables so the user
has data to query immediately after opening the page, without having
to upload anything.

Two sources of sample data are supported:
  1. Local CSV file shipped with the backend (sample_timeseries.csv).
  2. Read-only views over the connected Supabase Steam database.

This module is invoked once during application startup. The database
bootstrap includes a small retry loop to ride out the Render free-tier
cold start (the container may not have outbound internet for the
first 1-2 seconds after the process starts).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.data_service import DataProcessor
from app.services.db_service import (
    describe_database,
    get_database_overview,
    get_database_summary,
)
from app.services.session_service import session_manager

logger = logging.getLogger(__name__)

# Filename of the bundled CSV sample shipped with the backend.
LOCAL_SAMPLE_NAME = "sample_timeseries.csv"

# Cold-start retry policy. We give the container up to ~10 seconds to
# gain outbound network access; that is usually enough on Render free
# tier (DNS is set up almost immediately, but the first TCP connect
# to Supabase can take a couple of seconds).
_DB_RETRY_ATTEMPTS = 4
_DB_RETRY_DELAY_SECONDS = 2.0


def register_local_sample() -> bool:
    """
    Register the bundled local CSV sample as a session table.
    Returns True if the file was found and registered.
    """
    file_path = os.path.join(settings.TEMP_DATA_DIR, LOCAL_SAMPLE_NAME)
    if not os.path.isfile(file_path):
        # Fall back to a copy living next to the package.
        repo_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", LOCAL_SAMPLE_NAME)
        )
        if os.path.isfile(repo_path):
            file_path = repo_path
        else:
            logger.info(
                "Local sample '%s' not found; skipping registration.",
                LOCAL_SAMPLE_NAME,
            )
            return False

    try:
        ctx = DataProcessor.extract_data_context(file_path)
        session_manager.add_table(
            table_name=LOCAL_SAMPLE_NAME,
            file_path=file_path,
            columns=ctx.columns,
            source="sample",
        )
        logger.info(
            "Local sample registered: %s (%d rows, %d cols)",
            LOCAL_SAMPLE_NAME,
            ctx.num_rows,
            ctx.num_columns,
        )
        return True
    except Exception as exc:
        logger.warning("Could not register local sample: %s", exc)
        return False


async def _try_fetch_db_state() -> Optional[Dict[str, Any]]:
    """
    Single attempt to ping the database and produce a fresh overview.
    Returns None on any failure.
    """
    try:
        overview = await get_database_overview()
        if not overview.get("available"):
            return None
        summary = await get_database_summary()
        return {"overview": overview, "summary": summary}
    except Exception as exc:
        logger.debug("DB state fetch attempt failed: %s", exc)
        return None


async def _wait_for_database(wait_seconds: float = _DB_RETRY_DELAY_SECONDS) -> bool:
    """
    Poll the database with a short delay between attempts. Returns
    True once the database is reachable and the row counts come back
    populated. Returns False if every attempt fails.

    The goal is to avoid noisy "[Errno 101] Network is unreachable"
    warnings that appear when the app boots before Render finishes
    wiring up outbound network access on the free tier.
    """
    for attempt in range(1, _DB_RETRY_ATTEMPTS + 1):
        state = await _try_fetch_db_state()
        if state is not None:
            return True
        if attempt < _DB_RETRY_ATTEMPTS:
            logger.info(
                "Database not reachable yet (attempt %d/%d). "
                "Waiting %.1fs for outbound network...",
                attempt,
                _DB_RETRY_ATTEMPTS,
                wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
    return False


async def register_db_sample() -> bool:
    """
    Register virtual sample tables that map onto the Supabase Steam
    schema. These entries have no on-disk file but expose column
    metadata so the LLM knows about them.
    Returns True if at least one table was successfully registered.
    """
    schema = describe_database()
    registered = 0
    for table_name, info in schema.items():
        columns_meta: Dict[str, Dict[str, Any]] = {}
        for col in info["columns"]:
            col_name = col["name"]
            columns_meta[col_name] = {
                "dtype": col["type"],
                "business_meaning": (
                    f"{col_name} ({col['type']})"
                    + (f" — {col['key']}" if col.get("key") else "")
                ),
            }
        session_manager.add_table(
            table_name=f"db.{table_name}",
            file_path="",
            columns=columns_meta,
            source="db",
        )
        registered += 1

    # Wait for the database to be reachable (handles Render cold start),
    # then cache the row-count summary in the session.
    db_ready = await _wait_for_database()
    if db_ready:
        try:
            overview = await get_database_overview()
            summary = await get_database_summary()
            session_manager.set_db_summary(summary, overview.get("available", False))
            logger.info(
                "DB sample registered (%d tables, available=%s, summary length=%d)",
                registered,
                overview.get("available", False),
                len(summary),
            )
        except Exception as exc:
            logger.warning("Could not cache DB summary: %s", exc)
            session_manager.set_db_summary("", False)
    else:
        logger.warning(
            "Database still unreachable after %d attempts. "
            "Sample tables are registered, but row counts will be 0 "
            "until the next /api/status poll succeeds.",
            _DB_RETRY_ATTEMPTS,
        )
        session_manager.set_db_summary("", False)

    return registered > 0


async def bootstrap_sample_data() -> Dict[str, Any]:
    """
    Run all sample-data registration on startup. Returns a status dict
    that the application can use for logging or for /api/status.
    """
    local_ok = register_local_sample()
    db_ok = await register_db_sample()
    return {
        "local_sample": local_ok,
        "db_sample": db_ok,
        "tables": session_manager.get_table_names(),
        "db_ready": session_manager.is_db_available(),
    }
