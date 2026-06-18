"""Structured workflow (CSV-only mode)."""
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from app.core.config import settings
from app.services.data_service import DataProcessor
from app.services.db_service import query_table, describe_tables
from app.services.llm_service import LLMService
from app.services.session_service import session_manager

logger = logging.getLogger(__name__)

WorkflowEventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


def build_workflow_emitter(callbacks=None):
    subs = list(callbacks or [])

    async def emit(event):
        for cb in subs:
            try:
                await cb(event)
            except Exception as exc:
                logger.debug("workflow event subscriber error: %s", exc)

    return emit


SYSTEM_PROMPT_TEMPLATE = (
    "# ROLE\n"
    "You are a Data Analysis AI. Communicate with the system in this exact format:\n"
    "\n"
    "Response to user: None | <text>\n"
    "Request system:   None | E2B_EXE | QUERY_CSV\n"
    "Code:             None | <python> | <json query>\n"
    "\n"
    "Set Response to user to a non-empty string only when you are ready to answer.\n"
    "Set Request system to E2B_EXE to run Python in the sandbox, or QUERY_CSV to read a bundled CSV.\n"
    "\n"
    "TOOLS\n"
    "- get_data_context() / get_data_context(tableName) / get_data_context('tables')\n"
    "- query_table({table, columns?, filters?, order_by?, order_dir?, limit?})\n"
    "  Allowed tables: 'metadata', 'reviews', 'sample_timeseries'.\n"
    "  filters: [{column, op, value}] with op in '=', '!=', '<', '<=', '>', '>='.\n"
    "  limit 1..50, default 20.\n"
    "\n"
    "FILE RULES (sandbox)\n"
    "- Read CSVs from root: pd.read_csv('metadata.csv' | 'reviews.csv' | 'sample_timeseries.csv').\n"
    "- Save outputs to temp_data/ so the backend can serve them.\n"
    "\n"
    "BEST PRACTICES\n"
    "- For monthly aggregation across years, ALWAYS group by Year-Month, never by month name alone.\n"
    "- Array fields in metadata.csv (publishers, developers, genres, categories, supported_languages) are comma-separated; use string contains / split if you need to filter them.\n"
    "\n"
    "AVAILABLE DATA\n"
    "<<DATA_CONTEXT>>\n"
)


USER_QUERY_DEFAULT_UPLOAD = "Please briefly describe this data"


def build_prompt(user_query, system_data):
    q = f"User query: {user_query}" if user_query else "User query: None"
    s = f"System: {system_data}" if system_data else "System: None"
    return f"{q}\n{s}"


def build_initial_prompt_for_upload(data_context_summary):
    return build_prompt(USER_QUERY_DEFAULT_UPLOAD, data_context_summary)


def build_tool_result_prompt(tool_result, retries=0):
    return build_prompt(None, f"{tool_result} + Retries numbers: {retries}")


def parse_ai_response(response):
    result = {"response_to_user": None, "request_system": None, "code": None}
    lines = (response or "").strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Response to user:"):
            collected = []
            first = line[len("Response to user:"):].strip()
            if first.lower() != "none":
                collected.append(first)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(("Response to user:", "Request system:", "Code:")):
                collected.append(lines[i])
                i += 1
            text = "\n".join(collected).strip()
            if text and text.lower() != "none":
                result["response_to_user"] = text
            continue
        if line.startswith("Request system:"):
            collected = []
            first = line[len("Request system:"):].strip()
            if first.lower() != "none":
                collected.append(first)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(("Response to user:", "Request system:", "Code:")):
                collected.append(lines[i])
                i += 1
            text = "\n".join(collected).strip()
            if text and text.lower() != "none":
                result["request_system"] = text
            continue
        if line.startswith("Code:"):
            collected = []
            first = line[len("Code:"):].strip()
            if first.lower() != "none":
                collected.append(first)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(("Response to user:", "Request system:", "Code:")):
                collected.append(lines[i])
                i += 1
            text = "\n".join(collected).strip()
            if text:
                result["code"] = text
            continue
        i += 1
    return result


def get_data_context(table_or_list=None):
    if table_or_list is None:
        return session_manager.get_all_tables_info()
    if table_or_list.lower() in ("list", "listname", "list_name", "tables"):
        names = session_manager.get_table_names()
        if not names:
            return "No tables available."
        return "Available tables: " + ", ".join(names)
    if table_or_list in session_manager.tables:
        meta = session_manager.tables[table_or_list]
        cols = meta.get("columns", {})
        source = meta.get("source", "upload")
        lines = [f"Table: {table_or_list} (source: {source})"]
        for col, info in cols.items():
            lines.append(
                f"  - {col} ({info.get('dtype', 'unknown')}, "
                f"{info.get('business_meaning', 'Unknown')})"
            )
        return "\n".join(lines)
    names = session_manager.get_table_names()
    if not names:
        return "No tables available."
    return "Available tables: " + ", ".join(names)


