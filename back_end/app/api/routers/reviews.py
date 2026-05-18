"""
Reviews router — collects user feedback and appends it to a local file.

The requirements also mention a Google Sheets link for optional integration.
The current implementation writes to a local `reviews.txt` file, which can
be replaced by a Google Sheets API client in production.
"""
import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.security import get_api_key

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_api_key)])

# Path to the reviews file
REVIEWS_FILE = os.path.join(settings.TEMP_DATA_DIR, "..", "reviews.txt")
REVIEWS_FILE = os.path.abspath(REVIEWS_FILE)


# ── Request / Response models ────────────────────────────────────────

class ReviewRequest(BaseModel):
    """
    Schema for submitting a user review / feedback message.
    """
    reviewer_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional display name of the reviewer.",
    )
    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Optional rating from 1 (worst) to 5 (best).",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Free-text review or feedback message.",
    )

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message must contain non-whitespace characters.")
        return stripped


class ReviewResponse(BaseModel):
    """
    Confirmation response after storing a review.
    """
    status: str = "success"
    message: str = "Thank you for your feedback! Your review has been recorded."
    timestamp: str = ""


# ── Storage helper ───────────────────────────────────────────────────

def _append_review_to_file(review_text: str) -> None:
    """
    Append a formatted review entry to the local reviews.txt file.
    
    Each entry is separated by a blank line and timestamped.
    The file is created if it does not already exist.
    """
    dir_name = os.path.dirname(REVIEWS_FILE)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = (
        f"--- Review submitted at {timestamp} ---\n"
        f"{review_text}\n"
        f"{'-' * 60}\n\n"
    )

    with open(REVIEWS_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

    logger.info("Review appended to %s", REVIEWS_FILE)


# ── Endpoint ─────────────────────────────────────────────────────────

@router.post(
    "/reviews",
    summary="Submit a user review / feedback message",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_review(
    payload: ReviewRequest,
    _: str = Depends(get_api_key),
) -> ReviewResponse:
    """
    Accept a user review and store it.

    The review is appended to the local `reviews.txt` file (one per line).
    In production, this could be replaced by a Google Sheets API call
    (see the link in the requirements).

    **Request body example:**
    ```json
    {
        "reviewer_name": "John Doe",
        "rating": 4,
        "message": "Great tool! The AI analysis was spot-on."
    }
    ```
    """
    # ── Build formatted text ─────────────────────────────────────────
    parts: list[str] = []
    if payload.reviewer_name:
        parts.append(f"Reviewer: {payload.reviewer_name}")
    if payload.rating is not None:
        stars = "⭐" * payload.rating
        parts.append(f"Rating: {payload.rating}/5 {stars}")
    parts.append(f"Message:\n{payload.message}")

    review_text = "\n".join(parts)

    # ── Persist ──────────────────────────────────────────────────────
    try:
        _append_review_to_file(review_text)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store review: {exc}",
        )

    return ReviewResponse(
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    )