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
    
    # Phase 4: Active Intervention Methods
    
    async def create_modified_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        modified_state: Dict[str, Any],
        description: Optional[str] = None,
    ) -> str:
        """Create a new checkpoint with modified state.
        
        Args:
            thread_id: Thread ID
            checkpoint_id: Original checkpoint ID to modify
            modified_state: Modified state dictionary
            description: Optional description of the modification
            
        Returns:
            New checkpoint ID
        """
        await self._ensure_initialized()
        
        # Generate new checkpoint ID
        import uuid
        new_checkpoint_id = f"{checkpoint_id}_modified_{uuid.uuid4().hex[:8]}"
        
        # Serialize modified state
        state_data = self._serialize_state(modified_state)
        
        # Create metadata
        metadata = {
            "modified_from": checkpoint_id,
            "modification_time": datetime.now().isoformat(),
            "description": description or "State modified programmatically",
        }
        
        async with self.db_manager.get_connection() as db:
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
        
        return new_checkpoint_id
    
    async def create_resume_checkpoint(
        self,
        original_thread_id: str,
        checkpoint_id: str,
        new_thread_id: str,
        modified_state: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> str:
        """Create a checkpoint in a new thread for resuming execution.
        
        Args:
            original_thread_id: Original thread ID
            checkpoint_id: Checkpoint ID to resume from
            new_thread_id: New thread ID for resumed execution
            modified_state: Optional modified state (if None, uses original state)
            description: Optional description
            
        Returns:
            New checkpoint ID in the new thread
        """
        await self._ensure_initialized()
        
        async with self.db_manager.get_connection() as db:
            # Get original checkpoint
            async with db.execute("""
                SELECT checkpoint_data FROM checkpoints
                WHERE thread_id = ? AND checkpoint_id = ?
            """, (original_thread_id, checkpoint_id)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Checkpoint {checkpoint_id} not found in thread {original_thread_id}")
                
                original_data = row[0]
            
            # Deserialize original state
            state = self._deserialize_state(original_data)
            
            # Apply modifications if provided
            if modified_state:
                state.update(modified_state)
            
            # Serialize state
            state_data = self._serialize_state(state)
            
            # Create new checkpoint ID
            new_checkpoint_id = f"{checkpoint_id}_resume_start"
            
            # Create metadata
            metadata = {
                "resumed_from_thread": original_thread_id,
                "resumed_from_checkpoint": checkpoint_id,
                "resume_time": datetime.now().isoformat(),
                "description": description or "Resumed execution from checkpoint",
            }
            
            # Insert checkpoint in new thread
            await db.execute("""
                INSERT INTO checkpoints 
                (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, 
                 parent_checkpoint_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                new_thread_id,
                new_checkpoint_id,
                "",
                state_data,
                None,
                json.dumps(metadata),
                datetime.now().isoformat()
            ))
            await db.commit()
        
        return new_checkpoint_id
    
    async def create_branch(
        self,
        original_thread_id: str,
        checkpoint_id: str,
        branch_name: str,
        modified_state: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> str:
        """Create a new execution branch from a checkpoint.
        
        Args:
            original_thread_id: Original thread ID
            checkpoint_id: Checkpoint ID to branch from
            branch_name: Name for the branch
            modified_state: Optional modified state
            description: Optional description
            
        Returns:
            New branch thread ID
        """
        await self._ensure_initialized()
        
        # Create branch thread ID
        branch_thread_id = f"{original_thread_id}_{branch_name}"
        
        async with self.db_manager.get_connection() as db:
            # Get original checkpoint
            async with db.execute("""
                SELECT checkpoint_data FROM checkpoints
                WHERE thread_id = ? AND checkpoint_id = ?
            """, (original_thread_id, checkpoint_id)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Checkpoint {checkpoint_id} not found in thread {original_thread_id}")
                
                original_data = row[0]
            
            # Deserialize original state
            state = self._deserialize_state(original_data)
            
            # Apply modifications if provided
            if modified_state:
                state.update(modified_state)
            
            # Serialize state
            state_data = self._serialize_state(state)
            
            # Create new checkpoint ID
            new_checkpoint_id = f"{checkpoint_id}_branch_start"
            
            # Create metadata
            metadata = {
                "branched_from_thread": original_thread_id,
                "branched_from_checkpoint": checkpoint_id,
                "branch_name": branch_name,
                "branch_time": datetime.now().isoformat(),
                "description": description or f"Branch '{branch_name}' from checkpoint",
            }
            
            # Insert checkpoint in branch thread
            await db.execute("""
                INSERT INTO checkpoints 
                (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, 
                 parent_checkpoint_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                branch_thread_id,
                new_checkpoint_id,
                "",
                state_data,
                None,
                json.dumps(metadata),
                datetime.now().isoformat()
            ))
            await db.commit()
        
        return branch_thread_id