async def handle_query_csv(payload_text):
    payload = {}
    raw = (payload_text or "").strip()
    if raw:
        fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        candidate = fence.group(1).strip() if fence else raw
        try:
            payload = json.loads(candidate)
        except Exception as exc:
            return {"success": False, "text": "", "columns": [], "rows": [], "error": f"Could not parse QUERY_CSV payload: {exc}"}
    if not isinstance(payload, dict) or "table" not in payload:
        return {"success": False, "text": "", "columns": [], "rows": [], "error": "QUERY_CSV payload must be a JSON object with a 'table' key."}
    return query_table(
        table=payload.get("table", ""),
        columns=payload.get("columns"),
        filters=payload.get("filters"),
        order_by=payload.get("order_by"),
        order_dir=payload.get("order_dir", "asc"),
        limit=payload.get("limit", 20),
    )


def execute_code_e2b(code, files_to_mount):
    from e2b_code_interpreter import Sandbox

    if not settings.E2B_API_KEY:
        return {"success": False, "logs": "", "results": [], "error": "E2B_API_KEY not configured", "sandbox_files": []}

    os.environ["E2B_API_KEY"] = settings.E2B_API_KEY
    try:
        with Sandbox() as sandbox:
            for file_path in files_to_mount:
                if not os.path.isfile(file_path):
                    continue
                file_name = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    sandbox.files.write(file_name, f)
            sandbox.commands.run("mkdir -p temp_data")
            execution = sandbox.run_code(code, timeout=180)
            sandbox_files = []
            try:
                for f in sandbox.files.list("temp_data"):
                    local_path = Path(settings.TEMP_DATA_DIR) / f.name
                    content = sandbox.files.read(f"temp_data/{f.name}")
                    if content and len(content) > 0:
                        sandbox_files.append(f.name)
                        mode = "w" if isinstance(content, str) else "wb"
                        with open(local_path, mode, encoding="utf-8" if mode == "w" else None) as out:
                            out.write(content)
            except Exception:
                pass
            if execution.error:
                return {
                    "success": False,
                    "logs": execution.logs.stdout if execution.logs else "",
                    "results": [r.text for r in execution.results if r.text],
                    "error": f"Execution error:\n{execution.error.value}",
                    "sandbox_files": sandbox_files,
                }
            return {
                "success": True,
                "logs": execution.logs.stdout if execution.logs else "",
                "results": [str(r.text) for r in execution.results if r and getattr(r, "text", None)],
                "error": None,
                "sandbox_files": sandbox_files,
            }
    except Exception as exc:
        return {"success": False, "logs": "", "results": [], "error": f"Sandbox error: {exc}", "sandbox_files": []}


