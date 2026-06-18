"""
Database query service — read-only access to the Supabase Steam schema.

The LLM uses this module via the workflow tool `query_database(...)`.
It is intentionally restricted to safe, read-only operations on a small
allow-list of tables (games, users, reviews) so the model can describe
and query sample data without being able to mutate the database.

Why a custom service instead of letting the model run raw SQL?
  - The free-tier Render instance has limited RAM; we cap the row count
    and reject obvious mutation statements.
  - It produces a compact text/JSON summary that fits inside the
    LLM context window for follow-up reasoning.
  - It is safe by default even if the model misbehaves.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.db.sessions import AsyncSessionLocal
from app.models import Game, Review, SteamUser

logger = logging.getLogger(__name__)

# ── Safety knobs ─────────────────────────────────────────────────────
MAX_ROWS_RETURNED = 50
# Only these tables may be queried through the LLM tool.
ALLOWED_TABLES = frozenset({"games", "users", "reviews"})
# Only these columns may be selected. The model is given a fixed
# allow-list (rather than SELECT *) so it cannot pull very long text
# blobs into the context window unnecessarily.
ALLOWED_COLUMNS = {
    "games": [
        "steam_appid", "name", "is_free", "supported_languages",
        "required_age", "release_date", "publishers", "developers",
        "categories", "genres", "price_text",
    ],
    "users": [
        "steamid", "personaname", "num_games_owned",
    ],
    "reviews": [
        "recommendationid", "steam_appid", "steamid", "language",
        "review_text", "timestamp_created", "timestamp_updated",
        "refunded", "received_for_free", "written_during_early_access",
        "primarily_steam_deck", "playtime_at_review",
        "playtime_last_two_weeks", "playtime_forever",
    ],
}
# Aggregations the model may request explicitly.
ALLOWED_AGGREGATES = frozenset({"count", "avg", "min", "max", "sum"})
# Sortable columns (string-typed, to avoid weird behaviour on dates).
SORTABLE_COLUMNS = {
    "games": ["name", "release_date", "required_age"],
    "users": ["personaname", "num_games_owned"],
    "reviews": [
        "timestamp_created", "playtime_at_review",
        "playtime_last_two_weeks", "playtime_forever",
    ],
}


# ── Helpers ──────────────────────────────────────────────────────────

def _serialise(value: Any) -> Any:
    """Convert SQLAlchemy / Python values into JSON-safe primitives."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _rows_to_text(rows: Sequence[Dict[str, Any]], columns: Sequence[str]) -> str:
    """Format a small list of rows as a compact, human-readable table."""
    if not rows:
        return "(no rows)"
    header = " | ".join(columns)
    sep = "-+-".join("-" * len(c) for c in columns)
    body_lines = []
    for r in rows:
        body_lines.append(" | ".join(str(r.get(c, ""))[:80] for c in columns))
    return "\n".join([header, sep, *body_lines])


def _validate_identifier(name: str, allow_list: Sequence[str]) -> Optional[str]:
    """Return the identifier if it is in the allow-list, else None."""
    if not name:
        return None
    if name in allow_list:
        return name
    return None


def _apply_filter(stmt, model, column: str, op: str, value: Any):
    """
    Apply a simple WHERE clause: column op value.
    Supported ops: =, !=, <, <=, >, >=, like, ilike.
    Unknown ops raise ValueError.
    """
    col_attr = getattr(model, column, None)
    if col_attr is None:
        raise ValueError(f"Unknown column '{column}' for this table")
    op_normalised = op.lower()
    if op_normalised == "=":
        return stmt.where(col_attr == value)
    if op_normalised == "!=":
        return stmt.where(col_attr != value)
    if op_normalised == "<":
        return stmt.where(col_attr < value)
    if op_normalised == "<=":
        return stmt.where(col_attr <= value)
    if op_normalised == ">":
        return stmt.where(col_attr > value)
    if op_normalised == ">=":
        return stmt.where(col_attr >= value)
    if op_normalised in ("like", "ilike"):
        return stmt.where(col_attr.ilike(value) if op_normalised == "ilike" else col_attr.like(value))
    raise ValueError(f"Unsupported operator '{op}'")


# ── Tool: query_database ─────────────────────────────────────────────

