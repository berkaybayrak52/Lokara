'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { API_URL, api } from '@/lib/api';

const TaxBuildingListSchema = z.object({
  buildings: z.array(z.object({ id: z.string(), label: z.string() })),
});
const AfaHistorySchema = z.object({
  records: z.array(
    z.object({
      id: z.string().nullable(),
      version: z.number().int().nullable(),
      buildingId: z.string(),
      taxYear: z.number().int(),
      annualAfaCents: z.number().int(),
      result: z.record(z.unknown()),
      rechtsstand: z.string(),
      productionBlocked: z.boolean(),
      generatedAt: z.string(),
    }),
  ),
});
const ReadinessSchema = z.object({
  id: z.string(),
  findings: z.array(z.record(z.unknown())),
  rechtsstand: z.string(),
  productionBlocked: z.boolean(),
  generatedAt: z.string(),
});
const ExportHistorySchema = z.object({
  exports: z.array(
    z.object({
      id: z.string(),
      version: z.number().int(),
      sha256: z.string(),
      generatedAt: z.string(),
      artifacts: z.array(
        z.object({
          id: z.string(),
          filename: z.string(),
          sha256: z.string(),
          artifactKind: z.string(),
        }),
      ),
      readinessFindings: z.array(z.record(z.unknown())),
      blockers: z.array(z.string()),
      afaRechtsstand: z.string(),
      exportRechtsstand: z.string(),
      exportKind: z.enum(['anlage_v_pdf', 'anlage_v_csv', 'datev_extf']),
      buildingId: z.string().nullable(),
      taxYear: z.number().int().nullable(),
    }),
  ),
});
const AfaResponseSchema = z.object({
  id: z.string().nullable(),
  taxYearAfaCents: z.number().int(),
  deductibleAfaCents: z.number().int(),
  nonDeductibleAfaCents: z.number().int(),
  productionBlocked: z.boolean(),
});
const ProfileResponseSchema = z.object({ id: z.string() });
const ProfileDetailSchema = z.object({
  id: z.string(),
  version: z.number().int(),
  profile: z.record(z.unknown()),
  productionBlocked: z.boolean(),
  generatedAt: z.string(),
});
const MappingResponseSchema = z.object({ id: z.string() });
const MappingDetailSchema = z.object({
  id: z.string(),
  version: z.number().int(),
  taxYear: z.number().int(),
  mapping: z.array(z.record(z.unknown())),
  sourceVersion: z.string(),
  rechtsstand: z.string(),
  productionBlocked: z.boolean(),
  generatedAt: z.string(),
});

export function useTaxBuildings(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'tax', 'buildings'],
    queryFn: () => api(`/a/${accountId}/tax/buildings`, TaxBuildingListSchema),
  });
}
export function useTaxAfaHistory(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'tax', 'afa'],
    queryFn: () => api(`/a/${accountId}/tax/afa/history`, AfaHistorySchema),
  });
}
export function useTaxExportHistory(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'tax', 'exports'],
    queryFn: () => api(`/a/${accountId}/tax/exports`, ExportHistorySchema),
  });
}
export function useTaxAdviserProfile(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'tax', 'adviser-profile'],
    queryFn: () => api(`/a/${accountId}/tax/adviser-profile`, ProfileDetailSchema),
    retry: false,
  });
}
export function useTaxMapping(accountId: string, taxYear: number) {
  return useQuery({
    queryKey: ['account', accountId, 'tax', 'mapping', taxYear],
    queryFn: () => api(`/a/${accountId}/tax/mappings/${taxYear}`, MappingDetailSchema),
    retry: false,
  });
}
export function useTaxActions(accountId: string) {
  const client = useQueryClient();
  const post = (path: string, body: object, schema: z.ZodType) =>
    api(`/a/${accountId}${path}`, schema, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  return {
    previewAfa: useMutation({
      mutationFn: (body: object) => post('/tax/afa/preview', body, AfaResponseSchema),
    }),
    saveAfa: useMutation({
      mutationFn: (body: object) => post('/tax/afa', body, AfaResponseSchema),
      onSuccess: () => client.invalidateQueries({ queryKey: ['account', accountId, 'tax', 'afa'] }),
    }),
    checkReadiness: useMutation({
      mutationFn: (body: object) => post('/tax/readiness', body, ReadinessSchema),
    }),
    saveProfile: useMutation({
      mutationFn: (body: object) => post('/tax/adviser-profile', body, ProfileResponseSchema),
      onSuccess: () =>
        client.invalidateQueries({
          queryKey: ['account', accountId, 'tax', 'adviser-profile'],
        }),
    }),
    saveMapping: useMutation({
      mutationFn: ({ taxYear, body }: { taxYear: number; body: object }) =>
        post(`/tax/mappings/${taxYear}`, body, MappingResponseSchema),
      onSuccess: (_data, variables) =>
        client.invalidateQueries({
          queryKey: ['account', accountId, 'tax', 'mapping', variables.taxYear],
        }),
    }),
    generate: useMutation({ mutationFn: (body: object) => post('/tax/exports', body, z.never()) }),
  };
}
export function taxArtifactUrl(accountId: string, exportId: string, artifactId: string) {
  return `${API_URL}/a/${accountId}/tax/exports/${exportId}/artifacts/${artifactId}`;
}
