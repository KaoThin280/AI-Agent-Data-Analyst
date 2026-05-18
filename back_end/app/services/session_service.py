"""
Session manager — tracks uploaded tables, generated files, and installed packages
throughout the lifecycle of a single server instance (singleton pattern).
"""
import os
import logging
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """
    In-memory session state for the current server run.

    Because this is a free-tier single-user app, we use a simple singleton
    rather than a full database.  For production, replace with Redis / SQL.
    """

    def __init__(self):
        self.tables: Dict[str, Dict[str, Any]] = {}
        self.generated_files: List[str] = []
        self.installed_packages: Set[str] = set()
        self.base_dir: str = settings.TEMP_DATA_DIR
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info("SessionManager initialised. Temp dir: %s", self.base_dir)

    # ── Table registration ───────────────────────────────────────────

    def add_table(self, table_name: str, file_path: str, columns: dict) -> None:
        """Register an uploaded file's metadata."""
        self.tables[table_name] = {
            "path": file_path,
            "columns": columns,
        }
        logger.info("Table registered: %s (%s)", table_name, file_path)

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
            return "No tables have been uploaded yet."

        lines = ["Available tables in the current session:"]
        for name, meta in self.tables.items():
            cols = meta.get("columns", {})
            col_summary = ", ".join(
                f"{col} ({info.get('business_meaning', 'Unknown')})"
                for col, info in cols.items()
            )
            lines.append(f"- {name}: [{col_summary}]")
        return "\n".join(lines)

    # ── Raw table data for frontend manual plotting ──────────────────

    def get_table_data(self, table_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Return the full table as a list of row-dicts (JSON-safe).
        The DataFrame is loaded on demand and released immediately.

        Args:
            table_name: The filename (or alias) under which the table is registered.

        Returns:
            A list of dicts (one per row), or None if the table/file does not exist.
        """
        meta = self.tables.get(table_name)
        if not meta:
            logger.warning("Table '%s' not found in session.", table_name)
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


# Singleton — shared across all routes
session_manager = SessionManager()