async def query_database(
    table: str,
    columns: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    order_by: Optional[str] = None,
    order_dir: str = "asc",
    limit: int = 20,
    aggregate: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Read-only query against the Supabase Steam schema.

    Parameters
    ----------
    table : str
        One of: games, users, reviews.
    columns : list[str] | None
        Subset of columns to return. Defaults to all allowed columns.
    filters : list[dict] | None
        Each dict has keys: column, op, value. Multiple filters are
        combined with AND.
    order_by : str | None
        Column name to sort by (must be in the sortable allow-list).
    order_dir : str
        'asc' or 'desc'.
    limit : int
        Max rows to return. Hard-capped at MAX_ROWS_RETURNED.
    aggregate : dict | None
        Optional aggregation, e.g. {"func": "count", "column": "steam_appid"}.

    Returns
    -------
    dict with keys:
        success (bool), table, columns, row_count, rows (list of dicts),
        text (compact string summary), error (str | None).
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
                f"Allowed tables: {', '.join(sorted(ALLOWED_TABLES))}."
            ),
        }

    model = {
        "games": Game,
        "users": SteamUser,
        "reviews": Review,
    }[table_normalised]

    allowed_cols = ALLOWED_COLUMNS[table_normalised]
    if columns:
        safe_cols = []
        for c in columns:
            v = _validate_identifier(c, allowed_cols)
            if v:
                safe_cols.append(v)
        if not safe_cols:
            return {
                "success": False,
                "table": table_normalised,
                "columns": [],
                "row_count": 0,
                "rows": [],
                "text": "",
                "error": "None of the requested columns are allowed.",
            }
        select_cols = safe_cols
    else:
        select_cols = list(allowed_cols)

    try:
        safe_limit = max(1, min(int(limit or 20), MAX_ROWS_RETURNED))

        async with AsyncSessionLocal() as session:  # type: AsyncSession
            if aggregate:
                agg_func = (aggregate.get("func") or "").lower()
                agg_column = aggregate.get("column") or "*"
                if agg_func not in ALLOWED_AGGREGATES:
                    raise ValueError(f"Unsupported aggregate '{agg_func}'")
                if agg_func == "count":
                    sql_func = func.count(
                        getattr(model, agg_column, None)
                        if agg_column != "*" else None
                    ) if agg_column != "*" else func.count()
                    stmt = select(sql_func)
                else:
                    col_attr = getattr(model, agg_column, None)
                    if col_attr is None:
                        raise ValueError(
                            f"Unknown column '{agg_column}' for aggregate"
                        )
                    sql_func = {
                        "avg": func.avg,
                        "min": func.min,
                        "max": func.max,
                        "sum": func.sum,
                    }[agg_func](col_attr)
                    stmt = select(sql_func)

                if filters:
                    for f in filters:
                        stmt = _apply_filter(
                            stmt, model, f["column"], f["op"], f["value"]
                        )

                result = await session.execute(stmt)
                scalar = result.scalar()
                agg_value = _serialise(scalar)
                text = f"{agg_func.upper()}({agg_column}) = {agg_value}"
                return {
                    "success": True,
                    "table": table_normalised,
                    "columns": [f"{agg_func}({agg_column})"],
                    "row_count": 1,
                    "rows": [{f"{agg_func}({agg_column})": agg_value}],
                    "text": text,
                    "error": None,
                }

            cols_attr = [getattr(model, c) for c in select_cols]
            stmt = select(*cols_attr)

            if filters:
                for f in filters:
                    stmt = _apply_filter(
                        stmt, model, f["column"], f["op"], f["value"]
                    )

            if order_by:
                sort_col = _validate_identifier(
                    order_by, SORTABLE_COLUMNS[table_normalised]
                )
                if sort_col:
                    sort_attr = getattr(model, sort_col)
                    stmt = stmt.order_by(
                        desc(sort_attr) if order_dir.lower() == "desc" else asc(sort_attr)
                    )

            stmt = stmt.limit(safe_limit)

            result = await session.execute(stmt)
            db_rows = result.all()

            rows: List[Dict[str, Any]] = []
            for row in db_rows:
                row_dict = {}
                for col_name, value in zip(select_cols, row):
                    row_dict[col_name] = _serialise(value)
                rows.append(row_dict)

            text = _rows_to_text(rows, select_cols)

            return {
                "success": True,
                "table": table_normalised,
                "columns": select_cols,
                "row_count": len(rows),
                "rows": rows,
                "text": text,
                "error": None,
            }

    except Exception as exc:
        logger.exception("query_database failed for table=%s", table_normalised)
        return {
            "success": False,
            "table": table_normalised,
            "columns": [],
            "row_count": 0,
            "rows": [],
            "text": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


# ── Tool: describe_database ──────────────────────────────────────────

def describe_database() -> Dict[str, Any]:
    """
    Return a structured description of the database schema. The LLM
    uses this to understand which tables and columns it can query.
    """
    schema = {
        "games": {
            "description": (
                "One row per Steam game. Contains metadata such as name, "
                "release date, price, supported languages, and flattened "
                "comma-separated lists of publishers, developers, "
                "categories, and genres."
            ),
            "columns": [
                {"name": "steam_appid", "type": "INTEGER", "key": "primary"},
                {"name": "name", "type": "TEXT", "key": None},
                {"name": "is_free", "type": "BOOLEAN", "key": None},
                {"name": "supported_languages", "type": "TEXT", "key": None},
                {"name": "required_age", "type": "INTEGER", "key": None},
                {"name": "release_date", "type": "DATE", "key": None},
                {"name": "publishers", "type": "TEXT", "key": None},
                {"name": "developers", "type": "TEXT", "key": None},
                {"name": "categories", "type": "TEXT", "key": None},
                {"name": "genres", "type": "TEXT", "key": None},
                {"name": "price_text", "type": "TEXT", "key": None},
            ],
            "row_count_estimate": None,
        },
        "users": {
            "description": (
                "Steam user profiles extracted from reviews. personaname "
                "is the display name."
            ),
            "columns": [
                {"name": "steamid", "type": "BIGINT", "key": "primary"},
                {"name": "personaname", "type": "TEXT", "key": None},
                {"name": "num_games_owned", "type": "INTEGER", "key": None},
            ],
            "row_count_estimate": None,
        },
        "reviews": {
            "description": (
                "User reviews of games, including language, optional review "
                "text, timestamps, refund / free-copy flags, and playtime "
                "statistics."
            ),
            "columns": [
                {"name": "recommendationid", "type": "BIGINT", "key": "primary"},
                {"name": "steam_appid", "type": "INTEGER",
                 "key": "FK -> games.steam_appid"},
                {"name": "steamid", "type": "BIGINT",
                 "key": "FK -> users.steamid"},
                {"name": "language", "type": "TEXT", "key": None},
                {"name": "review_text", "type": "TEXT", "key": None},
                {"name": "timestamp_created", "type": "TIMESTAMPTZ", "key": None},
                {"name": "timestamp_updated", "type": "TIMESTAMPTZ", "key": None},
                {"name": "refunded", "type": "BOOLEAN", "key": None},
                {"name": "received_for_free", "type": "BOOLEAN", "key": None},
                {"name": "written_during_early_access", "type": "BOOLEAN",
                 "key": None},
                {"name": "primarily_steam_deck", "type": "BOOLEAN",
                 "key": None},
                {"name": "playtime_at_review", "type": "INTEGER", "key": None},
                {"name": "playtime_last_two_weeks", "type": "INTEGER",
                 "key": None},
                {"name": "playtime_forever", "type": "INTEGER", "key": None},
            ],
            "row_count_estimate": None,
        },
    }
    return schema


# ── Tool: get_database_summary ───────────────────────────────────────

async def get_database_summary() -> str:
    """
    Build a human-readable summary of the database contents (row counts
    and a small sample per table). Used by the workflow on startup so
    the LLM has a sense of how much data is available.
    """
    lines: List[str] = []
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        for model, label in ((Game, "games"), (SteamUser, "users"), (Review, "reviews")):
            try:
                count = (await session.execute(select(func.count()).select_from(model))).scalar() or 0
            except Exception:
                count = -1
            lines.append(f"- {label}: {count} row(s)")

        try:
            sample = (await session.execute(
                select(Game.name, Game.release_date, Game.genres, Game.price_text)
                .order_by(Game.release_date.desc().nullslast())
                .limit(5)
            )).all()
            if sample:
                lines.append("")
                lines.append("Recent games sample:")
                for name, rdate, genres, price in sample:
                    lines.append(
                        f"  - {name} | released {rdate or 'unknown'} | "
                        f"genres: {genres or 'n/a'} | price: {price or 'n/a'}"
                    )
        except Exception:
            pass

    return "\n".join(lines)


# ── Tool: get_database_overview (for /api/intro) ─────────────────────

async def get_database_overview() -> Dict[str, Any]:
    """
    Return a compact overview of the database (row counts only) for
    the frontend intro/status endpoints. Always returns a dict, even
    if the database is unreachable, so the frontend can still render
    a meaningful greeting.
    """
    counts = {"games": 0, "users": 0, "reviews": 0}
    available = False
    error: Optional[str] = None
    try:
        async with AsyncSessionLocal() as session:  # type: AsyncSession
            for model, key in ((Game, "games"), (SteamUser, "users"), (Review, "reviews")):
                try:
                    cnt = (await session.execute(
                        select(func.count()).select_from(model)
                    )).scalar() or 0
                    counts[key] = int(cnt)
                except Exception as inner_exc:
                    logger.warning("count failed for %s: %s", key, inner_exc)
            available = True
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.warning("Database not reachable for overview: %s", exc)

    return {
        "available": available,
        "counts": counts,
        "error": error,
    }
