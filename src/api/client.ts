const STORAGE_KEY = 'rewind_api_base_url';

export function getApiBaseUrl(): string {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && saved.trim()) {
    return saved.trim().replace(/\/+$/, '');
  }
  const envUrl = (import.meta as any).env?.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return 'http://localhost:8081';
}

export function setApiBaseUrl(url: string): void {
  const clean = url.trim().replace(/\/+$/, '');
  localStorage.setItem(STORAGE_KEY, clean);
  window.dispatchEvent(new CustomEvent('rewind-api-url-change', { detail: { url: clean } }));
}

export class ApiError extends Error {
  status: number;
  url: string;
  data?: any;

  constructor(message: string, status: number, url: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.url = url;
    this.data = data;
  }
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const normalizedPath = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const fullUrl = `${baseUrl}${normalizedPath}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const res = await fetch(fullUrl, {
      ...options,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorBody: any = null;
      try {
        errorBody = await res.json();
      } catch {
        errorBody = await res.text();
      }

      const msg = errorBody?.detail || errorBody?.error || errorBody?.message || `Request failed with status ${res.status}`;
      throw new ApiError(msg, res.status, fullUrl, errorBody);
    }

    if (res.status === 204) {
      return null as unknown as T;
    }

    return (await res.json()) as T;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) {
      throw err;
    }
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out after 15 seconds. Ensure the FastAPI backend is running.', 408, fullUrl);
    }

    // If direct connection failed (e.g. CORS or container port conflict) and baseUrl is localhost, try relative proxy
    if (baseUrl.includes('localhost') && normalizedPath.startsWith('/api')) {
      try {
        const proxyRes = await fetch(normalizedPath, {
          ...options,
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            ...(options.headers || {}),
          },
        });
        if (proxyRes.ok) {
          if (proxyRes.status === 204) return null as unknown as T;
          return (await proxyRes.json()) as T;
        }
      } catch {
        // proxy also failed, rethrow original error
      }
    }

    const networkMsg = err.message || 'Failed to connect to backend server';
    throw new ApiError(`Network error connecting to ${fullUrl}: ${networkMsg}`, 0, fullUrl);
  }
}

export async function checkBackendHealth(targetUrl?: string): Promise<{ ok: boolean; latencyMs: number; error?: string }> {
  const base = targetUrl ? targetUrl.trim().replace(/\/+$/, '') : getApiBaseUrl();
  const start = performance.now();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4000);

  const testEndpoints = ['/health', '/api/health', '/api/runs', '/'];

  for (const ep of testEndpoints) {
    const url = `${base}${ep}`;
    try {
      const res = await fetch(url, {
        method: 'GET',
        signal: controller.signal,
        headers: { 'Accept': 'application/json' },
      });
      clearTimeout(timeoutId);
      const latencyMs = Math.round(performance.now() - start);

      if (res.ok) {
        return { ok: true, latencyMs };
      }

      // Check if it's the container's control-plane port conflict
      if (res.status === 401) {
        return {
          ok: false,
          latencyMs,
          error: `Port 8000 returned 401 Unauthorized (Reserved by AI Studio control plane). Point Rewind to your FastAPI port, e.g. http://localhost:8081`,
        };
      }

      return {
        ok: false,
        latencyMs,
        error: `Endpoint ${url} returned HTTP ${res.status} ${res.statusText}`,
      };
    } catch {
      // try next endpoint
    }
  }

  clearTimeout(timeoutId);
  return {
    ok: false,
    latencyMs: 0,
    error: `Cannot connect to ${base}. FastAPI backend is offline or unreachable.`,
  };
}
