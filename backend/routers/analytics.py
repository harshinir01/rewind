"""
Analytics router for Rewind backend.
Computes statistics from actual SQLite records.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.analytics_service import get_analytics_metrics

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/metrics")
def analytics_metrics(db: Session = Depends(get_db)):
    """Return analytics computed from actual database records."""
    return get_analytics_metrics(db)
