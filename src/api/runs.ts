import { apiFetch } from './client';
import { AgentRun, RunDetail } from '../types';

export interface GetRunsParams {
  search?: string;
  status?: 'all' | 'failed' | 'passed';
  limit?: number;
  offset?: number;
}

export async function getRuns(params: GetRunsParams = {}): Promise<AgentRun[]> {
  const query = new URLSearchParams();
  if (params.search) query.set('search', params.search);
  if (params.status && params.status !== 'all') query.set('status', params.status);
  if (params.limit) query.set('limit', String(params.limit));
  if (params.offset) query.set('offset', String(params.offset));

  const qs = query.toString();
  const endpoint = qs ? `/api/runs?${qs}` : '/api/runs';
  const data = await apiFetch<AgentRun[] | { runs: AgentRun[] }>(endpoint);

  if (Array.isArray(data)) {
    return data;
  }
  if (data && Array.isArray((data as any).runs)) {
    return (data as any).runs;
  }
  return [];
}

export async function getRunById(id: string): Promise<RunDetail> {
  return await apiFetch<RunDetail>(`/api/runs/${encodeURIComponent(id)}`);
}

export async function deleteRun(id: string): Promise<{ success: boolean; id: string }> {
  return await apiFetch<{ success: boolean; id: string }>(`/api/runs/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}
