"""
API Key authentication middleware for FastAPI.
All protected endpoints must pass the 'X-API-Key' header
matching BACKEND_SECRET_TOKEN from .env.
"""
import logging
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

logger = logging.getLogger(__name__)

# Define the expected header name
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key_header: str = Security(API_KEY_HEADER)) -> str:
    """
    Validate the API key sent via the X-API-Key header.
    
    Returns:
        The validated API key string.
    
    Raises:
        HTTPException 401: If the key is missing or does not match.
    """
    if not api_key_header:
        logger.warning("API request rejected: missing API key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Provide it in the 'X-API-Key' header.",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    if api_key_header != settings.BACKEND_SECRET_TOKEN:
        logger.warning("API request rejected: invalid API key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key.",
            headers={"WWW-Authenticate": "APIKey"},
        )
    
    logger.debug("API key validated successfully")
    return api_key_header