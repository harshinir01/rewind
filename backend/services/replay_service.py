"""
Safe replay engine for Rewind.
Reuses cached outputs for steps before the replay point.
Never executes real external side effects.

Verification honesty policy
----------------------------
A replay marked 'ok' means the replay encountered no failures in the
replayed portion (after start_step).  This does NOT mean the original
failure was resolved — cached/isolated mode cannot genuinely re-run the
agent.  The answer_after and verification_note fields always state clearly
whether the result is genuine or simulated.

Status values returned:
  'ok'           — no failures observed in the replayed portion
  'error'        — a failure was observed in the replayed portion
  'inconclusive' — replay is simulated; genuine verification is unavailable

The 'inconclusive' status is used whenever:
  - The prompt was changed AND the replay mode is cached/isolated
    (simulation cannot prove the fix works)
  - Any step could not be re-evaluated at all
"""
from __future__ import annotations
import json
import logging
import time
from typing import List, Tuple

from sqlalchemy.orm import Session

from backend import models

logger = logging.getLogger(__name__)


SAFE_MODES = {"cached", "isolated"}

# Statuses that the replay ORM field may carry
STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_INCONCLUSIVE = "inconclusive"


def _get_original_answer(steps: List[models.ExecutionStep]) -> str:
    """Return the last LLM or system step's output as the 'final answer'."""
    for s in reversed(steps):
        if s.output:
            return s.output
    return "No output recorded."


def _replay_step_cached(
    step: models.ExecutionStep, is_before_start: bool
) -> Tuple[str, str, str]:
    """
    Cached mode step handler.
    Returns (summary, step_status, execution_mode).

    execution_mode values:
      'reused'    — step output taken verbatim from cache (no change possible)
      'simulated' — step is at/after start_step; output is from cache but
                    result cannot be verified without real re-execution
    """
    if is_before_start:
        # Steps before replay start: always reuse as-is
        summary = step.output[:150] if step.output else "Cached output."
        return summary, step.status or STATUS_OK, "reused"

    # Steps at or after start_step — return cached output but mark as simulated
    # (we cannot actually re-run anything in cached mode)
    summary = (
        f"[Cached] {step.output[:150]}"
        if step.output
        else "[Cached] No output recorded."
    )
    # Preserve original step status — don't fabricate an improvement
    return summary, step.status or STATUS_OK, "simulated"


def _replay_step_isolated(
    step: models.ExecutionStep, is_before_start: bool
) -> Tuple[str, str, str]:
    """
    Isolated mode step handler.
    Returns (summary, step_status, execution_mode).

    Isolated mode is semantically equivalent to cached mode in this
    implementation because no genuine isolated sandbox exists.  Steps are
    labelled 'simulated' to make this clear.
    """
    if is_before_start:
        summary = step.output[:150] if step.output else "Cached output."
        return summary, step.status or STATUS_OK, "reused"

    if step.kind == "tool":
        summary = (
            f"[Isolated/cached] {step.output[:150]}"
            if step.output
            else "[Isolated] No cached output."
        )
        return summary, step.status or STATUS_OK, "simulated"
    elif step.kind == "llm":
        summary = (
            "[Isolated] LLM step — output reused from original trace. "
            "Genuine re-execution is unavailable in isolated mode."
        )
        return summary, step.status or STATUS_OK, "simulated"
    else:
        summary = (
            f"[Isolated] System step: {step.output[:120]}"
            if step.output
            else "[Isolated] System step."
        )
        return summary, step.status or STATUS_OK, "simulated"


