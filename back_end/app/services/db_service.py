"""
CSV query service - read-only access to the bundled CSV samples.

The LLM uses this module via the workflow tool. The "database" is now
just the CSV files in back_end/temp_data/, so queries are implemented
as pandas read_csv + filter + sort + head.

This is intentionally restricted to safe, read-only operations on a
small allow-list of tables (metadata, reviews, sample_timeseries) so
the model can describe and query sample data without being able to
mutate the files.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Allow-list of tables the LLM tool can query. The keys are the on-disk
# CSV filenames in back_end/temp_data/. The "kind" field is for human
# reference only and is not used for matching.
# ----------------------------------------------------------------------
ALLOWED_TABLES: Dict[str, Dict[str, Any]] = {
    "metadata": {
        "file": "metadata.csv",
        "description": "Steam game metadata (name, release date, price, ...).",
    },
    "reviews": {
        "file": "reviews.csv",
        "description": "User reviews with timestamps and playtime stats.",
    },
    "sample_timeseries": {
        "file": "sample_timeseries.csv",
        "description": "Daily revenue series for 2024-2025.",
    },
}

# Hard cap on rows returned to the LLM.
MAX_ROWS_RETURNED = 50

# Sortable columns per table (whitelist to keep queries predictable).
SORTABLE_COLUMNS: Dict[str, List[str]] = {
    "metadata": [
        "name", "release_date", "required_age", "price_text", "steam_appid",
    ],
    "reviews": [
        "timestamp_created", "playtime_at_review",
        "playtime_last_two_weeks", "playtime_forever",
    ],
    "sample_timeseries": ["date", "revenue"],
}

# Allowed filter operators.
_OPS = {"=", "!=", "<", "<=", ">", ">="}


def _table_path(table: str) -> Optional[str]:
    """Resolve a logical table name to an on-disk CSV path."""
    info = ALLOWED_TABLES.get(table)
    if not info:
        return None
    return os.path.join(settings.TEMP_DATA_DIR, info["file"])


def _validate_columns(table: str, requested: Optional[List[str]]) -> Optional[List[str]]:
    """Return the column list to read, or None if the request is invalid."""
    if not requested:
        return None
    path = _table_path(table)
    if not path or not os.path.isfile(path):
        return None
    try:
        df = pd.read_csv(path, nrows=0)
    except Exception:
        return None
    valid = set(df.columns)
    safe = [c for c in requested if c in valid]
    return safe or None


def _format_rows(df: pd.DataFrame) -> str:
    """Format a small DataFrame as a compact text table."""
    if df.empty:
        return "(no rows)"
    cols = list(df.columns)
    header = " | ".join(cols)
    sep = "-+-".join("-" * len(c) for c in cols)
    body = "\n".join(
        " | ".join(
            "" if pd.isna(v) else str(v)[:80] for v in row
        )
        for row in df.itertuples(index=False, name=None)
    )
    return "\n".join([header, sep, body])


def query_table(
    table: str,
    columns: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    order_by: Optional[str] = None,
    order_dir: str = "asc",
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Read-only query against one of the bundled CSV samples.

    Parameters
    ----------
    table : str
        One of: metadata, reviews, sample_timeseries.
    columns : list[str] | None
        Subset of columns to return. None = all columns.
    filters : list[dict] | None
        Each dict has keys: column, op, value. Multiple filters are
        combined with AND.
    order_by : str | None
        Column name to sort by (must be in SORTABLE_COLUMNS).
    order_dir : str
        'asc' or 'desc'.
    limit : int
        Max rows to return (1..MAX_ROWS_RETURNED).

    Returns
    -------
    dict with keys: success, table, columns, row_count, rows, text, error.
    """
    table_normalised = (table or "").strip().lower()
    if table_normalised not in ALLOWED_TABLES:
        return {
            "success": False,
            "table": table_normalised,
            "columns": [],
            "row_count": 0,
            "rows": [],
            "text": "",
            "error": (
                f"Table '{table}' is not accessible. "
                f"Allowed tables: {', '.join(sorted(ALLOWED_TABLES.keys()))}."
            ),
        }

    path = _table_path(table_normalised)
    if not path or not os.path.isfile(path):
        return {
            "success": False,
            "table": table_normalised,
            "columns": [],
            "row_count": 0,
            "rows": [],
            "text": "",
            "error": f"Data file for table '{table}' is missing on disk.",
        }

    safe_limit = max(1, min(int(limit or 20), MAX_ROWS_RETURNED))
    select_cols = _validate_columns(table_normalised, columns)

    try:
        df = pd.read_csv(path)

        # Apply filters with safe operator whitelist.
        if filters:
            for f in filters:
                col = f.get("column")
                op = (f.get("op") or "").strip()
                val = f.get("value")
                if col not in df.columns or op not in _OPS:
                    continue
                if op == "=":
                    df = df[df[col] == val]
                elif op == "!=":
                    df = df[df[col] != val]
                elif op == "<":
                    df = df[df[col] < val]
                elif op == "<=":
                    df = df[df[col] <= val]
                elif op == ">":
                    df = df[df[col] > val]
                elif op == ">=":
                    df = df[df[col] >= val]

        # Select columns last so filter eval still works on full df.
        if select_cols:
            df = df[select_cols]

        # Sort by an allow-listed column.
        if order_by and order_by in SORTABLE_COLUMNS.get(table_normalised, []):
            df = df.sort_values(by=order_by, ascending=(order_dir.lower() != "desc"))

        df = df.head(safe_limit)

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            rows.append({
                col: (None if pd.isna(v) else v) for col, v in row.items()
            })

        out_cols = list(df.columns)
        return {
            "success": True,
            "table": table_normalised,
            "columns": out_cols,
            "row_count": len(rows),
            "rows": rows,
            "text": _format_rows(df),
            "error": None,
        }

    except Exception as exc:
        logger.exception("query_table failed for table=%s", table_normalised)
        return {
            "success": False,
            "table": table_normalised,
            "columns": [],
            "row_count": 0,
            "rows": [],
            "text": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def describe_tables() -> Dict[str, Any]:
    """Return a static description of every accessible table."""
    result: Dict[str, Any] = {}
    for table, info in ALLOWED_TABLES.items():
        path = _table_path(table)
        columns: List[str] = []
        if path and os.path.isfile(path):
            try:
                df = pd.read_csv(path, nrows=0)
                columns = list(df.columns)
            except Exception:
                pass
        result[table] = {
            "description": info["description"],
            "file": info["file"],
            "columns": columns,
        }
    return result
