'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import type { AllocationKey } from '@/lib/contracts';
import {
  CostCatalogueResponseSchema,
  CostEntryOutSchema,
  CostListResponseSchema,
  CostVoidOutSchema,
} from '@/lib/contracts';

export function useCosts(accountId: string, buildingId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings', buildingId, 'costs'],
    queryFn: () => api(`/a/${accountId}/buildings/${buildingId}/costs`, CostListResponseSchema),
    retry: false,
  });
}

export function useCostCatalogue(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'cost-catalogue'],
    queryFn: () => api(`/a/${accountId}/cost-catalogue`, CostCatalogueResponseSchema),
    staleTime: 60 * 60 * 1000,
    retry: false,
  });
}

export interface KeyChoice {
  key: AllocationKey;
  directUnitId?: string | null;
  directTenancyId?: string | null;
}

export interface CostCreateInput {
  catalogueId: string;
  label: string;
  amountCents: number;
  periodFrom: string;
  periodTo: string;
  keyOverride?: AllocationKey;
  directUnitId?: string;
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

export function useVoidCost(accountId: string, buildingId: string) {
  const invalidate = useCostInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: ({ costId, reason }: { costId: string; reason: string }) =>
      api(`/a/${accountId}/costs/${costId}/void`, CostVoidOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      }),
    onSuccess: invalidate,
  });
}
