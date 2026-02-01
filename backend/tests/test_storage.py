"""Tests for storage layer: DatabaseManager, SqliteCheckpointer."""
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from src.storage.db_manager import get_db_manager, reset_db_manager
from src.storage.sqlite_checkpointer import SqliteCheckpointer

# Project-local temp dir (avoids pytest tmp_path permission issues on some systems)
_STORAGE_TMP = Path(__file__).resolve().parent / ".tmp" / "storage"


@pytest.fixture
def db_path():
    """Unique DB path per test for isolation."""
    _STORAGE_TMP.mkdir(parents=True, exist_ok=True)
    p = _STORAGE_TMP / f"test_{uuid.uuid4().hex[:12]}.db"
    return str(p)


@pytest.fixture
def db(db_path):
    reset_db_manager()
    m = get_db_manager(db_path)
    return m


@pytest.mark.asyncio
async def test_db_manager_init(db):
    await db.initialize()
    async with db.get_connection() as conn:
        async with conn.execute("SELECT 1") as cur:
            row = await cur.fetchone()
            assert row[0] == 1


@pytest.mark.asyncio
async def test_db_manager_checkpoints_table(db):
    await db.initialize()
    async with db.get_connection() as conn:
        await conn.execute(
            "INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, parent_checkpoint_id, metadata, created_at) VALUES (?,?,?,?,?,?,?)",
            ("t1", "cp1", "", b'{"x":1}', None, "{}", datetime.now().isoformat()),
        )
        await conn.commit()
        async with conn.execute("SELECT COUNT(*) FROM checkpoints") as cur:
            n = (await cur.fetchone())[0]
            assert n == 1


@pytest.mark.asyncio
async def test_checkpointer_put_get(db_path):
    reset_db_manager()
    cp = SqliteCheckpointer(db_path)
    config = {"configurable": {"thread_id": "test-thread"}}
    checkpoint = {
        "id": "ck-1",
        "parent_checkpoint_id": None,
        "channel_values": {"query": "hello", "step_count": 1},
        "metadata": {},
    }
    metadata = {"source": "input", "step": 1}

    await cp.put(config, checkpoint, metadata, {})
    out = await cp.aget_tuple({**config, "configurable": {**config["configurable"], "checkpoint_id": "ck-1"}})
    assert out is not None
    assert out.checkpoint["id"] == "ck-1"
    assert out.checkpoint["channel_values"]["query"] == "hello"


@pytest.mark.asyncio
async def test_checkpointer_list(db_path):
    reset_db_manager()
    cp = SqliteCheckpointer(db_path)
    config = {"configurable": {"thread_id": "list-thread"}}
    for i in range(3):
        await cp.put(
            config,
            {
                "id": f"ck-{i}",
                "parent_checkpoint_id": f"ck-{i-1}" if i else None,
                "channel_values": {"step_count": i},
                "metadata": {},
            },
            {"step": i},
            {},
        )

    listed = await cp.list(config, limit=10)
    assert len(listed) == 3
