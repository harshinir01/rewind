"""Tests for /api/runs — service-level, no HTTP client required."""
import pytest
from backend import models
from backend.services.analytics_service import get_analytics_metrics
from .conftest import DEMO_RUN_PAYLOAD, seed_run


# ============================================================================
# Run CRUD — using the router functions directly with a real DB session
# ============================================================================

def _create_run_via_router(db, payload=None):
    """Call the runs router create function directly."""
    from backend.schemas import CreateRunSchema
    from backend.routers.runs import create_run
    p = payload or DEMO_RUN_PAYLOAD
    schema = CreateRunSchema(**p)
    return create_run(schema, db)


def test_create_run(db):
    result = _create_run_via_router(db)
    assert result["id"] == "test-run-001"
    assert result["agent"] == "test-agent"
    assert result["ok"] is False
    assert len(result["steps"]) == 3


def test_duplicate_run_rejected(db):
    from fastapi import HTTPException
    _create_run_via_router(db)
    with pytest.raises(HTTPException) as exc_info:
        _create_run_via_router(db)
    assert exc_info.value.status_code == 409


def test_list_runs_empty(db):
    from backend.routers.runs import list_runs
    result = list_runs(db=db)
    assert result == []


def test_list_runs_returns_created(db):
    from backend.routers.runs import list_runs
    _create_run_via_router(db)
    result = list_runs(db=db)
    assert len(result) == 1
    assert result[0]["id"] == "test-run-001"


def test_list_runs_filter_failed(db):
    from backend.routers.runs import list_runs
    _create_run_via_router(db)
    result = list_runs(status="failed", db=db)
    assert len(result) == 1


def test_list_runs_filter_passed(db):
    from backend.routers.runs import list_runs
    _create_run_via_router(db)
    result = list_runs(status="passed", db=db)
    assert len(result) == 0


def test_list_runs_search(db):
    from backend.routers.runs import list_runs
    _create_run_via_router(db)
    result = list_runs(search="test-agent", db=db)
    assert len(result) == 1

    result2 = list_runs(search="nonexistent-xyz", db=db)
    assert result2 == []


def test_list_runs_pagination(db):
    from backend.routers.runs import list_runs
    from backend.schemas import CreateRunSchema
    from backend.routers.runs import create_run
    for i in range(3):
        p = {**DEMO_RUN_PAYLOAD, "id": f"run-page-{i}", "steps": [], "diagnosis": None}
        create_run(CreateRunSchema(**p), db)

    page1 = list_runs(limit=2, offset=0, db=db)
    assert len(page1) == 2

    page2 = list_runs(limit=2, offset=2, db=db)
    assert len(page2) == 1


def test_get_run_by_id(db):
    from backend.routers.runs import get_run
    _create_run_via_router(db)
    result = get_run("test-run-001", db)
    assert result["id"] == "test-run-001"
    assert len(result["steps"]) == 3


def test_get_run_not_found(db):
    from fastapi import HTTPException
    from backend.routers.runs import get_run
    with pytest.raises(HTTPException) as exc_info:
        get_run("nonexistent-run-id", db)
    assert exc_info.value.status_code == 404


def test_delete_run(db):
    from fastapi import HTTPException
    from backend.routers.runs import delete_run, get_run
    _create_run_via_router(db)
    result = delete_run("test-run-001", db)
    assert result["success"] is True
    assert result["id"] == "test-run-001"

    with pytest.raises(HTTPException):
        get_run("test-run-001", db)


def test_delete_nonexistent_run(db):
    from fastapi import HTTPException
    from backend.routers.runs import delete_run
    with pytest.raises(HTTPException) as exc_info:
        delete_run("no-such-run", db)
    assert exc_info.value.status_code == 404
