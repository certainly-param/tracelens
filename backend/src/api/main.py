"""FastAPI main application."""
import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
import json

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import (
    TRACELENS_CORS_ORIGINS,
    TRACELENS_RATE_LIMIT,
    TRACELENS_RATE_LIMIT_WRITE,
)
from .auth import verify_api_key
from .audit import log_state_update, log_resume, log_branch

from .models import (
    GraphResponse,
    CheckpointListResponse,
    CheckpointModel,
    SpanListResponse,
    SpanModel,
    RunListResponse,
    RunModel,
    CheckpointDiffResponse,
    TimelineResponse,
    TimelineEvent,
    StateUpdateRequest,
    StateUpdateResponse,
    ValidationResponse,
    ValidationError,
    ResumeRequest,
    ResumeResponse,
    BranchRequest,
    BranchResponse,
)
from .graph_builder import GraphBuilder
from ..storage.db_manager import get_db_manager
from ..instrumentation import setup_opentelemetry

# Initialize OpenTelemetry
setup_opentelemetry()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tracelens.api")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="TraceLens API",
    description="Visual Debugger and Replay Engine for LangGraph Agents",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=TRACELENS_CORS_ORIGINS if TRACELENS_CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve database path relative to project root (where .env file is)
# This ensures the API uses the same database as the verification script
project_root = Path(__file__).parent.parent.parent.parent
db_path_env = os.getenv("DATABASE_PATH", "./tracelens.db")
if os.path.isabs(db_path_env):
    db_path = db_path_env
else:
    # Resolve relative path from project root
    db_path = str(project_root / db_path_env)

