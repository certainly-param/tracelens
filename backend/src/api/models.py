"""Pydantic models for API request/response validation."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


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
