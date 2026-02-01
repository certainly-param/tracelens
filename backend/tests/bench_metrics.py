"""
Benchmarks for TraceLens performance and scale metrics.

Run: pytest tests/bench_metrics.py -v --benchmark-only
     pytest tests/bench_metrics.py -v --benchmark-only --benchmark-save=run
"""
import asyncio
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_backend))

from src.storage.db_manager import get_db_manager, reset_db_manager
from src.storage.sqlite_checkpointer import SqliteCheckpointer


def _db_path():
    d = Path(tempfile.gettempdir()) / "tracelens_bench"
    d.mkdir(parents=True, exist_ok=True)
    return str(d / "bench.db")


def _clean(db_path: str):
    reset_db_manager()
    for p in [db_path, db_path + "-shm", db_path + "-wal"]:
        if os.path.exists(p):
            try:
                os.unlink(p)
            except Exception:
                pass


@pytest.fixture(scope="module")
def bench_db_path():
    p = _db_path()
    yield p
    _clean(p)


async def _seed_50_workflows(db_path: str):
    _clean(db_path)
    reset_db_manager()
    m = get_db_manager(db_path)
    await m.initialize()
    async with m.get_connection() as db:
        for tid in range(50):
            thread = f"workflow-{tid}"
            for i in range(20):
                cp_id = f"cp-{tid}-{i}"
                parent = f"cp-{tid}-{i-1}" if i else None
                data = json.dumps({"step_count": i, "query": "q"}).encode()
                meta = json.dumps({"step": i})
                await db.execute(
                    "INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint_ns, checkpoint_data, parent_checkpoint_id, metadata, created_at) VALUES (?,?,?,?,?,?,?)",
                    (thread, cp_id, "", data, parent, meta, datetime.now().isoformat()),
                )
            await db.execute(
                "INSERT INTO traces (trace_id, span_id, parent_span_id, name, attributes, start_time, end_time, thread_id) VALUES (?,?,?,?,?,?,?,?)",
                (f"tr-{tid}", f"sp-{tid}", None, "agent.node.n", "{}", datetime.now().isoformat(), datetime.now().isoformat(), thread),
            )
        await db.commit()


# --- 1. Checkpoint storage: 1000+ checkpoints ---


@pytest.mark.benchmark(group="checkpoint_storage", min_rounds=1, warmup=False)
def test_bench_checkpoint_insert_1000(benchmark, bench_db_path):
    """Insert 1000 checkpoints; report total time and per-checkpoint ms."""

    def run():
        async def _run():
            _clean(bench_db_path)
            reset_db_manager()
            cp = SqliteCheckpointer(bench_db_path)
            config = {"configurable": {"thread_id": "bench-thread"}}
            for i in range(1000):
                await cp.put(
                    config,
                    {
                        "id": f"ck-{i}",
                        "parent_checkpoint_id": f"ck-{i-1}" if i else None,
                        "channel_values": {"step_count": i, "query": "q", "results": ["r"] * 10},
                        "metadata": {},
                    },
                    {"step": i},
                    {},
                )

        asyncio.run(_run())

    benchmark(run)
    s = getattr(benchmark, "stats", None)
    mean_s = getattr(s, "mean", None) if s is not None else None
    if mean_s is not None:
        benchmark.extra_info["total_checkpoints"] = 1000
        benchmark.extra_info["total_seconds"] = round(float(mean_s), 4)
        benchmark.extra_info["ms_per_checkpoint"] = round(mean_s * 1000 / 1000, 4)
        benchmark.extra_info["checkpoints_per_second"] = round(1000 / mean_s, 2)


# --- 2 & 5. Checkpoint lookup / time-travel ---


@pytest.fixture(scope="module")
def lookup_cp_and_config(bench_db_path):
    """Seed DB and return (cp, config) for lookup benchmark."""
    _clean(bench_db_path)
    reset_db_manager()
    cp = SqliteCheckpointer(bench_db_path)
    config = {"configurable": {"thread_id": "lookup-thread"}}

    async def seed():
        for i in range(500):
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

    asyncio.run(seed())
    return cp, config


@pytest.mark.benchmark(group="checkpoint_lookup", min_rounds=100)
def test_bench_checkpoint_lookup(benchmark, lookup_cp_and_config):
    """Single checkpoint fetch by (thread_id, checkpoint_id)."""
    cp, config = lookup_cp_and_config

    def fetch():
        async def _fetch():
            return await cp.aget_tuple({
                **config,
                "configurable": {**config["configurable"], "checkpoint_id": "ck-250"},
            })

        return asyncio.run(_fetch())

    benchmark(fetch)
    benchmark.extra_info["description"] = "time-travel checkpoint fetch"


# --- 3. State size: 10KB, 100KB, 1MB, 10MB ---


