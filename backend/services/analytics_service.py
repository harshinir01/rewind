"""
Analytics service — computes statistics from actual SQLite records.
"""
from __future__ import annotations
from typing import Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models


def get_analytics_metrics(db: Session) -> Dict:
    """
    Calculate analytics from actual database records.
    Returns empty-state values if database is empty.
    """
    total = db.query(func.count(models.AgentRun.id)).scalar() or 0

    if total == 0:
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate": 0.0,
            "total_spend": 0.0,
            "most_common_mistake": None,
            "most_common_count": 0,
        }

    successful = db.query(func.count(models.AgentRun.id)).filter(models.AgentRun.ok == True).scalar() or 0
    failed = total - successful
    success_rate = round((successful / total) * 100, 1)

    total_spend_raw = db.query(func.sum(models.AgentRun.cost)).scalar() or 0.0
    total_spend = round(float(total_spend_raw), 4)

    # Most common failure label
    label_counts = (
        db.query(models.AgentRun.label, func.count(models.AgentRun.id).label("cnt"))
        .filter(models.AgentRun.label.isnot(None))
        .group_by(models.AgentRun.label)
        .order_by(func.count(models.AgentRun.id).desc())
        .first()
    )

    most_common_mistake = None
    most_common_count = 0
    if label_counts:
        most_common_mistake = label_counts[0]
        most_common_count = label_counts[1]

    return {
        "total_runs": total,
        "successful_runs": successful,
        "failed_runs": failed,
        "success_rate": success_rate,
        "total_spend": total_spend,
        "most_common_mistake": most_common_mistake,
        "most_common_count": most_common_count,
    }
