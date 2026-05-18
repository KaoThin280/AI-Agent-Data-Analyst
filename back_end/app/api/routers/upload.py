"""Upload router — handles file ingestion, DataContext extraction,
and initial LLM analysis in one atomic operation using the structured
AI-System communication protocol.

Flow:
  Receive file -> save to disk -> extract DataContext -> register in session
  -> send structured prompt to AI -> parse AI response -> return to frontend.
"""
import os
import gc
import logging
from typing import Any, Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status

from app.core.config import settings
from app.core.security import get_api_key
from app.services.data_service import DataProcessor, DataContext
from app.services.structured_workflow import run_structured_workflow
from app.services.session_service import session_manager

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

router = APIRouter(dependencies=[Depends(get_api_key)])


@router.post(
    "/upload",
    summary="Upload a CSV or Excel file for AI analysis",
    response_description="Initial AI overview of the uploaded data",
    status_code=status.HTTP_201_CREATED,
)
async def handle_upload(
    file: UploadFile = File(
        ...,
        description="Tabular data file (.csv, .xls, .xlsx). Max size: 100 MB.",
    ),
    _: str = Depends(get_api_key),
) -> Dict[str, Any]:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file extension '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    safe_filename = os.path.basename(file.filename or "")
    if not safe_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    os.makedirs(settings.TEMP_DATA_DIR, exist_ok=True)
    file_path = os.path.join(settings.TEMP_DATA_DIR, safe_filename)

    try:
        contents = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read uploaded file: {exc}",
        )
    finally:
        await file.close()

    if len(contents) > MAX_FILE_SIZE_BYTES:
        size_mb = len(contents) / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size ({size_mb:.1f} MB) exceeds the "
                f"maximum allowed size of {MAX_FILE_SIZE_MB} MB."
            ),
        )

    try:
        with open(file_path, "wb") as f:
            f.write(contents)
        logger.info("File saved: %s (%d bytes)", file_path, len(contents))
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write file to disk: {exc}",
        )

    try:
        data_context: DataContext = DataProcessor.extract_data_context(file_path)
    except ValueError as exc:
        gc.collect()
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except PermissionError:
                logger.warning("Could not remove file (still in use): %s", file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    session_manager.add_table(
        table_name=safe_filename,
        file_path=file_path,
        columns=data_context.columns,
    )

    try:
        # Use structured workflow with default upload query
        data_context_summary = data_context.to_summary()
        workflow_result = run_structured_workflow(
            user_query="Please briefly describe this data",
            data_context_summary=data_context_summary,
            installed_packages=session_manager.installed_packages,
            files_in_session=[file_path],
            max_retries=3,
        )
        ai_analysis = workflow_result.get("response_to_user", "")
    except RuntimeError as exc:
        logger.error("LLM unavailable for analysis: %s", exc)
        ai_analysis = (
            "File uploaded successfully. AI analysis is currently "
            "unavailable due to a configuration issue. "
            "The data has been registered for chat queries."
        )

    return {
        "status": "success",
        "file_name": safe_filename,
        "num_rows": data_context.num_rows,
        "num_columns": data_context.num_columns,
        "ai_analysis": ai_analysis,
        "data_context": data_context.to_dict(),
    }