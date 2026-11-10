import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ChevronRight,
  Play,
  RotateCcw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ShieldAlert,
  Sparkles,
  Layers,
} from 'lucide-react';
import { getRunById } from '../api/runs';
import { executeReplay } from '../api/replay';
import { RunDetail, ReplayResult, ExecutionStep } from '../types';
import {
  formatDuration,
  formatNumber,
  truncateFirstLine,
  KIND_LABELS,
} from '../utils/formatters';

export const TryFix: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [promptText, setPromptText] = useState('');
  const [originalPrompt, setOriginalPrompt] = useState('');
  const [startStep, setStartStep] = useState<number>(1);
  const [replayMode, setReplayMode] = useState<'cached' | 'isolated'>('cached');

  const [isReplaying, setIsReplaying] = useState(false);
  const [replayResult, setReplayResult] = useState<ReplayResult | null>(null);
  const [replayError, setReplayError] = useState<string | null>(null);

  const fetchRun = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getRunById(id);
      setRun(data);
      const f = data.fail_step && data.fail_step > 0 ? data.fail_step : 1;
      setStartStep(f);

      const basePrompt = data.prompt || 'You are an AI agent.';
      const suggestedFix = data.suggested_fix ? `\n${data.suggested_fix}` : '';
      setOriginalPrompt(basePrompt);
      setPromptText(basePrompt + suggestedFix);
    } catch (err: any) {
      setError(err.message || `Failed to load run ${id}`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRun();
  }, [fetchRun]);

  const handleResetPrompt = () => {
    setPromptText(originalPrompt);
  };

  const handleRunReplay = async () => {
    if (!id || !run) return;
    setIsReplaying(true);
    setReplayError(null);
    setReplayResult(null);

    try {
      const result = await executeReplay(id, {
        prompt: promptText,
        start_step: startStep,
        replay_mode: replayMode,
      });
      setReplayResult(result);
    } catch (err: any) {
      setReplayError(err.message || 'Replay request failed on the backend.');
    } finally {
      setIsReplaying(false);
    }
  };

  if (loading) {
    return (
      <div className="panel p-12 text-center flex flex-col items-center justify-center gap-3">
        <span className="spin" />
        <span className="text-sm" style={{ color: 'var(--muted)' }}>
          Loading replay workspace for {id}...
        </span>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="panel p-8 text-center flex flex-col items-center justify-center gap-3">
        <AlertTriangle className="w-8 h-8" style={{ color: 'var(--bad)' }} />
        <b className="font-semibold text-sm" style={{ color: 'var(--bad-ink)' }}>
          Run Not Available
        </b>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          {error || `Run ${id} could not be loaded.`}
        </p>
        <Link to="/" className="btn text-xs mt-2">
          Back to All Runs
        </Link>
      </div>
    );
  }

  const steps = run.steps || [];
  const originalFailureSteps = steps.slice(Math.max(0, startStep - 1));
  const stats = replayResult?.stats;

  return (
    <div className="flex flex-col gap-4">
      {/* Breadcrumb & Header */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--muted)' }}>
          <Link to="/" className="hover:underline">
            All runs
          </Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <Link to={`/run/${run.id}`} className="mono hover:underline font-medium">
            {run.id}
          </Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <span>Try a fix</span>
        </div>

        <h1 className="text-xl sm:text-2xl font-semibold">Try a fix from step {startStep}</h1>
        <p className="text-sm max-w-[70ch]" style={{ color: 'var(--muted)' }}>
          Change the instructions you give your agent, then run it again from the mistake. Earlier steps are
          reused and tools are safely simulated or cached, so it is fast, cheap and safe.
        </p>
      </div>

      {/* Main Replay Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)] gap-3.5 items-start">
        {/* Left: Prompt Editor & Controls */}
        <section className="panel flex flex-col" aria-label="Agent instructions">
          <header className="flex items-center justify-between p-3 border-b" style={{ borderColor: 'var(--line)' }}>
            <h3 className="text-xs font-semibold uppercase tracking-wider">1. Agent instructions</h3>
            <button
              type="button"
              onClick={handleResetPrompt}
              className="btn ghost text-xs py-1 px-2 min-h-0 h-7"
              title="Reset prompt back to original"
            >
              <RotateCcw className="w-3 h-3" />
              Undo edits
            </button>
          </header>

          <div className="p-3.5 flex flex-col gap-3.5">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="prompt" className="text-xs" style={{ color: 'var(--muted)' }}>
                Review and tweak the prompt. You can add guardrails, instructions, or error-handling rules:
              </label>
              <textarea
                id="prompt"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                spellCheck={false}
                rows={9}
                className="w-full p-2.5 rounded-lg border mono text-xs leading-relaxed outline-none"
                style={{
                  background: 'var(--surface)',
                  borderColor: 'var(--line)',
                  color: 'var(--ink)',
                }}
              />
            </div>

            {/* Replay Safety Controls (Requirement 9) */}
            <div className="flex flex-col gap-1.5 p-2.5 rounded-lg border" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)' }}>
              <div className="flex items-center gap-1.5 text-xs font-semibold">
                <ShieldAlert className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
                <span>Replay Safety Mode</span>
              </div>
              <p className="text-[11px]" style={{ color: 'var(--muted)' }}>
                Prevents external side effects by serving cached tool responses or running in an isolated sandbox.
              </p>
              <div className="flex gap-2 mt-1">
                <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                  <input
                    type="radio"
                    name="replayMode"
                    value="cached"
                    checked={replayMode === 'cached'}
                    onChange={() => setReplayMode('cached')}
                  />
                  <span>Cached Tool Results (Safe)</span>
                </label>
                <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                  <input
                    type="radio"
                    name="replayMode"
                    value="isolated"
                    checked={replayMode === 'isolated'}
                    onChange={() => setReplayMode('isolated')}
                  />
                  <span>Isolated Sandbox</span>
                </label>
              </div>
            </div>

            {/* Step Selection */}
            <div className="flex items-center justify-between text-xs pt-1">
              <label htmlFor="startStepSelect" style={{ color: 'var(--muted)' }}>
                Replay starting from:
              </label>
              <select
                id="startStepSelect"
                value={startStep}
                onChange={(e) => setStartStep(Number(e.target.value))}
                className="p-1 px-2 border rounded text-xs mono"
                style={{ background: 'var(--surface)', borderColor: 'var(--line)' }}
              >
                {steps.map((s, idx) => (
                  <option key={idx + 1} value={idx + 1}>
                    Step {idx + 1}: {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <button
                type="button"
                onClick={handleRunReplay}
                disabled={isReplaying}
                className="btn primary w-full justify-center py-2 text-sm"
              >
                {isReplaying ? (
                  <>
                    <span className="spin" />
                    Replaying on backend...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    Run again from step {startStep}
                  </>
                )}
              </button>
            </div>

            {replayError && (
              <div className="p-2.5 rounded-lg border text-xs" style={{ background: 'var(--bad-soft)', borderColor: 'var(--bad-line)', color: 'var(--bad-ink)' }}>
                <b>Replay Failed:</b> {replayError}
              </div>
            )}
          </div>
        </section>

        {/* Right: Results & Before/After Comparison */}
        <div className="flex flex-col gap-3.5">
          {/* Result metrics bar */}
          <div className="flex flex-wrap gap-2.5">
            <div className="flex flex-col gap-0.5 px-3 py-2 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[130px] flex-1">
              {replayResult ? (
                <b
                  className="text-sm font-semibold"
                  style={{ color: replayResult.status === 'ok' ? 'var(--ok)' : 'var(--bad-ink)' }}
                >
                  {replayResult.status === 'ok' ? 'Worked' : 'Went wrong'}
                </b>
              ) : (
                <b className="text-sm font-semibold" style={{ color: 'var(--bad-ink)' }}>
                  Went wrong
                </b>
              )}
              <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
                {replayResult ? 'Replay Result' : 'Original run status'}
              </span>
            </div>

            {stats && (
              <>
                <div className="flex flex-col gap-0.5 px-3 py-2 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[130px] flex-1">
                  <b className="text-sm font-semibold num">
                    {formatNumber(stats.tokens_saved)} tok ({stats.tokens_saved_percent}%)
                  </b>
                  <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
                    Saved vs starting over
                  </span>
                </div>
                <div className="flex flex-col gap-0.5 px-3 py-2 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[130px] flex-1">
                  <b className="text-sm font-semibold num">
                    {formatDuration(stats.duration_saved_ms)} faster
                  </b>
                  <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
                    {formatDuration(stats.replay_duration_ms)} vs {formatDuration(stats.full_duration_ms)}
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Comparison Panels */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {/* Original Run Column */}
            <section className="panel flex flex-col" aria-label="Original run">
              <header className="flex items-center justify-between p-3 border-b" style={{ borderColor: 'var(--line)' }}>
                <h3 className="text-xs font-semibold uppercase tracking-wider">Original run</h3>
                <span className="chip fail text-xs">Went wrong</span>
              </header>

              <ul className="list-none m-0 p-0 divide-y divide-[var(--line)]">
                {originalFailureSteps.map((s, idx) => {
                  const stepNum = startStep + idx;
                  const isMistake = stepNum === run.fail_step;
                  return (
                    <li key={stepNum} className="p-2.5 px-3 flex flex-col gap-1 text-xs">
                      <div className="flex items-center justify-between gap-1.5">
                        <div className="flex items-center gap-1.5">
                          {isMistake ? (
                            <XCircle className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--bad)' }} />
                          ) : (
                            <CheckCircle className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--ok)' }} />
                          )}
                          <span className="mono font-medium">
                            {stepNum} {s.name}
                          </span>
                        </div>
                        <span className="tag text-[10px]">{KIND_LABELS[s.kind]}</span>
                      </div>
                      <span className="text-[11px] truncate pl-5" style={{ color: 'var(--muted)' }}>
                        {truncateFirstLine(s.output)}
                      </span>
                    </li>
                  );
                })}
              </ul>

              <div className="p-3 border-t mt-auto flex flex-col gap-1 text-xs" style={{ borderColor: 'var(--line)' }}>
                <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
                  Original final answer
                </span>
                <p className="font-medium text-xs leading-relaxed">
                  {steps[steps.length - 1]?.output || 'No final answer produced.'}
                </p>
              </div>
            </section>

            {/* With Your Fix Column */}
            <section className="panel flex flex-col" aria-label="With your fix">
              <header className="flex items-center justify-between p-3 border-b" style={{ borderColor: 'var(--line)' }}>
                <h3 className="text-xs font-semibold uppercase tracking-wider">With your fix</h3>
                <span
                  className={`chip text-xs ${
                    replayResult ? (replayResult.status === 'ok' ? 'pass' : 'fail') : ''
                  }`}
                >
                  {isReplaying ? 'Replaying...' : replayResult ? (replayResult.status === 'ok' ? 'Worked' : 'Went wrong') : 'Not run yet'}
                </span>
              </header>

              <ul className="list-none m-0 p-0 divide-y divide-[var(--line)]">
                <li
                  className="p-2.5 px-3 flex items-center justify-between gap-2 text-xs"
                  style={{ background: 'var(--code-bg)', color: 'var(--muted)' }}
                >
                  <span className="flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5" style={{ color: 'var(--ok)' }} />
                    <span>Steps 1 to {startStep - 1}</span>
                  </span>
                  <span className="tag text-[10px]">reused from cache</span>
                </li>

                {isReplaying ? (
                  <li className="p-8 text-center flex flex-col items-center justify-center gap-2 text-xs" style={{ color: 'var(--muted)' }}>
                    <span className="spin" />
                    <span>Executing re-evaluation on FastAPI backend...</span>
                  </li>
                ) : replayResult ? (
                  replayResult.steps.map((s, idx) => (
                    <li key={idx} className="p-2.5 px-3 flex flex-col gap-1 text-xs">
                      <div className="flex items-center justify-between gap-1.5">
                        <div className="flex items-center gap-1.5">
                          {s.status === 'ok' ? (
                            <CheckCircle className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--ok)' }} />
                          ) : (
                            <XCircle className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--bad)' }} />
                          )}
                          <span className="mono font-medium">
                            {s.step_number} {s.name}
                          </span>
                        </div>
                        <span className="tag text-[10px]">{s.execution_mode}</span>
                      </div>
                      <span className="text-[11px] truncate pl-5" style={{ color: 'var(--muted)' }}>
                        {s.summary}
                      </span>
                    </li>
                  ))
                ) : (
                  <li className="p-8 text-center text-xs" style={{ color: 'var(--muted)' }}>
                    Nothing has run yet. Press <b>"Run again from step {startStep}"</b> to test your prompt
                    modification against this execution.
                  </li>
                )}
              </ul>

              {replayResult && (
                <div className="p-3 border-t mt-auto flex flex-col gap-1 text-xs" style={{ borderColor: 'var(--line)' }}>
                  <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
                    Agent's replayed final answer
                  </span>
                  <p className="font-medium text-xs leading-relaxed">
                    {replayResult.answer_after}
                  </p>
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};
