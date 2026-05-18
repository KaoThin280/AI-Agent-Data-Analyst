"""
Structured workflow implementing the proposed AI-System communication protocol.

This module replaces the old agentic workflow with a strict loop:
  System -> AI (prompt with structure)
  AI -> System (response with structure: Response to user, Request system, Code)
  System processes Request system (tool/code) -> loop until Response to user != None
"""

import os
import re
import json
import logging
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.data_service import DataProcessor
from app.services.session_service import session_manager

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 1. Prompt builder
# ──────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """
# ROLE AND CORE DIRECTIVES
You are an advanced Data Analysis AI Agent operating within a strictly formatted system. You communicate either directly with the User or implicitly with the System (to execute code or use tools). 
Your primary goal is to provide accurate answers, execute analytical code, and manage data contexts efficiently. 

# COMMUNICATION PROTOCOL
You will receive inputs from the system in a specific format and MUST output your response in an exact, strict format. Do not add any conversational text outside of the defined output structure.

## INPUT FORMAT (From System to You)
All inputs you receive will follow this exact structure:
"
User query: None | <<text query from FE>>
System: None | <<data context>> | <<result of tool called>> | <<code executed result + Retries numbers>>
"
- If a file is uploaded, the User query will be: "Please briefly describe this data" and the System will provide the data context.
- The System will provide <<selected data context>> based on the current active table.
- Keep in mind that system backend APIs require authorization; any data provided in the system context has already passed these secure backend checks.

## OUTPUT FORMAT (From You to System/User)
Every response you generate MUST follow this exact structure, with no exceptions, using "None" where a field is not applicable:
"
Response to user: None | <<text response to user>>
Request system: None | <<tool to use>> | E2B_EXE
Code: None | <<last code was generated of last user query>>
"

### Output Field Definitions:
1. `Response to user`:
   - Set to `None` IF you need to interact with the system (using a tool or executing code).
   - Set to `<<text response to user>>` IF you have completed your task and are ready to answer the user.
2. `Request system`:
   - Set to `None` IF you are sending a final response to the user.
   - Set to `<<tool to use>>` IF you need to call a built-in function.
   - Set to `E2B_EXE` IF you need the system to execute Python code in the E2B environment.
3. `Code`:
   - Set to `None` IF no code is involved.
   - Set to `<<code to execute>>` IF `Request system: E2B_EXE`.
   - Set to `<<last code was generated of last user query>>` IF you are providing the final `Response to user` after a successful code execution or after hitting the maximum retry limit.

# AVAILABLE SYSTEM TOOLS
You can request the following tools in the `Request system` field:
- `get_data_context()`: Returns all current data context available in the system.
- `get_data_context(tableName)`: Returns the data context of a specific table.
- `get_data_context("listName")`: Returns a list of all existing table names in the system.
- [E2B Environment Tools]: Use standard commands to check installed libraries or available data paths in the E2B environment.

# EXECUTION FLOW & RETRY LOGIC

Scenario 1: No Code Required
If the user query can be answered using existing knowledge or provided data context without calculation:
"
Response to user: <<your detailed answer here>>
Request system: None
Code: None
"

Scenario 2: Code Execution Required (E2B_EXE)
If calculations, data manipulation, or chart generation are needed:
"
Response to user: None
Request system: E2B_EXE
Code: <<your python script here>>
"

Scenario 3: Handling Code Results & Errors
After you request `E2B_EXE`, the system will return:
"
User query: None
System: <<code executed result + Retries numbers>>
"
- If the result is SUCCESS (text, new data name, or chart generated):
  - **CRITICAL CONTEXT RULE:** DO NOT reset the conversation or ask generic questions like "How would you like me to analyze this data?". 
  - Instead, acknowledge the successful execution. If a chart or file was created, summarize what the chart shows or explicitly inform the user that the visualization is ready.
  - Provide your final `Response to user` and include the successful code in `Code`.
