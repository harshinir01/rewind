"""
Health router for Rewind backend.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models

router = APIRouter(tags=["Health"])


@router.get("/")
@router.get("/health")
@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Returns actual backend status and database record count."""
    try:
        db_count = db.query(func.count(models.AgentRun.id)).scalar() or 0
    except Exception:
        db_count = 0
    return {
        "status": "ok",
        "service": "rewind-fastapi-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database_records": db_count,
        "version": "2.0.0",
    }
