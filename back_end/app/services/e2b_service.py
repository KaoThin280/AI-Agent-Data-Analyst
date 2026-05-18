"""
E2B Sandbox execution service and Agentic Workflow orchestrator.

Workflow:
  1. LLM generates Python code + dependencies.
  2. Code is executed in an E2B sandbox (with retry loop up to 4 attempts).
  3. On success, new files (CSV, HTML, PNG) in temp_data/ are detected.
  4. New DataContext objects are created for any new tabular files.
  5. Those DataContexts are sent back to the LLM for final insight.
  6. The final payload is returned to the caller (frontend).
"""
import os
import json
import logging
import time
import shutil
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.data_service import DataProcessor
from app.services.session_service import session_manager

logger = logging.getLogger(__name__)

# ── E2B Sandbox Runner ───────────────────────────────────────────────

class E2BService:
    """
    Wraps E2B Code Interpreter sandbox operations.
    """

    @staticmethod
    def execute(
        code: str,
        files_to_mount: List[str],
        deps_to_install: List[str],
    ) -> Dict[str, Any]:
        """
        Execute Python code inside an ephemeral E2B sandbox.

        Args:
            code: The Python source code to run.
            files_to_mount: List of local file paths to upload into the sandbox.
            deps_to_install: List of pip package names to install before execution.

        Returns:
            Dict with keys:
                - success (bool)
                - logs (str) — stdout output
                - results (list) — text results from the execution
                - error (str | None) — error trace if failed
                - sandbox_files (list) — files written inside sandbox temp_data/
        """
        from e2b_code_interpreter import Sandbox

        if not settings.E2B_API_KEY:
            raise RuntimeError("E2B_API_KEY is not configured in .env")

        os.environ["E2B_API_KEY"] = settings.E2B_API_KEY
        logger.info("Creating E2B sandbox...")

        try:
            with Sandbox.create() as sandbox:
                # 1. Upload required files
                for file_path in files_to_mount:
                    if not os.path.isfile(file_path):
                        logger.warning("Mount file not found: %s", file_path)
                        continue
                    file_name = os.path.basename(file_path)
                    with open(file_path, "rb") as f:
                        sandbox.files.write(file_name, f)
                    logger.debug("Uploaded %s to sandbox", file_name)

                # 2. Install dependencies
                if deps_to_install:
                    install_cmd = f"pip install {' '.join(deps_to_install)}"
                    logger.info("Installing deps: %s", install_cmd)
                    install_result = sandbox.commands.run(install_cmd)
                    if install_result.exit_code != 0:
                        logger.error("pip install failed: %s", install_result.stderr)
                        return {
                            "success": False,
                            "logs": install_result.stderr,
                            "results": [],
                            "error": f"pip install failed:\n{install_result.stderr}",
                            "sandbox_files": [],
                        }

                # 3. Ensure temp_data directory exists inside sandbox
                sandbox.commands.run("mkdir -p temp_data")

                # 4. Execute the code
                logger.info("Executing AI-generated code...")
                execution = sandbox.run_code(code, timeout=180)  # 3 minute timeout

                # 5. Read sandbox files from temp_data/ AND download to host
                sandbox_files = []
                try:
                    files_in_sandbox = sandbox.files.list("temp_data")
                    temp_dir = Path(settings.TEMP_DATA_DIR)
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    for f in files_in_sandbox:
                                            local_path = temp_dir / f.name
                                            try:
                                                content = sandbox.files.read(f"temp_data/{f.name}")
                                                if content is None or len(content) == 0:
                                                    logger.warning("Skipping empty file '%s' from sandbox", f.name)
                                                    continue  # skip adding to sandbox_files, skip saving empty file
                                                sandbox_files.append(f.name)
                                                # Write text or binary content appropriately
                                                if isinstance(content, str):
                                                    with open(local_path, "w", encoding="utf-8") as local_f:
                                                        local_f.write(content)
                                                else:
                                                    with open(local_path, "wb") as local_f:
                                                        local_f.write(content)
                                                logger.info("Downloaded sandbox file to %s", local_path)
                                            except Exception as dl_exc:
                                                logger.warning("Could not download file %s: %s", f.name, dl_exc)
                except Exception:
                    pass  # directory may be empty

                if execution.error:
                    error_msg = (
                        f"Execution error:\n{execution.error.value}\n\n"
                        f"Code executed:\n```python\n{code}\n```"
                    )
                    logger.warning("E2B execution failed.")
                    return {
                        "success": False,
                        "logs": execution.logs.stdout if execution.logs else "",
                        "results": [res.text for res in execution.results if res.text],
                        "error": error_msg,
                        "sandbox_files": sandbox_files,
                    }

                results = [res.text for res in execution.results if res.text]
                logs = execution.logs.stdout if execution.logs else ""
                logger.info("E2B execution succeeded. %d result(s), %d log line(s).", len(results), len(logs))

                return {
                    "success": True,
                    "logs": logs,
                    "results": results,
                    "error": None,
                    "sandbox_files": sandbox_files,
                }

        except Exception as exc:
            logger.exception("E2B sandbox creation or execution failed.")
            return {
                "success": False,
                "logs": "",
                "results": [],
                "error": f"Sandbox error: {exc}",
                "sandbox_files": [],
            }

    @staticmethod
    def execute_with_tool_interface(
        ai_response: str,
        files_to_mount: List[str],
    ) -> Dict[str, Any]:
        """
        Execute code from JSON tool calls in AI response.

        Args:
            ai_response: LLM response containing JSON tool calls
            files_to_mount: List of local file paths to upload into sandbox

        Returns:
            Dict with keys:
                - success (bool)
                - code (str) - the code that was executed
                - logs (str) - stdout output
                - results (list) - text results from execution
                - error (str | None) - error trace if failed
                - sandbox_files (list) - files written in sandbox temp_data/
        """
        # Extract JSON tool calls
        tool_calls = LLMService.extract_tool_calls_json(ai_response)

        if not tool_calls:
            logger.warning("No tool calls found in AI response")
            return {
                "success": False,
                "code": None,
                "logs": "",
                "results": [],
                "error": "No executable code found in response (invalid JSON tool call)",
                "sandbox_files": [],
            }

        # Use the first tool call (typically only one)
        tool_call = tool_calls[0]
        code = tool_call.get("code", "").strip()

        if not code:
            return {
                "success": False,
                "code": None,
                "logs": "",
                "results": [],
                "error": "Tool call has empty code",
                "sandbox_files": [],
            }

        logger.info("Executing code from tool call (length: %d chars)", len(code))

        # Execute on E2B with no deps (assume all needed packages already installed)
        execution_result = E2BService.execute(
            code=code,
            files_to_mount=files_to_mount,
            deps_to_install=[],  # No separate deps from tool calls
        )

        # Add code to result
        execution_result["code"] = code
        return execution_result


