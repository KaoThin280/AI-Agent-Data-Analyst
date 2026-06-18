"""
Sample data service - registers the bundled CSV files so the user
has data to query immediately after opening the page, without
having to upload anything.

This module is invoked once during application startup.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.data_service import DataProcessor
from app.services.session_service import session_manager

logger = logging.getLogger(__name__)

# Bundled sample files (ship with the backend).
SAMPLE_FILES = {
    "sample_timeseries.csv": {
        "description": (
            "A small daily revenue series for two years (2024-2025). "
            "Useful for quick demos of time-series charts, monthly "
            "aggregation, and trend analysis."
        ),
        "columns": ["date", "revenue"],
        "kind": "timeseries",
    },
    "metadata.csv": {
        "description": (
            "Steam game metadata for a sample of titles. One row per "
            "game with name, release date, price, supported languages, "
            "and flattened lists of publishers, developers, categories, "
            "and genres."
        ),
        "columns": [
            "steam_appid", "name", "is_free", "supported_languages",
            "required_age", "release_date", "publishers", "developers",
            "categories", "genres", "price_text",
        ],
        "kind": "games_metadata",
    },
    "reviews.csv": {
        "description": (
            "User reviews for the games in metadata.csv, with language, "
            "timestamps, refund and free-copy flags, and playtime "
            "statistics. The review text column is intentionally not "
            "included in this sample."
        ),
        "columns": [
            "recommendationid", "steam_appid", "steamid", "language",
            "timestamp_created", "timestamp_updated", "refunded",
            "received_for_free", "written_during_early_access",
            "primarily_steam_deck", "playtime_at_review",
            "playtime_last_two_weeks", "playtime_forever",
        ],
        "kind": "user_reviews",
    },
}


def _resolve_file_path(filename: str) -> Optional[str]:
    """Find the sample file, preferring back_end/temp_data/."""
    primary = os.path.join(settings.TEMP_DATA_DIR, filename)
    if os.path.isfile(primary):
        return primary
    # Fall back to a copy next to the package.
    fallback = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", filename)
    )
    return fallback if os.path.isfile(fallback) else None


def _extract_column_meta(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Use DataProcessor to get column dtype + business meaning."""
    try:
        ctx = DataProcessor.extract_data_context(file_path)
        return ctx.columns
    except Exception as exc:
        logger.warning("Could not extract column metadata for %s: %s", file_path, exc)
        return {}


def register_sample_file(filename: str) -> bool:
    """
    Register a single bundled CSV as a session table.
    Returns True if the file was found and registered.
    """
    file_path = _resolve_file_path(filename)
    if not file_path:
        logger.info("Sample file '%s' not found; skipping registration.", filename)
        return False

    columns = _extract_column_meta(file_path)
    if not columns:
        return False

    session_manager.add_table(
        table_name=filename,
        file_path=file_path,
        columns=columns,
        source="sample",
    )
    logger.info(
        "Sample registered: %s (%d columns)",
        filename,
        len(columns),
    )
    return True


def register_all_samples() -> Dict[str, bool]:
    """Register every bundled CSV file. Returns a dict of name -> success."""
    results: Dict[str, bool] = {}
    for filename in SAMPLE_FILES.keys():
        results[filename] = register_sample_file(filename)
    return results


async def bootstrap_sample_data() -> Dict[str, Any]:
    """
    Run all sample-data registration on startup. Returns a status dict
    that the application can use for logging or for /api/status.
    """
    results = register_all_samples()
    return {
        "samples": results,
        "tables": session_manager.get_table_names(),
    }
