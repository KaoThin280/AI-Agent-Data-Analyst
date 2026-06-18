"""
Sample data service — registers pre-loaded sample tables so the user
has data to query immediately after opening the page, without having
to upload anything.

Two sources of sample data are supported:
  1. Local CSV file shipped with the backend (sample_timeseries.csv).
  2. Read-only views over the connected Supabase Steam database.

This module is invoked once during application startup.
"""
from __future__ import annotations

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

    # Cache the database summary for the system prompt.
    try:
        summary = await get_database_summary()
        overview = await get_database_overview()
        session_manager.set_db_summary(summary, overview["available"])
        logger.info(
            "DB sample registered (%d tables, available=%s, summary length=%d)",
            registered,
            overview["available"],
            len(summary),
        )
    except Exception as exc:
        logger.warning("Could not cache DB summary: %s", exc)
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
    }
