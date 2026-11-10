import { apiFetch } from './client';
import { BatchItem, BatchVerificationRequest, BatchVerificationResponse } from '../types';

export async function getBatchRuns(): Promise<BatchItem[]> {
  const data = await apiFetch<BatchItem[] | { items: BatchItem[] }>('/api/batch/runs');
  if (Array.isArray(data)) return data;
  if (data && Array.isArray((data as any).items)) return (data as any).items;
  return [];
}

export async function executeBatchVerification(payload: BatchVerificationRequest): Promise<BatchVerificationResponse> {
  return await apiFetch<BatchVerificationResponse>('/api/batch/verify', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
