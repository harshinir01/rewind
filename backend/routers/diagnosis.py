"""
Diagnosis router for Rewind backend.
"""
from __future__ import annotations
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models
from backend.services.diagnosis_service import diagnose_run

router = APIRouter(prefix="/api/runs", tags=["Diagnosis"])


def _diagnosis_to_dict(d: models.Diagnosis) -> dict:
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


@router.get("/{run_id}/diagnosis")
def get_diagnosis(run_id: str, db: Session = Depends(get_db)):
    """Return an existing diagnosis for a run, or 404 if not yet diagnosed."""
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    if not run.diagnosis:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' has not been diagnosed yet. POST to /api/runs/{run_id}/diagnose to trigger diagnosis.",
        )
    return _diagnosis_to_dict(run.diagnosis)


@router.post("/{run_id}/diagnose")
def trigger_diagnosis(run_id: str, db: Session = Depends(get_db)):
    """
    Trigger fault diagnosis on a run.
    Runs rule-based detectors and optionally an LLM judge.
    Returns and persists the diagnosis result.
    """
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    # If already diagnosed, return existing
    if run.diagnosis:
        return _diagnosis_to_dict(run.diagnosis)

    if not run.steps:
        raise HTTPException(
            status_code=422,
            detail=f"Run '{run_id}' has no recorded execution steps. Cannot diagnose an empty trace.",
        )

    try:
        diag = diagnose_run(run, db)
        return _diagnosis_to_dict(diag)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Diagnosis failed: {str(e)}",
        )