# ── Workflow Orchestrator ────────────────────────────────────────────

def _find_new_temp_files(before_files: Set[str]) -> List[str]:
    """
    Find files in temp_data/ that were not present in `before_files`.
    Only consider CSV, HTML, PNG files.
    """
    temp_dir = Path(settings.TEMP_DATA_DIR)
    if not temp_dir.exists():
        return []

    current_files = set()
    for f in temp_dir.iterdir():
        if f.suffix.lower() in {".csv", ".html", ".png"}:
            current_files.add(f.name)

    new_files = list(current_files - before_files)
    # Bỏ qua file rỗng (kích thước 0 bytes)
    valid_files = []
    for name in new_files:
        file_path = temp_dir / name
        if file_path.stat().st_size > 0:
            valid_files.append(name)
        else:
            logger.warning("Filtering out empty file '%s' from new files", name)
    return valid_files


def _clean_temp_directory(exclude_files: Optional[Set[str]] = None) -> None:
    """
        Clean all files in TEMP_DATA_DIR except those in exclude_files.
        Used to remove partial files from failed retry attempts.
        """
    temp_dir = Path(settings.TEMP_DATA_DIR)
    if not temp_dir.exists():
        return

    exclude = exclude_files or set()
    for f in temp_dir.iterdir():
        if f.is_file() and f.name not in exclude:
            try:
                f.unlink()
                logger.debug("Cleaned temp file: %s", f.name)
            except Exception as exc:
                logger.warning("Could not clean temp file %s: %s", f.name, exc)



