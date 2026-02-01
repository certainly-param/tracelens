"""Audit logging for sensitive operations."""
import json
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("tracelens.audit")


def _sanitize(obj: Any, max_len: int = 500) -> Any:
    """Sanitize object for logging (truncate large values)."""
    if isinstance(obj, dict):
        return {k: _sanitize(v, max_len) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(x, max_len) for x in obj[:10]]
    if isinstance(obj, str) and len(obj) > max_len:
        return obj[:max_len] + "..."
    return obj


def log_state_update(thread_id: str, checkpoint_id: str, new_checkpoint_id: str, description: Optional[str] = None):
    """Log checkpoint state update."""
    logger.info(
        "AUDIT: state_update",
        extra={
            "event": "state_update",
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "new_checkpoint_id": new_checkpoint_id,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def log_resume(thread_id: str, checkpoint_id: str, new_thread_id: str, description: Optional[str] = None):
    """Log resume execution."""
    logger.info(
        "AUDIT: resume_execution",
        extra={
            "event": "resume_execution",
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "new_thread_id": new_thread_id,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def log_branch(thread_id: str, checkpoint_id: str, branch_thread_id: str, branch_name: Optional[str] = None):
    """Log branch creation."""
    logger.info(
        "AUDIT: branch_created",
        extra={
            "event": "branch_created",
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "branch_thread_id": branch_thread_id,
            "branch_name": branch_name,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
