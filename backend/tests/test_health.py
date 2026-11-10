"""Tests for health endpoints — using the router functions directly.

NOTE: TestClient + anyio hangs under Python 3.14 in some environments.
      These tests call the router functions directly to avoid the issue.
"""
import pytest
from backend import models


def _get_db_count(db) -> int:
    return db.query(models.AgentRun).count()


def test_health_root_direct(db):
    """Test the health check logic directly without HTTP client."""
    from backend.routers.health import health_check
    result = health_check(db=db)
    assert result["status"] == "ok"
    assert "service" in result
    assert "timestamp" in result
    assert "database_records" in result
    assert isinstance(result["database_records"], int)


def test_health_api_direct(db):
    """Test /api/health response structure."""
    from backend.routers.health import health_check
    result = health_check(db=db)
    assert result["status"] == "ok"
    assert "version" in result


def test_health_returns_zero_records_on_empty_db(db):
    """Health check on empty database returns 0 records."""
    from backend.routers.health import health_check
    result = health_check(db=db)
    assert result["database_records"] == 0


def test_health_returns_correct_record_count(db):
    """Health check reflects actual record count."""
    from backend.routers.health import health_check
    from .conftest import seed_run
    seed_run(db)
    result = health_check(db=db)
    assert result["database_records"] == 1
