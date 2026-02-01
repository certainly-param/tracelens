"""Pytest configuration and fixtures."""
import os
import tempfile
import sys
from pathlib import Path

import pytest

pytest_plugins = ["pytest_asyncio"]

# Ensure backend/src is on path when running from project root or backend/
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Use a dedicated test DB dir; set before any app/storage imports
TEST_DB_DIR = Path(tempfile.gettempdir()) / "tracelens_tests"
TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
TEST_DB_PATH = str(TEST_DB_DIR / "tracelens_test.db")


def _setup_test_env():
    os.environ["DATABASE_PATH"] = TEST_DB_PATH
    os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
    os.environ["OTEL_CONSOLE_EXPORT"] = "false"
    os.environ.pop("TRACELENS_OTEL_VERBOSE", None)  # keep span export logging off in tests
    os.environ["TRACELENS_REQUIRE_AUTH"] = "false"  # disable auth in tests


# Set env before importing app (conftest loads first)
_setup_test_env()


@pytest.fixture(scope="session")
def db_path():
    """Session-scoped path to test database."""
    return TEST_DB_PATH


@pytest.fixture(scope="session")
def app(db_path):
    """Session-scoped FastAPI app using test DB."""
    os.environ["DATABASE_PATH"] = db_path
    from src.api.main import app as _app
    return _app


@pytest.fixture
def client(app):
    """Per-test HTTP client. Uses same app; DB state may change between tests."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def clean_db(db_path):
    """Remove test DB file so next use gets fresh schema. Use when needed."""
    from src.storage.db_manager import reset_db_manager
    reset_db_manager()
    p = Path(db_path)
    for f in [p, Path(str(p) + "-shm"), Path(str(p) + "-wal")]:
        if f.exists():
            f.unlink(missing_ok=True)
    yield
    reset_db_manager()


@pytest.fixture
def db_manager(db_path, clean_db):
    """Fresh DatabaseManager pointing at test DB."""
    from src.storage.db_manager import get_db_manager, reset_db_manager
    reset_db_manager()
    m = get_db_manager(db_path)
    return m
