import type {
  ArbitrationRules,
  BatchSummary,
  FieldDef,
  GoldenRecord,
  ParsedDraft,
  TestResult,
  Trigger,
} from './types';

const API = import.meta.env.VITE_API_URL ?? '';

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const api = {
  health: () => fetchJson<{ status: string; profiles: number; triggers: number }>('/api/health'),

  listTriggers: (params?: Record<string, string>) => {
    const q = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJson<{ count: number; triggers: Trigger[] }>(`/api/triggers${q}`);
  },

  getTrigger: (id: string) =>
    fetchJson<{ trigger: Trigger; arbitration_rules: ArbitrationRules; last_tested: unknown }>(
      `/api/triggers/${id}`
    ),

  updateTrigger: (id: string, body: Partial<Trigger>) =>
    fetchJson<Trigger>(`/api/triggers/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  parseTrigger: (text: string) =>
    fetchJson<ParsedDraft>('/api/triggers/parse', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  createTrigger: (draft: ParsedDraft, activate = false) =>
    fetchJson<Trigger>('/api/triggers', {
      method: 'POST',
      body: JSON.stringify({ draft, activate }),
    }),

  listProfiles: (params?: Record<string, string>) => {
    const q = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJson<{ count: number; profiles: GoldenRecord[] }>(`/api/profiles${q}`);
  },

  getQualifying: (triggerId: string) =>
    fetchJson<{ count: number; profiles: GoldenRecord[] }>(
      `/api/triggers/${triggerId}/qualifying`
    ),

  testTrigger: (triggerId: string, accountId: string) =>
    fetchJson<TestResult>(`/api/triggers/${triggerId}/test?account_id=${accountId}`, {
      method: 'POST',
    }),

  batchTest: (triggerId: string) =>
    fetchJson<BatchSummary>(`/api/triggers/${triggerId}/test/batch`, { method: 'POST' }),

  getQueue: (params?: Record<string, string>) => {
    const q = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJson<{ simulation_notice: string; count: number; entries: TestResult[] }>(
      `/api/queue${q}`
    );
  },

  listFields: () => fetchJson<{ fields: FieldDef[] }>('/api/fields'),
};
