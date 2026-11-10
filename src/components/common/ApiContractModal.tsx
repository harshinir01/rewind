import React from 'react';
import { X, ExternalLink, ShieldCheck } from 'lucide-react';
import { useBackend } from '../../context/BackendContext';

export const ApiContractModal: React.FC = () => {
  const { isContractOpen, setIsContractOpen, connection } = useBackend();

  if (!isContractOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in">
      <div
        className="panel max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl relative"
        style={{ background: 'var(--surface)', borderColor: 'var(--line)' }}
      >
        <header className="flex items-center justify-between px-4 py-3 border-b shrink-0" style={{ borderColor: 'var(--line)' }}>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5" style={{ color: 'var(--accent)' }} />
            <h2 className="text-base font-semibold">FastAPI Backend API Contract</h2>
          </div>
          <button
            type="button"
            onClick={() => setIsContractOpen(false)}
            className="btn ghost p-1 min-h-0 h-8 w-8 justify-center rounded-md"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        <div className="p-4 overflow-y-auto space-y-4 text-xs">
          <p style={{ color: 'var(--muted)' }}>
            Rewind directly queries your FastAPI backend. Below are the required REST endpoints and data contracts. All code is defined in <code className="mono">backend/main.py</code>.
          </p>

          <div className="space-y-3">
            <div className="p-3 rounded-lg border" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-xs mono text-[var(--accent)]">GET /api/runs</span>
                <span className="text-[11px] uppercase tracking-wide">All Runs & Filters</span>
              </div>
              <p className="text-[11px] mb-2" style={{ color: 'var(--muted)' }}>
                Query params: <code>search</code>, <code>status</code> (all/failed/passed), <code>limit</code>, <code>offset</code>
              </p>
              <pre className="p-2 rounded mono text-[11px] overflow-x-auto bg-[var(--surface)]">
{`Response: [
  {
    "id": "r-2041",
    "agent": "sql-agent",
    "task": "Revenue by region, Q3",
    "ok": false,
    "label": "ignored_error",
    "steps_count": 7,
    "cost": 0.041,
    "duration": "14.2s",
    "started_at": "Today 10:38",
    "fail_step": 5
  }
]`}
              </pre>
            </div>

            <div className="p-3 rounded-lg border" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-xs mono text-[var(--accent)]">GET /api/runs/&#123;id&#125;</span>
                <span className="text-[11px] uppercase tracking-wide">Run Details & Steps</span>
              </div>
              <pre className="p-2 rounded mono text-[11px] overflow-x-auto bg-[var(--surface)]">
{`Response: RunDetail {
  id, agent, task, ok, label, steps_count, cost, duration, started_at, fail_step,
  prompt: "...",
  suggested_fix: "...",
  steps: [
    {
      "step_number": 1,
      "name": "plan",
      "kind": "llm", // "llm" | "tool" | "system"
      "duration_ms": 820,
      "tokens": 412,
      "input": "...",
      "output": "...",
      "status": "ok" // "ok" | "error" | "fail"
    }
  ],
  diagnosis?: DiagnosisResult
}`}
              </pre>
            </div>

            <div className="p-3 rounded-lg border" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-xs mono text-[var(--accent)]">POST /api/runs/&#123;id&#125;/diagnose</span>
                <span className="text-[11px] uppercase tracking-wide">Fault Localization</span>
              </div>
              <pre className="p-2 rounded mono text-[11px] overflow-x-auto bg-[var(--surface)]">
{`Response: {
  "failure_category": "ignored_error",
  "reason": "A database search failed at step 4...",
  "evidence": [{"from": "Step 4 output", "text": "..."}],
  "fired_detectors": {"Ignored tool error": "..."},
  "judge_verdict": "Agrees with step 5...",
  "relevant_step": 5,
  "confidence": 0.95
}`}
              </pre>
            </div>

            <div className="p-3 rounded-lg border" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-xs mono text-[var(--accent)]">POST /api/runs/&#123;id&#125;/replay</span>
                <span className="text-[11px] uppercase tracking-wide">Cached Step Replay</span>
              </div>
              <pre className="p-2 rounded mono text-[11px] overflow-x-auto bg-[var(--surface)]">
{`Request: {
  "prompt": "Modified agent instructions...",
  "start_step": 5,
  "replay_mode": "cached"
}
Response: {
  "status": "ok",
  "answer_before": "₹0 in all regions",
  "answer_after": "Q3 revenue by region: South ₹4.8 Cr...",
  "steps": [...],
  "stats": {"tokens_saved": 2120, "duration_saved_ms": 9100}
}`}
              </pre>
            </div>

            <div className="p-3 rounded-lg border" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-xs mono text-[var(--accent)]">POST /api/batch/verify</span>
                <span className="text-[11px] uppercase tracking-wide">Batch Testing</span>
              </div>
              <pre className="p-2 rounded mono text-[11px] overflow-x-auto bg-[var(--surface)]">
{`Request: {
  "run_ids": ["r-2041", "r-2029"],
  "modified_prompt": "..."
}
Response: {
  "results": [...],
  "summary": {"total": 9, "fixed": 5, "regressions": 1, ...}
}`}
              </pre>
            </div>
          </div>
        </div>

        <div className="px-4 py-3 border-t shrink-0 flex justify-end" style={{ borderColor: 'var(--line)' }}>
          <button
            type="button"
            onClick={() => setIsContractOpen(false)}
            className="btn primary px-4 py-1.5 text-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
