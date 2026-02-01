"""API configuration from environment variables."""
import os
from typing import List


def _split_comma_list(value: str | None) -> List[str]:
    """Split comma-separated string into trimmed list."""
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


# Security
TRACELENS_API_KEY = os.getenv("TRACELENS_API_KEY", "")
TRACELENS_REQUIRE_AUTH = os.getenv("TRACELENS_REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")
TRACELENS_CORS_ORIGINS = _split_comma_list(
    os.getenv("TRACELENS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
)
TRACELENS_RATE_LIMIT = os.getenv("TRACELENS_RATE_LIMIT", "100/minute")
TRACELENS_RATE_LIMIT_WRITE = os.getenv("TRACELENS_RATE_LIMIT_WRITE", "20/minute")

# Limits
TRACELENS_MAX_STATE_SIZE = int(os.getenv("TRACELENS_MAX_STATE_SIZE", str(10 * 1024 * 1024)))  # 10MB default
