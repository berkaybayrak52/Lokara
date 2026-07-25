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
