"""Tests for FastAPI endpoints."""
import asyncio
import json
from datetime import datetime

import pytest


async def _seed_db(db_path: str):
    from src.storage.db_manager import get_db_manager, reset_db_manager
    reset_db_manager()
    m = get_db_manager(db_path)
    await m.initialize()
    async with m.get_connection() as db:
        thread = "seed-thread-1"
        for i in range(3):
            cp_id = f"cp-{i}"
            parent = f"cp-{i-1}" if i else None
            data = json.dumps({"step_count": i, "query": "test"}).encode()
            meta = json.dumps({"step": i})
            await db.execute(
                "INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, parent_checkpoint_id, metadata, created_at) VALUES (?,?,?,?,?,?,?)",
                (thread, cp_id, "", data, parent, meta, datetime.now().isoformat()),
            )
        await db.execute(
            "INSERT INTO traces (trace_id, span_id, parent_span_id, name, attributes, start_time, end_time, thread_id) VALUES (?,?,?,?,?,?,?,?)",
            ("tr1", "sp1", None, "agent.node.search", "{}", datetime.now().isoformat(), datetime.now().isoformat(), thread),
        )
        await db.commit()


@pytest.fixture
def seeded_client(client, db_path, clean_db):
    """Client with DB seeded with one run (checkpoints + traces). clean_db wipes DB first."""
    asyncio.run(_seed_db(db_path))
    return client


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_list_runs_empty(client, clean_db):
    """Expect 0 runs. clean_db ensures DB is empty (no leftover from other tests)."""
    r = client.get("/api/runs")
    assert r.status_code == 200
    data = r.json()
    assert "runs" in data
    assert data["total"] == 0


def test_list_runs_seeded(seeded_client):
    r = seeded_client.get("/api/runs")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any(run["thread_id"] == "seed-thread-1" for run in data["runs"])


def test_get_graph_missing(seeded_client):
    r = seeded_client.get("/api/runs/nonexistent-thread/graph")
    assert r.status_code == 200
    data = r.json()
    assert data["metadata"]["total_checkpoints"] == 0
    assert len(data["nodes"]) == 0


def test_get_graph_seeded(seeded_client):
    r = seeded_client.get("/api/runs/seed-thread-1/graph")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "edges" in data
    assert "metadata" in data


def test_list_checkpoints(seeded_client):
    r = seeded_client.get("/api/runs/seed-thread-1/checkpoints")
    assert r.status_code == 200
    data = r.json()
    assert data["thread_id"] == "seed-thread-1"
    assert data["total"] >= 1


def test_get_checkpoint(seeded_client):
    r = seeded_client.get("/api/runs/seed-thread-1/checkpoints/cp-1")
    assert r.status_code == 200
    data = r.json()
    assert data["checkpoint_id"] == "cp-1"
    assert "state" in data


def test_get_checkpoint_404(seeded_client):
    r = seeded_client.get("/api/runs/seed-thread-1/checkpoints/nonexistent")
    assert r.status_code == 404


def test_timeline(seeded_client):
    r = seeded_client.get("/api/runs/seed-thread-1/timeline")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert data["thread_id"] == "seed-thread-1"


def test_checkpoint_diff(seeded_client):
    r = seeded_client.get("/api/runs/seed-thread-1/checkpoints/cp-0/diff?compare_to=cp-1")
    assert r.status_code == 200
    data = r.json()
    assert "checkpoint_id_1" in data
    assert "checkpoint_id_2" in data
    assert "modified" in data
