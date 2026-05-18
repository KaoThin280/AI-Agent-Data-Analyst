"""
Download router — securely serves files generated during analysis.

Endpoints:
  GET /files              → List all available files in temp_data/
  GET /files/{filename}   → Download or view a specific file

Security:
  - Path traversal protection (rejects '..' and absolute paths)
  - Only serves files inside TEMP_DATA_DIR
  - Requires X-API-Key authentication
  - Correct MIME types for HTML (charts), CSV (data), PNG (images)
"""
import os
import mimetypes
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Depends, Path, status
from fastapi.responses import FileResponse, HTMLResponse, Response, JSONResponse
from app.services.session_service import session_manager
from app.core.config import settings
from app.core.security import get_api_key

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_api_key)])

# ── Allowed serving types ────────────────────────────────────────────
SERVER_DIR = os.path.abspath(settings.TEMP_DATA_DIR)


@router.get(
    "/files",
    summary="List all available files in the output directory",
    response_description="List of filenames with metadata",
)
async def list_files(
    _: str = Depends(get_api_key),
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Return a list of all files currently stored in the temp_data directory.

    Useful for the frontend to discover generated charts (HTML),
    new CSV files, or uploaded data.

    Each entry includes:
    - `name`: filename
    - `size_bytes`: file size in bytes
    - `modified`: last modified timestamp (ISO format)
    - `type`: MIME type guess
    """
    if not os.path.isdir(SERVER_DIR):
        return {"files": []}

    files = []
    for fname in os.listdir(SERVER_DIR):
        fpath = os.path.join(SERVER_DIR, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            mime_type, _ = mimetypes.guess_type(fname)
            files.append({
                "name": fname,
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
                "type": mime_type or "application/octet-stream",
            })

    return {"files": sorted(files, key=lambda x: x["name"])}


@router.get(
    "/files/{filename:path}",
    summary="Download or view a generated file (chart, CSV, PNG)",
    response_description="The file content with appropriate Content-Type",
)
async def download_file(
    filename: str = Path(
        ...,
        description="Relative path to the file inside temp_data/ "
                    "(e.g. 'chart.html', 'analysis_result.csv').",
    ),
    _: str = Depends(get_api_key),
):
    """
    Serve a file from the temp_data directory.

    **Security:**
    - Only allows files inside `temp_data/`
    - Rejects any path containing `..` or starting with `/` (absolute path)
    - Returns 404 if file does not exist

    **Content-Type handling:**
    - `.html` → `text/html` (renders in browser — interactive Plotly charts)
    - `.csv`  → `text/csv` (opens in spreadsheet or downloads)
    - `.png`  → `image/png`
    - other   → `application/octet-stream` (forces download)
    """
    # ── 1. Path traversal prevention ─────────────────────────────────
    # Reject absolute paths and any path with '..'
    if filename.startswith("/") or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path. Path traversal is not allowed.",
        )

    # ── 2. Resolve full path and validate it's inside SERVER_DIR ─────
    full_path = os.path.normpath(os.path.join(SERVER_DIR, filename))
    if not full_path.startswith(SERVER_DIR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access denied. File must be inside the data directory.",
        )

    # ── 3. Check file exists ─────────────────────────────────────────
    if not os.path.isfile(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found. "
                   f"Use GET /files to see available files.",
        )

    # ── 4. Determine content type ────────────────────────────────────
    mime_type, _ = mimetypes.guess_type(full_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    # ── 5. For HTML files, serve inline so browsers render the chart ─
    if mime_type == "text/html":
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content, status_code=200)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read HTML file: {exc}",
            )

    # ── 6. For other files, use FileResponse (supports streaming) ────
    return FileResponse(
        path=full_path,
        filename=filename,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
            if mime_type in ("image/png", "image/jpeg", "application/pdf")
            else f'attachment; filename="{filename}"'
        },
    )

@router.get(
    "/tables/{filename:path}",
    summary="Get table data as JSON (columns metadata + rows)",
    response_description="JSON with columns info, row data, and row count",
)
async def get_table_data_json(
    filename: str = Path(
        ...,
        description="Filename of the table (e.g. 'sample_timeseries.csv')",
    ),
    _: str = Depends(get_api_key),
):
    """
    Return table data in JSON format that the frontend DataExplorer expects.

    Structure:
    ```json
    {
      "columns": { "column_name": { "dtype": "...", "business_meaning": "..." }, ... },
      "data": [ { "col1": val1, "col2": val2 }, ... ],
      "num_rows": 123
    }
    ```

    Uses session_manager to get column metadata + row data.
    """
    # Path traversal prevention
    if filename.startswith("/") or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path. Path traversal is not allowed.",
        )

    # Check if table exists in session
    if filename not in session_manager.tables:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{filename}' not found in session.",
        )

    # Get column metadata from session
    meta = session_manager.tables[filename]
    columns = meta.get("columns", {})

    # Get row data
    from app.services.session_service import session_manager

    row_data = session_manager.get_table_data(filename)
    if row_data is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read data for table '{filename}'.",
        )

    return JSONResponse(content={
        "columns": columns,
        "data": row_data,
        "num_rows": len(row_data),
        "file_name": filename,
    })