"""
Replay router for Rewind backend.
"""
from __future__ import annotations
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models
from backend.schemas import ReplayRequestSchema
from backend.services.replay_service import execute_replay, STATUS_INCONCLUSIVE

router = APIRouter(prefix="/api/runs", tags=["Replay"])

# Verification notes by status — surfaced to the frontend
_VERIFICATION_NOTE = {
    "ok": (
        "CACHED REPLAY: Steps were replayed using the original cached outputs. "
        "No prompt change was made — this confirms the original outcome only."
    ),
    "error": (
        "CACHED REPLAY: Failures were detected in the replayed portion of the trace. "
        "The issue is likely NOT resolved by this prompt change."
    ),
    "inconclusive": (
        "SIMULATED REPLAY: The prompt was changed, but no genuine agent re-execution "
        "occurred. Cached step outputs were reused. This result cannot confirm whether "
        "the fix works. Run the agent manually with the updated prompt to verify."
    ),
}


@router.post("/{run_id}/replay")
def replay_run(run_id: str, req: ReplayRequestSchema, db: Session = Depends(get_db)):
    """
    Execute a safe cached/isolated replay of a run with a modified prompt.
    Never performs real external side effects.

    Status values in the response:
      'ok'           — no failures in replayed portion (prompt unchanged)
      'error'        — failures detected in replayed portion
      'inconclusive' — prompt was changed; result is simulated, not verified
    """
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    replay_mode = req.replay_mode or "cached"

    if replay_mode == "live":
        raise HTTPException(
            status_code=400,
            detail=(
                "Live replay is disabled for safety. Live mode would perform real external side effects "
                "(emails, API calls, database writes). Use 'cached' or 'isolated' mode instead."
            ),
        )

    if not run.steps:
        raise HTTPException(
            status_code=422,
            detail=f"Run '{run_id}' has no recorded execution steps. Cannot replay an empty trace.",
        )

    try:
        replay = execute_replay(
            run=run,
            modified_prompt=req.prompt,
            start_step=req.start_step,
            replay_mode=replay_mode,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")

    try:
        replay_steps = json.loads(replay.steps_json or "[]")
    except (json.JSONDecodeError, TypeError):
        replay_steps = []

    verification_note = _VERIFICATION_NOTE.get(
        replay.status,
        "Replay completed. See status for details.",
    )

    return {
        "run_id": run_id,
        "status": replay.status,
        "answer_before": replay.answer_before,
        "answer_after": replay.answer_after,
        "verification_note": verification_note,
        "steps": replay_steps,
        "stats": {
            "full_tokens": replay.full_tokens,
            "replay_tokens": replay.replay_tokens,
            "tokens_saved": replay.tokens_saved,
            "tokens_saved_percent": replay.tokens_saved_percent,
            "full_duration_ms": replay.full_duration_ms,
            "replay_duration_ms": replay.replay_duration_ms,
            "duration_saved_ms": replay.duration_saved_ms,
        },
    }
