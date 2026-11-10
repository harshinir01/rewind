import React, { useState, useEffect, useCallback } from 'react';
import { Play, RefreshCw, AlertTriangle, Layers, Database, AlertCircle } from 'lucide-react';
import { getBatchRuns, executeBatchVerification } from '../api/batch';
import { BatchItem, BatchVerificationResponse } from '../types';
import { formatNumber } from '../utils/formatters';

export const BatchVerification: React.FC = () => {
  const [items, setItems] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [ruleDiff, setRuleDiff] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResponse, setVerifyResponse] = useState<BatchVerificationResponse | null>(null);
  const [filterGroup, setFilterGroup] = useState<'all' | 'failed' | 'guard'>('all');

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getBatchRuns();
      setItems(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch batch test runs from FastAPI.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleRunBatch = async () => {
    if (!ruleDiff.trim()) return;
    setIsVerifying(true);
    setError(null);
    try {
      const res = await executeBatchVerification({
        run_ids: items.map((i) => i.id),
        modified_prompt: ruleDiff,
        target_rule: ruleDiff,
      });
      setVerifyResponse(res);
      setItems(res.results);
    } catch (err: any) {
      setError(err.message || 'Batch verification request failed on backend.');
    } finally {
      setIsVerifying(false);
    }
  };

  const filteredItems = items.filter((item) => {
    if (filterGroup === 'failed') return !item.is_guard;
    if (filterGroup === 'guard') return item.is_guard;
    return true;
  });

  const summary = verifyResponse?.summary;
  const fixedCount = summary?.fixed ?? items.filter((i) => i.before_status === 'fail' && i.after_status === 'pass').length;
  const failedInitial = summary?.failed_initial ?? items.filter((i) => i.before_status === 'fail').length;
  const regressionCount = summary?.regressions ?? items.filter((i) => i.before_status === 'pass' && i.after_status === 'fail').length;
  const guardCount = summary?.guard_total ?? items.filter((i) => i.is_guard).length;

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-xl sm:text-2xl font-semibold">Test a fix on many runs</h1>
        <p className="text-sm max-w-[72ch]" style={{ color: 'var(--muted)' }}>
          See whether one change to your agent's instructions fixes several failed runs at once, and check
          that it does not break runs that already worked.
        </p>
      </div>

      {/* The Change We Are Testing Panel */}
      <section className="panel flex flex-col" aria-label="The change we are testing">
        <header className="flex items-center justify-between p-3 border-b" style={{ borderColor: 'var(--line)' }}>
          <div className="flex flex-col gap-0.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider">The change we are testing</h3>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              Enter the instruction rule or prompt change to test across all recorded runs.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRunBatch}
            disabled={isVerifying || items.length === 0 || ruleDiff.trim() === ''}
            className="btn primary text-xs py-1.5 px-3 min-h-0 h-8"
            title={ruleDiff.trim() === '' ? 'Enter a query to run batch verification' : 'Run batch verification'}
          >
            {isVerifying ? (
              <>
                <span className="spin" />
                Running batch test...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                Run batch verification
              </>
            )}
          </button>
        </header>

        <div className="p-3.5 flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="rule-query" className="text-xs font-medium" style={{ color: 'var(--ink)' }}>
              Instruction rule to add to agent prompt:
            </label>
            <textarea
              id="rule-query"
              value={ruleDiff}
              onChange={(e) => setRuleDiff(e.target.value)}
              rows={4}
              placeholder="Enter your query here... e.g. If a tool returns an error, never treat it as an empty result. Read the error, correct the input, and retry once."
              className="w-full p-3 rounded-lg border mono text-xs leading-relaxed outline-none resize-y"
              style={{
                background: 'var(--surface)',
                borderColor: ruleDiff.trim() === '' ? 'var(--bad-line)' : 'var(--line)',
                color: 'var(--ink)',
                minHeight: '80px',
              }}
              disabled={isVerifying}
            />
            {ruleDiff.trim() === '' && (
              <p className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--bad-ink)' }}>
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                Please enter an instruction rule before running.
              </p>
            )}
          </div>

          <p className="text-xs" style={{ color: 'var(--muted)' }}>
            This rule will be appended to the agent's prompt and tested against failed runs (to verify repair) and working runs (as regression safety checks).
          </p>
        </div>
      </section>

      {/* Summary Stats Cards */}
      <div className="flex flex-wrap gap-2.5">
        <div className="flex flex-col gap-0.5 px-3 py-2 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[140px] flex-1">
          <b className="text-sm font-semibold" style={{ color: 'var(--ok)' }}>
            {isVerifying ? 'Running...' : `Fixed ${fixedCount} of ${failedInitial}`}
          </b>
          <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
            Failed runs that now work
          </span>
        </div>

        <div className="flex flex-col gap-0.5 px-3 py-2 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[140px] flex-1">
          <b
            className="text-sm font-semibold"
            style={{ color: regressionCount > 0 ? 'var(--bad-ink)' : 'inherit' }}
          >
            {isVerifying ? 'Checking...' : `Broke ${regressionCount} of ${guardCount}`}
          </b>
          <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
            Working runs that now fail (Regressions)
          </span>
        </div>

        <div className="flex flex-col gap-0.5 px-3 py-2 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[140px] flex-1">
          <b className="text-sm font-semibold num">{items.length}</b>
          <span className="text-[11px]" style={{ color: 'var(--muted)' }}>
            Total verification test suite
          </span>
        </div>
      </div>

      {/* Filter toolbar */}
      <div className="flex items-center justify-between gap-2">
        <div className="inline-flex border rounded-lg overflow-hidden bg-[var(--surface)] text-xs" style={{ borderColor: 'var(--line)' }}>
          <button
            type="button"
            onClick={() => setFilterGroup('all')}
            className={`px-3 py-1.5 font-medium cursor-pointer border-0 ${
              filterGroup === 'all' ? 'bg-[var(--accent-soft)] text-[var(--accent-ink)]' : 'text-[var(--muted)]'
            }`}
          >
            All ({items.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterGroup('failed')}
            className={`px-3 py-1.5 font-medium cursor-pointer border-l border-[var(--line)] ${
              filterGroup === 'failed' ? 'bg-[var(--accent-soft)] text-[var(--accent-ink)]' : 'text-[var(--muted)]'
            }`}
          >
            Failed Runs ({failedInitial})
          </button>
          <button
            type="button"
            onClick={() => setFilterGroup('guard')}
            className={`px-3 py-1.5 font-medium cursor-pointer border-l border-[var(--line)] ${
              filterGroup === 'guard' ? 'bg-[var(--accent-soft)] text-[var(--accent-ink)]' : 'text-[var(--muted)]'
            }`}
          >
            Safety Checks ({guardCount})
          </button>
        </div>

        <button
          type="button"
          onClick={() => fetchItems()}
          disabled={loading || isVerifying}
          className="btn ghost text-xs py-1 px-2 h-7 min-h-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Results Table */}
      <div className="panel">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse min-w-[860px] text-left text-xs">
            <thead>
              <tr style={{ background: 'var(--code-bg)' }}>
                <th className="p-2.5 px-3 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Run ID
                </th>
                <th className="p-2.5 px-3 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Question / Task
                </th>
                <th className="p-2.5 px-3 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Group
                </th>
                <th className="p-2.5 px-3 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Before
                </th>
                <th className="p-2.5 px-3 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  After
                </th>
                <th className="p-2.5 px-3 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Outcome
                </th>
                <th className="p-2.5 px-3 border-b text-right" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Tokens vs starting over
                </th>
                <th className="p-2.5 px-3 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  What happened
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center" style={{ color: 'var(--muted)' }}>
                    <div className="flex items-center justify-center gap-2">
                      <span className="spin" />
                      <span>Loading batch test suite from FastAPI backend...</span>
                    </div>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={8} className="p-6 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <AlertTriangle className="w-5 h-5" style={{ color: 'var(--bad)' }} />
                      <span className="text-xs" style={{ color: 'var(--bad-ink)' }}>
                        {error}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-10 text-center">
                    <div className="flex flex-col items-center gap-2 max-w-sm mx-auto">
                      <Layers className="w-8 h-8" style={{ color: 'var(--muted)' }} />
                      <b className="font-semibold text-xs">No Batch Test Runs Found</b>
                      <p className="text-xs" style={{ color: 'var(--muted)' }}>
                        The FastAPI backend has no batch test suite records at <code className="mono">/api/batch/runs</code>.
                        Once populated or seeded, multi-run prompt verification will run here.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredItems.map((r) => {
                  const isPending = isVerifying;
                  return (
                    <tr
                      key={r.id}
                      className="border-b transition-colors hover:bg-[var(--hover)]"
                      style={{ borderColor: 'var(--line)' }}
                    >
                      <td className="p-2.5 px-3 mono font-medium">{r.id}</td>
                      <td className="p-2.5 px-3 max-w-[260px] truncate" title={r.task}>
                        {r.task}
                      </td>
                      <td className="p-2.5 px-3">
                        {r.is_guard ? (
                          <span style={{ color: 'var(--muted)' }}>Safety check</span>
                        ) : (
                          <span>Failed before</span>
                        )}
                      </td>
                      <td className="p-2.5 px-3">
                        <span className={`chip ${r.before_status === 'fail' ? 'fail' : 'pass'}`}>
                          {r.before_status === 'fail' ? 'Failed' : 'Worked'}
                        </span>
                      </td>
                      <td className="p-2.5 px-3">
                        {isPending ? (
                          <span style={{ color: 'var(--muted)' }}>Running</span>
                        ) : (
                          <span className={`chip ${r.after_status === 'pass' ? 'pass' : 'fail'}`}>
                            {r.after_status === 'pass' ? 'Worked' : 'Failed'}
                          </span>
                        )}
                      </td>
                      <td className="p-2.5 px-3 font-medium">
                        {isPending ? (
                          ''
                        ) : r.outcome === 'Fixed' ? (
                          <span style={{ color: 'var(--ok)' }}>Fixed</span>
                        ) : r.outcome === 'Regression' ? (
                          <span style={{ color: 'var(--bad-ink)' }}>Now broken</span>
                        ) : r.outcome === 'Still failing' ? (
                          <span style={{ color: 'var(--bad-ink)' }}>Still failing</span>
                        ) : (
                          <span style={{ color: 'var(--muted)' }}>No change</span>
                        )}
                      </td>
                      <td className="p-2.5 px-3 text-right num">
                        {isPending
                          ? ''
                          : r.delta_tokens === 0
                          ? '0'
                          : (r.delta_tokens > 0 ? '+' : '−') + formatNumber(Math.abs(r.delta_tokens))}
                      </td>
                      <td className="p-2.5 px-3 min-w-[220px]" style={{ color: 'var(--muted)' }}>
                        {isPending ? '' : r.note}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
