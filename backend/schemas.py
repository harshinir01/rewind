"""
Pydantic schemas for Rewind API.
These match exactly the TypeScript interfaces in src/types/index.ts.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Execution Steps
# ---------------------------------------------------------------------------

class ExecutionStepSchema(BaseModel):
    step_number: int
    name: str
    kind: str = Field(description="'llm' | 'tool' | 'system'")
    duration_ms: int = 0
    tokens: int = 0
    input: str = ""
    output: str = ""
    status: str = Field(default="ok", description="'ok' | 'error' | 'fail'")
    tool_name: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------

class DiagnosisEvidenceSchema(BaseModel):
    # The TS interface uses "from" (a Python keyword), handled via alias
    from_: str = Field(alias="from")
    text: str

    model_config = {"populate_by_name": True}


class DiagnosisResultSchema(BaseModel):
    failure_category: str
    reason: str
    evidence: List[DiagnosisEvidenceSchema] = []
    fired_detectors: Dict[str, str] = {}
    judge_verdict: str = ""
    relevant_step: Optional[int] = None
    confidence: Optional[float] = None

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Agent Runs
# ---------------------------------------------------------------------------

class AgentRunSchema(BaseModel):
    id: str
    agent: str
    task: str
    ok: bool
    label: Optional[str] = None
    steps_count: int = 0
    cost: float = 0.0
    duration: str = ""
    duration_ms: Optional[int] = None
    started_at: str = ""
    fail_step: Optional[int] = None
    prompt: Optional[str] = None
    suggested_fix: Optional[str] = None

    model_config = {"from_attributes": True}


class RunDetailSchema(AgentRunSchema):
    steps: List[ExecutionStepSchema] = []
    diagnosis: Optional[DiagnosisResultSchema] = None


class CreateRunSchema(RunDetailSchema):
    """Used for POST /api/runs — allows full run submission."""
    pass


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------

class ReplayRequestSchema(BaseModel):
    prompt: str
    start_step: int
    replay_mode: Optional[str] = "cached"  # 'cached' | 'isolated' | 'live'


class ReplayStepSchema(BaseModel):
    step_number: int
    name: str
    kind: str
    summary: str
    status: str
    execution_mode: str  # 'reused' | 're-run' | 'simulated'


class ReplayStatsSchema(BaseModel):
    full_tokens: int = 0
    replay_tokens: int = 0
    tokens_saved: int = 0
    tokens_saved_percent: int = 0
    full_duration_ms: int = 0
    replay_duration_ms: int = 0
    duration_saved_ms: int = 0


class ReplayResultSchema(BaseModel):
    run_id: str
    status: str  # 'ok' | 'error' | 'inconclusive'
    answer_before: str
    answer_after: str
    verification_note: Optional[str] = None  # explains simulation vs genuine execution
    steps: List[ReplayStepSchema] = []
    stats: ReplayStatsSchema


# ---------------------------------------------------------------------------
# Batch Verification
# ---------------------------------------------------------------------------

class BatchItemSchema(BaseModel):
    id: str
    task: str
    is_guard: bool
    before_status: str   # 'pass' | 'fail'
    after_status: str    # 'pass' | 'fail'
    delta_tokens: int
    outcome: str         # 'Fixed' | 'Still failing' | 'Regression' | 'Unchanged' | 'Inconclusive' | 'Candidate fix (unverified)'
    note: str


class BatchVerificationRequestSchema(BaseModel):
    run_ids: List[str]
    modified_prompt: str
    target_rule: Optional[str] = None


class BatchVerificationSummarySchema(BaseModel):
    total: int
    fixed: int
    failed_initial: int
    regressions: int
    guard_total: int
    unchanged: int
    inconclusive: int = 0
    candidate: int = 0


class BatchVerificationResponseSchema(BaseModel):
    results: List[BatchItemSchema]
    summary: BatchVerificationSummarySchema


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class AnalyticsMetricsSchema(BaseModel):
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    total_spend: float
    most_common_mistake: Optional[str] = None
    most_common_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponseSchema(BaseModel):
    status: str
    service: str
    timestamp: str
    database_records: int
    version: str = "2.0.0"