def _make_state(size_kb: int) -> dict:
    base = {"step_count": 0, "query": "x", "results": []}
    pad = "x" * max(0, 1024 * size_kb - 200)
    base["payload"] = pad
    return base


@pytest.fixture(scope="module")
def app_client(bench_db_path):
    os.environ["DATABASE_PATH"] = bench_db_path
    from fastapi.testclient import TestClient
    from src.api.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def seeded_app(bench_db_path, app_client):
    """App client with 50 workflows seeded."""
    asyncio.run(_seed_50_workflows(bench_db_path))
    return app_client


@pytest.mark.parametrize("size_kb", [10, 100, 1024, 10 * 1024])
@pytest.mark.benchmark(group="state_size", min_rounds=5)
def test_bench_state_size_roundtrip(benchmark, bench_db_path, size_kb):
    """Serialize, store, retrieve state of given size (KB)."""

    def run():
        async def _run():
            _clean(bench_db_path)
            reset_db_manager()
            cp = SqliteCheckpointer(bench_db_path)
            config = {"configurable": {"thread_id": "size-thread"}}
            state = _make_state(size_kb)
            await cp.put(
                config,
                {"id": "ck-0", "parent_checkpoint_id": None, "channel_values": state, "metadata": {}},
                {},
                {},
            )
            out = await cp.aget_tuple({**config, "configurable": {**config["configurable"], "checkpoint_id": "ck-0"}})
            assert out is not None
            assert len(out.checkpoint["channel_values"].get("payload", "")) == len(state["payload"])

        asyncio.run(_run())

    benchmark(run)
    benchmark.extra_info["state_size_kb"] = size_kb


# --- 4. Concurrent workflows: GET /runs and /graph with 50 workflows ---


@pytest.mark.benchmark(group="concurrent_workflows", min_rounds=20)
def test_bench_api_runs_50_workflows(benchmark, seeded_app):
    """GET /api/runs with 50 workflows."""
    def run():
        r = seeded_app.get("/api/runs")
        assert r.status_code == 200
        assert r.json()["total"] >= 50

    benchmark(run)


@pytest.mark.benchmark(group="concurrent_workflows", min_rounds=20)
def test_bench_api_graph_latency(benchmark, seeded_app):
    """GET /api/runs/{id}/graph latency."""
    def run():
        r = seeded_app.get("/api/runs/workflow-25/graph")
        assert r.status_code == 200

    benchmark(run)


# --- 6. API /graph response time (update latency) ---


@pytest.mark.benchmark(group="api_latency", min_rounds=20)
def test_bench_api_graph_response_time(benchmark, seeded_app):
    """GET /graph response time (API update latency)."""
    def run():
        r = seeded_app.get("/api/runs/workflow-0/graph")
        assert r.status_code == 200

    benchmark(run)


# --- 7. Telemetry overhead: with vs without OTel ---


def _mock_workload_with_otel(iterations: int, thread_id: str = "bench"):
    """Run mock node+tool spans using real instrumentation."""
    from src.instrumentation import instrument_node_execution, instrument_tool_call
    for i in range(iterations):
        with instrument_node_execution("search", thread_id) as node_span:
            node_span.set_state_snapshot({"step_count": i, "results": [], "summary": ""})
            with instrument_tool_call("web_search", thread_id) as tool_span:
                tool_span.set_tool_input({"query": "q"})
                tool_span.set_tool_output("result")


def _mock_workload_without_otel(iterations: int):
    """Same logical workload, no spans."""
    for i in range(iterations):
        state = {"step_count": i, "results": [], "summary": ""}
        _ = state.get("step_count")
        inp = {"query": "q"}
        out = "result"
        _ = inp, out


@pytest.fixture(scope="module")
def otel_bench_db(bench_db_path):
    """Ensure OTel uses benchmark DB for overhead tests."""
    os.environ["DATABASE_PATH"] = bench_db_path
    os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    os.environ.pop("TRACELENS_OTEL_VERBOSE", None)  # no span export logging during benchmarks
    from src.instrumentation import setup_opentelemetry
    setup_opentelemetry()
    yield bench_db_path


@pytest.mark.benchmark(group="telemetry_overhead", min_rounds=10)
def test_bench_telemetry_with(benchmark, otel_bench_db):
    """Mock workflow with OTel instrumentation (100 iterations)."""
    def run():
        _mock_workload_with_otel(100)

    benchmark(run)
    benchmark.extra_info["iterations"] = 100
    benchmark.extra_info["mode"] = "with_otel"


@pytest.mark.benchmark(group="telemetry_overhead", min_rounds=10)
def test_bench_telemetry_without(benchmark):
    """Mock workflow without OTel (100 iterations)."""
    def run():
        _mock_workload_without_otel(100)

    benchmark(run)
    benchmark.extra_info["iterations"] = 100
    benchmark.extra_info["mode"] = "without_otel"