- If the result is an ERROR:
  1. Automatically analyze the error and generate a fixed version of the code.
  2. Send a new `E2B_EXE` request with `Response to user: None`.
  3. IF the system indicates `Retries numbers = 3` and it is STILL an error, YOU MUST STOP RETRYING. Output your final response explaining the error to the user, set `Request system: None`, and include the last attempted code in the `Code` field.

### FILE SYSTEM RULES (IMPORTANT)
- The system uploads data files to the **root directory** of the sandbox.
- **ALWAYS read input files from root**: `pd.read_csv('sample_timeseries.csv')`
- **NEVER use `temp_data/` for reading files**  that directory may be empty.
- **Save ALL output files** (HTML charts, CSVs, PNGs) into the `temp_data/` directory so the system can detect and return them to the user.
- Example read: `df = pd.read_csv('sample_timeseries.csv')`
- Example save: `fig.write_html('temp_data/chart.html')` or `df.to_csv('temp_data/result.csv')`

### DATA ANALYSIS BEST PRACTICES (CRITICAL)
- **Time Series Aggregation:** When grouping time series data by month across a dataset spanning multiple years, NEVER group solely by month name (e.g., `dt.month_name()`), as this incorrectly merges data from different years. ALWAYS group by Year-Month (e.g., use `df['date'].dt.to_period('M')` or format as `YYYY-MM`).

### Available data
<<DATA_CONTEXT>>