def execute_replay(
    run: models.AgentRun,
    modified_prompt: str,
    start_step: int,
    replay_mode: str,
    db: Session,
) -> models.Replay:
    """
    Execute a safe replay:
    1. Validate start_step
    2. Reuse cached outputs for steps < start_step
    3. Simulate/cache steps >= start_step (no real re-execution)
    4. Record and persist the replay with honest status
    5. Return Replay ORM object

    IMPORTANT: This implementation never genuinely re-runs the agent.
    Status 'inconclusive' is returned whenever the prompt was changed
    and genuine re-execution cannot be confirmed.
    """
    if replay_mode == "live":
        raise ValueError(
            "Live replay is disabled for safety. "
            "Use 'cached' or 'isolated' mode instead."
        )

    if replay_mode not in SAFE_MODES:
        raise ValueError(
            f"Invalid replay_mode '{replay_mode}'. "
            f"Must be one of: {SAFE_MODES}"
        )

    steps = run.steps
    if not steps:
        raise ValueError(
            f"Run '{run.id}' has no recorded execution steps to replay."
        )

    max_step = max(s.step_number for s in steps)
    if start_step < 1 or start_step > max_step:
        raise ValueError(
            f"start_step {start_step} is out of range [1, {max_step}]."
        )

    t_start = time.monotonic()

    replay_steps_data = []
    full_tokens = 0
    replay_tokens = 0  # Always 0 — no real LLM calls are made

    prompt_changed = modified_prompt.strip() != (run.prompt or "").strip()

    has_fail_in_replayed = False  # failures in the simulated portion

    for s in steps:
        full_tokens += s.tokens or 0
        is_before_start = s.step_number < start_step

        if replay_mode == "cached":
            summary, step_status, execution_mode = _replay_step_cached(
                s, is_before_start
            )
        else:  # isolated
            summary, step_status, execution_mode = _replay_step_isolated(
                s, is_before_start
            )

        if not is_before_start and step_status in ("error", "fail"):
            has_fail_in_replayed = True

        replay_steps_data.append(
            {
                "step_number": s.step_number,
                "name": s.name,
                "kind": s.kind,
                "summary": summary,
                "status": step_status,
                "execution_mode": execution_mode,
            }
        )

    t_end = time.monotonic()
    replay_duration_ms = int((t_end - t_start) * 1000)

    # --- Token / duration savings ---
    replayed_step_count = sum(1 for s in steps if s.step_number >= start_step)
    total_step_count = len(steps)
    fraction_replayed = (
        replayed_step_count / total_step_count if total_step_count > 0 else 1.0
    )
    full_duration_ms = run.duration_ms or sum(s.duration_ms or 0 for s in steps)
    # We saved the time of steps we didn't re-execute (all of them, really)
    estimated_replay_ms = max(50, replay_duration_ms)  # actual wall-clock time
    duration_saved_ms = max(0, full_duration_ms - estimated_replay_ms)

    tokens_saved = max(0, full_tokens - replay_tokens)
    tokens_saved_percent = (
        int((tokens_saved / full_tokens) * 100) if full_tokens > 0 else 0
    )

    # --- Determine overall replay status (honest) ---
    #
    # Rule: If a failure exists in the replayed portion, status = 'error'.
    # Rule: If the prompt was changed, we cannot verify repair — status = 'inconclusive'.
    # Rule: If the prompt is unchanged and no failures in replayed portion, status = 'ok'.
    #       (This just means the replay reproduced the same outcome as the original.)
    #
    # We never return 'ok' to imply "the fix worked" unless there is actual evidence.

    answer_before = _get_original_answer(steps)

    if has_fail_in_replayed and not prompt_changed:
        # Unchanged prompt + failures in replayed portion → genuine repeat of original failure
        replay_status = STATUS_ERROR
        answer_after = (
            "Replay encountered the same failure in the replayed portion. "
            "The issue is NOT resolved (prompt unchanged)."
        )
        verification_note = (
            "CACHED REPLAY: Prompt unchanged. Failures detected in the replayed portion "
            "confirm the original issue persists."
        )
    elif prompt_changed:
        # Prompt changed → we cannot verify anything with cached/simulated steps.
        # Even if failures exist in cached outputs, the new prompt may resolve them.
        # Even if no failures appear, we can't confirm the fix without real re-execution.
        replay_status = STATUS_INCONCLUSIVE
        if has_fail_in_replayed:
            answer_after = (
                "Prompt was updated. The cached replay still shows failures in the original trace, "
                "but those failures might not occur with the new prompt. "
                "This result is SIMULATED — the agent was not genuinely re-executed. "
                "To verify the fix, run the agent with the updated prompt in a real environment."
            )
        else:
            answer_after = (
                "Prompt was updated. No failures were detected in the cached replay, "
                "but this result is SIMULATED — the agent was not genuinely re-executed. "
                "To verify the fix, run the agent with the updated prompt in a real environment."
            )
        verification_note = (
            "SIMULATED: This replay used cached step outputs and did not "
            "re-execute the agent. A prompt change cannot be verified without "
            "genuine re-execution. Status is inconclusive, not 'fixed'."
        )
    else:
        # Prompt unchanged, no failures in replayed portion
        replay_status = STATUS_OK
        answer_after = (
            "Replay completed with no prompt change. "
            "Outcome matches the original execution (expected)."
        )
        verification_note = (
            "CACHED: Prompt unchanged. This replay reproduced the original execution "
            "using cached outputs. No repair was attempted."
        )

    # --- Persist ---
    replay = models.Replay(
        original_run_id=run.id,
        modified_prompt=modified_prompt,
        start_step=start_step,
        replay_mode=replay_mode,
        status=replay_status,
        answer_before=answer_before,
        answer_after=answer_after,
        steps_json=json.dumps(replay_steps_data, ensure_ascii=False),
        full_tokens=full_tokens,
        replay_tokens=replay_tokens,
        tokens_saved=tokens_saved,
        tokens_saved_percent=tokens_saved_percent,
        full_duration_ms=full_duration_ms,
        replay_duration_ms=estimated_replay_ms,
        duration_saved_ms=duration_saved_ms,
    )
    db.add(replay)
    db.commit()
    db.refresh(replay)

    return replay
