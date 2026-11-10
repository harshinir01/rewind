import { apiFetch } from './client';
import { ReplayRequest, ReplayResult } from '../types';

export async function executeReplay(runId: string, payload: ReplayRequest): Promise<ReplayResult> {
  return await apiFetch<ReplayResult>(`/api/runs/${encodeURIComponent(runId)}/replay`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
