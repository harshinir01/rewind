"""
Batch verification service for Rewind.
Replays multiple runs and aggregates results.

Honesty policy
--------------
A run is marked 'Fixed' only when:
  1. The original run failed (before_status == 'fail')
  2. The replay returned status 'ok' (no failures in replayed portion)
  3. The prompt was NOT changed (i.e. we're confirming the existing outcome)
     — OR — the replay returned a genuinely verified result.

Because our replay engine returns 'inconclusive' when the prompt is changed
(simulation cannot prove a fix), a changed-prompt replay on a failing run
produces outcome 'Candidate fix (unverified)', not 'Fixed'.

This prevents the system from falsely claiming repairs it cannot verify.
"""
from __future__ import annotations
import json
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend import models
from backend.services.replay_service import execute_replay

logger = logging.getLogger(__name__)


def execute_batch_verification(
    run_ids: List[str],
    modified_prompt: str,
    target_rule: Optional[str],
    db: Session,
) -> models.BatchVerification:
    """
    For each run_id:
    - Load the run from DB
    - Determine before_status (pass/fail based on run.ok)
    - Execute safe replay
    - Determine after_status from replay result
    - Classify outcome honestly

    Guard runs: runs that were originally successful (ok=True)
    Test runs: runs that originally failed (ok=False)

    Outcome values:
      'Fixed'                      — failing run, replay ok, prompt unchanged
      'Candidate fix (unverified)' — failing run, replay inconclusive (simulated)
      'Still failing'              — failing run, replay still errors
      'Unchanged'                  — guard run still passes
      'Regression'                 — guard run now fails after change
      'Inconclusive'               — replay could not complete or run not found
    """
    results = []
    not_found_ids = []

    prompt_changed = modified_prompt.strip() != ""

    for run_id in run_ids:
        run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
        if not run:
            not_found_ids.append(run_id)
            results.append(
                {
                    "id": run_id,
                    "task": "Unknown (run not found)",
                    "is_guard": False,
                    "before_status": "fail",
                    "after_status": "fail",
                    "delta_tokens": 0,
                    "outcome": "Inconclusive",
                    "note": f"Run ID '{run_id}' was not found in the database.",
                }
            )
            continue

        is_guard = run.ok  # Guard = originally successful run
        before_status = "pass" if run.ok else "fail"

        # Determine start_step for replay
        start_step = run.fail_step or 1
        if not run.steps:
            start_step = 1
        else:
            max_step = max(s.step_number for s in run.steps)
            if start_step > max_step:
                start_step = max(1, max_step)

        after_status = "fail"
        delta_tokens = 0
        outcome = "Inconclusive"
        note = ""

        try:
            replay = execute_replay(
                run=run,
                modified_prompt=modified_prompt,
                start_step=start_step,
                replay_mode="cached",
                db=db,
            )

            replay_status = replay.status  # 'ok', 'error', or 'inconclusive'
            after_ok = replay_status == "ok"
            after_status = "pass" if after_ok else "fail"
            delta_tokens = replay.replay_tokens - replay.full_tokens  # negative = savings

            if is_guard:
                # Guard run: should stay passing after any change
                if after_ok or replay_status == "inconclusive":
                    # 'ok' (unchanged prompt) or inconclusive (changed prompt, no failure seen)
                    if replay_status == "inconclusive":
                        outcome = "Unchanged"
                        note = (
                            "Guard run: simulated replay detected no regressions, "
                            "but genuine re-execution is needed to confirm."
                        )
                    else:
                        outcome = "Unchanged"
                        note = "Guard run remained successful after prompt change."
                else:
                    outcome = "Regression"
                    after_status = "fail"
                    note = (
                        "Guard run that previously passed now shows failures in replay. "
                        "Prompt change may have caused a regression."
                    )
            else:
                # Test run (originally failed): did the fix work?
                if replay_status == "ok":
                    # 'ok' with unchanged prompt → outcome unchanged
                    # 'ok' with changed prompt should not happen (we return 'inconclusive')
                    # but handle it defensively
                    if before_status == "fail":
                        outcome = "Fixed"
                        after_status = "pass"
                        note = "Previously failing run now passes with updated prompt."
                    else:
                        outcome = "Unchanged"
                        note = "No change in outcome."
                elif replay_status == "inconclusive":
                    # Simulated replay with changed prompt — cannot confirm fix
                    outcome = "Candidate fix (unverified)"
                    after_status = "fail"  # Cannot call it a pass without verification
                    note = (
                        "Prompt was changed and no failures were detected in the cached replay, "
                        "but this result is SIMULATED. "
                        "The fix cannot be confirmed without genuine agent re-execution. "
                        "Treat as a candidate, not a verified fix."
                    )
                elif replay_status == "error":
                    outcome = "Still failing"
                    after_status = "fail"
                    note = "Run still fails after prompt change. Issue not resolved."
                else:
                    outcome = "Inconclusive"
                    note = "Replay returned an unexpected status."

        except Exception as e:
            logger.warning(f"Replay failed for run {run_id}: {e}")
            outcome = "Inconclusive"
            note = f"Replay could not complete: {str(e)[:200]}"
            after_status = before_status  # Assume unchanged on error

        results.append(
            {
                "id": run.id,
                "task": run.task,
                "is_guard": is_guard,
                "before_status": before_status,
                "after_status": after_status,
                "delta_tokens": delta_tokens,
                "outcome": outcome,
                "note": note,
            }
        )

    # Aggregate summary
    total = len(results)
    fixed = sum(1 for r in results if r["outcome"] == "Fixed")
    candidate = sum(1 for r in results if r["outcome"] == "Candidate fix (unverified)")
    failed_initial = sum(1 for r in results if r["before_status"] == "fail")
    regressions = sum(1 for r in results if r["outcome"] == "Regression")
    guard_total = sum(1 for r in results if r["is_guard"])
    unchanged = sum(1 for r in results if r["outcome"] == "Unchanged")
    inconclusive = sum(
        1
        for r in results
        if r["outcome"] in ("Inconclusive", "Candidate fix (unverified)")
    )

    summary = {
        "total": total,
        "fixed": fixed,
        "failed_initial": failed_initial,
        "regressions": regressions,
        "guard_total": guard_total,
        "unchanged": unchanged,
        "inconclusive": inconclusive,
        "candidate": candidate,
    }

    # Persist
    batch = models.BatchVerification(
        run_ids_json=json.dumps(run_ids),
        modified_prompt=modified_prompt,
        target_rule=target_rule,
        results_json=json.dumps(results),
        summary_json=json.dumps(summary),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    return batch


def get_batch_runs_as_items(db: Session) -> List[Dict]:
    """
    Returns the latest batch verification results as BatchItem dicts,
    or runs from the DB if no batch has been executed yet.
    """
    # Check if any batch verifications exist
    latest_batch = (
        db.query(models.BatchVerification)
        .order_by(models.BatchVerification.created_at.desc())
        .first()
    )

    if latest_batch:
        try:
            return json.loads(latest_batch.results_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: return all runs as batch items
    runs = (
        db.query(models.AgentRun)
        .order_by(models.AgentRun.created_at.desc())
        .limit(50)
        .all()
    )
    items = []
    for run in runs:
        items.append(
            {
                "id": run.id,
                "task": run.task,
                "is_guard": run.ok,
                "before_status": "pass" if run.ok else "fail",
                "after_status": "pass" if run.ok else "fail",
                "delta_tokens": 0,
                "outcome": "Unchanged",
                "note": "No batch verification run yet.",
            }
        )
    return items
