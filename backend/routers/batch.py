"""
Batch verification router for Rewind backend.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import BatchVerificationRequestSchema
from backend.services.batch_service import execute_batch_verification, get_batch_runs_as_items

router = APIRouter(prefix="/api/batch", tags=["Batch"])


@router.get("/runs")
def get_batch_runs(db: Session = Depends(get_db)):
    """
    Returns the latest batch verification results as a list of BatchItems.
    If no batch has been run, returns all recorded runs as candidates.
    """
    return get_batch_runs_as_items(db)


@router.post("/verify")
def verify_batch(req: BatchVerificationRequestSchema, db: Session = Depends(get_db)):
    """
    Execute batch verification across multiple run IDs with a modified prompt.
    Returns individual results and aggregate summary.
    """
    if not req.run_ids:
        raise HTTPException(status_code=400, detail="run_ids must not be empty.")

    try:
        batch = execute_batch_verification(
            run_ids=req.run_ids,
            modified_prompt=req.modified_prompt,
            target_rule=req.target_rule,
            db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch verification failed: {str(e)}")

    import json
    try:
        results = json.loads(batch.results_json or "[]")
    except (json.JSONDecodeError, TypeError):
        results = []
    try:
        summary = json.loads(batch.summary_json or "{}")
    except (json.JSONDecodeError, TypeError):
        summary = {}

    return {"results": results, "summary": summary}
