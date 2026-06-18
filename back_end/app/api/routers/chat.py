"""Chat router - the core structured workflow endpoint.

Flow:
  1. Receive user query -> Build structured prompt (User query + System data)
  2. Send to AI -> Parse structured response
  3. If Request system = E2B_EXE -> Execute code in E2B sandbox -> Loop
  4. If Request system = QUERY_CSV -> Read bundled CSV sample -> Loop
  5. If Response to user != None -> Return final answer with workflow events
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

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
    response_description="AI reasoning, generated code, execution logs, final insight, workflow events",
)
async def handle_chat(
    query: str = Query(
        ...,
        min_length=1,
        max_length=5000,
        description="Your question or analysis request in natural language.",
    ),
    include_events: bool = Query(
        False,
        description="If true, the response includes a list of workflow events "
                    "(for the frontend status panel).",
    ),
    _: str = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Execute the structured AI-System communication loop.
    """
    data_context_summary = session_manager.get_all_tables_info()
    files_in_session = [
        meta["path"]
        for name, meta in session_manager.tables.items()
        if meta.get("path")
    ]

    logger.info(
        "Chat request: query='%s...'  tables=%d  files=%d",
        query[:80],
        len(session_manager.tables),
        len(files_in_session),
    )

    try:
        result = await run_structured_workflow(
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
    except Exception as exc:
        logger.exception("Unexpected workflow failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow failed: {exc}",
        )

    user_response = result.get("response_to_user", "")
    code_executed = result.get("code")
    artifacts_created = result.get("new_files", [])
    retries_used = result.get("retries_used", 0)
    events = result.get("events", []) if include_events else []

    payload = format_chat_response(
        user_response_text=user_response,
        code_executed=code_executed,
        artifacts_created=artifacts_created,
        retries_used=retries_used,
        error_message=None,
    )
    if include_events:
        payload["workflow_events"] = events
    return payload
