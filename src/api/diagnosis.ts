import { apiFetch } from './client';
import { DiagnosisResult } from '../types';

export async function getDiagnosis(runId: string): Promise<DiagnosisResult> {
  return await apiFetch<DiagnosisResult>(`/api/runs/${encodeURIComponent(runId)}/diagnosis`);
}

export async function requestDiagnosis(runId: string): Promise<DiagnosisResult> {
  return await apiFetch<DiagnosisResult>(`/api/runs/${encodeURIComponent(runId)}/diagnose`, {
    method: 'POST',
  });
}