def run_agentic_workflow(
    query: str,
    data_context_summary: str,
    installed_packages: Set[str],
    files_in_session: List[str],
    max_retries: int = 4,
) -> Dict[str, Any]:
    """
    Full agentic workflow: classify query -> execute with retry -> analyze new outputs -> return.

    Args:
        query: User's natural language query.
        data_context_summary: Current active DataContext summary string.
        installed_packages: Set of already installed pip packages.
        files_in_session: List of file paths currently mounted (uploaded files).
        max_retries: How many times to retry on execution error.

    Returns:
        Dict with keys:
            - user_response (str): final natural-language response.
            - code (str | None): last executed code.
            - new_files (list): list of generated file names.
            - logs (str): execution logs.
            - retries_used (int): number of retries actually used.
            - error (str | None): if all retries failed.
    """

    # Step 1: Classify if query needs code
    logger.info("Step 1: Classifying query: %s", query[:80])
    classification = LLMService.generate_query_classification(
        query=query,
        data_context_summary=data_context_summary,
        installed_packages=installed_packages,
    )

    if not classification["needs_code"]:
        logger.info("Query doesn't need code, generating text response")
        response = LLMService.generate_chat_response(
            query=query,
            data_context_summary=data_context_summary,
            installed_packages=installed_packages,
        )
        return {
            "user_response": response["user_response"],
            "code": None,
            "new_files": [],
            "logs": "",
            "retries_used": 0,
            "error": None,
        }

    # Step 2: Code needed - generate code with tool calls
    logger.info("Query needs code, generating tool calls")

    # Snapshot current temp files to detect new ones later
    temp_dir = Path(settings.TEMP_DATA_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    before_files = set()
    if temp_dir.exists():
        for f in temp_dir.iterdir():
            if f.is_file():
                before_files.add(f.name)

    # Generate initial code
    llm_result = LLMService.generate_code_with_tool_calls(
        query=query,
        data_context_summary=data_context_summary,
        installed_packages=installed_packages,
    )

    if not llm_result["tool_calls"]:
        # LLM didn't provide JSON tool calls - try extracting code block as fallback
        code_block = LLMService.extract_code(llm_result["raw"])
        if code_block:
            logger.info("No JSON tool calls found, but extracted code block - using as fallback")
            # Create a synthetic tool call from code block
            llm_result["tool_calls"] = [{
                "tool": "execute_code",
                "code": code_block,
                "description": "Code extracted from response (fallback)"
            }]
        else:
            logger.warning("LLM generated no tool calls and no code block")
            # If user_response is empty, fall back to simple chat
            if not llm_result.get("user_response"):
                logger.info("Falling back to simple chat response")
                fallback = LLMService.generate_chat_response(
                    query=query,
                    data_context_summary=data_context_summary,
                    installed_packages=installed_packages,
                )
                return {
                    "user_response": fallback["user_response"],
                    "code": None,
                    "new_files": [],
                    "logs": "",
                    "retries_used": 0,
                    "error": None,
                }
            return {
                "user_response": llm_result["user_response"],
                "code": None,
                "new_files": [],
                "logs": "",
                "retries_used": 0,
                "error": None,
            }

    # Step 3: Execute with retry loop — success processing now before break
        attempt = 0
        last_error = None
        execution_result = None
        ai_response = llm_result["raw"]
        new_files = []
        final_response = ""
        final_code = None
        response_logs = ""

        while attempt <= max_retries:
            logger.info("Step 3: Execution attempt %d/%d", attempt + 1, max_retries + 1)
            _clean_temp_directory(exclude_files=before_files)

            execution_result = E2BService.execute_with_tool_interface(
                ai_response=ai_response,
                files_to_mount=files_in_session,
            )

            if execution_result["success"]:
                logger.info("Execution succeeded on attempt %d", attempt + 1)

                # Step 4: Detect newly generated files (on success)
                new_files = _find_new_temp_files(before_files)
                logger.info("Step 4: Detected %d new file(s): %s", len(new_files), new_files)

                # Step 5: Process results and build final response
                response_logs = execution_result.get("logs", "")
                results_raw = execution_result.get("results", [])
                response_parts = []
                # Include the AI's descriptive explanation first
                if llm_result.get("user_response"):
                    response_parts.append(str(llm_result["user_response"]))
                if response_logs:
                    response_parts.append(str(response_logs))
                for r in results_raw:
                    if r is not None:
                        cleaned = str(r)
                        if cleaned.startswith("[") and cleaned.endswith("]"):
                            try:
                                import ast
                                parsed = ast.literal_eval(cleaned)
                                if isinstance(parsed, list):
                                    cleaned = "\n".join(str(item) for item in parsed)
                            except:
                                cleaned = cleaned.strip("[]")
                        response_parts.append(cleaned)
                final_response = "\n\n".join(p for p in response_parts if p)
                final_code = execution_result.get("code")
                break

            # Execution failed - request AI to fix
            last_error = execution_result["error"]
            logger.warning("Execution failed: %s", last_error[:200])

            if attempt < max_retries:
                # Build fix-request
                fix_prompt = (
                    f"The code I generated failed with this error:\n\n"
                    f"{last_error}\n\n"
                    f"Please fix it and provide corrected code in JSON format:\n"
                    f'{{"tool": "execute_code", "code": "...fixed code...", "description": "..."}}'
                )
                logger.info("Step 3b: Requesting LLM to fix code (attempt %d)", attempt + 1)
                llm_fix_result = LLMService.generate_code_with_tool_calls(
                    query=fix_prompt,
                    data_context_summary=data_context_summary,
                    installed_packages=installed_packages,
                )
                if llm_fix_result["tool_calls"]:
                    ai_response = llm_fix_result["raw"]
                attempt += 1
            else:
                # No more retries
                logger.error("All %d execution attempts failed.", max_retries + 1)
                return {
                    "user_response": (
                        f"Execution failed after {max_retries + 1} attempts. "
                        f"Error: {last_error}"
                    ),
                    "code": execution_result.get("code"),
                    "new_files": [],
                    "logs": execution_result["logs"] if execution_result else "",
                    "retries_used": attempt,
                    "error": last_error,
                }

        # Analyze new CSV files (after loop — success path)
        new_csvs = [f for f in new_files if f.lower().endswith(".csv")]
        for csv_file in new_csvs:
            csv_path = os.path.join(settings.TEMP_DATA_DIR, csv_file)
            logger.info("Step 5: Extracting DataContext from new CSV: %s", csv_file)
            try:
                new_context = DataProcessor.extract_data_context(csv_path)

                table_name = os.path.splitext(csv_file)[0]
                session_manager.add_table(
                    table_name=table_name,
                    file_path=csv_path,
                    columns=new_context.columns,
                )
                logger.info("Registered new table '%s' in session", table_name)
            except Exception as exc:
                logger.warning("Could not analyse new CSV %s: %s", csv_file, exc)

        # Register generated HTML/PNG files
        for f in new_files:
            if f.lower().endswith(".html") or f.lower().endswith(".png"):
                file_path = os.path.join(settings.TEMP_DATA_DIR, f)
                if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                    session_manager.generated_files.append(file_path)

        # Step 6: Build final payload
        return {
            "user_response": final_response,
            "code": final_code,
            "new_files": new_files,
            "logs": response_logs,
            "retries_used": attempt,
            "error": None,
        }
