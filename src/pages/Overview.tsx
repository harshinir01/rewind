import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, RefreshCw, AlertCircle, Database, ArrowUpDown, ChevronRight } from 'lucide-react';
import { getRuns } from '../api/runs';
import { getAnalyticsMetrics } from '../api/analytics';
import { AgentRun, AnalyticsMetrics } from '../types';
import { getFailureLabel, formatDuration, formatCost } from '../utils/formatters';
import { useBackend } from '../context/BackendContext';

export const Overview: React.FC = () => {
  const { connection, setIsConfigOpen } = useBackend();
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'failed' | 'passed'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<'id' | 'cost' | 'steps_count' | 'duration'>('id');
  const [sortAsc, setSortAsc] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [runsData, metricsData] = await Promise.allSettled([
        getRuns({ search: searchQuery, status: filter }),
        getAnalyticsMetrics(),
      ]);

      if (runsData.status === 'fulfilled') {
        setRuns(runsData.value);
      } else {
        const err = runsData.reason;
        setError(err.message || 'Failed to fetch runs from FastAPI backend.');
        setRuns([]);
      }

      if (metricsData.status === 'fulfilled') {
        setMetrics(metricsData.value);
      } else {
        setMetrics(null);
      }
    } catch (err: any) {
      setError(err.message || 'Unexpected connection error.');
      setRuns([]);
      setMetrics(null);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Client-side sort on loaded backend records
  const sortedRuns = [...runs].sort((a, b) => {
    let diff = 0;
    if (sortField === 'id') diff = a.id.localeCompare(b.id);
    else if (sortField === 'cost') diff = (a.cost || 0) - (b.cost || 0);
    else if (sortField === 'steps_count') diff = (a.steps_count || 0) - (b.steps_count || 0);
    return sortAsc ? diff : -diff;
  });

  const toggleSort = (field: 'id' | 'cost' | 'steps_count') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  // Compute stats if metrics endpoint isn't supported separately by backend
  const totalRuns = metrics?.total_runs ?? runs.length;
  const failedRuns = metrics?.failed_runs ?? runs.filter(r => !r.ok).length;
  const totalSpend = metrics?.total_spend ?? runs.reduce((acc, r) => acc + (r.cost || 0), 0);
  const topMistake = metrics?.most_common_mistake;

  return (
    <div className="flex flex-col gap-5">
      {/* Hero band from Rewind.html */}
      <section
        className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,340px)] gap-6 items-center p-6 rounded-2xl border transition-all"
        style={{
          backgroundColor: 'var(--accent-soft)',
          borderColor: 'var(--accent-line)',
          backgroundImage: 'radial-gradient(color-mix(in srgb, var(--accent) 22%, transparent) 1.1px, transparent 1.5px)',
          backgroundSize: '18px 18px',
        }}
      >
        <div className="flex flex-col gap-3.5">
          <h1 className="text-2xl lg:text-3xl font-semibold" style={{ color: 'var(--accent)' }}>
            Why did my AI agent get it wrong?
          </h1>
          <p className="text-sm max-w-[66ch]" style={{ color: 'var(--muted)' }}>
            Rewind saves everything your agent does, points to the exact step where it went off track, and lets you test a fix without starting over.
          </p>

          <ol className="list-none m-0 p-0 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <li className="flex flex-col gap-0.5 p-2.5 bg-[var(--surface)] border border-[var(--line)] rounded-xl">
              <span
                className="w-5 h-5 rounded-full inline-grid place-items-center text-xs font-semibold mb-1"
                style={{ backgroundColor: 'var(--accent)', color: 'var(--on-accent)' }}
              >
                1
              </span>
              <b className="font-semibold text-sm">Record</b>
              <small className="text-[12px] leading-tight" style={{ color: 'var(--muted)' }}>
                Every step your agent takes is saved automatically.
              </small>
            </li>
            <li className="flex flex-col gap-0.5 p-2.5 bg-[var(--surface)] border border-[var(--line)] rounded-xl">
              <span
                className="w-5 h-5 rounded-full inline-grid place-items-center text-xs font-semibold mb-1"
                style={{ backgroundColor: 'var(--accent)', color: 'var(--on-accent)' }}
              >
                2
              </span>
              <b className="font-semibold text-sm">Find the mistake</b>
              <small className="text-[12px] leading-tight" style={{ color: 'var(--muted)' }}>
                Rewind marks the step where things went wrong and explains why.
              </small>
            </li>
            <li className="flex flex-col gap-0.5 p-2.5 bg-[var(--surface)] border border-[var(--line)] rounded-xl">
              <span
                className="w-5 h-5 rounded-full inline-grid place-items-center text-xs font-semibold mb-1"
                style={{ backgroundColor: 'var(--accent)', color: 'var(--on-accent)' }}
              >
                3
              </span>
              <b className="font-semibold text-sm">Try a fix</b>
              <small className="text-[12px] leading-tight" style={{ color: 'var(--muted)' }}>
                Change the instructions and replay from that step only.
              </small>
            </li>
          </ol>
        </div>

        {/* SVG Diagram from Rewind.html */}
        <div className="w-full max-w-[340px] mx-auto">
          <svg viewBox="0 0 340 180" role="img" aria-label="Step fault localization diagram" className="w-full h-auto">
            <line x1="24" y1="96" x2="316" y2="96" style={{ stroke: 'var(--line)', strokeWidth: 3, strokeLinecap: 'round' }} />
            {[0, 1, 2, 3, 4, 5, 6].map((k) => {
              const x = 24 + k * 48.67;
              const isBad = k === 4;
              return (
                <g key={k}>
                  <circle
                    cx={x}
                    cy={96}
                    r={isBad ? 11 : 8}
                    style={{
                      fill: isBad ? 'var(--bad)' : 'var(--surface)',
                      stroke: isBad ? 'var(--bad)' : 'var(--muted)',
                      strokeWidth: 2.5,
                    }}
                  />
                  {isBad && (
                    <path
                      d={`M${x - 4} ${96 - 4} l8 8 M${x + 4} ${96 - 4} l-8 8`}
                      style={{ stroke: '#fff', strokeWidth: 2, strokeLinecap: 'round' }}
                    />
                  )}
                </g>
              );
            })}
            <path
              d="M316 108 C316 160 218 160 218.7 112"
              style={{
                fill: 'none',
                stroke: 'var(--accent)',
                strokeWidth: 2.5,
                strokeDasharray: '5 5',
                strokeLinecap: 'round',
              }}
            />
            <path
              d="M212 120 l6.7 -9 l7 9"
              style={{
                fill: 'none',
                stroke: 'var(--accent)',
                strokeWidth: 2.5,
                strokeLinecap: 'round',
                strokeLinejoin: 'round',
              }}
            />
            <text x="268" y="152" textAnchor="middle" style={{ fill: 'var(--accent-ink)', font: '600 13px var(--sans)' }}>
              Rewind to here
            </text>
            <text x="218.7" y="62" textAnchor="middle" style={{ fill: 'var(--bad-ink)', font: '600 13px var(--sans)' }}>
              The mistake
            </text>
            <text x="24" y="62" style={{ fill: 'var(--muted)', font: '400 13px var(--sans)' }}>
              Each dot is one step
            </text>
          </svg>
        </div>
      </section>

      {/* Backend Statistics Cards */}
      <div className="flex flex-wrap gap-3">
        <div className="flex flex-col gap-0.5 px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[140px] flex-1">
          <b className="text-base font-semibold num">{loading ? '-' : totalRuns}</b>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            Total runs recorded
          </span>
        </div>
        <div className="flex flex-col gap-0.5 px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[140px] flex-1">
          <b className="text-base font-semibold num" style={{ color: failedRuns > 0 ? 'var(--bad-ink)' : 'inherit' }}>
            {loading ? '-' : failedRuns}
          </b>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            Went wrong
          </span>
        </div>
        {topMistake && (
          <div className="flex flex-col gap-0.5 px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[160px] flex-1">
            <b className="text-base font-semibold">{getFailureLabel(topMistake)}</b>
            <span className="text-xs" style={{ color: 'var(--muted)' }}>
              Most common mistake
            </span>
          </div>
        )}
        <div className="flex flex-col gap-0.5 px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--line)] rounded-xl min-w-[140px] flex-1">
          <b className="text-base font-semibold num">{loading ? '-' : `$${totalSpend.toFixed(2)}`}</b>
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            Total execution spend
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Recorded Agent Runs</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => fetchData()}
            disabled={loading}
            className="btn ghost text-xs py-1 px-2.5 min-h-[32px]"
            title="Refresh runs from backend"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap gap-2.5 items-center justify-between">
        <label className="flex items-center gap-2 min-h-[38px] px-3 border rounded-lg bg-[var(--surface)] text-[var(--muted)] flex-1 min-w-[240px] max-w-sm" style={{ borderColor: 'var(--line)' }}>
          <Search className="w-4 h-4 shrink-0" />
          <input
            type="search"
            placeholder="Search by task, agent or run number"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="border-0 outline-none bg-transparent text-sm w-full"
            style={{ color: 'var(--ink)' }}
          />
        </label>

        <div className="inline-flex border rounded-lg overflow-hidden bg-[var(--surface)]" style={{ borderColor: 'var(--line)' }}>
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`min-h-[36px] px-3.5 border-0 text-sm font-medium transition-colors cursor-pointer ${
              filter === 'all' ? 'bg-[var(--accent-soft)] text-[var(--accent-ink)]' : 'text-[var(--muted)]'
            }`}
          >
            All
          </button>
          <button
            type="button"
            onClick={() => setFilter('failed')}
            className={`min-h-[36px] px-3.5 border-l border-[var(--line)] text-sm font-medium transition-colors cursor-pointer ${
              filter === 'failed' ? 'bg-[var(--accent-soft)] text-[var(--accent-ink)]' : 'text-[var(--muted)]'
            }`}
          >
            Went wrong
          </button>
          <button
            type="button"
            onClick={() => setFilter('passed')}
            className={`min-h-[36px] px-3.5 border-l border-[var(--line)] text-sm font-medium transition-colors cursor-pointer ${
              filter === 'passed' ? 'bg-[var(--accent-soft)] text-[var(--accent-ink)]' : 'text-[var(--muted)]'
            }`}
          >
            Worked
          </button>
        </div>
      </div>

      {/* Runs Table */}
      <div className="panel">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse min-w-[860px] text-left">
            <thead>
              <tr style={{ background: 'var(--code-bg)' }}>
                <th
                  onClick={() => toggleSort('id')}
                  className="cursor-pointer text-xs font-semibold p-2.5 px-3.5 border-b"
                  style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}
                >
                  <span className="flex items-center gap-1">
                    Run <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
                <th className="text-xs font-semibold p-2.5 px-3.5 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Agent
                </th>
                <th className="text-xs font-semibold p-2.5 px-3.5 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  What it was asked
                </th>
                <th className="text-xs font-semibold p-2.5 px-3.5 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Result
                </th>
                <th className="text-xs font-semibold p-2.5 px-3.5 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  What went wrong
                </th>
                <th
                  onClick={() => toggleSort('steps_count')}
                  className="cursor-pointer text-xs font-semibold p-2.5 px-3.5 border-b text-right"
                  style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}
                >
                  <span className="flex items-center justify-end gap-1">
                    Steps <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
                <th
                  onClick={() => toggleSort('cost')}
                  className="cursor-pointer text-xs font-semibold p-2.5 px-3.5 border-b text-right"
                  style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}
                >
                  <span className="flex items-center justify-end gap-1">
                    Cost <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
                <th className="text-xs font-semibold p-2.5 px-3.5 border-b text-right" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Time taken
                </th>
                <th className="text-xs font-semibold p-2.5 px-3.5 border-b" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  When
                </th>
                <th className="text-xs font-semibold p-2.5 px-3.5 border-b text-right" style={{ borderColor: 'var(--line)', color: 'var(--muted)' }}>
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={10} className="p-8 text-center" style={{ color: 'var(--muted)' }}>
                    <div className="flex items-center justify-center gap-2">
                      <span className="spin" />
                      <span>Loading recorded runs from FastAPI backend...</span>
                    </div>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={10} className="p-8 text-center">
                    <div className="flex flex-col items-center gap-2 max-w-md mx-auto">
                      <AlertCircle className="w-6 h-6" style={{ color: 'var(--bad)' }} />
                      <b className="font-semibold" style={{ color: 'var(--bad-ink)' }}>
                        Backend Error
                      </b>
                      <p className="text-xs" style={{ color: 'var(--muted)' }}>
                        {error}
                      </p>
                      <button
                        type="button"
                        onClick={() => setIsConfigOpen(true)}
                        className="btn primary text-xs mt-2"
                      >
                        Configure FastAPI URL
                      </button>
                    </div>
                  </td>
                </tr>
              ) : sortedRuns.length === 0 ? (
                <tr>
                  <td colSpan={10} className="p-10 text-center">
                    <div className="flex flex-col items-center gap-2 max-w-md mx-auto">
                      <Database className="w-8 h-8" style={{ color: 'var(--muted)' }} />
                      <b className="font-semibold text-sm">No Executions Recorded Yet</b>
                      <p className="text-xs leading-relaxed" style={{ color: 'var(--muted)' }}>
                        Your connected FastAPI database is currently empty. When your agents record traces or POST to{' '}
                        <code className="mono">/api/runs</code>, their executions, steps, and fault localizations will appear here.
                      </p>
                      <button
                        type="button"
                        onClick={() => setIsConfigOpen(true)}
                        className="btn text-xs mt-2"
                      >
                        Backend Status & Seed Options
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                sortedRuns.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b transition-colors hover:bg-[var(--hover)]"
                    style={{ borderColor: 'var(--line)' }}
                  >
                    <td className="p-2.5 px-3.5">
                      <Link
                        to={`/run/${r.id}`}
                        className="mono text-xs font-medium border-b hover:opacity-80 transition-opacity"
                        style={{ color: 'var(--accent-ink)', borderColor: 'var(--accent-line)' }}
                      >
                        {r.id}
                      </Link>
                    </td>
                    <td className="p-2.5 px-3.5 mono text-xs">{r.agent}</td>
                    <td className="p-2.5 px-3.5 text-sm max-w-[280px] truncate" title={r.task}>
                      {r.task}
                    </td>
                    <td className="p-2.5 px-3.5 text-xs">
                      <span className="flex items-center gap-1.5">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            r.ok ? 'bg-[var(--ok)]' : 'bg-[var(--bad)]'
                          }`}
                        />
                        {r.ok ? 'Worked' : 'Went wrong'}
                      </span>
                    </td>
                    <td className="p-2.5 px-3.5">
                      {r.label ? (
                        <span className="chip fail text-xs">{getFailureLabel(r.label)}</span>
                      ) : (
                        <span className="text-xs" style={{ color: 'var(--muted)' }}>
                          Nothing
                        </span>
                      )}
                    </td>
                    <td className="p-2.5 px-3.5 text-xs text-right num">{r.steps_count}</td>
                    <td className="p-2.5 px-3.5 text-xs text-right num">{formatCost(r.cost)}</td>
                    <td className="p-2.5 px-3.5 text-xs text-right num">{r.duration || formatDuration(r.duration_ms)}</td>
                    <td className="p-2.5 px-3.5 text-xs" style={{ color: 'var(--muted)' }}>
                      {r.started_at}
                    </td>
                    <td className="p-2.5 px-3.5 text-right">
                      <Link
                        to={`/run/${r.id}`}
                        className="btn ghost text-xs py-1 px-2 min-h-0 h-7 inline-flex items-center gap-1"
                      >
                        <span>Inspect</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
