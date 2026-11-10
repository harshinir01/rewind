import React, { useState, useEffect, useRef } from 'react';
import { X, CheckCircle2, AlertTriangle, RefreshCw, Database } from 'lucide-react';
import { useBackend } from '../../context/BackendContext';

export const ConnectionModal: React.FC = () => {
  const { connection, isConfigOpen, setIsConfigOpen, updateBaseUrl, checkHealth, seedDemoData } = useBackend();
  const [urlInput, setUrlInput] = useState(connection.baseUrl);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [seedStatus, setSeedStatus] = useState<string | null>(null);
  const [isSeeding, setIsSeeding] = useState(false);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync URL input when modal opens so it reflects any external changes
  useEffect(() => {
    if (isConfigOpen) {
      setUrlInput(connection.baseUrl);
      setTestResult(null);
      setSeedStatus(null);
    }
  }, [isConfigOpen, connection.baseUrl]);

  // Escape key closes the modal
  useEffect(() => {
    if (!isConfigOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsConfigOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isConfigOpen, setIsConfigOpen]);

  // Clear any pending auto-close timer on unmount
  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  if (!isConfigOpen) return null;

  const handleSaveAndTest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsTesting(true);
    setTestResult(null);

    const ok = await updateBaseUrl(urlInput);
    setIsTesting(false);
    setTestResult({
      ok,
      message: ok
        ? `Successfully connected to FastAPI backend at ${urlInput}`
        : `Could not reach ${urlInput}. Verify that your FastAPI server is running with CORS enabled.`,
    });
  };

  const handleSeed = async () => {
    if (isSeeding) return; // prevent duplicate clicks
    setIsSeeding(true);
    setSeedStatus('Seeding demo data into FastAPI backend...');
    const res = await seedDemoData();
    setSeedStatus(res.message);
    setIsSeeding(false);
    if (res.success) {
      // Show the success message briefly, then close
      closeTimerRef.current = setTimeout(() => setIsConfigOpen(false), 1500);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in"
      onClick={(e) => { if (e.target === e.currentTarget) setIsConfigOpen(false); }}
    >
      <div
        className="panel max-w-lg w-full shadow-2xl relative"
        style={{ background: 'var(--surface)', borderColor: 'var(--line)' }}
      >
        <header className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--line)' }}>
          <h2 className="text-base font-semibold">FastAPI Backend Connection</h2>
          <button
            type="button"
            onClick={() => setIsConfigOpen(false)}
            className="btn ghost p-1 min-h-0 h-8 w-8 justify-center rounded-md"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        <form onSubmit={handleSaveAndTest} className="p-4 space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--muted)' }}>
              Backend API Base URL
            </label>
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="http://localhost:8081"
              className="w-full px-3 py-2 border rounded-lg mono text-xs"
              style={{
                background: 'var(--code-bg)',
                borderColor: 'var(--line)',
                color: 'var(--ink)',
              }}
              required
            />
            <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
              Default: <code className="mono">http://localhost:8000</code> or <code className="mono">http://localhost:8081</code>.
              Inside cloud containers, if port 8000 is reserved by the system, run your FastAPI on <code className="mono">8081</code>.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isTesting}
              className="btn primary flex-1 justify-center py-2 text-sm"
            >
              {isTesting ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Save & Test Connection'}
            </button>
            <button
              type="button"
              onClick={() => checkHealth(urlInput)}
              disabled={isTesting}
              className="btn flex-1 justify-center py-2 text-sm"
            >
              Check Health
            </button>
          </div>

          {testResult && (
            <div
              className={`p-3 rounded-lg border text-xs flex items-start gap-2 ${
                testResult.ok ? 'bg-[var(--ok-soft)] text-[var(--ok)]' : 'bg-[var(--bad-soft)] text-[var(--bad-ink)]'
              }`}
              style={{ borderColor: testResult.ok ? 'transparent' : 'var(--bad-line)' }}
            >
              {testResult.ok ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
              <span>{testResult.message}</span>
            </div>
          )}

          <div className="p-3 border rounded-lg text-xs space-y-2" style={{ borderColor: 'var(--line)', background: 'var(--code-bg)' }}>
            <b className="font-semibold block text-[13px]">How to Run the FastAPI Backend:</b>
            <pre className="p-2 rounded mono text-[11px] overflow-x-auto" style={{ background: 'var(--surface)' }}>
{`# In terminal:
pip install fastapi uvicorn pydantic
uvicorn backend.main:app --reload --port 8081`}
            </pre>
            <p style={{ color: 'var(--muted)' }}>
              A full reference server is included in <code className="mono">backend/main.py</code>.
            </p>
          </div>

          {connection.status === 'connected' && (
            <div className="pt-2 border-t flex flex-col gap-2" style={{ borderColor: 'var(--line)' }}>
              <span className="text-xs" style={{ color: 'var(--muted)' }}>
                Database is connected. Want to seed reference demo traces into your FastAPI database?
              </span>
              <button
                type="button"
                onClick={handleSeed}
                disabled={isSeeding}
                className="btn text-xs justify-center py-1.5"
              >
                {isSeeding
                  ? <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  : <Database className="w-3.5 h-3.5" />}
                {isSeeding ? 'Seeding...' : 'Seed Demo Traces into FastAPI'}
              </button>
              {seedStatus && (
                <span className="text-xs font-mono" style={{ color: 'var(--ok)' }}>
                  {seedStatus}
                </span>
              )}
            </div>
          )}
        </form>
      </div>
    </div>
  );
};
