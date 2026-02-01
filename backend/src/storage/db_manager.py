"""Database connection management and utilities."""
import aiosqlite
import json
from pathlib import Path
from typing import Optional, AsyncContextManager
from contextlib import asynccontextmanager
import os


class DatabaseManager:
    """Manages SQLite database connections with WAL mode."""
    
    def __init__(self, db_path: str = "./tracelens.db"):
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        """Initialize database with schema and WAL mode."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for concurrent reads/writes
            await db.execute("PRAGMA journal_mode=WAL;")
            
            # Create checkpoints table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    checkpoint_ns TEXT DEFAULT '',
                    checkpoint_data BLOB NOT NULL,
                    parent_checkpoint_id TEXT,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (thread_id, checkpoint_id)
                )
            """)
            
            # Create traces table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT NOT NULL,
                    span_id TEXT NOT NULL,
                    parent_span_id TEXT,
                    name TEXT NOT NULL,
                    attributes JSON,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    thread_id TEXT,
                    PRIMARY KEY (trace_id, span_id)
                )
            """)
            
            # Create indexes for efficient queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_thread 
                ON checkpoints(thread_id, created_at)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_traces_thread 
                ON traces(thread_id, start_time)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_traces_parent 
                ON traces(parent_span_id)
            """)
            
            await db.commit()
        
        self._initialized = True
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[aiosqlite.Connection]:
        """Get a database connection with proper initialization."""
        if not self._initialized:
            await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Ensure WAL mode is enabled
            await db.execute("PRAGMA journal_mode=WAL;")
            yield db


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None
_db_manager_path: Optional[str] = None


def get_db_manager(db_path: Optional[str] = None) -> DatabaseManager:
    """Get or create the global database manager."""
    global _db_manager, _db_manager_path
    
    # Resolve the actual path to use
    if db_path is None:
        db_path = os.getenv("DATABASE_PATH", "./tracelens.db")
    
    # Convert to absolute path for comparison
    if not os.path.isabs(db_path):
        # If relative, resolve from project root (where .env is)
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent
        resolved_path = str(project_root / db_path)
    else:
        resolved_path = db_path
    
    # Recreate manager if path changed
    if _db_manager is None or _db_manager_path != resolved_path:
        _db_manager = DatabaseManager(resolved_path)
        _db_manager_path = resolved_path
        _db_manager._initialized = False  # Force re-initialization

    return _db_manager


def reset_db_manager():
    """Reset the global database manager. For testing only."""
    global _db_manager, _db_manager_path
    _db_manager = None
    _db_manager_path = None
