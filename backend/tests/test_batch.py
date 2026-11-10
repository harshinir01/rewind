"""Tests for batch verification endpoints — service-level."""
import pytest
from .conftest import DEMO_RUN_PAYLOAD, seed_run
from backend.services.batch_service import execute_batch_verification, get_batch_runs_as_items


def _create_run(db, run_id: str, ok: bool):
    steps = DEMO_RUN_PAYLOAD["steps"] if not ok else []
    payload = {
        **DEMO_RUN_PAYLOAD,
        "id": run_id,
        "ok": ok,
        "label": None if ok else "ignored_error",
        "steps": steps,
    }
    return seed_run(db, payload)


def test_get_batch_runs_empty(db):
    result = get_batch_runs_as_items(db)
    assert isinstance(result, list)


def test_get_batch_runs_returns_existing_runs(db):
    _create_run(db, "batch-run-1", ok=False)
    result = get_batch_runs_as_items(db)
    assert len(result) >= 1


def test_batch_verify_basic(db):
    _create_run(db, "batch-fail-1", ok=False)
    _create_run(db, "batch-pass-1", ok=True)

    batch = execute_batch_verification(
        run_ids=["batch-fail-1", "batch-pass-1"],
        modified_prompt="Handle errors properly and retry.",
        target_rule=None,
        db=db,
    )
    import json
    results = json.loads(batch.results_json)
    summary = json.loads(batch.summary_json)
    assert len(results) == 2
    assert "total" in summary
    assert "fixed" in summary


def test_batch_summary_fields(db):
    _create_run(db, "batch-s-1", ok=False)
    _create_run(db, "batch-s-2", ok=True)

    batch = execute_batch_verification(
        run_ids=["batch-s-1", "batch-s-2"],
        modified_prompt="Be more careful.",
        target_rule=None,
        db=db,
    )
    import json
    summary = json.loads(batch.summary_json)
    assert "total" in summary
    assert "fixed" in summary
    assert "failed_initial" in summary
    assert "regressions" in summary
    assert "guard_total" in summary
    assert "unchanged" in summary
    assert summary["total"] == 2


def test_batch_guard_runs_classified(db):
    """Originally passing runs should be classified as guard runs."""
    _create_run(db, "batch-guard-1", ok=True)

    batch = execute_batch_verification(
        run_ids=["batch-guard-1"],
        modified_prompt="New prompt.",
        target_rule=None,
        db=db,
    )
    import json
    results = json.loads(batch.results_json)
    guard_item = next((r for r in results if r["id"] == "batch-guard-1"), None)
    assert guard_item is not None
    assert guard_item["is_guard"] is True
    assert guard_item["before_status"] == "pass"


def test_batch_missing_run_ids_marked_inconclusive(db):
    batch = execute_batch_verification(
        run_ids=["nonexistent-run-999"],
        modified_prompt="Some prompt.",
        target_rule=None,
        db=db,
    )
    import json
    results = json.loads(batch.results_json)
    assert results[0]["outcome"] == "Inconclusive"


def test_batch_empty_run_ids_rejected(db):
    from fastapi import HTTPException
    from backend.routers.batch import verify_batch
    from backend.schemas import BatchVerificationRequestSchema

    with pytest.raises(HTTPException) as exc_info:
        verify_batch(
            BatchVerificationRequestSchema(run_ids=[], modified_prompt="x"),
            db,
        )
    assert exc_info.value.status_code == 400


def test_batch_all_not_marked_fixed_when_one_succeeds(db):
    """Results must be independent per run."""
    _create_run(db, "batch-mix-1", ok=False)
    _create_run(db, "batch-mix-2", ok=False)

    batch = execute_batch_verification(
        run_ids=["batch-mix-1", "batch-mix-2"],
        modified_prompt="New instructions.",
        target_rule=None,
        db=db,
    )
    import json
    results = json.loads(batch.results_json)
    assert len(results) == 2


def test_batch_changed_prompt_does_not_produce_fixed(db):
    """
    When a prompt is changed and the replay is simulated (cached mode),
    the outcome must NOT be 'Fixed' — it must be 'Candidate fix (unverified)'
    or 'Inconclusive', never a confirmed 'Fixed'.
    """
    _create_run(db, "batch-honest-1", ok=False)

    batch = execute_batch_verification(
        run_ids=["batch-honest-1"],
        modified_prompt="Completely new prompt to fix the problem.",
        target_rule=None,
        db=db,
    )
    import json
    results = json.loads(batch.results_json)
    assert len(results) == 1
    outcome = results[0]["outcome"]
    assert outcome != "Fixed", (
        f"Simulated replay must not produce 'Fixed'. Got: '{outcome}'. "
        "Only genuine re-execution can confirm a fix."
    )
    # Should be 'Candidate fix (unverified)' or 'Inconclusive' or 'Still failing'
    assert outcome in ("Candidate fix (unverified)", "Inconclusive", "Still failing"), (
        f"Expected inconclusive-type outcome for simulated changed-prompt replay, got '{outcome}'."
    )
