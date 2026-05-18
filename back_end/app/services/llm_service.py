"""
Unified LLM Service – now using OpenRouter API.

Provider: OpenRouter (OpenAI Compatible)
Model: meta-llama/llama-3-8b-instruct:free (or any model you set).
"""

import os
import re
import logging
from typing import Optional

from openai import OpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Model name ──────────────────────────────────────────────────────────
# Sử dụng model miễn phí của Meta Llama 3 trên OpenRouter để test.
# Bạn có thể đổi sang "google/gemma-7b-it:free" hoặc các model khác.
OPENROUTER_MODEL_ID = "deepseek/deepseek-v4-flash"

# ── OpenRouter client (lazy init) ──────────────────────────────────────
_openrouter_client = None

def _get_openrouter_client():
    global _openrouter_client
    if _openrouter_client is None and getattr(settings, "OPENROUTER_API_KEY", None):
        # Khởi tạo client OpenAI nhưng trỏ Base URL về OpenRouter
        _openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        logger.info("OpenRouter client initialised.")
    return _openrouter_client

# ── Single LLM caller with Retry Logic ─────────────────────────────────
# Tự động thử lại tối đa 3 lần nếu gặp lỗi mạng hoặc API nghẽn.
# Thời gian chờ sẽ tăng dần: 2s, 4s, 8s...
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    reraise=True
)
def _call_openrouter(
    system_text: str,
    user_text: str,
    max_tokens: int = 3000,
    temperature: float = 0.2,
) -> str:
    """Call OpenRouter API with a system instruction and user message."""
    client = _get_openrouter_client()
    if not client:
        raise RuntimeError("OPENROUTER_API_KEY not configured in .env")

    # Gọi API theo chuẩn Chat Completions
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL_ID,
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        # OpenRouter khuyến nghị gửi thêm headers này để định danh ứng dụng trên bảng xếp hạng (không bắt buộc)
        extra_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Data Analyst AI Web",
        }
    )
    
    return response.choices[0].message.content

# ── Service class ──────────────────────────────────────────────────────
class LLMService:
    """High-level service that calls OpenRouter and parses output."""

    @staticmethod
    def _call_llm(
        system_text: str,
        user_text: str,
        max_tokens: int = 3000,
        temperature: float = 0.2,
    ) -> str:
        """Single provider call – OpenRouter."""
        logger.info("Calling OpenRouter (model: %s)", OPENROUTER_MODEL_ID)
        return _call_openrouter(system_text, user_text, max_tokens, temperature)

    @staticmethod
    def call_llm_structured(
        system_text: str,
        user_text: str,
        max_tokens: int = 3000,
        temperature: float = 0.2,
    ) -> str:
        """Public method to call LLM with custom system & user text."""
        return LLMService._call_llm(
            system_text=system_text,
            user_text=user_text,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # ── Keep other static methods if needed (extract_code, etc.) ──────
    @staticmethod
    def extract_code(text: str) -> Optional[str]:
        """Extract Python code from ```python ... ``` fenced block."""
        match = re.search(r"```(?:python|py)\s*\n(.*?)\n```", text, re.DOTALL)
        return match.group(1).strip() if match else None