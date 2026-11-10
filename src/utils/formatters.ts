import { FailureCategory, StepKind } from '../types';

export const FAILURE_LABELS: Record<string, string> = {
  ignored_error: 'Ignored an error',
  infinite_loop: 'Got stuck in a loop',
  goal_drift: 'Wandered off task',
  bad_arguments: 'Used wrong inputs',
  wrong_tool: 'Used wrong tool',
  lost_context: 'Lost context',
};

export function getFailureLabel(category?: FailureCategory | string): string {
  if (!category) return 'Unknown error';
  return FAILURE_LABELS[category] || category.replace(/_/g, ' ');
}

export const KIND_LABELS: Record<StepKind, string> = {
  llm: 'AI thinking',
  tool: 'Tool',
  system: 'System',
};

export const KIND_DESCRIPTIONS: Record<StepKind, string> = {
  llm: 'The AI decided what to do next.',
  tool: 'The agent used a tool and got a result back.',
  system: 'Rewind stopped the run.',
};

export const DETECTOR_NAMES: Record<string, string> = {
  'Repeated identical call': 'Same action repeated',
  'Ignored tool error': 'Error was ignored',
  'Argument absent from context': 'Made-up input value',
  'Output schema mismatch': 'Unexpected result format',
  'Step or budget limit': 'Ran out of steps',
};

export function getDetectorName(detector: string): string {
  return DETECTOR_NAMES[detector] || detector;
}

export function formatNumber(n: number | string | undefined | null): string {
  if (n === undefined || n === null) return '0';
  return Number(n).toLocaleString('en-US');
}

export function formatDuration(ms?: number | null, fallbackStr?: string): string {
  if (fallbackStr) return fallbackStr;
  if (ms === undefined || ms === null) return '0ms';
  return ms >= 1000 ? (ms / 1000).toFixed(1) + 's' : ms + 'ms';
}

export function formatCost(cost?: number | null): string {
  if (cost === undefined || cost === null) return '$0.000';
  return `$${cost.toFixed(3)}`;
}

export function truncateFirstLine(s: string, maxLength: number = 96): string {
  if (!s) return '';
  const first = String(s).split('\n')[0].trim();
  return first.length > maxLength ? first.slice(0, maxLength - 3) + '...' : first;
}
