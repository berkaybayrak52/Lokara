'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from '@/lib/api';
import type {
  CalibrationDataState,
  HeatingCostCategory,
  MeterDeviceType,
  ReadingReason,
  RemoteReadability,
} from '@/lib/contracts';
import {
  HeatingBillingModeListSchema,
  HeatingBillingModeOutSchema,
  HeatingCostListResponseSchema,
  HeatingCostOutSchema,
  MeterOutSchema,
  MeterWorkspaceResponseSchema,
  ReadingPlausibilityResponseSchema,
} from '@/lib/contracts';

const MdlStatementOutSchema = z.object({
  id: z.string(),
  branch: z.enum(['NET', 'GROSS']),
  periodLabel: z.string(),
  confirmedTotalCents: z.number().int(),
  ownerPositionCents: z.number().int(),
  positionCount: z.number().int(),
  sourceRef: z.string(),
  version: z.number().int(),
});
const MdlStatementListSchema = z.array(MdlStatementOutSchema);

export function useMeterWorkspace(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'meter-workspace'],
    queryFn: () => api(`/a/${accountId}/meter-workspace`, MeterWorkspaceResponseSchema),
    retry: false,
  });
}

export function useMeters(accountId: string, buildingId: string) {
  const workspace = useMeterWorkspace(accountId);
  return {
    ...workspace,
    data: workspace.data
      ? {
          meters: workspace.data.buildings
            .filter((building) => building.id === buildingId)
            .flatMap((building) => [
              ...building.buildingMeters,
              ...building.units.flatMap((unit) => unit.meters),
            ]),
          periodLabel: workspace.data.periodLabel,
        }
      : undefined,
  };
}

export function useHeatingCosts(accountId: string, buildingId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings', buildingId, 'heating-costs'],
    queryFn: () =>
      api(`/a/${accountId}/buildings/${buildingId}/heating-costs`, HeatingCostListResponseSchema),
    retry: false,
  });
}

export function useHeatingBillingModes(accountId: string, buildingId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings', buildingId, 'heating-billing-modes'],
    queryFn: () =>
      api(
        `/a/${accountId}/buildings/${buildingId}/heating-billing-modes`,
        HeatingBillingModeListSchema,
      ),
    retry: false,
  });
}

export function useMdlStatements(accountId: string, buildingId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings', buildingId, 'mdl-statements'],
    queryFn: () =>
      api(`/a/${accountId}/buildings/${buildingId}/mdl-statements`, MdlStatementListSchema),
    retry: false,
  });
}

function useMeterInvalidation(accountId: string, buildingId?: string) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['account', accountId, 'meter-workspace'] });
    if (buildingId) {
      void queryClient.invalidateQueries({
        queryKey: ['account', accountId, 'buildings', buildingId],
      });
    }
    void queryClient.invalidateQueries({ queryKey: ['account', accountId, 'statement'] });
  };
}

export interface MeterCreateInput {
  unitId?: string | null;
  deviceType: MeterDeviceType;
  serial: string;
  label?: string | null;
  location?: string | null;
  manufacturer?: string | null;
  model?: string | null;
  installedOn: string;
  remoteReadability: RemoteReadability;
  calibrationDataState: CalibrationDataState;
  calibrationDate?: string | null;
  calibrationEvidenceRef?: string | null;
  valuationFactorX1000?: number | null;
  creationMode: 'NEW' | 'EXISTING' | 'REPLACEMENT';
  replacesMeterId?: string | null;
  replacementDate?: string | null;
  oldFinalValueX1000?: number | null;
  newInitialValueX1000?: number | null;
  replacementReason?: string | null;
  gasConversion?: {
    calorificFactorKwhPerM3: string;
    conditionNumber: string;
    validFrom: string;
    validTo: string | null;
    supplierInvoiceReference: string;
  } | null;
}

export function useCreateMeter(accountId: string, buildingId: string) {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: (input: MeterCreateInput) =>
      api(`/a/${accountId}/buildings/${buildingId}/meters`, MeterOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export function useEndMeter(accountId: string, buildingId: string, action: 'remove' | 'void') {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: ({
      meterId,
      effectiveOn,
      reason,
    }: {
      meterId: string;
      effectiveOn: string;
      reason: string;
    }) =>
      api(`/a/${accountId}/meters/${meterId}/${action}`, MeterOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ effectiveOn, reason }),
      }),
    onSuccess: invalidate,
  });
}

export interface ReadingCreateInput {
  meterId: string;
  readAt: string;
  valueX1000: number;
  reason: ReadingReason;
  note?: string | null;
  supersedesReadingId?: string | null;
  confirmationNote?: string | null;
  confirmedFindingCodes?: string[];
}

export function useCheckReading(accountId: string) {
  return useMutation({
    mutationFn: ({ meterId, ...body }: ReadingCreateInput) =>
      api(`/a/${accountId}/meters/${meterId}/readings/check`, ReadingPlausibilityResponseSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
  });
}

export function useCreateReading(accountId: string, buildingId: string) {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: ({ meterId, ...body }: ReadingCreateInput) =>
      api(`/a/${accountId}/meters/${meterId}/readings`, MeterOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    onSuccess: invalidate,
  });
}

export interface HeatingCostCreateInput {
  category: HeatingCostCategory;
  label: string;
  amountCents: number;
  periodFrom: string;
  periodTo: string;
  co2KgX1000?: number | null;
  co2CostCents?: number | null;
  sourceRef: string;
}

export function useCreateHeatingCost(accountId: string, buildingId: string) {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: (input: HeatingCostCreateInput) =>
      api(`/a/${accountId}/buildings/${buildingId}/heating-costs`, HeatingCostOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}

export function useVoidHeatingCost(accountId: string, buildingId: string) {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: ({ heatingCostId, reason }: { heatingCostId: string; reason: string }) =>
      api(`/a/${accountId}/heating-costs/${heatingCostId}/void`, HeatingCostOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      }),
    onSuccess: invalidate,
  });
}

interface HeatingBillingModeInput {
  periodFrom: string;
  periodTo: string;
  mode: 'LOKARA' | 'EXTERNAL_PROVIDER';
  providerName?: string | null;
  providerReference?: string | null;
  externalStatus?:
    'BEAUFTRAGT' | 'DATEN_UEBERMITTELT' | 'ABRECHNUNG_ERHALTEN' | 'GEPRUEFT' | 'UEBERNOMMEN' | null;
  mdlStatementId?: string | null;
  note?: string | null;
}

export function useCreateHeatingBillingMode(accountId: string, buildingId: string) {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: (input: HeatingBillingModeInput) =>
      api(
        `/a/${accountId}/buildings/${buildingId}/heating-billing-modes`,
        HeatingBillingModeOutSchema,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(input),
        },
      ),
    onSuccess: invalidate,
  });
}

interface MdlStatementInput {
  branch: 'NET' | 'GROSS';
  periodFrom: string;
  periodTo: string;
  confirmedTotalCents: number;
  ownerPositionCents: number;
  positions: { tenancyId: string; amountCents: number }[];
  sourceRef: string;
  co2KgX1000?: number | null;
  co2CostCents?: number | null;
  heatedAreaSqmX100?: number | null;
  co2EvidencePresent: boolean;
}

export function useConfirmMdlStatement(accountId: string, buildingId: string) {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: (input: MdlStatementInput) =>
      api(`/a/${accountId}/buildings/${buildingId}/mdl-statements`, MdlStatementOutSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  });
}
