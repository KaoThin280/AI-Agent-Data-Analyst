"""Chat router — the core structured workflow endpoint.

Flow:
  1. Receive user query → Build structured prompt (User query + System data)
  2. Send to AI → Parse structured response (Response to user / Request system / Code)
  3. If Request system = E2B_EXE → Execute code in E2B sandbox → Loop
  4. If Response to user != None → Return final answer
"""
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Depends, status

from app.core.security import get_api_key
from app.services.structured_workflow import run_structured_workflow
from app.services.session_service import session_manager
from app.utils.response_formatter import format_chat_response

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_api_key)])


@router.post(
    "/chat",
    summary="Send a natural-language query for AI-powered data analysis",
    response_description="AI reasoning, generated code, execution logs, and final insight",
)
async def handle_chat(
    query: str = Query(
        ...,
        min_length=1,
        max_length=5000,
        description="Your question or analysis request in natural language.",
    ),
    _: str = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Execute the structured AI-System communication loop:

    1. Build prompt with User query + System data context
    2. AI responds with structured output (Response to user / Request system / Code)
    3. If code needed → Execute in E2B sandbox → Feed result back to AI
    4. Loop until AI returns final response to user

    Returns:
        - `status`: "success" or "error"
        - `user_response`: Natural-language answer
        - `code_executed`: Python code that was run (if any)
        - `artifacts_created`: List of generated file names
        - `retries_used`: Number of retry attempts
        - `error_message`: Error details if failed
    """
    # Build current data context summary
    data_context_summary = session_manager.get_all_tables_info()
    files_in_session = [
        meta["path"]
        for meta in session_manager.tables.values()
        if meta.get("path")
    ]

    logger.info(
        "Chat request: query='%s...'  tables=%d  files=%d",
        query[:80],
        len(session_manager.tables),
        len(files_in_session),
    )

    try:
        result = run_structured_workflow(
            user_query=query,
            data_context_summary=data_context_summary,
            installed_packages=session_manager.installed_packages,
            files_in_session=files_in_session,
            max_retries=4,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Workflow engine unavailable: {exc}",
        )

    # Map structured workflow result keys to chat response format
    user_response = result.get("response_to_user", "")
    code_executed = result.get("code")
    artifacts_created = result.get("new_files", [])
    retries_used = result.get("retries_used", 0)

    return format_chat_response(
        user_response_text=user_response,
        code_executed=code_executed,
        artifacts_created=artifacts_created,
        retries_used=retries_used,
        error_message=None,
    )