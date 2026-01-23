"""FastAPI main application."""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import json

from .models import (
    GraphResponse,
    CheckpointListResponse,
    CheckpointModel,
    SpanListResponse,
    SpanModel,
    RunListResponse,
    RunModel,
)
from .graph_builder import GraphBuilder
from ..storage.db_manager import get_db_manager
from ..instrumentation import setup_opentelemetry

# Initialize OpenTelemetry
setup_opentelemetry()

# Create FastAPI app
app = FastAPI(
    title="TraceLens API",
    description="Visual Debugger and Replay Engine for LangGraph Agents",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "tracelens"}


@app.get("/api/runs", response_model=RunListResponse)
async def list_runs():
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
async def get_graph(thread_id: str):
    """Get graph structure for a specific run."""
    try:
        graph = await graph_builder.build_graph(thread_id)
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build graph: {str(e)}")


@app.get("/api/runs/{thread_id}/checkpoints", response_model=CheckpointListResponse)
async def list_checkpoints(thread_id: str):
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
async def get_checkpoint(thread_id: str, checkpoint_id: str):
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
async def list_spans(thread_id: str):
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
