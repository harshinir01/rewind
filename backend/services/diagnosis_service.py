"""
Diagnosis service for Rewind.
Combines rule-based detectors with optional LLM-based analysis.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend import models
from backend.config import LLM_API_KEY, LLM_MODEL, LLM_PROVIDER
from backend.services.failure_detectors import run_all_detectors, DetectorFinding

logger = logging.getLogger(__name__)


def _build_trace_summary(run: models.AgentRun) -> str:
    """Build a concise text representation of an execution trace for LLM context."""
    lines = [
        f"Agent: {run.agent}",
        f"Task: {run.task}",
        f"Outcome: {'success' if run.ok else 'failure'}",
        f"Failure label: {run.label or 'unknown'}",
        f"Steps: {len(run.steps)}",
        "",
        "--- Execution Steps ---",
    ]
    for s in run.steps:
        lines.append(
            f"Step {s.step_number} [{s.kind.upper()}] {s.name} "
            f"(status={s.status}, {s.tokens} tokens, {s.duration_ms}ms)"
        )
        if s.input:
            lines.append(f"  Input: {s.input[:300]}")
        if s.output:
            lines.append(f"  Output: {s.output[:300]}")
        if s.error_message:
            lines.append(f"  Error: {s.error_message[:200]}")
    return "\n".join(lines)


def _call_llm_diagnosis(trace_summary: str, detector_findings: List[DetectorFinding]) -> Optional[Dict]:
    """
    Call the configured LLM for diagnosis.
    Returns parsed dict or None if LLM is unavailable or call fails.
    """
    if not LLM_API_KEY:
        return None

    detector_summary = ""
    if detector_findings:
        lines = []
        for f in detector_findings:
            lines.append(f"- {f.detector_name}: {f.evidence} (category: {f.failure_category})")
        detector_summary = "Rule-based detectors already found:\n" + "\n".join(lines)
    else:
        detector_summary = "Rule-based detectors found no specific issues."

    prompt = f"""You are an AI agent debugging assistant. Analyze this agent execution trace and identify the root cause of failure.

{trace_summary}

{detector_summary}

Respond ONLY with valid JSON in this exact format:
{{
  "failure_category": "one of: ignored_error, infinite_loop, goal_drift, bad_arguments, wrong_tool, lost_context",
  "reason": "clear 1-3 sentence explanation of what went wrong and why",
  "relevant_step": <step number where the mistake occurred, as integer>,
  "judge_verdict": "brief verdict from the AI reviewer perspective",
  "confidence": <float between 0.0 and 1.0>
}}

Base your analysis ONLY on the actual steps shown above. Do not invent steps, tools, or outputs that are not present."""

    try:
        if LLM_PROVIDER == "google":
            import google.generativeai as genai
            genai.configure(api_key=LLM_API_KEY)
            model = genai.GenerativeModel(LLM_MODEL)
            response = model.generate_content(prompt)
            raw = response.text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)

        elif LLM_PROVIDER == "openai":
            import openai
            client = openai.OpenAI(api_key=LLM_API_KEY)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)

        elif LLM_PROVIDER == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=LLM_API_KEY)
            response = client.messages.create(
                model=LLM_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)

    except ImportError as e:
        logger.warning(f"LLM provider '{LLM_PROVIDER}' SDK not installed: {e}")
    except Exception as e:
        logger.warning(f"LLM diagnosis call failed: {e}")

    return None


def _validate_step_reference(step_num: Optional[int], steps) -> Optional[int]:
    """Ensure a step number actually exists in the trace. Return None if not."""
    if step_num is None:
        return None
    valid_nums = {s.step_number for s in steps}
    return step_num if step_num in valid_nums else None


def diagnose_run(run: models.AgentRun, db: Session) -> models.Diagnosis:
    """
    Full diagnosis pipeline:
    1. Run rule-based detectors
    2. Optionally call LLM for deeper analysis
    3. Build and persist diagnosis
    4. Return the Diagnosis ORM object
    """
    steps = run.steps

    # --- Step 1: Rule-based detection ---
    findings = run_all_detectors(steps)

    fired_detectors: Dict[str, str] = {}
    primary_finding: Optional[DetectorFinding] = None

    for f in findings:
        fired_detectors[f.detector_name] = f.evidence
        if primary_finding is None:
            primary_finding = f

    # Determine category and relevant step from detectors
    failure_category = primary_finding.failure_category if primary_finding else (run.label or "ignored_error")
    relevant_step = primary_finding.relevant_step if primary_finding else run.fail_step

    # Validate step reference
    relevant_step = _validate_step_reference(relevant_step, steps)

    # Build evidence from actual steps
    evidence_list = []
    if relevant_step:
        for s in steps:
            if s.step_number == relevant_step:
                if s.output:
                    evidence_list.append({"from": f"Step {s.step_number} output", "text": s.output[:400]})
                if s.input:
                    evidence_list.append({"from": f"Step {s.step_number} input", "text": s.input[:400]})
                break

    # Also add the fail_step evidence if different from relevant_step
    if run.fail_step and run.fail_step != relevant_step:
        for s in steps:
            if s.step_number == run.fail_step:
                if s.output:
                    evidence_list.append({"from": f"Step {s.step_number} output (fail step)", "text": s.output[:400]})
                break

    # Build reason from primary finding
    reason = (
        primary_finding.evidence if primary_finding
        else f"Agent failed at step {run.fail_step or 'unknown'} during task '{run.task}'."
    )

    judge_verdict = "No LLM reviewer configured. Rule-based analysis only."
    confidence = 0.75 if primary_finding else 0.5

    # --- Step 2: Optional LLM enhancement ---
    if LLM_API_KEY and steps:
        trace_summary = _build_trace_summary(run)
        llm_result = _call_llm_diagnosis(trace_summary, findings)

        if llm_result:
            # Validate LLM references
            llm_step = _validate_step_reference(llm_result.get("relevant_step"), steps)

            # Only override if LLM provides valid data
            if llm_result.get("failure_category") in [
                "ignored_error", "infinite_loop", "goal_drift",
                "bad_arguments", "wrong_tool", "lost_context"
            ]:
                failure_category = llm_result["failure_category"]

            if llm_result.get("reason"):
                reason = llm_result["reason"]

            if llm_step:
                relevant_step = llm_step

            if llm_result.get("judge_verdict"):
                judge_verdict = llm_result["judge_verdict"]

            if llm_result.get("confidence") is not None:
                try:
                    confidence = float(llm_result["confidence"])
                except (ValueError, TypeError):
                    pass
        else:
            if LLM_API_KEY:
                judge_verdict = "LLM reviewer was configured but could not complete analysis. Rule-based findings shown."

    # --- Step 3: Persist ---
    diag = models.Diagnosis(
        run_id=run.id,
        failure_category=failure_category,
        reason=reason,
        relevant_step=relevant_step,
        evidence_json=json.dumps(evidence_list, ensure_ascii=False),
        fired_detectors_json=json.dumps(fired_detectors, ensure_ascii=False),
        judge_verdict=judge_verdict,
        confidence=confidence,
    )
    db.add(diag)
    db.commit()
    db.refresh(diag)

    return diag
