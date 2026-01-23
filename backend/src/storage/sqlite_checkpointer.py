"""Custom SQLite checkpointer for LangGraph."""
import json
import pickle
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import cloudpickle

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata
from langgraph.checkpoint.base import CheckpointTuple

from .db_manager import get_db_manager


class SqliteCheckpointer(BaseCheckpointSaver):
    """SQLite-based checkpointer for LangGraph state persistence."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the SQLite checkpointer.
        
        Args:
            db_path: Path to SQLite database file. Defaults to DATABASE_PATH env var or ./tracelens.db
        """
        self.db_manager = get_db_manager(db_path)
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure database is initialized."""
        if not self._initialized:
            await self.db_manager.initialize()
            self._initialized = True
    
    def _serialize_state(self, state: Dict[str, Any]) -> bytes:
        """Serialize state dictionary to bytes.
        
        Attempts JSON serialization first, falls back to pickle for complex objects.
        """
        try:
            # Try JSON first for simple types
            return json.dumps(state).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to cloudpickle for complex objects
            return cloudpickle.dumps(state)
    
    def _deserialize_state(self, data: bytes) -> Dict[str, Any]:
        """Deserialize bytes back to state dictionary."""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    async def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Dict[str, Any],
    ) -> None:
        """Save a checkpoint to SQLite."""
        await self._ensure_initialized()
        
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = checkpoint.get("id", str(datetime.now().timestamp()))
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        parent_checkpoint_id = checkpoint.get("parent_checkpoint_id")
        
        # Serialize checkpoint data
        checkpoint_data = self._serialize_state(checkpoint.get("channel_values", {}))
        
        # Serialize metadata
        metadata_json = json.dumps(metadata) if metadata else None
        
        async with self.db_manager.get_connection() as db:
            await db.execute("""
                INSERT OR REPLACE INTO checkpoints 
                (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, 
                 parent_checkpoint_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                thread_id,
                checkpoint_id,
                checkpoint_ns,
                checkpoint_data,
                parent_checkpoint_id,
                metadata_json,
                datetime.now().isoformat()
            ))
            await db.commit()
    
    # Alias for compatibility
    async def aput(self, *args, **kwargs):
        """Alias for put method."""
        return await self.put(*args, **kwargs)
    
    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: List[Tuple[str, Any]],
        task_id: Optional[str] = None,
        task_path: str = "",
    ) -> None:
        """Write multiple channel writes in a batch.
        
        This method is called by LangGraph to handle batch channel writes.
        The writes parameter is a sequence of tuples: (channel_name: str, value: Any)
        This is for writing individual channel values, not full checkpoints.
        
        Args:
            config: RunnableConfig with thread_id and other settings
            writes: Sequence of (channel_name, value) tuples
            task_id: Task identifier
            task_path: Path to the task in the graph
        """
        # For now, aput_writes is used for incremental channel updates.
        # The full checkpoint is saved via the put() method.
        # We can implement this to track individual channel writes if needed,
        # but for MVP, we'll just pass through as the main checkpointing
        # happens in put().
        
        # If writes is empty, nothing to do
        if not writes:
            return
        
        # Note: Individual channel writes are typically handled by the put() method
        # when the full checkpoint is saved. This method might be called for
        # incremental updates, but the main checkpoint persistence happens via put().
        # For now, we'll implement a no-op or log for debugging.
        pass
    
    async def get(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """Retrieve a checkpoint from SQLite."""
        result = await self.aget_tuple(config)
        return result.checkpoint if result else None
    
    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Retrieve a checkpoint tuple from SQLite."""
        await self._ensure_initialized()
        
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if not checkpoint_id:
            # Get the latest checkpoint for this thread
            async with self.db_manager.get_connection() as db:
                async with db.execute("""
                    SELECT checkpoint_id, checkpoint_data, parent_checkpoint_id, metadata
                    FROM checkpoints
                    WHERE thread_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (thread_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return None
                    
                    checkpoint_id, checkpoint_data, parent_checkpoint_id, metadata_json = row
        else:
            # Get specific checkpoint
            async with self.db_manager.get_connection() as db:
                async with db.execute("""
                    SELECT checkpoint_id, checkpoint_data, parent_checkpoint_id, metadata
                    FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_id = ?
                """, (thread_id, checkpoint_id)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return None
                    
                    checkpoint_id, checkpoint_data, parent_checkpoint_id, metadata_json = row
        
        # Deserialize state
        channel_values = self._deserialize_state(checkpoint_data)
        
        # Parse metadata
        metadata = json.loads(metadata_json) if metadata_json else {}
        
        checkpoint = {
            "id": checkpoint_id,
            "parent_checkpoint_id": parent_checkpoint_id,
            "channel_values": channel_values,
            "metadata": metadata,
        }
        
        checkpoint_config = {
            **config,
            "configurable": {
                **config.get("configurable", {}),
                "checkpoint_id": checkpoint_id,
            }
        }
        
        return CheckpointTuple(
            config=checkpoint_config,
            checkpoint=checkpoint,
            metadata=metadata,
        )
    
    async def list(
        self,
        config: Dict[str, Any],
        *,
        before: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[CheckpointTuple]:
        """List checkpoints for a thread."""
        await self._ensure_initialized()
        
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        
        query = """
            SELECT checkpoint_id, checkpoint_data, parent_checkpoint_id, 
                   metadata, created_at
            FROM checkpoints
            WHERE thread_id = ?
        """
        params = [thread_id]
        
        if before:
            query += " AND created_at < ?"
            params.append(before)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        checkpoints = []
        async with self.db_manager.get_connection() as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    checkpoint_id, checkpoint_data, parent_checkpoint_id, metadata_json, created_at = row
                    
                    channel_values = self._deserialize_state(checkpoint_data)
                    metadata = json.loads(metadata_json) if metadata_json else {}
                    
                    checkpoint = {
                        "id": checkpoint_id,
                        "parent_checkpoint_id": parent_checkpoint_id,
                        "channel_values": channel_values,
                        "metadata": metadata,
                    }
                    
                    checkpoint_config = {
                        **config,
                        "configurable": {
                            **config.get("configurable", {}),
                            "checkpoint_id": checkpoint_id,
                        }
                    }
                    
                    checkpoints.append(CheckpointTuple(
                        config=checkpoint_config,
                        checkpoint=checkpoint,
                        metadata=metadata,
                    ))
        
        return checkpoints
