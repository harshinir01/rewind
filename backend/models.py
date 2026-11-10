"""
SQLAlchemy ORM models for Rewind backend.
All structured data is stored as JSON text in SQLite TEXT columns.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, Float, Integer, String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=_uuid)
    agent = Column(String, nullable=False, index=True)
    task = Column(Text, nullable=False)
    ok = Column(Boolean, nullable=False, default=False)
    label = Column(String, nullable=True, index=True)      # failure category
    steps_count = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    duration = Column(String, nullable=True)               # human-readable e.g. "14.2s"
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(String, nullable=True)             # human-readable timestamp
    fail_step = Column(Integer, nullable=True)
    prompt = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)

    # Relationships
    steps = relationship("ExecutionStep", back_populates="run", cascade="all, delete-orphan", order_by="ExecutionStep.step_number")
    diagnosis = relationship("Diagnosis", back_populates="run", uselist=False, cascade="all, delete-orphan")
    replays = relationship("Replay", back_populates="original_run", cascade="all, delete-orphan")


class ExecutionStep(Base):
    __tablename__ = "execution_steps"

    id = Column(String, primary_key=True, default=_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False)                   # 'llm' | 'tool' | 'system'
    tool_name = Column(String, nullable=True)
    input = Column(Text, default="")
    output = Column(Text, default="")
    error_message = Column(Text, nullable=True)
    status = Column(String, default="ok")                   # 'ok' | 'error' | 'fail'
    duration_ms = Column(Integer, default=0)
    tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=_now)

    run = relationship("AgentRun", back_populates="steps")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(String, primary_key=True, default=_uuid)
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    failure_category = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    relevant_step = Column(Integer, nullable=True)
    evidence_json = Column(Text, default="[]")              # JSON list of {from, text}
    fired_detectors_json = Column(Text, default="{}")       # JSON dict
    judge_verdict = Column(Text, default="")
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_now)

    run = relationship("AgentRun", back_populates="diagnosis")


class Replay(Base):
    __tablename__ = "replays"

    id = Column(String, primary_key=True, default=_uuid)
    original_run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    modified_prompt = Column(Text, nullable=True)
    start_step = Column(Integer, nullable=False, default=1)
    replay_mode = Column(String, default="cached")
    status = Column(String, default="ok")
    answer_before = Column(Text, default="")
    answer_after = Column(Text, default="")
    steps_json = Column(Text, default="[]")                 # JSON list of ReplayStep
    full_tokens = Column(Integer, default=0)
    replay_tokens = Column(Integer, default=0)
    tokens_saved = Column(Integer, default=0)
    tokens_saved_percent = Column(Integer, default=0)
    full_duration_ms = Column(Integer, default=0)
    replay_duration_ms = Column(Integer, default=0)
    duration_saved_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=_now)

    original_run = relationship("AgentRun", back_populates="replays")


class BatchVerification(Base):
    __tablename__ = "batch_verifications"

    id = Column(String, primary_key=True, default=_uuid)
    run_ids_json = Column(Text, default="[]")               # JSON list of run IDs
    modified_prompt = Column(Text, nullable=True)
    target_rule = Column(String, nullable=True)
    results_json = Column(Text, default="[]")               # JSON list of BatchItem
    summary_json = Column(Text, default="{}")               # JSON BatchVerificationSummary
    created_at = Column(DateTime, default=_now)