# Initialize graph builder
graph_builder = GraphBuilder(db_path)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Centralized error handling; log and return sanitized response."""
    if isinstance(exc, HTTPException):
        raise exc  # Let FastAPI handle HTTPException
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check logs for details."},
    )


@app.get("/api/health")
@limiter.limit(TRACELENS_RATE_LIMIT)
async def health_check(request: Request):
    """Health check endpoint. Verifies API and database connectivity."""
    try:
        db_manager = get_db_manager(db_path)
        await db_manager.initialize()
        async with db_manager.get_connection() as db:
            await db.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        logger.warning("Health check DB failure: %s", e)
        db_status = "error"
    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "service": "tracelens",
        "database": db_status,
    }


@app.get("/api/runs", response_model=RunListResponse)
@limiter.limit(TRACELENS_RATE_LIMIT)
async def list_runs(request: Request):
    """List all execution runs (threads)."""
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        # Get unique thread IDs with metadata
        async with db.execute("""
            SELECT 
                thread_id,
                MIN(created_at) as first_checkpoint,
                MAX(created_at) as last_checkpoint,
                COUNT(*) as checkpoint_count
            FROM checkpoints
            GROUP BY thread_id
            ORDER BY last_checkpoint DESC
        """) as cursor:
            rows = await cursor.fetchall()
            
            runs = []
            for thread_id, first_cp, last_cp, cp_count in rows:
                # Get span count
                async with db.execute("""
                    SELECT COUNT(*) FROM traces WHERE thread_id = ?
                """, (thread_id,)) as span_cursor:
                    span_count = (await span_cursor.fetchone())[0]
                
                # Determine status
                status = "completed"
                # Could check if there are active spans (end_time is NULL)
                
                run = RunModel(
                    thread_id=thread_id,
                    created_at=datetime.fromisoformat(first_cp) if isinstance(first_cp, str) else first_cp,
                    last_updated=datetime.fromisoformat(last_cp) if isinstance(last_cp, str) else last_cp,
                    checkpoint_count=cp_count,
                    span_count=span_count,
                    status=status,
                )
                runs.append(run)
            
            return RunListResponse(runs=runs, total=len(runs))


@app.get("/api/runs/{thread_id}/graph", response_model=GraphResponse)
@limiter.limit(TRACELENS_RATE_LIMIT)
async def get_graph(request: Request, thread_id: str):
    """Get graph structure for a specific run."""
    try:
        graph = await graph_builder.build_graph(thread_id)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build graph: {str(e)}")


@app.get("/api/runs/{thread_id}/checkpoints", response_model=CheckpointListResponse)
@limiter.limit(TRACELENS_RATE_LIMIT)
async def list_checkpoints(request: Request, thread_id: str):
    """Get checkpoint history for a run."""
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        async with db.execute("""
            SELECT checkpoint_id, parent_checkpoint_id, created_at, 
                   checkpoint_data, metadata
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY created_at ASC
        """, (thread_id,)) as cursor:
            rows = await cursor.fetchall()
            
            checkpoints = []
            for row in rows:
                cp_id, parent_id, created_at, cp_data, metadata_json = row
                
                # Deserialize checkpoint data (just summary)
                try:
                    state_data = json.loads(cp_data.decode('utf-8'))
                except:
                    # Try pickle
                    import pickle
                    try:
                        state_data = pickle.loads(cp_data)
                    except:
                        state_data = {}
                
                # Create summary
                state_summary = {
                    "step_count": state_data.get("step_count", 0),
                    "has_results": bool(state_data.get("results")),
                    "has_summary": bool(state_data.get("summary")),
                    "error_count": state_data.get("error_count", 0),
                }
                
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                checkpoint = CheckpointModel(
                    checkpoint_id=cp_id,
                    parent_checkpoint_id=parent_id,
                    created_at=datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at,
                    state_summary=state_summary,
                    metadata=metadata,
                )
                checkpoints.append(checkpoint)
            
            return CheckpointListResponse(
                thread_id=thread_id,
                checkpoints=checkpoints,
                total=len(checkpoints),
            )


@app.get("/api/runs/{thread_id}/checkpoints/{checkpoint_id}")
@limiter.limit(TRACELENS_RATE_LIMIT)
async def get_checkpoint(request: Request, thread_id: str, checkpoint_id: str):
    """Get specific checkpoint state."""
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        async with db.execute("""
            SELECT checkpoint_data, metadata, created_at
            FROM checkpoints
            WHERE thread_id = ? AND checkpoint_id = ?
        """, (thread_id, checkpoint_id)) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Checkpoint not found")
            
            cp_data, metadata_json, created_at = row
            
            # Deserialize checkpoint data
            try:
                state_data = json.loads(cp_data.decode('utf-8'))
            except:
                import pickle
                try:
                    state_data = pickle.loads(cp_data)
                except:
                    state_data = {}
            
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            return {
                "checkpoint_id": checkpoint_id,
                "thread_id": thread_id,
                "created_at": created_at,
                "state": state_data,
                "metadata": metadata,
            }


@app.get("/api/runs/{thread_id}/spans", response_model=SpanListResponse)
@limiter.limit(TRACELENS_RATE_LIMIT)
async def list_spans(request: Request, thread_id: str):
    """Get OpenTelemetry spans for a run."""
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        async with db.execute("""
            SELECT trace_id, span_id, parent_span_id, name,
                   start_time, end_time, attributes
            FROM traces
            WHERE thread_id = ?
            ORDER BY start_time ASC
        """, (thread_id,)) as cursor:
            rows = await cursor.fetchall()
            
            spans = []
            for row in rows:
                trace_id, span_id, parent_span_id, name, start_time, end_time, attributes_json = row
                
                # Parse timestamps
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                if isinstance(end_time, str) and end_time:
                    end_time = datetime.fromisoformat(end_time)
                
                # Calculate duration
                duration = None
                if start_time and end_time:
                    duration = (end_time - start_time).total_seconds()
                
                # Parse attributes
                attributes = json.loads(attributes_json) if attributes_json else {}
                
                # Determine status
                status = "ok"
                if "error" in str(attributes.get("status", "")).lower():
                    status = "error"
                
                span = SpanModel(
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=parent_span_id,
                    name=name,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    attributes=attributes,
                    status=status,
                )
                spans.append(span)
            
            return SpanListResponse(
                thread_id=thread_id,
                spans=spans,
                total=len(spans),
            )


@app.get("/api/runs/{thread_id}/checkpoints/{checkpoint_id_1}/diff", response_model=CheckpointDiffResponse)
@limiter.limit(TRACELENS_RATE_LIMIT)
async def get_checkpoint_diff(
    request: Request,
    thread_id: str, 
    checkpoint_id_1: str, 
    compare_to: str
):
    """Compare state between two checkpoints."""
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        # Get both checkpoints
        async with db.execute("""
            SELECT checkpoint_data FROM checkpoints
            WHERE thread_id = ? AND checkpoint_id = ?
        """, (thread_id, checkpoint_id_1)) as cursor:
            row1 = await cursor.fetchone()
            if not row1:
                raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id_1} not found")
            cp_data_1 = row1[0]
        
        async with db.execute("""
            SELECT checkpoint_data FROM checkpoints
            WHERE thread_id = ? AND checkpoint_id = ?
        """, (thread_id, compare_to)) as cursor:
            row2 = await cursor.fetchone()
            if not row2:
                raise HTTPException(status_code=404, detail=f"Checkpoint {compare_to} not found")
            cp_data_2 = row2[0]
        
        # Deserialize both checkpoints
        def deserialize_checkpoint(data):
            try:
                return json.loads(data.decode('utf-8'))
            except:
                import pickle
                try:
                    return pickle.loads(data)
                except:
                    return {}
        
        state_1 = deserialize_checkpoint(cp_data_1)
        state_2 = deserialize_checkpoint(cp_data_2)
        
        # Compute diff
        added = {}
        removed = {}
        modified = {}
        
        all_keys = set(state_1.keys()) | set(state_2.keys())
        
        for key in all_keys:
            val1 = state_1.get(key)
            val2 = state_2.get(key)
            
            if key not in state_1:
                added[key] = val2
            elif key not in state_2:
                removed[key] = val1
            elif val1 != val2:
                modified[key] = {"old": val1, "new": val2}
        
        return CheckpointDiffResponse(
            checkpoint_id_1=checkpoint_id_1,
            checkpoint_id_2=compare_to,
            added=added,
            removed=removed,
            modified=modified,
        )


@app.get("/api/runs/{thread_id}/timeline", response_model=TimelineResponse)
@limiter.limit(TRACELENS_RATE_LIMIT)
async def get_timeline(request: Request, thread_id: str):
    """Get execution timeline with all events (checkpoints, spans, transitions)."""
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    events = []
    
    async with db_manager.get_connection() as db:
        # Get all checkpoints
        async with db.execute("""
            SELECT checkpoint_id, created_at, metadata
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY created_at ASC
        """, (thread_id,)) as cursor:
            checkpoint_rows = await cursor.fetchall()
            for cp_id, created_at, metadata_json in checkpoint_rows:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                events.append(TimelineEvent(
                    event_id=f"cp_{cp_id}",
                    event_type="checkpoint",
                    timestamp=created_at,
                    checkpoint_id=cp_id,
                    description=f"Checkpoint: {cp_id[:8]}...",
                    metadata=metadata,
                ))
        
        # Get all spans
        async with db.execute("""
            SELECT span_id, name, start_time, attributes
            FROM traces
            WHERE thread_id = ?
            ORDER BY start_time ASC
        """, (thread_id,)) as cursor:
            span_rows = await cursor.fetchall()
            for span_id, name, start_time, attributes_json in span_rows:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                attributes = json.loads(attributes_json) if attributes_json else {}
                
                # Extract node_id if available
                node_id = attributes.get("node.id") or attributes.get("langgraph.node")
                
                events.append(TimelineEvent(
                    event_id=f"span_{span_id}",
                    event_type="span",
                    timestamp=start_time,
                    span_id=span_id,
                    node_id=node_id,
                    description=f"Span: {name}",
                    metadata=attributes,
                ))
    
    # Sort all events by timestamp
    events.sort(key=lambda e: e.timestamp)
    
    return TimelineResponse(
        thread_id=thread_id,
        events=events,
        total=len(events),
    )


# Phase 4: Active Intervention Endpoints

@app.put("/api/runs/{thread_id}/checkpoints/{checkpoint_id}/state", response_model=StateUpdateResponse)
@limiter.limit(TRACELENS_RATE_LIMIT_WRITE)
async def update_checkpoint_state(
    request: Request,
    thread_id: str,
    checkpoint_id: str,
    body: StateUpdateRequest,
    _: None = Depends(verify_api_key),
):
    """Update checkpoint state (creates a new checkpoint with modified state). JSON-serializable state only."""
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        # Verify original checkpoint exists
        async with db.execute("""
            SELECT checkpoint_data FROM checkpoints
            WHERE thread_id = ? AND checkpoint_id = ?
        """, (thread_id, checkpoint_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        # Create new checkpoint ID
        import uuid
        new_checkpoint_id = f"{checkpoint_id}_modified_{uuid.uuid4().hex[:8]}"
        
        # JSON-only serialization (no pickle from API - prevents RCE)
        state_data = json.dumps(body.state).encode('utf-8')
        
        # Create metadata
        metadata = {
            "modified_from": checkpoint_id,
            "modification_time": datetime.now().isoformat(),
            "description": body.description or "State modified via API",
        }
        
        # Insert new checkpoint
        await db.execute("""
            INSERT INTO checkpoints 
            (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, 
             parent_checkpoint_id, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            thread_id,
            new_checkpoint_id,
            "",
            state_data,
            checkpoint_id,
            json.dumps(metadata),
            datetime.now().isoformat()
        ))
        await db.commit()
        
        log_state_update(thread_id, checkpoint_id, new_checkpoint_id, body.description)
        return StateUpdateResponse(
            success=True,
            new_checkpoint_id=new_checkpoint_id,
            thread_id=thread_id,
            message=f"State updated successfully. New checkpoint: {new_checkpoint_id}",
        )


