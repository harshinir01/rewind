"""Tests for analytics endpoints — service-level."""
import pytest
from .conftest import DEMO_RUN_PAYLOAD, seed_run
from backend.services.analytics_service import get_analytics_metrics


def _make_run(db, run_id: str, ok: bool, cost: float = 0.01, label: str = None):
    payload = {
        **DEMO_RUN_PAYLOAD,
        "id": run_id,
        "ok": ok,
        "cost": cost,
        "label": label,
        "steps": [],
    }
    return seed_run(db, payload)


def test_analytics_empty_database(db):
    result = get_analytics_metrics(db)
    assert result["total_runs"] == 0
    assert result["successful_runs"] == 0
    assert result["failed_runs"] == 0
    assert result["success_rate"] == 0.0
    assert result["total_spend"] == 0.0
    assert result["most_common_mistake"] is None


def test_analytics_counts_runs(db):
    _make_run(db, "a-run-1", ok=True)
    _make_run(db, "a-run-2", ok=False)
    result = get_analytics_metrics(db)
    assert result["total_runs"] == 2
    assert result["successful_runs"] == 1
    assert result["failed_runs"] == 1


def test_analytics_success_rate(db):
    _make_run(db, "sr-1", ok=True)
    _make_run(db, "sr-2", ok=True)
    _make_run(db, "sr-3", ok=False)
    result = get_analytics_metrics(db)
    assert abs(result["success_rate"] - 66.7) < 0.5


def test_analytics_total_spend(db):
    _make_run(db, "ts-1", ok=True, cost=0.010)
    _make_run(db, "ts-2", ok=False, cost=0.025)
    result = get_analytics_metrics(db)
    assert abs(result["total_spend"] - 0.035) < 0.001


def test_analytics_most_common_mistake(db):
    _make_run(db, "mc-1", ok=False, label="ignored_error")
    _make_run(db, "mc-2", ok=False, label="ignored_error")
    _make_run(db, "mc-3", ok=False, label="infinite_loop")
    result = get_analytics_metrics(db)
    assert result["most_common_mistake"] == "ignored_error"
    assert result["most_common_count"] == 2


def test_analytics_response_schema(db):
    result = get_analytics_metrics(db)
    required_fields = [
        "total_runs", "successful_runs", "failed_runs",
        "success_rate", "total_spend",
    ]
    for field in required_fields:
        assert field in result, f"Missing field: {field}"
