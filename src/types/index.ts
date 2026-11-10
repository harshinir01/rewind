export type FailureCategory =
  | 'ignored_error'
  | 'infinite_loop'
  | 'goal_drift'
  | 'bad_arguments'
  | 'wrong_tool'
  | 'lost_context'
  | string;

export type StepKind = 'llm' | 'tool' | 'system';
export type StepStatus = 'ok' | 'error' | 'fail';

export interface ExecutionStep {
  step_number: number;
  name: string;
  kind: StepKind;
  duration_ms: number;
  tokens: number;
  input: string;
  output: string;
  status: StepStatus;
  tool_name?: string;
  error_message?: string;
}

export interface DiagnosisEvidence {
  from: string;
  text: string;
}

export interface DiagnosisResult {
  failure_category: FailureCategory;
  reason: string;
  evidence: DiagnosisEvidence[];
  fired_detectors: Record<string, string>;
  judge_verdict: string;
  relevant_step?: number;
  confidence?: number;
}

export interface AgentRun {
  id: string;
  agent: string;
  task: string;
  ok: boolean;
  label?: FailureCategory;
  steps_count: number;
  cost: number;
  duration: string;
  duration_ms?: number;
  started_at: string;
  fail_step?: number;
  prompt?: string;
  suggested_fix?: string;
}

export interface RunDetail extends AgentRun {
  steps: ExecutionStep[];
  diagnosis?: DiagnosisResult;
}

export interface ReplayRequest {
  prompt: string;
  start_step: number;
  replay_mode?: 'cached' | 'isolated' | 'live';
}

export interface ReplayStep {
  step_number: number;
  name: string;
  kind: StepKind;
  summary: string;
  status: 'ok' | 'error' | 'fail';
  execution_mode: 'reused' | 're-run' | 'simulated';
}

export interface ReplayResult {
  run_id: string;
  status: 'ok' | 'error' | 'inconclusive';
  answer_before: string;
  answer_after: string;
  verification_note?: string;
  steps: ReplayStep[];
  stats: {
    full_tokens: number;
    replay_tokens: number;
    tokens_saved: number;
    tokens_saved_percent: number;
    full_duration_ms: number;
    replay_duration_ms: number;
    duration_saved_ms: number;
  };
}

export interface BatchItem {
  id: string;
  task: string;
  is_guard: boolean;
  before_status: 'pass' | 'fail';
  after_status: 'pass' | 'fail';
  delta_tokens: number;
  outcome: 'Fixed' | 'Still failing' | 'Regression' | 'Unchanged' | 'Inconclusive' | 'Candidate fix (unverified)';
  note: string;
}

export interface BatchVerificationRequest {
  run_ids: string[];
  modified_prompt: string;
  target_rule?: string;
}

export interface BatchVerificationResponse {
  results: BatchItem[];
  summary: {
    total: number;
    fixed: number;
    failed_initial: number;
    regressions: number;
    guard_total: number;
    unchanged: number;
    inconclusive?: number;
    candidate?: number;
  };
}

export interface AnalyticsMetrics {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  success_rate: number;
  total_spend: number;
  most_common_mistake?: string;
  most_common_count?: number;
}

export interface BackendConnectionState {
  status: 'checking' | 'connected' | 'offline';
  baseUrl: string;
  latencyMs?: number;
  error?: string;
  lastChecked?: string;
}