@app.post("/api/runs/{thread_id}/checkpoints/{checkpoint_id}/validate", response_model=ValidationResponse)
@limiter.limit(TRACELENS_RATE_LIMIT)
async def validate_checkpoint_state(request: Request, thread_id: str, checkpoint_id: str, body: StateUpdateRequest):
    """Validate checkpoint state before updating."""
    errors = []
    warnings = []
    
    # Basic validation rules
    state = body.state
    
    # Check required fields (example for research agent)
    if "query" not in state:
        errors.append(ValidationError(
            field="query",
            message="Query field is required",
            severity="error"
        ))
    
    if "step_count" in state:
        if not isinstance(state["step_count"], int):
            errors.append(ValidationError(
                field="step_count",
                message="step_count must be an integer",
                severity="error"
            ))
        elif state["step_count"] > 50:
            warnings.append(ValidationError(
                field="step_count",
                message="step_count is unusually high (>50), may indicate infinite loop",
                severity="warning"
            ))
    
    # Check state size
    try:
        state_size = len(json.dumps(state))
        if state_size > 10 * 1024 * 1024:  # 10MB
            warnings.append(ValidationError(
                field="__state_size__",
                message=f"State size is large ({state_size / 1024 / 1024:.1f}MB), may impact performance",
                severity="warning"
            ))
    except:
        pass
    
    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@app.post("/api/runs/{thread_id}/checkpoints/{checkpoint_id}/resume", response_model=ResumeResponse)
