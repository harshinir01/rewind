import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { List, Layers, Sun, Moon, Database, ShieldCheck, Undo2 } from 'lucide-react';
import { useBackend } from '../../context/BackendContext';

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { connection, setIsConfigOpen, setIsContractOpen, theme, toggleTheme } = useBackend();

  const isRunsActive = location.pathname === '/' || location.pathname.startsWith('/run/');
  const isBatchActive = location.pathname.startsWith('/batch');
  const isTryFixActive = location.pathname.startsWith('/replay/');

  // Extract active run ID if user is in details or replay
  const runMatch = location.pathname.match(/\/(run|replay)\/([^/]+)/);
  const activeRunId = runMatch ? runMatch[2] : null;

  return (
    <aside className="w-full md:w-52 shrink-0 flex flex-col gap-6 md:sticky top-6 self-start">
      <Link to="/" className="flex flex-col gap-0.5 no-underline">
        <b className="flex items-center gap-2 font-semibold text-2xl" style={{ color: 'var(--accent)' }}>
          <svg className="w-5 h-5 shrink-0 stroke-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 6 3 12l8 6V6Z" />
            <path d="M21 6l-8 6 8 6V6Z" />
          </svg>
          Rewind
        </b>
        <span className="text-[13px]" style={{ color: 'var(--muted)' }}>
          Find out why your AI agent slipped
        </span>
      </Link>

      <nav className="flex flex-col gap-1" aria-label="Main navigation">
        <Link
          to="/"
          className={`flex items-center gap-2.5 min-h-[38px] px-2.5 py-1.5 rounded-lg text-sm transition-colors duration-150 ${
            isRunsActive && !isTryFixActive
              ? 'font-medium'
              : 'text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--ink)]'
          }`}
          style={
            isRunsActive && !isTryFixActive
              ? { backgroundColor: 'var(--accent-soft)', color: 'var(--accent-ink)', boxShadow: '0 0 0 1px var(--accent-line)' }
              : {}
          }
        >
          <List className="w-4 h-4 shrink-0" />
          <span>All runs</span>
        </Link>

        {activeRunId && (
          <Link
            to={`/replay/${activeRunId}`}
            className={`flex items-center gap-2.5 min-h-[38px] px-2.5 py-1.5 rounded-lg text-sm transition-colors duration-150 ${
              isTryFixActive
                ? 'font-medium'
                : 'text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--ink)]'
            }`}
            style={
              isTryFixActive
                ? { backgroundColor: 'var(--accent-soft)', color: 'var(--accent-ink)', boxShadow: '0 0 0 1px var(--accent-line)' }
                : {}
            }
          >
            <Undo2 className="w-4 h-4 shrink-0" />
            <span>Try a fix ({activeRunId})</span>
          </Link>
        )}

        <Link
          to="/batch"
          className={`flex items-center gap-2.5 min-h-[38px] px-2.5 py-1.5 rounded-lg text-sm transition-colors duration-150 ${
            isBatchActive
              ? 'font-medium'
              : 'text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--ink)]'
          }`}
          style={
            isBatchActive
              ? { backgroundColor: 'var(--accent-soft)', color: 'var(--accent-ink)', boxShadow: '0 0 0 1px var(--accent-line)' }
              : {}
          }
        >
          <Layers className="w-4 h-4 shrink-0" />
          <span>Test a fix on many runs</span>
        </Link>
      </nav>

      <div className="flex flex-col gap-3 text-xs" style={{ color: 'var(--muted)' }}>
        <div className="flex flex-col gap-1 p-2.5 border rounded-lg" style={{ borderColor: 'var(--line)', background: 'var(--surface)' }}>
          <span className="text-[11px] uppercase tracking-wider font-semibold">FastAPI Backend</span>
          <button
            type="button"
            onClick={() => setIsConfigOpen(true)}
            className="flex items-center justify-between gap-1 text-left hover:opacity-85 transition-opacity"
            title="Click to configure backend URL"
          >
            <span className="mono text-[11px] truncate max-w-[130px] font-medium" style={{ color: 'var(--ink)' }}>
              {connection.baseUrl.replace(/^https?:\/\//, '')}
            </span>
            <span
              className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                connection.status === 'connected'
                  ? 'bg-[#3B7A4E]'
                  : connection.status === 'checking'
                  ? 'bg-amber-500 animate-pulse'
                  : 'bg-[#B8431F]'
              }`}
            />
          </button>
          <div className="flex items-center justify-between text-[11px] pt-1 border-t" style={{ borderColor: 'var(--line)' }}>
            <span>{connection.status === 'connected' ? `${connection.latencyMs || 12}ms` : 'Disconnected'}</span>
            <button
              type="button"
              onClick={() => setIsConfigOpen(true)}
              className="underline hover:text-[var(--ink)] cursor-pointer"
            >
              Config
            </button>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsContractOpen(true)}
          className="btn ghost text-xs justify-start px-2 py-1.5 h-auto min-h-0"
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>API Contracts</span>
        </button>

        <button
          className="btn ghost text-xs justify-start px-2 py-1.5 h-auto min-h-0"
          type="button"
          onClick={toggleTheme}
          aria-label="Switch between light and dark mode"
        >
          {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
        </button>
      </div>
    </aside>
  );
};
