import React from 'react';
import { AlertCircle, RefreshCw, Settings, FileCode } from 'lucide-react';
import { useBackend } from '../../context/BackendContext';

export const BackendStatusBanner: React.FC = () => {
  const { connection, checkHealth, setIsConfigOpen, setIsContractOpen } = useBackend();

  if (connection.status === 'connected') {
    return null;
  }

  return (
    <div
      className="p-3.5 mb-5 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-sm transition-all"
      style={{
        backgroundColor: 'var(--bad-soft)',
        borderColor: 'var(--bad-line)',
        color: 'var(--ink)',
      }}
      role="alert"
    >
      <div className="flex items-start gap-2.5">
        <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: 'var(--bad-ink)' }} />
        <div>
          <b className="font-semibold" style={{ color: 'var(--bad-ink)' }}>
            FastAPI Backend Disconnected ({connection.baseUrl})
          </b>
          <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
            {connection.error || 'Rewind enforces zero mock data. All runs, traces, and repairs must come from your backend.'}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 self-end md:self-auto shrink-0">
        <button
          type="button"
          onClick={() => checkHealth()}
          className="btn text-xs py-1 px-2.5 min-h-[30px]"
          disabled={connection.status === 'checking'}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${connection.status === 'checking' ? 'animate-spin' : ''}`} />
          Retry
        </button>
        <button
          type="button"
          onClick={() => setIsConfigOpen(true)}
          className="btn text-xs py-1 px-2.5 min-h-[30px]"
        >
          <Settings className="w-3.5 h-3.5" />
          Set URL
        </button>
        <button
          type="button"
          onClick={() => setIsContractOpen(true)}
          className="btn text-xs py-1 px-2.5 min-h-[30px]"
        >
          <FileCode className="w-3.5 h-3.5" />
          API Docs
        </button>
      </div>
    </div>
  );
};
