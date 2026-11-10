"""Tests for diagnosis endpoints — service-level."""
import pytest
from backend import models
from .conftest import DEMO_RUN_PAYLOAD, seed_run


def test_diagnosis_not_found_before_trigger(db):
    from fastapi import HTTPException
    from backend.routers.diagnosis import get_diagnosis
    seed_run(db)
    with pytest.raises(HTTPException) as exc_info:
        get_diagnosis("test-run-001", db)
    assert exc_info.value.status_code == 404


def test_trigger_diagnosis(db):
    from backend.routers.diagnosis import trigger_diagnosis
    seed_run(db)
    result = trigger_diagnosis("test-run-001", db)
    assert "failure_category" in result
    assert "reason" in result
    assert "evidence" in result
    assert "fired_detectors" in result
    assert "judge_verdict" in result
    assert result["failure_category"] in [
        "ignored_error", "infinite_loop", "goal_drift",
        "bad_arguments", "wrong_tool", "lost_context"
    ]


def test_get_diagnosis_after_trigger(db):
    from backend.routers.diagnosis import trigger_diagnosis, get_diagnosis
    seed_run(db)
    trigger_diagnosis("test-run-001", db)
    result = get_diagnosis("test-run-001", db)
    assert "failure_category" in result


def test_diagnose_idempotent(db):
    """Calling diagnose twice returns the same result (cached)."""
    from backend.routers.diagnosis import trigger_diagnosis
    seed_run(db)
    r1 = trigger_diagnosis("test-run-001", db)
    r2 = trigger_diagnosis("test-run-001", db)
    assert r1["failure_category"] == r2["failure_category"]


def test_diagnose_nonexistent_run(db):
    from fastapi import HTTPException
    from backend.routers.diagnosis import trigger_diagnosis
    with pytest.raises(HTTPException) as exc_info:
        trigger_diagnosis("no-such-run", db)
    assert exc_info.value.status_code == 404


def test_diagnose_run_without_steps(db):
    """A run with no steps cannot be diagnosed."""
    from fastapi import HTTPException
    from backend.routers.diagnosis import trigger_diagnosis
    seed_run(db, {**DEMO_RUN_PAYLOAD, "id": "empty-run", "steps": []})
    with pytest.raises(HTTPException) as exc_info:
        trigger_diagnosis("empty-run", db)
    assert exc_info.value.status_code == 422


def test_diagnosis_evidence_references_real_steps(db):
    """Evidence must reference steps from the actual trace."""
    from backend.routers.diagnosis import trigger_diagnosis
    seed_run(db)
    result = trigger_diagnosis("test-run-001", db)
    # Relevant step must be a valid step number (1-3)
    if result.get("relevant_step") is not None:
        assert 1 <= result["relevant_step"] <= 3  # 3 steps in DEMO_RUN_PAYLOAD
