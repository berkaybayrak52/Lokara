/**
 * The interceptor contract (docs/04): on a 401 refresh the session once,
 * replay the failed request once, and never double-fire — concurrent 401s
 * share a single in-flight refresh.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { RenterOverviewResponseSchema } from './contracts';

const PingSchema = z.object({ pong: z.boolean() });

type FetchMock = ReturnType<typeof vi.fn<typeof fetch>>;

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

async function loadApi() {
  // Fresh module per test — the single-flight promise is module state.
  vi.resetModules();
  return import('./api');
}

let fetchMock: FetchMock;

beforeEach(() => {
  fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal('fetch', fetchMock);
});

function callsTo(pathSuffix: string): number {
  return fetchMock.mock.calls.filter(([url]) => String(url).endsWith(pathSuffix)).length;
}

describe('api interceptor', () => {
  it('returns parsed data on 200 without touching the session', async () => {
    const { api } = await loadApi();
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { pong: true }));

    await expect(api('/ping', PingSchema)).resolves.toEqual({ pong: true });
    expect(callsTo('/api/session')).toBe(0);
  });

  it('handles a 204 with no body', async () => {
    const { api } = await loadApi();
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(api('/thing', z.undefined())).resolves.toBeUndefined();
  });

  it('rejects a 200 whose body violates the contract', async () => {
    const { api } = await loadApi();
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { pong: 'yes' }));

    await expect(api('/ping', PingSchema)).rejects.toThrow();
  });

  it('on 401: refreshes once, replays once, succeeds', async () => {
    const { api } = await loadApi();
    fetchMock.mockImplementation(async (url) => {
      if (String(url).endsWith('/api/session')) return jsonResponse(200, { ok: true });
      return callsTo('/ping') > 1
        ? jsonResponse(200, { pong: true })
        : jsonResponse(401, { detail: 'expired' });
    });

    await expect(api('/ping', PingSchema)).resolves.toEqual({ pong: true });
    expect(callsTo('/api/session')).toBe(1);
    expect(callsTo('/ping')).toBe(2); // original + exactly one replay
  });

  it('on 401 with failing refresh: throws 401 and never replays', async () => {
    const { api, ApiError } = await loadApi();
    fetchMock.mockImplementation(async (url) => {
      if (String(url).endsWith('/api/session')) return jsonResponse(502, {});
      return jsonResponse(401, { detail: 'expired' });
    });

    await expect(api('/ping', PingSchema)).rejects.toThrow(ApiError);
    expect(callsTo('/ping')).toBe(1); // no replay without a session
  });

  it('a replay that 401s again surfaces the error — no refresh loop', async () => {
    const { api, ApiError } = await loadApi();
    fetchMock.mockImplementation(async (url) => {
      if (String(url).endsWith('/api/session')) return jsonResponse(200, { ok: true });
      return jsonResponse(401, { detail: 'still broken' });
    });

    await expect(api('/ping', PingSchema)).rejects.toThrow(ApiError);
    expect(callsTo('/api/session')).toBe(1); // refresh fired once, not in a loop
    expect(callsTo('/ping')).toBe(2);
  });

  it('concurrent 401s share ONE refresh (single-flight, no double-fire)', async () => {
    const { api } = await loadApi();
    const firstCallPerPath = new Set<string>();
    fetchMock.mockImplementation(async (url) => {
      const path = String(url);
      if (path.endsWith('/api/session')) {
        await new Promise((resolve) => setTimeout(resolve, 10)); // a slow refresh
        return jsonResponse(200, { ok: true });
      }
      if (!firstCallPerPath.has(path)) {
        firstCallPerPath.add(path);
        return jsonResponse(401, { detail: 'expired' });
      }
      return jsonResponse(200, { pong: true });
    });

    const results = await Promise.all([
      api('/ping-a', PingSchema),
      api('/ping-b', PingSchema),
      api('/ping-c', PingSchema),
    ]);
    expect(results).toEqual([{ pong: true }, { pong: true }, { pong: true }]);
    expect(callsTo('/api/session')).toBe(1); // the whole point
  });

  it('a later 401 (after the shared refresh resolved) may refresh again', async () => {
    const { api } = await loadApi();
    fetchMock.mockImplementation(async (url) => {
      const path = String(url);
      if (path.endsWith('/api/session')) return jsonResponse(200, { ok: true });
      const nth = callsTo(path.slice(path.lastIndexOf('/')));
      return nth % 2 === 1 ? jsonResponse(401, {}) : jsonResponse(200, { pong: true });
    });

    await api('/first', PingSchema);
    await api('/second', PingSchema);
    expect(callsTo('/api/session')).toBe(2); // one per expired session, not one forever
  });

  it('turns a recognized preview refusal into 404 without falling through to fetch', async () => {
    const previousPreview = process.env.NEXT_PUBLIC_DEMO_PREVIEW;
    process.env.NEXT_PUBLIC_DEMO_PREVIEW = 'true';
    try {
      const { api } = await loadApi();

      await expect(api('/renter/t_anna', RenterOverviewResponseSchema)).rejects.toMatchObject({
        name: 'ApiError',
        status: 404,
        path: '/renter/t_anna',
      });
      expect(fetchMock).not.toHaveBeenCalled();
    } finally {
      if (previousPreview === undefined) delete process.env.NEXT_PUBLIC_DEMO_PREVIEW;
      else process.env.NEXT_PUBLIC_DEMO_PREVIEW = previousPreview;
      vi.resetModules();
    }
  });
});
