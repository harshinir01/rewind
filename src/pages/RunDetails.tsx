import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ChevronRight,
  AlertTriangle,
  CheckCircle,
  Undo2,
  RefreshCw,
  Sparkles,
  Info,
  ArrowUp,
  ArrowDown,
  Terminal,
} from 'lucide-react';
import { getRunById } from '../api/runs';
import { requestDiagnosis } from '../api/diagnosis';
import { RunDetail, ExecutionStep, StepKind } from '../types';
import {
  getFailureLabel,
  KIND_LABELS,
  KIND_DESCRIPTIONS,
  DETECTOR_NAMES,
  formatDuration,
  formatNumber,
  formatCost,
} from '../utils/formatters';

const DEFAULT_DETECTORS = [
  'Repeated identical call',
  'Ignored tool error',
  'Argument absent from context',
  'Output schema mismatch',
  'Step or budget limit',
];

export const RunDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<RunDetail | null>(null);
  const [selectedStepIndex, setSelectedStepIndex] = useState<number>(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [diagnosisError, setDiagnosisError] = useState<string | null>(null);

  const fetchRun = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getRunById(id);
      setRun(data);
      // Default selected step to failStep or 1
      const initial = data.fail_step && data.fail_step > 0 ? data.fail_step : 1;
      setSelectedStepIndex(initial);
    } catch (err: any) {
      setError(err.message || `Failed to fetch run details for ${id}`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  // Keyboard navigation for steps (Up / Down)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (/INPUT|TEXTAREA|SELECT/.test((e.target as HTMLElement)?.tagName)) return;
      if (!run || !run.steps || run.steps.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedStepIndex((prev) => Math.min(run.steps.length, prev + 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedStepIndex((prev) => Math.max(1, prev - 1));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [run]);

  const handleRunDiagnosis = async () => {
    if (!id) return;
    setIsDiagnosing(true);
    setDiagnosisError(null);
    try {
      const diag = await requestDiagnosis(id);
      setRun((prev) => (prev ? { ...prev, diagnosis: diag } : null));
    } catch (err: any) {
      setDiagnosisError(err.message || 'Diagnosis request failed on the backend.');
    } finally {
      setIsDiagnosing(false);
    }
  };

  if (loading) {
    return (
      <div className="panel p-12 text-center flex flex-col items-center justify-center gap-3">
        <span className="spin" />
        <span className="text-sm" style={{ color: 'var(--muted)' }}>
          Loading execution trace for {id}...
        </span>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="panel p-8 text-center flex flex-col items-center justify-center gap-3">
        <AlertTriangle className="w-8 h-8" style={{ color: 'var(--bad)' }} />
        <b className="font-semibold text-sm" style={{ color: 'var(--bad-ink)' }}>
          Run Trace Not Found
        </b>
        <p className="text-xs max-w-md" style={{ color: 'var(--muted)' }}>
          {error || `Run '${id}' does not exist in the connected FastAPI backend.`}
        </p>
        <div className="flex gap-2 mt-2">
          <Link to="/" className="btn text-xs">
            Return to All Runs
          </Link>
          <button type="button" onClick={() => fetchRun()} className="btn primary text-xs">
            Retry Fetch
          </button>
        </div>
      </div>
    );
  }

  const steps = run.steps || [];
  const currentStep: ExecutionStep | undefined = steps[selectedStepIndex - 1];
  const failStepNum = run.fail_step;
  const diagnosis = run.diagnosis;

  return (
    <div className="flex flex-col gap-4">
      {/* Page Header & Breadcrumbs */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--muted)' }}>
          <Link to="/" className="hover:underline">
            All runs
          </Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <span className="mono font-medium">{run.id}</span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="text-xl sm:text-2xl font-semibold">{run.task}</h1>
            {run.label && <span className="chip fail text-xs">{getFailureLabel(run.label)}</span>}
          </div>

          <div className="flex items-center gap-2">
            {failStepNum && (
              <Link to={`/replay/${run.id}`} className="btn primary text-xs py-1.5 px-3">
                <Undo2 className="w-3.5 h-3.5" />
                Try a fix from step {failStepNum}
              </Link>
            )}
            <button
              type="button"
              onClick={() => fetchRun()}
              className="btn ghost text-xs py-1.5 px-2"
              title="Refresh trace"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs" style={{ color: 'var(--muted)' }}>
          <span>
            Agent: <span className="mono font-medium">{run.agent}</span>
          </span>
          <span>{steps.length} steps</span>
          <span>{formatCost(run.cost)} spent</span>
          <span>{run.duration || formatDuration(run.duration_ms)} total</span>
          <span>Started {run.started_at}</span>
        </div>
      </div>

      {/* Callout */}
      <div
        className="p-3 px-3.5 rounded-xl border flex items-start gap-3 text-xs"
        style={{
          backgroundColor: 'var(--accent-soft)',
          borderColor: 'var(--accent-line)',
          color: 'var(--ink)',
        }}
      >
        <Info className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--accent-ink)' }} />
        <div>
          {failStepNum ? (
            <span>
              <b>Start here.</b> Your agent went wrong at step <b>{failStepNum}</b>, marked in red on the left.
              Read the explanation on the right, then press <b>Try a fix</b> to test a prompt change.
            </span>
          ) : (
            <span>
              This agent execution completed successfully with no recorded faults. You can inspect each step's
              inputs and outputs below.
            </span>
          )}
        </div>
      </div>

      {/* 3-Column Layout from Rewind.html */}
      <div className="grid grid-cols-1 lg:grid-cols-[270px_minmax(0,1fr)_340px] gap-3.5 items-start">
        {/* Column 1: Execution Timeline */}
        <section className="panel" aria-label="What the agent did">
          <header className="flex items-center justify-between p-3 border-b" style={{ borderColor: 'var(--line)' }}>
            <h3 className="text-xs font-semibold uppercase tracking-wider">What the agent did</h3>
            <span className="text-[11px] flex items-center gap-1" style={{ color: 'var(--muted)' }}>
              Use ↑ ↓ keys
            </span>
          </header>

          <ol className="list-none m-0 p-0 divide-y" style={{ borderColor: 'var(--line)' }}>
            {steps.length === 0 ? (
              <li className="p-4 text-xs text-center" style={{ color: 'var(--muted)' }}>
                No execution steps recorded for this run.
              </li>
            ) : (
              steps.map((s, idx) => {
                const stepNum = s.step_number || idx + 1;
                const isSelected = stepNum === selectedStepIndex;
                const isFailure = stepNum === failStepNum;
                const isError = s.status === 'error';

                return (
                  <li key={stepNum}>
                    <button
                      type="button"
                      onClick={() => setSelectedStepIndex(stepNum)}
                      className={`w-full text-left p-2.5 px-3 transition-colors flex flex-col gap-1 cursor-pointer border-0 ${
                        isSelected ? 'bg-[var(--accent-soft)]' : 'hover:bg-[var(--hover)] bg-transparent'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span
                            className={`w-2 h-2 rounded-full shrink-0 ${
                              isFailure
                                ? 'bg-[var(--bad)] ring-2 ring-[var(--bad-soft)]'
                                : isError
                                ? 'border border-[var(--bad)]'
                                : 'border border-[var(--muted)]'
                            }`}
                          />
                          <span className="mono text-xs font-medium truncate">
                            {String(stepNum).padStart(2, '0')} {s.name}
                          </span>
                        </div>
                        <span className="text-[11px] num shrink-0" style={{ color: 'var(--muted)' }}>
                          {formatDuration(s.duration_ms)}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5 pl-4 flex-wrap">
                        <span className="tag text-[10px]">{KIND_LABELS[s.kind] || s.kind}</span>
                        {s.tokens > 0 && (
                          <span className="text-[10px] num" style={{ color: 'var(--muted)' }}>
                            {formatNumber(s.tokens)} tok
                          </span>
                        )}
                        {isFailure && <span className="tag fail text-[10px]">Mistake is here</span>}
                        {isError && !isFailure && <span className="tag fail text-[10px]">Error</span>}
                      </div>
                    </button>
                  </li>
                );
              })
            )}
          </ol>

          <div className="p-2.5 px-3 text-[11px] border-t" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)', color: 'var(--muted)' }}>
            Tokens are small pieces of text an AI reads and writes. Replaying from failure saves tokens.
          </div>
        </section>

        {/* Column 2: Step Inspector */}
        <section className="panel" aria-label="Step detail">
          {currentStep ? (
            <>
              <header className="flex items-center justify-between p-3 border-b" style={{ borderColor: 'var(--line)' }}>
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold">Step {selectedStepIndex}</h2>
                    <span className="mono text-xs" style={{ color: 'var(--muted)' }}>
                      {currentStep.name}
                    </span>
                  </div>
                  <p className="text-xs" style={{ color: 'var(--muted)' }}>
                    {KIND_DESCRIPTIONS[currentStep.kind] || 'Execution step'}
                  </p>
                </div>

                <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--muted)' }}>
                  <span className="tag text-xs">{KIND_LABELS[currentStep.kind]}</span>
                  {currentStep.duration_ms > 0 && (
                    <span className="num">{formatDuration(currentStep.duration_ms)}</span>
                  )}
                  {currentStep.tokens > 0 && (
                    <span className="num">{formatNumber(currentStep.tokens)} tokens</span>
                  )}
                </div>
              </header>

              <div className="p-3.5 flex flex-col gap-3.5">
                <div className="flex flex-col gap-1.5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
                    What went in
                  </h3>
                  <pre className="code-block text-xs">{currentStep.input || '(no input payload)'}</pre>
                </div>

                <div className="flex flex-col gap-1.5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
                    {currentStep.status === 'error' ? 'What came out (an error)' : 'What came out'}
                  </h3>
                  <pre
                    className={`code-block text-xs ${
                      currentStep.status === 'error' ? 'err' : ''
                    }`}
                  >
                    {currentStep.output || '(no output payload)'}
                  </pre>
                </div>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-xs" style={{ color: 'var(--muted)' }}>
              Select a step on the left to inspect its inputs, outputs, and parameters.
            </div>
          )}
        </section>

        {/* Column 3: Diagnosis Panel */}
        <aside className="panel flex flex-col" aria-label="What went wrong">
          <header className="flex items-center justify-between p-3 border-b" style={{ borderColor: 'var(--line)' }}>
            <h3 className="text-xs font-semibold uppercase tracking-wider">What went wrong</h3>
            {run.label && <span className="chip fail text-xs">{getFailureLabel(run.label)}</span>}
          </header>

          <div className="p-3.5 flex flex-col gap-4 text-xs">
            {diagnosis ? (
              <>
                <div className="flex flex-col gap-1.5">
                  <h2 className="text-sm font-semibold">
                    The mistake happened at step {diagnosis.relevant_step || failStepNum || 1} of {steps.length}
                  </h2>
                  <p className="leading-relaxed" style={{ color: 'var(--ink)' }}>
                    {diagnosis.reason}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Link
                    to={`/replay/${run.id}`}
                    className="btn primary text-xs py-1.5 px-3 flex items-center gap-1.5"
                  >
                    <Undo2 className="w-3.5 h-3.5" />
                    Try a fix from step {diagnosis.relevant_step || failStepNum || 1}
                  </Link>
                  {selectedStepIndex !== (diagnosis.relevant_step || failStepNum) && (
                    <button
                      type="button"
                      onClick={() => setSelectedStepIndex(diagnosis.relevant_step || failStepNum || 1)}
                      className="btn text-xs py-1.5 px-2.5"
                    >
                      Jump to mistake step
                    </button>
                  )}
                </div>

                {/* Evidence */}
                {diagnosis.evidence && diagnosis.evidence.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
                      Proof from the run
                    </h3>
                    {diagnosis.evidence.map((ev, i) => (
                      <div key={i} className="flex flex-col gap-1">
                        <span className="text-[11px] font-medium" style={{ color: 'var(--muted)' }}>
                          {ev.from}
                        </span>
                        <pre className="code-block text-[11px] max-h-24 p-2">{ev.text}</pre>
                      </div>
                    ))}
                  </div>
                )}

                {/* Automatic Checks */}
                <div className="flex flex-col gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
                    Automatic checks
                  </h3>
                  <ul className="list-none m-0 p-0 flex flex-col gap-2">
                    {DEFAULT_DETECTORS.map((detectorName) => {
                      const hitMsg = diagnosis.fired_detectors?.[detectorName];
                      return (
                        <li key={detectorName} className="flex items-start gap-2">
                          {hitMsg ? (
                            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--bad)' }} />
                          ) : (
                            <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--muted)' }} />
                          )}
                          <div className="flex flex-col">
                            <span className={hitMsg ? 'font-medium' : ''} style={{ color: hitMsg ? 'var(--bad-ink)' : 'var(--muted)' }}>
                              {DETECTOR_NAMES[detectorName] || detectorName}
                            </span>
                            {hitMsg && (
                              <small className="text-[11px] mt-0.5" style={{ color: 'var(--muted)' }}>
                                {hitMsg}
                              </small>
                            )}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                {/* AI Reviewer / Judge */}
                {diagnosis.judge_verdict && (
                  <div className="flex flex-col gap-1 pt-1">
                    <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
                      AI reviewer verdict
                    </h3>
                    <p className="leading-relaxed" style={{ color: 'var(--muted)' }}>
                      {diagnosis.judge_verdict}
                    </p>
                  </div>
                )}
              </>
            ) : (
              <div className="flex flex-col items-center justify-center p-6 text-center gap-3">
                <Sparkles className="w-6 h-6" style={{ color: 'var(--muted)' }} />
                <b className="font-semibold text-xs">Run Not Diagnosed Yet</b>
                <p className="text-xs" style={{ color: 'var(--muted)' }}>
                  This run does not have an attached diagnosis from the backend. You can trigger automated fault localization now.
                </p>
                <button
                  type="button"
                  onClick={handleRunDiagnosis}
                  disabled={isDiagnosing}
                  className="btn primary text-xs py-1.5 px-3"
                >
                  {isDiagnosing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Run Fault Diagnosis'}
                </button>
              </div>
            )}
          </div>

          <div className="p-2.5 px-3 text-[11px] border-t mt-auto" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)', color: 'var(--muted)' }}>
            Trying a fix reuses steps 1 to {(failStepNum || 1) - 1} from this run, so you only pay for what changes.
          </div>
        </aside>
      </div>
    </div>
  );
};
