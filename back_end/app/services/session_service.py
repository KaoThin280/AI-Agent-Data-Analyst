"""
Session manager — tracks uploaded tables, generated files, installed
packages, and pre-loaded sample data throughout the lifecycle of a
single server instance (singleton pattern).

Free-tier deployment uses in-memory state; for production replace
with a persistent store.
"""
import json
import os
import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """
    In-memory session state for the current server run.

    Tracks three categories of tables:
      - user-uploaded CSV/Excel files (added via /upload)
      - pre-loaded local sample files (e.g. sample_timeseries.csv)
      - virtual sample views backed by the Supabase database
        (added via /sample-data/db)
    """

    def __init__(self):
        self.tables: Dict[str, Dict[str, Any]] = {}
        self.generated_files: List[str] = []
        self.installed_packages: Set[str] = set()
        self.base_dir: str = settings.TEMP_DATA_DIR
        os.makedirs(self.base_dir, exist_ok=True)
        # Cached database summary text (refreshed lazily).
        self.db_summary: str = ""
        self.db_available: bool = False
        logger.info("SessionManager initialised. Temp dir: %s", self.base_dir)

    # ── Table registration ───────────────────────────────────────────

    def add_table(
        self,
        table_name: str,
        file_path: str,
        columns: dict,
        source: str = "upload",
    ) -> None:
        """Register a file's metadata. source: upload / sample / db."""
        self.tables[table_name] = {
            "path": file_path,
            "columns": columns,
            "source": source,
        }
        logger.info(
            "Table registered: %s (%s, source=%s)",
            table_name,
            file_path,
            source,
        )

    def remove_table(self, table_name: str) -> None:
        """Remove a table from session state."""
        self.tables.pop(table_name, None)
        logger.info("Table removed: %s", table_name)

    # ── Info generation for LLM context ──────────────────────────────

    def get_all_tables_info(self) -> str:
        """
        Build a human-readable summary of all registered tables.
        This string is injected into the LLM system prompt.
        """
        if not self.tables:
            return "No tables have been loaded yet."

        lines = ["Available tables in the current session:"]
        for name, meta in self.tables.items():
            cols = meta.get("columns", {})
            source = meta.get("source", "upload")
            col_summary = ", ".join(
                f"{col} ({info.get('business_meaning', 'Unknown')})"
                for col, info in cols.items()
            )
            tag = f" [source: {source}]" if source != "upload" else ""
            lines.append(f"- {name}{tag}: [{col_summary}]")
        return "\n".join(lines)

    # ── Raw table data for frontend manual plotting ──────────────────

    def get_table_data(self, table_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Return the full table as a list of row-dicts (JSON-safe).
        The DataFrame is loaded on demand and released immediately.

        Returns None for virtual tables that have no underlying file.
        """
        meta = self.tables.get(table_name)
        if not meta:
            logger.warning("Table '%s' not found in session.", table_name)
            return None

        # Virtual DB views have no file path on disk.
        if meta.get("source") == "db":
            return None

        file_path = meta.get("path")
        if not file_path or not os.path.isfile(file_path):
            logger.warning("File for table '%s' not found: %s", table_name, file_path)
            return None

        try:
            df = pd.read_csv(file_path, low_memory=True)
            data = df.to_dict(orient="records")
            del df
            return data
        except Exception as exc:
            logger.error("Failed to read table '%s': %s", table_name, exc)
            return None

    # ── Installed packages tracking ──────────────────────────────────

    def add_packages(self, packages: List[str]) -> None:
        """Record newly installed pip packages."""
        self.installed_packages.update(packages)

    def get_table_names(self) -> List[str]:
        """Return all registered table names (for frontend listing)."""
        return list(self.tables.keys())

    # ── Database summary caching ────────────────────────────────────

    def set_db_summary(self, summary: str, available: bool) -> None:
        """Cache the database summary so we do not query on every request."""
        self.db_summary = summary
        self.db_available = available

    def get_db_summary(self) -> str:
        return self.db_summary

    def is_db_available(self) -> bool:
        return self.db_available


# Singleton — shared across all routes
session_manager = SessionManager()
