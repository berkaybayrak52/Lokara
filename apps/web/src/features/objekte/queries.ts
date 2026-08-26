'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/lib/api';
import {
  BuildingDetailResponseSchema,
  BuildingListResponseSchema,
  BuildingSummarySchema,
  TenancyOutSchema,
  UnitDetailResponseSchema,
  UnitSummarySchema,
} from '@/lib/contracts';

export function useBuildings(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings'],
    queryFn: () => api(`/a/${accountId}/buildings`, BuildingListResponseSchema),
  });
}

export function useBuildingDetail(accountId: string, buildingId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings', buildingId],
    queryFn: () => api(`/a/${accountId}/buildings/${buildingId}`, BuildingDetailResponseSchema),
    retry: false,
  });
}

export function useUnitDetail(accountId: string, unitId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'units', unitId],
    queryFn: () => api(`/a/${accountId}/units/${unitId}`, UnitDetailResponseSchema),
    retry: false,
  });
}

interface BuildingCreateInput {
  name: string;
  street: string;
  houseNumber: string;
  postalCode: string;
  city: string;
  country: string;
  buildingType: string;
  isResidential: boolean;
}

export function useCreateBuilding(accountId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: BuildingCreateInput) =>
      api(`/a/${accountId}/buildings`, BuildingSummarySchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['account', accountId, 'buildings'] }),
  });
}

interface UnitCreateInput {
  label: string;
  areaSqmX100: number;
}

export function useCreateUnit(accountId: string, buildingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UnitCreateInput) =>
      api(`/a/${accountId}/buildings/${buildingId}/units`, UnitSummarySchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['account', accountId, 'buildings'] }),
  });
}

interface TenancyCreateInput {
  renterName: string;
  validFrom: string;
  validTo: string | null;
  baseRentCents: number;
  // API TenancyCreate (schemas.py): initial advance + its non-empty declaration ref.
  initialAdvancePaymentCents: number;
  advanceDeclarationRef: string;
}

export function useCreateTenancy(accountId: string, unitId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TenancyCreateInput) =>
      api(`/a/${accountId}/units/${unitId}/tenancies`, TenancyOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['account', accountId, 'units', unitId] });
      void queryClient.invalidateQueries({ queryKey: ['account', accountId, 'buildings'] });
    },
  });
}
