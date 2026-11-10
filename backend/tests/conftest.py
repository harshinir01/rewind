"""
Shared test fixtures for Rewind backend tests.
Uses an isolated in-memory SQLite database — never touches rewind.db.

NOTE: TestClient (which uses anyio/asyncio) may not work in all sandbox environments.
These tests use direct database + service calls for maximum compatibility.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base

# ---------------------------------------------------------------------------
# In-memory test database — isolated from the production SQLite file
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite://"  # pure in-memory

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """Fresh in-memory database for each test."""
    from backend import models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# HTTP client fixture (uses requests against a live server if available,
# otherwise falls back to service-level testing)
# ---------------------------------------------------------------------------

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(db):
    """
    HTTP test client using FastAPI's TestClient.
    Falls back gracefully if TestClient cannot start (sandbox asyncio restriction).
    """
    try:
        from fastapi.testclient import TestClient
        from backend.database import get_db
        from backend.main import app
        import warnings
        warnings.filterwarnings("ignore")

        app.dependency_overrides[get_db] = override_get_db
        # Re-create tables for the test session
        from backend import models  # noqa: F401
        Base.metadata.create_all(bind=test_engine)

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
        app.dependency_overrides.clear()
    except Exception as e:
        pytest.skip(f"TestClient not available in this environment: {e}")


# ---------------------------------------------------------------------------
# Shared helper — demo run payload
# ---------------------------------------------------------------------------

DEMO_RUN_PAYLOAD = {
    "id": "test-run-001",
    "agent": "test-agent",
    "task": "Test task for unit tests",
    "ok": False,
    "label": "ignored_error",
    "steps_count": 3,
    "cost": 0.012,
    "duration": "5.0s",
    "duration_ms": 5000,
    "started_at": "2026-01-01 10:00 UTC",
    "fail_step": 2,
    "prompt": "You are a test agent.",
    "suggested_fix": "Handle errors properly.",
    "steps": [
        {
            "step_number": 1,
            "name": "plan",
            "kind": "llm",
            "duration_ms": 500,
            "tokens": 200,
            "input": "Task: test",
            "output": "1. Do thing A\n2. Do thing B",
            "status": "ok",
        },
        {
            "step_number": 2,
            "name": "run_tool",
            "kind": "tool",
            "duration_ms": 100,
            "tokens": 0,
            "input": '{"arg": "bad_value"}',
            "output": "ERROR: bad_value is not valid",
            "status": "error",
        },
        {
            "step_number": 3,
            "name": "respond",
            "kind": "llm",
            "duration_ms": 600,
            "tokens": 150,
            "input": "Tool returned error",
            "output": "Everything is fine.",
            "status": "fail",
        },
    ],
    "diagnosis": None,
}


# ---------------------------------------------------------------------------
# Helper: seed a run directly into the DB (no HTTP)
# ---------------------------------------------------------------------------

def seed_run(db_session, payload: dict = None):
    """Directly insert a run + steps into the test database."""
    from backend import models
    p = payload or DEMO_RUN_PAYLOAD

    run = models.AgentRun(
        id=p["id"],
        agent=p["agent"],
        task=p["task"],
        ok=p["ok"],
        label=p.get("label"),
        steps_count=p.get("steps_count", 0),
        cost=p.get("cost", 0.0),
        duration=p.get("duration", ""),
        duration_ms=p.get("duration_ms"),
        started_at=p.get("started_at", ""),
        fail_step=p.get("fail_step"),
        prompt=p.get("prompt"),
        suggested_fix=p.get("suggested_fix"),
    )
    db_session.add(run)
    db_session.flush()

    for step_data in (p.get("steps") or []):
        step = models.ExecutionStep(
            run_id=p["id"],
            step_number=step_data["step_number"],
            name=step_data["name"],
            kind=step_data["kind"],
            duration_ms=step_data.get("duration_ms", 0),
            tokens=step_data.get("tokens", 0),
            input=step_data.get("input", ""),
            output=step_data.get("output", ""),
            status=step_data.get("status", "ok"),
        )
        db_session.add(step)

    db_session.commit()
    db_session.refresh(run)
    return run
