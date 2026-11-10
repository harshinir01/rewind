import { apiFetch } from './client';
import { AnalyticsMetrics } from '../types';

export async function getAnalyticsMetrics(): Promise<AnalyticsMetrics> {
  return await apiFetch<AnalyticsMetrics>('/api/analytics/metrics');
}