@limiter.limit(TRACELENS_RATE_LIMIT_WRITE)
async def resume_execution(
    request: Request,
    thread_id: str,
    checkpoint_id: str,
    body: ResumeRequest,
    _: None = Depends(verify_api_key),
):
    """Resume execution from a checkpoint (optionally with modified state).
    
    Note: This creates a new thread for the resumed execution to preserve the original.
    Actual execution requires running the agent separately with the new thread_id.
    """
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        # Get the checkpoint to resume from
        async with db.execute("""
            SELECT checkpoint_data, metadata FROM checkpoints
            WHERE thread_id = ? AND checkpoint_id = ?
        """, (thread_id, checkpoint_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Checkpoint not found")
            
            cp_data, metadata_json = row
        
        # Deserialize state
        try:
            state = json.loads(cp_data.decode('utf-8'))
        except:
            import pickle
            state = pickle.loads(cp_data)
        
        # Apply modifications if provided
        if request.modified_state:
            state.update(request.modified_state)
        
        # Create new thread ID for resumed execution
        import uuid
        new_thread_id = f"{thread_id}_resume_{uuid.uuid4().hex[:8]}"
        
        # JSON-only for API-originated writes
        state_data = json.dumps(state).encode('utf-8')
        
        # Create metadata for resume checkpoint
        resume_metadata = {
            "resumed_from_thread": thread_id,
            "resumed_from_checkpoint": checkpoint_id,
            "resume_time": datetime.now().isoformat(),
            "description": body.description or "Resumed execution from checkpoint",
        }
        
        # Create initial checkpoint in new thread
        await db.execute("""
            INSERT INTO checkpoints 
            (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, 
             parent_checkpoint_id, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            new_thread_id,
            f"{checkpoint_id}_resume_start",
            "",
            state_data,
            None,
            json.dumps(resume_metadata),
            datetime.now().isoformat()
        ))
        await db.commit()
        
        log_resume(thread_id, checkpoint_id, new_thread_id, body.description)
        return ResumeResponse(
            success=True,
            new_thread_id=new_thread_id,
            original_thread_id=thread_id,
            from_checkpoint_id=checkpoint_id,
            message=f"Resume checkpoint created. Use thread_id '{new_thread_id}' to continue execution.",
        )


@app.post("/api/runs/{thread_id}/checkpoints/{checkpoint_id}/branch", response_model=BranchResponse)
@limiter.limit(TRACELENS_RATE_LIMIT_WRITE)
async def create_branch(
    request: Request,
    thread_id: str,
    checkpoint_id: str,
    body: BranchRequest,
    _: None = Depends(verify_api_key),
):
    """Create a new execution branch from a checkpoint.
    
    Similar to resume, but explicitly creates a named branch for A/B testing or exploration.
    """
    db_manager = get_db_manager(db_path)
    await db_manager.initialize()
    
    async with db_manager.get_connection() as db:
        # Get the checkpoint to branch from
        async with db.execute("""
            SELECT checkpoint_data, metadata FROM checkpoints
            WHERE thread_id = ? AND checkpoint_id = ?
        """, (thread_id, checkpoint_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Checkpoint not found")
            
            cp_data, metadata_json = row
        
        # Deserialize state
        try:
            state = json.loads(cp_data.decode('utf-8'))
        except:
            import pickle
            state = pickle.loads(cp_data)
        
        # Apply modifications if provided (JSON-serializable only from API)
        if body.modified_state:
            state.update(body.modified_state)
        
        # Create branch thread ID
        import uuid
        branch_name = body.branch_name or f"branch_{uuid.uuid4().hex[:8]}"
        branch_thread_id = f"{thread_id}_{branch_name}"
        
        # JSON-only for API-originated writes
        state_data = json.dumps(state).encode('utf-8')
        
        # Create metadata for branch checkpoint
        branch_metadata = {
            "branched_from_thread": thread_id,
            "branched_from_checkpoint": checkpoint_id,
            "branch_name": branch_name,
            "branch_time": datetime.now().isoformat(),
            "description": body.description or f"Branch '{branch_name}' from checkpoint",
        }
        
        # Create initial checkpoint in branch thread
        await db.execute("""
            INSERT INTO checkpoints 
            (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, 
             parent_checkpoint_id, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            branch_thread_id,
            f"{checkpoint_id}_branch_start",
            "",
            state_data,
            None,
            json.dumps(branch_metadata),
            datetime.now().isoformat()
        ))
        await db.commit()
        
        log_branch(thread_id, checkpoint_id, branch_thread_id, branch_name)
        return BranchResponse(
            success=True,
            branch_thread_id=branch_thread_id,
            original_thread_id=thread_id,
            from_checkpoint_id=checkpoint_id,
            branch_name=branch_name,
            message=f"Branch '{branch_name}' created. Use thread_id '{branch_thread_id}' for branched execution.",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
