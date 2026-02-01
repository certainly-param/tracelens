"""API key authentication."""
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import TRACELENS_API_KEY, TRACELENS_REQUIRE_AUTH

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str | None:
    """Verify API key. Returns None if auth is disabled or key is valid."""
    if not TRACELENS_REQUIRE_AUTH:
        return None
    if not TRACELENS_API_KEY:
        # Auth required but no key configured - allow all (dev mode)
        return None
    if api_key and api_key == TRACELENS_API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key. Set X-API-Key header or TRACELENS_API_KEY.",
    )
