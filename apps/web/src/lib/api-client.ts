import type { DemoSummaryResponse, DevTokenResponse, HealthResponse } from '@lokara/api/contract';

/**
 * The typed HTTP client for apps/api — the ONLY way the web app touches data.
 * Response shapes come from the shared contract types, so api changes surface
 * as compile errors here, not runtime surprises.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
  ) {
    super(`API request failed: ${status} ${path}`);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: 'no-store', ...init });
  if (!response.ok) {
    throw new ApiError(response.status, path);
  }
  return (await response.json()) as T;
}

export const apiClient = {
  health: () => request<HealthResponse>('/health'),

  /** Dev-only login stand-in until Supabase Auth lands (M5). */
  devToken: () => request<DevTokenResponse>('/auth/dev-token', { method: 'POST' }),

  demoSummary: (accessToken: string) =>
    request<DemoSummaryResponse>('/demo/summary', {
      headers: { Authorization: `Bearer ${accessToken}` },
    }),
};
