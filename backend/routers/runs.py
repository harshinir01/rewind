"""
Runs router for Rewind backend.
Handles CRUD for AgentRun records with real SQLite persistence.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Annotated

from backend.database import get_db
from backend import models
from backend.schemas import AgentRunSchema, RunDetailSchema, CreateRunSchema

router = APIRouter(prefix="/api/runs", tags=["Runs"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _orm_step_to_schema(s: models.ExecutionStep) -> dict:
    return {
        "step_number": s.step_number,
        "name": s.name,
        "kind": s.kind,
        "duration_ms": s.duration_ms or 0,
        "tokens": s.tokens or 0,
        "input": s.input or "",
        "output": s.output or "",
        "status": s.status or "ok",
        "tool_name": s.tool_name,
        "error_message": s.error_message,
    }


def _orm_diagnosis_to_schema(d: models.Diagnosis) -> Optional[dict]:
    if not d:
        return None
    try:
        evidence = json.loads(d.evidence_json or "[]")
    except (json.JSONDecodeError, TypeError):
        evidence = []
    try:
        fired_detectors = json.loads(d.fired_detectors_json or "{}")
    except (json.JSONDecodeError, TypeError):
        fired_detectors = {}

    return {
        "failure_category": d.failure_category,
        "reason": d.reason,
        "evidence": evidence,
        "fired_detectors": fired_detectors,
        "judge_verdict": d.judge_verdict or "",
        "relevant_step": d.relevant_step,
        "confidence": d.confidence,
    }


def _orm_run_to_agent_run(r: models.AgentRun) -> dict:
    return {
        "id": r.id,
        "agent": r.agent,
        "task": r.task,
        "ok": r.ok,
        "label": r.label,
        "steps_count": r.steps_count or len(r.steps),
        "cost": r.cost or 0.0,
        "duration": r.duration or "",
        "duration_ms": r.duration_ms,
        "started_at": r.started_at or "",
        "fail_step": r.fail_step,
        "prompt": r.prompt,
        "suggested_fix": r.suggested_fix,
    }


def _orm_run_to_run_detail(r: models.AgentRun) -> dict:
    base = _orm_run_to_agent_run(r)
    base["steps"] = [_orm_step_to_schema(s) for s in r.steps]
    base["diagnosis"] = _orm_diagnosis_to_schema(r.diagnosis) if r.diagnosis else None
    return base


# ---------------------------------------------------------------------------
# GET /api/runs
# ---------------------------------------------------------------------------

@router.get("", response_model=List[AgentRunSchema])
def list_runs(
    search: Annotated[Optional[str], Query(description="Search across ID, agent, task, or label")] = None,
    status: Annotated[Optional[str], Query(description="'failed' | 'passed' | 'all'")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
):
    """List agent runs with search, filter, and pagination from SQLite."""
    query = db.query(models.AgentRun)

    if status == "failed":
        query = query.filter(models.AgentRun.ok == False)  # noqa: E712
    elif status == "passed":
        query = query.filter(models.AgentRun.ok == True)   # noqa: E712

    if search:
        q = f"%{search.strip().lower()}%"
        from sqlalchemy import or_, func as sqlfunc
        query = query.filter(
            or_(
                sqlfunc.lower(models.AgentRun.id).like(q),
                sqlfunc.lower(models.AgentRun.agent).like(q),
                sqlfunc.lower(models.AgentRun.task).like(q),
                sqlfunc.lower(models.AgentRun.label).like(q),
            )
        )

    query = query.order_by(models.AgentRun.created_at.desc())
    runs = query.offset(offset).limit(limit).all()

    return [_orm_run_to_agent_run(r) for r in runs]


# ---------------------------------------------------------------------------
# GET /api/runs/{run_id}
# ---------------------------------------------------------------------------

@router.get("/{run_id}", response_model=RunDetailSchema)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Fetch a single run with full execution steps and diagnosis."""
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found in database.",
        )
    return _orm_run_to_run_detail(run)


# ---------------------------------------------------------------------------
# POST /api/runs
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED, response_model=RunDetailSchema)
def create_run(run_data: CreateRunSchema, db: Session = Depends(get_db)):
    """
    Create a new agent run record.
    Accepts the full RunDetail schema from the frontend or recording client.
    """
    run_id = run_data.id or str(uuid.uuid4())

    # Check for duplicate
    existing = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' already exists. Use a unique ID.",
        )

    run = models.AgentRun(
        id=run_id,
        agent=run_data.agent,
        task=run_data.task,
        ok=run_data.ok,
        label=run_data.label,
        steps_count=run_data.steps_count or len(run_data.steps or []),
        cost=run_data.cost or 0.0,
        duration=run_data.duration or "",
        duration_ms=run_data.duration_ms,
        started_at=run_data.started_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        fail_step=run_data.fail_step,
        prompt=run_data.prompt,
        suggested_fix=run_data.suggested_fix,
    )
    db.add(run)
    db.flush()  # get the ID before adding steps

    # Add steps
    for step_data in (run_data.steps or []):
        step = models.ExecutionStep(
            run_id=run_id,
            step_number=step_data.step_number,
            name=step_data.name,
            kind=step_data.kind,
            tool_name=step_data.tool_name,
            input=step_data.input or "",
            output=step_data.output or "",
            status=step_data.status or "ok",
            tokens=step_data.tokens or 0,
            duration_ms=step_data.duration_ms or 0,
            error_message=step_data.error_message,
        )
        db.add(step)

    # Add diagnosis if provided
    if run_data.diagnosis:
        d = run_data.diagnosis
        evidence_list = []
        for ev in (d.evidence or []):
            # Handle both 'from_' (Python attr) and serialized 'from' (JSON key)
            from_val = ev.from_ if hasattr(ev, 'from_') else getattr(ev, 'from', '')
            evidence_list.append({"from": from_val, "text": ev.text})

        diag = models.Diagnosis(
            run_id=run_id,
            failure_category=d.failure_category,
            reason=d.reason,
            relevant_step=d.relevant_step,
            evidence_json=json.dumps(evidence_list, ensure_ascii=False),
            fired_detectors_json=json.dumps(d.fired_detectors or {}, ensure_ascii=False),
            judge_verdict=d.judge_verdict or "",
            confidence=d.confidence,
        )
        db.add(diag)

    db.commit()
    db.refresh(run)
    return _orm_run_to_run_detail(run)


# ---------------------------------------------------------------------------
# DELETE /api/runs/{run_id}
# ---------------------------------------------------------------------------

@router.delete("/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    """Delete a run and all its associated data."""
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found.",
        )
    db.delete(run)
    db.commit()
    return {"success": True, "id": run_id}
