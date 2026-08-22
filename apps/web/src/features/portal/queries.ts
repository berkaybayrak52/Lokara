'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import {
  DemoLoadResponseSchema,
  DemoStatementResponseSchema,
  DemoSummaryResponseSchema,
  MeResponseSchema,
} from '@/lib/contracts';

/** The Person's relationships — drives the left nav (navigation only; every
 * request re-authorizes independently on the API). */
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api('/me', MeResponseSchema),
  });
}

export function useAccountSummary(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'summary'],
    queryFn: () => api(`/a/${accountId}/summary`, DemoSummaryResponseSchema),
    retry: false, // a 404 is the designed empty state, not a flake
  });
}

/** One-click "Demo-Szenario laden" (docs/06): idempotent fixture seed. */
export function useLoadDemo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api('/demo/load', DemoLoadResponseSchema, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}

/**
 * Back to exactly the seeded scenario. Destructive, so the UI gates it behind
 * a confirmation — but it is the honest fix for a demo account polluted by a
 * rehearsal: better one deliberate reset than a pitch that opens on
 * "Testgasse 5". Invalidates everything, since it replaced everything.
 */
export function useResetDemo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api('/demo/reset', DemoLoadResponseSchema, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}

/** The statement run is explicit (the demo beat is the click), so the query
 * stays disabled until the user asks for the numbers. */
export function useDemoStatement(accountId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['account', accountId, 'statement', 'demo'],
    queryFn: () => api(`/a/${accountId}/statements/demo`, DemoStatementResponseSchema),
    enabled,
    retry: false,
  });
}

/** One object, one period — the selection Page 01 § 4 D1 makes before anything
 * is calculated. `periodTo` is inclusive, as a landlord reads a billing period;
 * the API converts it to the half-open window the engines use.
 *
 * The selection is part of the query key, so switching object or period does
 * not show the previous run's figures under the new heading. */
export function useStatement(
  accountId: string,
  selection: { buildingId: string; periodFrom: string; periodTo: string },
  enabled: boolean,
) {
  const query = new URLSearchParams({
    building_id: selection.buildingId,
    period_from: selection.periodFrom,
    period_to: selection.periodTo,
  });
  return useQuery({
    queryKey: [
      'account',
      accountId,
      'statement',
      selection.buildingId,
      selection.periodFrom,
      selection.periodTo,
    ],
    queryFn: () => api(`/a/${accountId}/statements?${query}`, DemoStatementResponseSchema),
    enabled,
    retry: false,
  });
}
