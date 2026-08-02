'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from '@/lib/api';
import type { AllocationKey } from '@/lib/contracts';
import { CostEntryOutSchema, CostListResponseSchema } from '@/lib/contracts';

export function useCosts(accountId: string, buildingId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings', buildingId, 'costs'],
    queryFn: () =>
      api(`/a/${accountId}/buildings/${buildingId}/costs`, CostListResponseSchema),
    retry: false,
  });
}

export interface KeyChoice {
  key: AllocationKey;
  directUnitId?: string | null;
  directTenancyId?: string | null;
}

export interface CostCreateInput extends KeyChoice {
  label: string;
  amountCents: number;
  periodFrom: string;
  periodTo: string;
}

/** Invalidates costs AND the statement: a cost change re-runs the calculation. */
function useCostInvalidation(accountId: string, buildingId: string) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({
      queryKey: ['account', accountId, 'buildings', buildingId, 'costs'],
    });
    void queryClient.invalidateQueries({
      queryKey: ['account', accountId, 'statement'],
    });
  };
}

export function useCreateCost(accountId: string, buildingId: string) {
  const invalidate = useCostInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: (input: CostCreateInput) =>
      api(`/a/${accountId}/buildings/${buildingId}/costs`, CostEntryOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

/** Re-key a cost: appends an assignment server-side — no entered data is lost. */
export function useReassignKey(accountId: string, buildingId: string) {
  const invalidate = useCostInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: ({ costId, ...choice }: KeyChoice & { costId: string }) =>
      api(`/a/${accountId}/costs/${costId}/key`, CostEntryOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(choice),
      }),
    onSuccess: invalidate,
  });
}

export function useDeleteCost(accountId: string, buildingId: string) {
  const invalidate = useCostInvalidation(accountId, buildingId);
  return useMutation({
    // 204 No Content — nothing to parse, so the schema is the empty response.
    mutationFn: (costId: string) =>
      api(`/a/${accountId}/costs/${costId}`, z.undefined(), { method: 'DELETE' }),
    onSuccess: invalidate,
  });
}
