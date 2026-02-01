"""Pydantic models for API request/response validation."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import json


class NodeModel(BaseModel):
    """Node representation in graph."""
    id: str
    label: str
    type: str = Field(default="agent_node")
    status: str = Field(default="pending")  # pending, active, completed, failed
    timestamp: Optional[datetime] = None
    duration: Optional[float] = None  # in seconds
    metadata: Optional[Dict[str, Any]] = None


class EdgeModel(BaseModel):
    """Edge representation in graph."""
    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None


class GraphResponse(BaseModel):
    """Graph structure response."""
    nodes: List[NodeModel]
    edges: List[EdgeModel]
    metadata: Dict[str, Any]


class CheckpointModel(BaseModel):
    """Checkpoint representation."""
    checkpoint_id: str
    parent_checkpoint_id: Optional[str] = None
    created_at: datetime
    state_summary: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class CheckpointListResponse(BaseModel):
    """List of checkpoints."""
    thread_id: str
    checkpoints: List[CheckpointModel]
    total: int


class SpanModel(BaseModel):
    """OpenTelemetry span representation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # in seconds
    attributes: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="ok")  # ok, error


class SpanListResponse(BaseModel):
    """List of spans."""
    thread_id: str
    spans: List[SpanModel]
    total: int


class RunModel(BaseModel):
    """Execution run representation."""
    thread_id: str
    created_at: datetime
    last_updated: datetime
    checkpoint_count: int
    span_count: int
    status: str = Field(default="running")  # running, completed, failed


class RunListResponse(BaseModel):
    """List of runs."""
    runs: List[RunModel]
    total: int


class CheckpointDiffResponse(BaseModel):
    """Checkpoint state diff response."""
    checkpoint_id_1: str
    checkpoint_id_2: str
    added: Dict[str, Any] = Field(default_factory=dict)
    removed: Dict[str, Any] = Field(default_factory=dict)
    modified: Dict[str, Any] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    """Timeline event representation."""
    event_id: str
    event_type: str  # checkpoint, span, node_transition
    timestamp: datetime
    checkpoint_id: Optional[str] = None
    span_id: Optional[str] = None
    node_id: Optional[str] = None
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    """Timeline response."""
    thread_id: str
    events: List[TimelineEvent]
    total: int


# Phase 4: Active Intervention Models

def _get_max_state_size() -> int:
    """Lazy import to avoid circular dependency."""
    try:
        from .config import TRACELENS_MAX_STATE_SIZE
        return TRACELENS_MAX_STATE_SIZE
    except ImportError:
        return 10 * 1024 * 1024  # 10MB default


class StateUpdateRequest(BaseModel):
    """Request to update checkpoint state. JSON-serializable only (no pickle from API)."""
    state: Dict[str, Any]
    description: Optional[str] = Field(None, description="Description of the change", max_length=1000)

    @field_validator("state")
    @classmethod
    def validate_state_json_serializable_and_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure state is JSON-serializable and within size limit."""
        try:
            serialized = json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"State must be JSON-serializable. Pickle/complex objects not allowed from API. {e}"
            )
        max_size = _get_max_state_size()
        if len(serialized) > max_size:
            raise ValueError(
                f"State size ({len(serialized)} bytes) exceeds limit ({max_size} bytes)"
            )
        return v


class StateUpdateResponse(BaseModel):
    """Response after updating checkpoint state."""
    success: bool
    new_checkpoint_id: str
    thread_id: str
    message: str


class ValidationError(BaseModel):
    """Validation error detail."""
    field: str
    message: str
    severity: str = Field(default="error")  # error, warning


class ValidationResponse(BaseModel):
    """State validation response."""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)


class ResumeRequest(BaseModel):
    """Request to resume execution from checkpoint."""
    from_checkpoint_id: str
    modified_state: Optional[Dict[str, Any]] = None
    description: Optional[str] = Field(None, description="Description of resume operation", max_length=1000)

    @field_validator("modified_state")
    @classmethod
    def validate_modified_state(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        try:
            serialized = json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"modified_state must be JSON-serializable. {e}")
        max_size = _get_max_state_size()
        if len(serialized) > max_size:
            raise ValueError(f"modified_state size ({len(serialized)} bytes) exceeds limit ({max_size} bytes)")
        return v


class ResumeResponse(BaseModel):
    """Response after resuming execution."""
    success: bool
    new_thread_id: str
    original_thread_id: str
    from_checkpoint_id: str
    message: str


class BranchRequest(BaseModel):
    """Request to create execution branch."""
    from_checkpoint_id: str
    branch_name: Optional[str] = Field(None, max_length=100)
    modified_state: Optional[Dict[str, Any]] = None
    description: Optional[str] = Field(None, description="Description of the branch", max_length=1000)

    @field_validator("modified_state")
    @classmethod
    def validate_modified_state(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        try:
            serialized = json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"modified_state must be JSON-serializable. {e}")
        max_size = _get_max_state_size()
        if len(serialized) > max_size:
            raise ValueError(f"modified_state size ({len(serialized)} bytes) exceeds limit ({max_size} bytes)")
        return v


class BranchResponse(BaseModel):
    """Response after creating branch."""
    success: bool
    branch_thread_id: str
    original_thread_id: str
    from_checkpoint_id: str
    branch_name: Optional[str] = None
    message: str
