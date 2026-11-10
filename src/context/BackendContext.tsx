import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getApiBaseUrl, setApiBaseUrl as saveApiBaseUrl, checkBackendHealth, apiFetch } from '../api/client';
import { BackendConnectionState } from '../types';

interface BackendContextType {
  connection: BackendConnectionState;
  checkHealth: (targetUrl?: string) => Promise<boolean>;
  updateBaseUrl: (newUrl: string) => Promise<boolean>;
  seedDemoData: () => Promise<{ success: boolean; message: string }>;
  isConfigOpen: boolean;
  setIsConfigOpen: (open: boolean) => void;
  isContractOpen: boolean;
  setIsContractOpen: (open: boolean) => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const BackendContext = createContext<BackendContextType | null>(null);

export const BackendProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [connection, setConnection] = useState<BackendConnectionState>({
    status: 'checking',
    baseUrl: getApiBaseUrl(),
  });
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [isContractOpen, setIsContractOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  // Sync theme with document element
  useEffect(() => {
    const saved = localStorage.getItem('rewind_theme') as 'light' | 'dark' | null;
    const initial = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    setTheme(initial);
    document.documentElement.setAttribute('data-theme', initial);
  }, []);

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    localStorage.setItem('rewind_theme', next);
    document.documentElement.setAttribute('data-theme', next);
  };

  const checkHealth = useCallback(async (targetUrl?: string): Promise<boolean> => {
    const url = targetUrl || connection.baseUrl;
    setConnection(prev => ({ ...prev, status: 'checking', baseUrl: url, error: undefined }));

    const res = await checkBackendHealth(url);
    const state: BackendConnectionState = {
      status: res.ok ? 'connected' : 'offline',
      baseUrl: url,
      latencyMs: res.latencyMs,
      error: res.error,
      lastChecked: new Date().toLocaleTimeString(),
    };
    setConnection(state);
    return res.ok;
  }, [connection.baseUrl]);

  const updateBaseUrl = async (newUrl: string): Promise<boolean> => {
    const clean = newUrl.trim().replace(/\/+$/, '');
    saveApiBaseUrl(clean);
    return await checkHealth(clean);
  };

  const seedDemoData = async (): Promise<{ success: boolean; message: string }> => {
    try {
      const res = await apiFetch<any>('/api/dev/seed', { method: 'POST' });
      await checkHealth();
      return { success: true, message: `Successfully seeded ${res.seeded || res.total_runs || 'sample'} runs into the FastAPI backend!` };
    } catch (err: any) {
      return { success: false, message: err.message || 'Seed endpoint not available on backend' };
    }
  };

  useEffect(() => {
    checkHealth();

    const handleUrlChange = (e: any) => {
      if (e.detail?.url) {
        checkHealth(e.detail.url);
      }
    };
    window.addEventListener('rewind-api-url-change', handleUrlChange);
    return () => window.removeEventListener('rewind-api-url-change', handleUrlChange);
  }, [checkHealth]);

  return (
    <BackendContext.Provider
      value={{
        connection,
        checkHealth,
        updateBaseUrl,
        seedDemoData,
        isConfigOpen,
        setIsConfigOpen,
        isContractOpen,
        setIsContractOpen,
        theme,
        toggleTheme,
      }}
    >
      {children}
    </BackendContext.Provider>
  );
};

export function useBackend(): BackendContextType {
  const ctx = useContext(BackendContext);
  if (!ctx) {
    throw new Error('useBackend must be used within a BackendProvider');
  }
  return ctx;
}
