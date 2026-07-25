'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from '@/lib/api';
import type { MeasurementUnit, MeterKind, ReadingReason } from '@/lib/contracts';
import {
  HeatingCostListResponseSchema,
  HeatingCostOutSchema,
  MeterListResponseSchema,
  MeterOutSchema,
} from '@/lib/contracts';

export function useMeters(accountId: string, buildingId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings', buildingId, 'meters'],
    queryFn: () => api(`/a/${accountId}/buildings/${buildingId}/meters`, MeterListResponseSchema),
    retry: false,
  });
}

export function useHeatingCosts(accountId: string, buildingId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'buildings', buildingId, 'heating-costs'],
    queryFn: () =>
      api(`/a/${accountId}/buildings/${buildingId}/heating-costs`, HeatingCostListResponseSchema),
    retry: false,
  });
}

/**
 * Meters and heating costs both feed the Heizkostenabrechnung, so every
 * mutation here invalidates the statement too — the Abrechnung can never show
 * numbers derived from readings that have since changed.
 */
function useMeterInvalidation(accountId: string, buildingId: string) {
  const queryClient = useQueryClient();
  return () => {
    for (const key of ['meters', 'heating-costs']) {
      void queryClient.invalidateQueries({
        queryKey: ['account', accountId, 'buildings', buildingId, key],
      });
    }
    void queryClient.invalidateQueries({ queryKey: ['account', accountId, 'statement'] });
  };
}

export interface MeterCreateInput {
  unitId?: string | null;
  kind: MeterKind;
  measurementUnit: MeasurementUnit;
  serial: string;
  label?: string | null;
  calibrationValidUntil?: string | null;
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

export function useDeleteMeter(accountId: string, buildingId: string) {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: (meterId: string) =>
      api(`/a/${accountId}/meters/${meterId}`, z.undefined(), { method: 'DELETE' }),
    onSuccess: invalidate,
  });
}

export interface ReadingCreateInput {
  meterId: string;
  readAt: string;
  valueX1000: number;
  reason: ReadingReason;
  note?: string | null;
}

/** Create-only by design: there is no update mutation, because there is no
 *  update endpoint — a correction is another POST. */
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
  label: string;
  amountCents: number;
  periodFrom: string;
  periodTo: string;
  co2KgX1000?: number | null;
  co2CostCents?: number | null;
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

export function useDeleteHeatingCost(accountId: string, buildingId: string) {
  const invalidate = useMeterInvalidation(accountId, buildingId);
  return useMutation({
    mutationFn: (heatingCostId: string) =>
      api(`/a/${accountId}/heating-costs/${heatingCostId}`, z.undefined(), { method: 'DELETE' }),
    onSuccess: invalidate,
  });
}
