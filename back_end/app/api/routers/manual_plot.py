"""
Manual Plot router — serves raw tabular data to the frontend so it can
render charts client-side using its own charting library.

This is an alternative to the AI-generated charts.  The frontend calls
GET /tables/{session_id} to fetch the full JSON data for a specific
uploaded table and plots it however the user wants.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Depends, status

from app.core.security import get_api_key
from app.services.session_service import session_manager

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_api_key)])


@router.get(
    "/tables/{session_id}",
    summary="Get raw tabular data for manual charting",
    response_description="Full table contents as a JSON array of row-objects",
)
async def get_table_data(
    session_id: str = Path(
        ...,
        min_length=1,
        description="The filename or alias of the uploaded table "
                    "(e.g. 'sales_data.csv').",
    ),
) -> Dict[str, Any]:
    """
    Return the **complete** contents of a previously uploaded table as
    a JSON-serialisable list of row dicts.

    The frontend can then use this data to plot charts with its own
    library (e.g. Chart.js, Recharts, D3.js) without needing the AI
    to generate visualisation code.

    **Security:** This endpoint does **not** accept arbitrary file paths.
    `session_id` must match a table that was previously registered via
    `POST /upload`.

    **Memory:** The CSV is loaded into memory only for the duration of
    this request; the DataFrame is deleted before the response is sent.
    """
    # 1. Look up the table in the session
    table_names = session_manager.get_table_names()
    logger.debug("Requested table '%s'. Available: %s", session_id, table_names)

    if session_id not in table_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{session_id}' not found. "
                   f"Available tables: {', '.join(table_names) if table_names else '(none)'}",
        )

    # 2. Load data on demand (memory-efficient — release after read)
    rows = session_manager.get_table_data(session_id)
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{session_id}' exists in session but its "
                   f"underlying file could not be read.",
        )

    # 3. Return column types alongside the data for frontend convenience
    meta = session_manager.tables.get(session_id, {})
    columns = meta.get("columns", {})

    return {
        "table_name": session_id,
        "num_rows": len(rows),
        "columns": columns,
        "data": rows,
    }