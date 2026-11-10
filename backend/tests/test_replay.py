"""Tests for replay endpoints — service-level."""
import pytest
from .conftest import DEMO_RUN_PAYLOAD, seed_run


REPLAY_REQUEST = {
    "prompt": "If a tool returns an error, retry with corrected arguments.",
    "start_step": 2,
    "replay_mode": "cached",
}


def _do_replay(db, run_id="test-run-001", **kwargs):
    """Execute replay using the service directly."""
    from backend import models
    from backend.services.replay_service import execute_replay
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    req = {**REPLAY_REQUEST, **kwargs}
    return execute_replay(
        run=run,
        modified_prompt=req["prompt"],
        start_step=req["start_step"],
        replay_mode=req.get("replay_mode", "cached"),
        db=db,
    )


def test_replay_cached_mode(db):
    import json
    seed_run(db)
    replay = _do_replay(db)
    # With a changed prompt, honest replay returns 'inconclusive'; with same
    # prompt it returns 'ok' or 'error'. All three are valid statuses.
    assert replay.status in ("ok", "error", "inconclusive")
    assert replay.answer_before is not None
    assert replay.answer_after is not None
    steps = json.loads(replay.steps_json)
    assert isinstance(steps, list)
    assert len(steps) == 3


def test_replay_contains_correct_stats_fields(db):
    seed_run(db)
    replay = _do_replay(db)
    assert hasattr(replay, "full_tokens")
    assert hasattr(replay, "replay_tokens")
    assert hasattr(replay, "tokens_saved")
    assert hasattr(replay, "tokens_saved_percent")
    assert hasattr(replay, "full_duration_ms")
    assert hasattr(replay, "replay_duration_ms")
    assert hasattr(replay, "duration_saved_ms")


def test_replay_steps_have_execution_mode(db):
    import json
    seed_run(db)
    replay = _do_replay(db)
    steps = json.loads(replay.steps_json)
    for step in steps:
        assert "execution_mode" in step
        assert step["execution_mode"] in ("reused", "re-run", "simulated")


def test_replay_steps_before_start_are_reused(db):
    import json
    seed_run(db)
    # start_step=2 means step 1 should be reused
    replay = _do_replay(db, start_step=2)
    steps = json.loads(replay.steps_json)
    step_1 = next((s for s in steps if s["step_number"] == 1), None)
    if step_1:
        assert step_1["execution_mode"] == "reused"


def test_replay_isolated_mode(db):
    seed_run(db)
    replay = _do_replay(db, replay_mode="isolated")
    assert replay is not None
    # Isolated mode with a changed prompt returns 'inconclusive' (honest — cannot verify repair)
    assert replay.status in ("ok", "error", "inconclusive")


def test_replay_live_mode_rejected(db):
    seed_run(db)
    from backend.services.replay_service import execute_replay
    from backend import models
    run = db.query(models.AgentRun).filter(models.AgentRun.id == "test-run-001").first()
    with pytest.raises(ValueError) as exc_info:
        execute_replay(run=run, modified_prompt="x", start_step=1, replay_mode="live", db=db)
    assert "live" in str(exc_info.value).lower() or "safety" in str(exc_info.value).lower()


def test_replay_nonexistent_run(db):
    """Service expects a valid run object, not an ID."""
    # Test the router-level 404
    from fastapi import HTTPException
    from backend.routers.replay import replay_run
    from backend.schemas import ReplayRequestSchema
    with pytest.raises(HTTPException) as exc_info:
        replay_run("no-such-run", ReplayRequestSchema(**REPLAY_REQUEST), db)
    assert exc_info.value.status_code == 404


def test_replay_invalid_start_step(db):
    seed_run(db)
    from backend import models
    from backend.services.replay_service import execute_replay
    run = db.query(models.AgentRun).filter(models.AgentRun.id == "test-run-001").first()
    with pytest.raises(ValueError):
        execute_replay(run=run, modified_prompt="x", start_step=999, replay_mode="cached", db=db)


def test_replay_tokens_saved_non_negative(db):
    seed_run(db)
    replay = _do_replay(db)
    assert replay.tokens_saved >= 0
    assert replay.duration_saved_ms >= 0


def test_replay_persisted(db):
    """Replay is persisted — a second replay of the same run should work fine."""
    seed_run(db)
    r1 = _do_replay(db)
    r2 = _do_replay(db)
    assert r1 is not None
    assert r2 is not None


def test_replay_changed_prompt_returns_inconclusive(db):
    """
    When the prompt is changed and replay is simulated,
    status must be 'inconclusive' — never 'ok' (which would falsely imply a verified fix).
    """
    seed_run(db)
    from backend import models
    from backend.services.replay_service import execute_replay
    run = db.query(models.AgentRun).filter(models.AgentRun.id == "test-run-001").first()
    # Use a prompt that differs from the original ("You are a test agent.")
    replay = execute_replay(
        run=run,
        modified_prompt="Completely different prompt to fix the agent.",
        start_step=2,
        replay_mode="cached",
        db=db,
    )
    # With a changed prompt, we cannot verify repair — must be inconclusive
    assert replay.status == "inconclusive", (
        f"Expected 'inconclusive' for simulated changed-prompt replay, got '{replay.status}'. "
        "Replay must not falsely claim success without genuine re-execution."
    )


def test_replay_unchanged_prompt_returns_ok_or_error(db):
    """
    When the prompt is unchanged, replay reproduces the original execution.
    Status should be 'ok' (no failures in replayed portion) or 'error' (failures exist).
    """
    seed_run(db)
    from backend import models
    from backend.services.replay_service import execute_replay
    run = db.query(models.AgentRun).filter(models.AgentRun.id == "test-run-001").first()
    # Use the SAME prompt as the original run
    original_prompt = run.prompt or ""
    replay = execute_replay(
        run=run,
        modified_prompt=original_prompt,
        start_step=1,
        replay_mode="cached",
        db=db,
    )
    assert replay.status in ("ok", "error"), (
        f"Unchanged-prompt replay should be 'ok' or 'error', got '{replay.status}'."
    )
    assert replay.status != "inconclusive", (
        "An unchanged-prompt replay should not be inconclusive."
    )
