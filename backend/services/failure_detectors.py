"""
Rule-based failure detectors for Rewind.
Each detector evaluates an execution trace and returns structured findings.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DetectorFinding:
    detector_name: str
    failure_category: str
    relevant_step: Optional[int]
    evidence: str
    severity: str = "high"  # "high" | "medium" | "low"
    fired: bool = True


def _steps_from_orm(steps) -> List[Dict]:
    """Convert ORM ExecutionStep objects to plain dicts."""
    result = []
    for s in steps:
        result.append({
            "step_number": s.step_number,
            "name": s.name,
            "kind": s.kind,
            "tool_name": getattr(s, "tool_name", None),
            "input": s.input or "",
            "output": s.output or "",
            "status": s.status or "ok",
            "duration_ms": s.duration_ms or 0,
            "tokens": s.tokens or 0,
            "error_message": getattr(s, "error_message", None),
        })
    return result


# ---------------------------------------------------------------------------
# Individual Detectors
# ---------------------------------------------------------------------------

def detect_repeated_identical_calls(steps: List[Dict]) -> Optional[DetectorFinding]:
    """Detects when the same tool is called with identical arguments multiple times."""
    seen: Dict[str, List[int]] = {}
    for s in steps:
        if s["kind"] == "tool":
            key = f"{s['name']}::{s['input']}"
            seen.setdefault(key, []).append(s["step_number"])

    for key, step_nums in seen.items():
        if len(step_nums) >= 2:
            tool_name = key.split("::")[0]
            return DetectorFinding(
                detector_name="Repeated identical call",
                failure_category="infinite_loop",
                relevant_step=step_nums[0],
                evidence=f"Tool '{tool_name}' was called with identical arguments at steps {step_nums}.",
            )
    return None


def detect_ignored_tool_error(steps: List[Dict]) -> Optional[DetectorFinding]:
    """
    Detects when a tool returns an error but the next LLM step
    does not handle it and continues as if it succeeded.
    """
    for i, s in enumerate(steps):
        if s["kind"] == "tool" and s["status"] == "error":
            # Look at the next LLM step
            for j in range(i + 1, len(steps)):
                next_s = steps[j]
                if next_s["kind"] == "llm":
                    out_lower = next_s["output"].lower()
                    # Heuristic: if output doesn't mention error, failure, retry → ignored
                    error_keywords = ["error", "fail", "retry", "wrong", "exception", "cannot", "unable"]
                    if not any(kw in out_lower for kw in error_keywords):
                        return DetectorFinding(
                            detector_name="Ignored tool error",
                            failure_category="ignored_error",
                            relevant_step=next_s["step_number"],
                            evidence=(
                                f"Step {s['step_number']} returned an error: "
                                f"{s['output'][:200]}. "
                                f"Step {next_s['step_number']} (LLM) continued without acknowledging it."
                            ),
                        )
                    break
    return None


def detect_bad_arguments(steps: List[Dict]) -> Optional[DetectorFinding]:
    """
    Detects when a tool is called with arguments that were not
    present in the execution context (e.g. referencing a column not in schema).
    """
    # Collect all outputs from tool steps as "known context"
    context_tokens: set[str] = set()
    for s in steps:
        if s["kind"] in ("tool", "system") and s["output"]:
            # Tokenize outputs roughly
            tokens = s["output"].lower().replace('"', ' ').replace(',', ' ').split()
            context_tokens.update(tokens)

    for s in steps:
        if s["kind"] == "tool" and s["status"] == "error":
            inp = s["input"]
            # Try to parse as JSON
            try:
                args = json.loads(inp)
                if isinstance(args, dict):
                    for val in args.values():
                        v = str(val).lower()
                        # If the value looks like a column/field name and was not in context
                        if len(v) > 3 and "_" in v and v not in context_tokens:
                            return DetectorFinding(
                                detector_name="Argument absent from context",
                                failure_category="bad_arguments",
                                relevant_step=s["step_number"],
                                evidence=(
                                    f"Step {s['step_number']} used argument '{val}' "
                                    f"which does not appear in prior tool outputs."
                                ),
                                severity="medium",
                            )
            except (json.JSONDecodeError, TypeError):
                pass
    return None


def detect_step_limit_violation(steps: List[Dict], max_steps: int = 50) -> Optional[DetectorFinding]:
    """Detects when a run was cut off by the step limit."""
    system_steps = [s for s in steps if s["kind"] == "system"]
    for s in system_steps:
        out_lower = s["output"].lower()
        if "step limit" in out_lower or "max_steps" in out_lower or "stopped" in out_lower:
            return DetectorFinding(
                detector_name="Step or budget limit",
                failure_category="infinite_loop",
                relevant_step=s["step_number"],
                evidence=f"System step {s['step_number']}: {s['output'][:300]}",
            )
    if len(steps) >= max_steps:
        return DetectorFinding(
            detector_name="Step or budget limit",
            failure_category="infinite_loop",
            relevant_step=len(steps),
            evidence=f"Run reached {len(steps)} steps (limit: {max_steps}).",
        )
    return None


def detect_goal_drift(steps: List[Dict]) -> Optional[DetectorFinding]:
    """
    Heuristic: if an LLM step outputs 'following that thread' or 
    similar phrases indicating topic change, flag it.
    """
    drift_phrases = [
        "following that thread",
        "following this thread",
        "let me also",
        "i'll also investigate",
        "going down this path",
        "this raises another",
    ]
    for s in steps:
        if s["kind"] == "llm":
            out_lower = s["output"].lower()
            for phrase in drift_phrases:
                if phrase in out_lower:
                    return DetectorFinding(
                        detector_name="Goal drift signal",
                        failure_category="goal_drift",
                        relevant_step=s["step_number"],
                        evidence=f"Step {s['step_number']} output suggests topic drift: '{phrase}' detected.",
                        severity="medium",
                    )
    return None


def detect_lost_context(steps: List[Dict]) -> Optional[DetectorFinding]:
    """
    Detects when a later LLM step contradicts earlier factual tool outputs,
    suggesting the agent lost track of established context.
    """
    # Simplified heuristic: if final LLM answer says "no data" / "0" but
    # intermediate tool outputs had non-empty results
    tool_outputs_had_data = False
    for s in steps[:-2]:  # all but last two steps
        if s["kind"] == "tool" and s["output"] and len(s["output"]) > 10:
            if "results" in s["output"].lower() or "[" in s["output"]:
                tool_outputs_had_data = True
                break

    if tool_outputs_had_data:
        last_llm = None
        for s in reversed(steps):
            if s["kind"] == "llm":
                last_llm = s
                break
        if last_llm:
            out_lower = last_llm["output"].lower()
            if any(p in out_lower for p in ["no data", "0 in all", "nothing found", "no results"]):
                return DetectorFinding(
                    detector_name="Lost context",
                    failure_category="lost_context",
                    relevant_step=last_llm["step_number"],
                    evidence=(
                        f"Earlier tool steps returned data, but step {last_llm['step_number']} "
                        f"reported no results: {last_llm['output'][:200]}"
                    ),
                    severity="medium",
                )
    return None


# ---------------------------------------------------------------------------
# Run all detectors
# ---------------------------------------------------------------------------

def run_all_detectors(steps_orm) -> List[DetectorFinding]:
    """Run all detectors on the given ORM steps. Returns list of findings that fired."""
    steps = _steps_from_orm(steps_orm)
    findings: List[DetectorFinding] = []

    detectors = [
        detect_repeated_identical_calls,
        detect_ignored_tool_error,
        detect_bad_arguments,
        detect_step_limit_violation,
        detect_goal_drift,
        detect_lost_context,
    ]

    for detector in detectors:
        try:
            finding = detector(steps)
            if finding is not None:
                findings.append(finding)
        except Exception:
            pass  # Never let a detector crash the whole pipeline

    return findings
