"""Response formatting utilities for clean, structured responses to users."""
import re
from typing import Dict, Any, List, Optional


def clean_response_text(text: str) -> str:
    """
    Remove code blocks, backticks, and code-related markdown from response text.
    Preserves basic structure but removes technical artifacts.
    """
    if not text:
        return text

    # Remove code fences (```python ... ```, ```...```, etc)
    text = re.sub(r"```(?:python|py|javascript|js|sql|bash)?\s*\n?.*?\n?```", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove inline backticks (code references like `variable`)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove remaining triple backticks
    text = text.replace("```", "")

    # Clean up multiple consecutive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def format_chat_response(
    user_response_text: str,
    code_executed: Optional[str] = None,
    artifacts_created: Optional[List[str]] = None,
    retries_used: int = 0,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Format a standardized chat response with clean structure.

    Args:
        user_response_text: Natural language response (will be cleaned)
        code_executed: Python code that was run (if any)
        artifacts_created: List of generated file names
        retries_used: Number of retries needed
        error_message: Error message if execution failed

    Returns:
        Standardized response dict for frontend
    """
    return {
        "status": "error" if error_message else "success",
        "user_response": clean_response_text(user_response_text),
        "code_executed": code_executed,
        "artifacts_created": artifacts_created or [],
        "retries_used": retries_used,
        "error_message": error_message,
    }


def format_upload_response(
    file_name: str,
    num_rows: int,
    num_columns: int,
    ai_analysis: str,
    data_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Format response for file upload endpoint."""
    return {
        "status": "success",
        "file_name": file_name,
        "num_rows": num_rows,
        "num_columns": num_columns,
        "ai_analysis": clean_response_text(ai_analysis),
        "data_context": data_context,
    }
