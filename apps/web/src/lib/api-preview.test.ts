import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { api } from './api';

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
  vi.stubEnv('NEXT_PUBLIC_DEMO_PREVIEW', 'true');
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('preview transport write isolation', () => {
  it.each(['POST', 'PUT', 'PATCH', 'DELETE', 'post'])(
    'refuses unsupported %s requests before reaching the backend', async (method) => {
      await expect(api('/a/account-1/buildings/building-1/uvi-runs', z.unknown(), {
        method,
        body: JSON.stringify({ tenancyId: 'tenancy-1', targetMonth: '2026-07-01' }),
      })).rejects.toMatchObject({ status: 403 });
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it('preserves supported synthetic payment decisions without network access', async () => {
    await expect(api('/a/acc_demo_lokara/bank-transactions/transaction-1/decision', z.object({
      transaction_id: z.string(), outcome: z.string(), ledger_entry_id: z.null(),
    }), { method: 'POST', body: JSON.stringify({ outcome: 'rejected' }) })).resolves.toEqual({
      transaction_id: 'transaction-1', outcome: 'rejected', ledger_entry_id: null,
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('allows a live UVI write when preview is disabled', async () => {
    vi.stubEnv('NEXT_PUBLIC_DEMO_PREVIEW', 'false');
    await expect(api('/a/account-1/buildings/building-1/uvi-runs', z.unknown(), {
      method: 'POST',
    })).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