async def run_structured_workflow(
    user_query,
    data_context_summary,
    installed_packages,
    files_in_session,
    max_retries=3,
    event_callbacks=None,
):
    """Main workflow loop. Returns dict with response_to_user, code, new_files, logs, retries_used, events."""
    emit = build_workflow_emitter(event_callbacks)
    events_log: List[Dict[str, Any]] = []

    async def _emit(event):
        events_log.append(dict(event))
        await emit(event)

    temp_dir = Path(settings.TEMP_DATA_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    before_files = {f.name for f in temp_dir.iterdir() if f.is_file()} if temp_dir.exists() else set()

    current_query = user_query
    current_system_data = data_context_summary
    retries_used = 0
    last_code = None
    all_new_files: List[str] = []

    await _emit({"type": "start", "stage": "init", "message": "Workflow started."})

    for iteration in range(1, 11):
        await _emit({"type": "iteration", "iteration": iteration, "stage": "calling_llm", "message": "Calling AI..."})

        prompt = build_prompt(current_query, current_system_data)
        system_text = SYSTEM_PROMPT_TEMPLATE.replace("<<DATA_CONTEXT>>", data_context_summary or "No tables loaded.")

        try:
            raw_response = await asyncio.to_thread(
                LLMService.call_llm_structured,
                system_text=system_text,
                user_text=prompt,
                temperature=0.2,
                max_tokens=3000,
            )
        except Exception as exc:
            await _emit({"type": "error", "stage": "llm", "message": f"AI call failed: {exc}"})
            return {
                "response_to_user": f"AI call failed: {exc}",
                "code": None,
                "new_files": [],
                "logs": "",
                "retries_used": retries_used,
                "events": events_log,
            }

        await _emit({"type": "llm_response", "stage": "llm", "message": "AI responded."})
        parsed = parse_ai_response(raw_response)
        current_query = None

        response_to_user = parsed.get("response_to_user")
        request_system = (parsed.get("request_system") or "").strip()
        code = parsed.get("code")

        if response_to_user is not None:
            await _emit({"type": "done", "stage": "final", "message": "AI produced final response."})
            return {
                "response_to_user": response_to_user,
                "code": code or last_code,
                "new_files": all_new_files,
                "logs": "",
                "retries_used": retries_used,
                "events": events_log,
            }

        # E2B_EXE
        if request_system == "E2B_EXE" and code:
            await _emit({"type": "tool", "stage": "e2b", "message": "Executing Python code in E2B sandbox..."})
            result = execute_code_e2b(code, files_in_session)
            last_code = code
            if result["success"]:
                new_files = sorted(
                    (set(temp_dir.iterdir()) if temp_dir.exists() else set()) - before_files
                    if False else  # placeholder
                    []
                )
                try:
                    current_files = {f.name for f in temp_dir.iterdir() if f.is_file() and f.suffix.lower() in {".csv", ".html", ".png"}}
                    new_files = sorted(current_files - before_files)
                    new_files = [n for n in new_files if (temp_dir / n).stat().st_size > 0]
                except Exception:
                    pass
                all_new_files.extend(new_files)
                output_parts = []
                if result.get("logs"):
                    output_parts.append(result["logs"])
                for r in result.get("results", []):
                    if r:
                        output_parts.append(str(r))
                result_text = "\n".join(output_parts) if output_parts else "Code executed successfully (no output)"
                current_system_data = result_text
                retries_used = 0
                await _emit({"type": "tool_result", "stage": "e2b", "message": f"Code OK. {len(new_files)} new file(s).", "files": new_files})
                continue
            else:
                err = result.get("error", "Unknown error")
                await _emit({"type": "tool_error", "stage": "e2b", "message": err[:200]})
                if retries_used < max_retries:
                    retries_used += 1
                    current_system_data = f"{err} + Retries numbers: {retries_used}"
                    continue
                return {
                    "response_to_user": f"Execution failed after {max_retries} attempts. Last error: {err[:300]}",
                    "code": code,
                    "new_files": all_new_files,
                    "logs": result.get("logs", ""),
                    "retries_used": retries_used,
                    "events": events_log,
                }

        # QUERY_CSV
        if request_system == "QUERY_CSV":
            await _emit({"type": "tool", "stage": "query_csv", "message": "Querying bundled CSV..."})
            result = await handle_query_csv(code or "")
            last_code = code
            if result.get("success"):
                summary_lines = [
                    f"CSV query OK ({result.get('table')} table)",
                    f"Returned {result.get('row_count')} row(s), {len(result.get('columns') or [])} column(s).",
                ]
                if result.get("text"):
                    summary_lines.append("Preview:")
                    summary_lines.append(result["text"])
                current_system_data = "\n".join(summary_lines)
                retries_used = 0
                await _emit({"type": "tool_result", "stage": "query_csv", "message": f"Query OK: {result.get('row_count')} row(s).", "row_count": result.get("row_count")})
                continue
            else:
                err = result.get("error", "Unknown error")
                await _emit({"type": "tool_error", "stage": "query_csv", "message": err})
                if retries_used < max_retries:
                    retries_used += 1
                    current_system_data = f"QUERY_CSV error: {err} + Retries numbers: {retries_used}"
                    continue
                return {
                    "response_to_user": f"CSV query failed after {max_retries} attempts. Last error: {err[:300]}",
                    "code": code,
                    "new_files": all_new_files,
                    "logs": "",
                    "retries_used": retries_used,
                    "events": events_log,
                }

        # Unknown request
        await _emit({"type": "warning", "stage": "parse", "message": f"Unknown request: {request_system!r}"})
        current_system_data = f"Error: Unknown or empty request '{request_system}'. Please follow the protocol."
        continue

    await _emit({"type": "done", "stage": "final", "message": "Workflow finished."})
    return {
        "response_to_user": "Analysis complete. Please see the results above.",
        "code": last_code,
        "new_files": all_new_files,
        "logs": "",
        "retries_used": retries_used,
        "events": events_log,
    }