### Additional note:
- You must use plotly and save to temp_data/ because the system will automatically detect and register any new files generated there. You can then reference these files in your final response to the user.
- Markdown code fence format is not required in your code output. Just provide the raw code in the `Code` field when requesting E2B_EXE.
"""

USER_QUERY_DEFAULT_UPLOAD = "Please briefly describe this data"

def build_prompt(user_query: Optional[str], system_data: str) -> str:
    """Build the structured prompt to send to AI."""
    query_line = f"User query: {user_query}" if user_query else "User query: None"
    sys_line = f"System: {system_data}" if system_data else "System: None"
    return f"{query_line}\n{sys_line}"

def build_initial_prompt_for_upload(data_context_summary: str) -> str:
    """Build prompt for initial file upload description."""
    return build_prompt(USER_QUERY_DEFAULT_UPLOAD, data_context_summary)

def build_tool_result_prompt(tool_result: str, retries: int = 0) -> str:
    """Build prompt after tool/code execution result is available."""
    system_part = f"{tool_result} + Retries numbers: {retries}"
    return build_prompt(None, system_part)

# ──────────────────────────────────────────────
# 2. Response parser
# ──────────────────────────────────────────────

def parse_ai_response(response: str) -> Dict[str, Optional[str]]:
    """
    Parse AI's three-line structured response.
    
    Returns dict with keys: response_to_user, request_system, code
    """
    result = {
        "response_to_user": None,
        "request_system": None,
        "code": None,
    }
    
    lines = response.strip().split("\n")
    i = 0
    while i < len(lines):
        line_stripped = lines[i].strip()
        
        if line_stripped.startswith("Response to user:"):
            # Collect multiple lines for Response to user
            response_lines = []
            first_val = line_stripped[len("Response to user:"):].strip()
            if first_val.lower() != "none":
                response_lines.append(first_val)
            i += 1
            # Collect remaining lines until next section
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith(("Response to user:", "Request system:", "Code:")):
                    break
                response_lines.append(lines[i])
                i += 1
            full_response = "\n".join(response_lines).strip()
            if full_response and full_response.lower() != "none":
                result["response_to_user"] = full_response
            continue
            
        elif line_stripped.startswith("Request system:"):
            req_lines = []
            first_val = line_stripped[len("Request system:"):].strip()
            if first_val.lower() != "none":
                req_lines.append(first_val)
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith(("Response to user:", "Request system:", "Code:")):
                    break
                req_lines.append(lines[i])
                i += 1
            full_req = "\n".join(req_lines).strip()
            if full_req and full_req.lower() != "none":
                result["request_system"] = full_req
            continue
            
        elif line_stripped.startswith("Code:"):
            # Collect all remaining lines as code (multi-line)
            code_lines = []
            # First line: content after "Code:"
            first_val = line_stripped[len("Code:"):].strip()
            if first_val.lower() != "none":
                code_lines.append(first_val)
            # Remaining lines until end
            i += 1
            while i < len(lines):
                next_line = lines[i]
                # Stop if we hit another section header
                if next_line.strip().startswith(("Response to user:", "Request system:", "Code:")):
                    break
                code_lines.append(next_line)
                i += 1
            full_code = "\n".join(code_lines).strip()
            if full_code:
                result["code"] = full_code
            # Don't increment i again (already at next section or end)
            continue
            
        else:
            i += 1
    
    return result

# ──────────────────────────────────────────────
# 3. Data context tools
# ──────────────────────────────────────────────

def get_data_context(table_or_list: Optional[str] = None) -> str:
    """
    Tool: get data context. Follows the spec:
    - None: returns all current data context
    - tableName: returns data context of that table
    - listName: returns list of table names
    """
    if table_or_list is None:
        return session_manager.get_all_tables_info()
    
    # Check if it's a table name
    if table_or_list in session_manager.tables:
        meta = session_manager.tables[table_or_list]
        cols = meta.get("columns", {})
        lines = [f"Table: {table_or_list}"]
        for col, info in cols.items():
            lines.append(f"  - {col} ({info.get('dtype', 'unknown')}, {info.get('business_meaning', 'Unknown')})")
        return "\n".join(lines)
    
    # Otherwise treat as list name -> return table names
    names = session_manager.get_table_names()
    if not names:
        return "No tables available."
    return "Available tables: " + ", ".join(names)

# ──────────────────────────────────────────────
# 4. Execute code via E2B
# ──────────────────────────────────────────────

def execute_code_e2b(code: str, files_to_mount: List[str]) -> Dict[str, Any]:
    """
    Execute Python code in E2B sandbox.
    Returns execution result as dict with success, logs, results, error, sandbox_files.
    """
    from e2b_code_interpreter import Sandbox
    from app.core.config import settings
    
    if not settings.E2B_API_KEY:
        return {
            "success": False,
            "logs": "",
            "results": [],
            "error": "E2B_API_KEY is not configured in .env",
            "sandbox_files": []
        }
    
    os.environ["E2B_API_KEY"] = settings.E2B_API_KEY
    logger.info("Creating E2B sandbox for code execution...")
    
    try:
        with Sandbox.create() as sandbox:
            # Upload required files
            for file_path in files_to_mount:
                if not os.path.isfile(file_path):
                    logger.warning("Mount file not found: %s", file_path)
                    continue
                file_name = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    sandbox.files.write(file_name, f)
            
            # Ensure temp_data directory exists inside sandbox
            sandbox.commands.run("mkdir -p temp_data")
            
            # Execute the code
            logger.info("Executing code (length: %d chars)...", len(code))
            execution = sandbox.run_code(code, timeout=180)
            
            # Read sandbox files from temp_data/
            sandbox_files = []
            try:
                files_in_sandbox = sandbox.files.list("temp_data")
                temp_dir = Path(settings.TEMP_DATA_DIR)
                temp_dir.mkdir(parents=True, exist_ok=True)
                for f in files_in_sandbox:
                    local_path = temp_dir / f.name
                    content = sandbox.files.read(f"temp_data/{f.name}")
                    if content and len(content) > 0:
                        sandbox_files.append(f.name)
                        if isinstance(content, str):
                            with open(local_path, "w", encoding="utf-8") as local_f:
                                local_f.write(content)
                        else:
                            with open(local_path, "wb") as local_f:
                                local_f.write(content)
                        logger.info("Downloaded sandbox file: %s", local_path)
            except Exception:
                pass  # directory may be empty
            
            if execution.error:
                error_msg = f"Execution error:\n{execution.error.value}\n\nCode executed:\n{code}"
                return {
                    "success": False,
                    "logs": execution.logs.stdout if execution.logs else "",
                    "results": [res.text for res in execution.results if res.text],
                    "error": error_msg,
                    "sandbox_files": sandbox_files,
                }
            
            results = [str(res.text) for res in execution.results if res and hasattr(res, "text") and res.text]
            logs = execution.logs.stdout if execution.logs else ""
            return {
                "success": True,
                "logs": logs,
                "results": results,
                "error": None,
                "sandbox_files": sandbox_files,
            }
            
    except Exception as exc:
        logger.exception("E2B sandbox execution failed.")
        return {
            "success": False,
            "logs": "",
            "results": [],
            "error": f"Sandbox error: {exc}",
            "sandbox_files": []
        }

# ──────────────────────────────────────────────
# 5. Main workflow loop
# ──────────────────────────────────────────────

def run_structured_workflow(
    user_query: Optional[str],
    data_context_summary: str,
    installed_packages: Set[str],
    files_in_session: List[str],
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Execute the structured AI-System communication loop.
    
    Returns:
        Dict with keys: response_to_user, code, new_files, logs, retries_used
    """
    # Snapshot current temp files to detect new ones later
    temp_dir = Path(settings.TEMP_DATA_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    before_files = set()
    if temp_dir.exists():
        for f in temp_dir.iterdir():
            if f.is_file():
                before_files.add(f.name)
    
    current_query = user_query
    current_system_data = data_context_summary
    retries_used = 0
    last_code = None
    all_logs = ""
    all_new_files = []
    
    # Loop until AI returns a response to user (or max iterations)
    max_iterations = 10  # safety limit
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.info("Workflow iteration %d: query=%s, retries=%d", 
                    iteration, str(current_query)[:50] if current_query else "None", retries_used)
        
        # Build prompt
        prompt = build_prompt(current_query, current_system_data)
        
        # Call LLM (use the LLMService, but with a single unified method)
        # Since we need the LLM to follow the structured output, we use generate_chat_response
        # which returns just text. But we need to instruct it properly.
        # We'll use a special call: pass the whole prompt as user query and system prompt includes the protocol.
        
        # Actually, we need to integrate with the existing LLMService but override the system instruction.
        # For simplicity, we call the internal _call_llm with our system template.
        
        # Build the system instruction with data context embedded
        system_text = SYSTEM_PROMPT_TEMPLATE.replace("<<DATA_CONTEXT>>", data_context_summary)
        
        raw_response = LLMService.call_llm_structured(
            system_text=system_text,
            user_text=prompt,
            temperature=0.2,
            max_tokens=3000,
        )
        logger.info("Raw AI response (first 500 chars): %s", raw_response[:500])
        
        # Parse the structured response
        parsed = parse_ai_response(raw_response)
        
        # Update current query to None (after first iteration, it's a follow-up)
        current_query = None
        
        # Check if AI wants to respond to user
        response_to_user = parsed.get("response_to_user")
        request_system = parsed.get("request_system")
        code = parsed.get("code")
        
        if response_to_user is not None:
            logger.info("AI returned final response to user (iteration %d)", iteration)
            # Final response
            return {
                "response_to_user": response_to_user,
                "code": code or last_code,
                "new_files": all_new_files,
                "logs": all_logs,
                "retries_used": retries_used,
            }
        
        # If no response_to_user, we must process a tool/code request
        
        # Handle get_data_context tool
        if request_system is not None and request_system.startswith("get_data_context"):
            # Parse argument
            tool_arg = None
            if ":" in request_system:
                tool_arg = request_system.split(":", 1)[1].strip()
            result = get_data_context(tool_arg)
            current_system_data = result
            logger.info("Tool 'get_data_context' executed, returning context")
            continue
        
        # Handle E2B_EXE
        if request_system == "E2B_EXE" and code:
            logger.info("Executing code via E2B (retry %d)", retries_used)
            exec_result = execute_code_e2b(code, files_in_session)
            last_code = code
            
            if exec_result["success"]:
                # Detect new files
                new_files = []
                try:
                    temp_dir_local = Path(settings.TEMP_DATA_DIR)
                    current_files = set()
                    for f in temp_dir_local.iterdir():
                        if f.suffix.lower() in {".csv", ".html", ".png"}:
                            current_files.add(f.name)
                    new_files = list(current_files - before_files)
                    # Filter empty files
                    valid = []
                    for name in new_files:
                        fpath = temp_dir_local / name
                        if fpath.stat().st_size > 0:
                            valid.append(name)
                    new_files = valid
                except Exception:
                    pass
                all_new_files.extend(new_files)
                
                # Build result for system
                output_parts = []
                if exec_result.get("logs"):
                    output_parts.append(exec_result["logs"])
                # Fix: handle results that might be objects, not strings
                for r in exec_result.get("results", []):
                    if r:
                        if isinstance(r, str):
                            output_parts.append(r)
                        elif hasattr(r, "text"):
                            # E2B Result object with .text attribute
                            output_parts.append(str(r.text))
                        elif hasattr(r, "__str__"):
                            # Fallback: convert to string
                            output_parts.append(str(r))
                
                # Indicate success
                #result_text = "\n".join(output_parts) if output_parts else "Code executed successfully (no output)"
                result_text = "\n".join(str(part) for part in output_parts) if output_parts else "Code executed successfully (no output)"
                current_system_data = result_text
                retries_used = 0  # Reset retries on success
                logger.info("Code executed successfully. New files: %s", new_files)
                
                # Register new CSV files
                new_csvs = [f for f in new_files if f.lower().endswith(".csv")]
                for csv_file in new_csvs:
                    csv_path = os.path.join(settings.TEMP_DATA_DIR, csv_file)
                    try:
                        new_context = DataProcessor.extract_data_context(csv_path)
                        table_name = os.path.splitext(csv_file)[0]
                        session_manager.add_table(
                            table_name=table_name,
                            file_path=csv_path,
                            columns=new_context.columns,
                        )
                    except Exception as exc:
                        logger.warning("Could not analyse new CSV %s: %s", csv_file, exc)
                
                # Register generated HTML/PNG files
                for f in new_files:
                    if f.lower().endswith(".html") or f.lower().endswith(".png"):
                        file_path = os.path.join(settings.TEMP_DATA_DIR, f)
                        if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                            session_manager.generated_files.append(file_path)
                
                continue
            else:
                # Execution failed
                error_msg = exec_result.get("error", "Unknown error")
                logger.warning("Code execution failed (attempt %d): %s", retries_used + 1, error_msg[:200])
                
                if retries_used < max_retries:
                    # Send error back to AI for correction
                    retries_used += 1
                    current_system_data = f"{error_msg} + Retries numbers: {retries_used}"
                    # current_query remains None (follow-up)
                    continue
                else:
                    # Max retries exceeded - return explanation + last code
                    logger.error("Max retries (%d) exceeded", max_retries)
                    return {
                        "response_to_user": f"Execution failed after {max_retries} attempts. Last error: {error_msg[:300]}",
                        "code": code,
                        "new_files": all_new_files,
                        "logs": exec_result.get("logs", ""),
                        "retries_used": retries_used,
                    }
        
        # If we reach here, unknown request_system value or missing code
        logger.warning("Unknown request_system: %s, code: %s", request_system, code)
        # Treat as error and loop back
        current_system_data = f"Error: Unknown request '{request_system}' or missing code. Please try again with correct format."
        continue
    
    # If loop ends without final response
    return {
        "response_to_user": "Analysis complete. Please see the results above.",
        "code": last_code,
        "new_files": all_new_files,
        "logs": all_logs,
        "retries_used": retries_used,
    }