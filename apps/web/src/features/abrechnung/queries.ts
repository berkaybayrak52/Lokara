'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from '@/lib/api';
import {
  StatementDraftReadinessSchema,
  StatementDraftSchema,
  StatementPeriodSuggestionSchema,
  StatementRecordSchema,
} from '@/lib/contracts';

export function useStatementRecords(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'statement-records'],
    queryFn: () => api(`/a/${accountId}/statement-records`, StatementRecordSchema.array()),
    retry: false,
  });
}

export function useStatementPeriodSuggestions(accountId: string, buildingId: string) {
  const query = new URLSearchParams({ building_id: buildingId });
  return useQuery({
    queryKey: ['account', accountId, 'statement-period-suggestions', buildingId],
    queryFn: () =>
      api(
        `/a/${accountId}/statement-period-suggestions?${query}`,
        StatementPeriodSuggestionSchema.array(),
      ),
    enabled: buildingId !== '',
    retry: false,
  });
}

export function useStatementDraft(accountId: string, draftId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'statement-draft', draftId],
    queryFn: () => api(`/a/${accountId}/statement-drafts/${draftId}`, StatementDraftSchema),
    enabled: draftId !== '',
    retry: false,
  });
}

export function useCreateStatementDraft(accountId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      buildingId: string;
      periodStart: string;
      periodEnd: string;
      title?: string;
      correctionOfStatementId?: string;
      correctionReason?: string;
    }) =>
      api(`/a/${accountId}/statement-drafts`, StatementDraftSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['account', accountId, 'statement-records'] }),
  });
}

export function useUpdateStatementDraft(accountId: string, draftId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      version: number;
      title?: string;
      currentStep?: number;
      selectedUnitIds?: string[];
      overrides?: Record<string, unknown>;
      correctionReason?: string;
    }) =>
      api(`/a/${accountId}/statement-drafts/${draftId}`, StatementDraftSchema, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      }),
    onSuccess: (draft) => {
      queryClient.setQueryData(['account', accountId, 'statement-draft', draftId], draft);
      void queryClient.invalidateQueries({
        queryKey: ['account', accountId, 'statement-draft-readiness', draftId],
      });
      void queryClient.invalidateQueries({
        queryKey: ['account', accountId, 'statement-records'],
      });
    },
  });
}

export function useStatementDraftReadiness(accountId: string, draftId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'statement-draft-readiness', draftId],
    queryFn: () =>
      api(`/a/${accountId}/statement-drafts/${draftId}/readiness`, StatementDraftReadinessSchema, {
        method: 'POST',
      }),
    enabled: draftId !== '',
    retry: false,
  });
}

export function useCancelStatementDraft(accountId: string, draftId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api(`/a/${accountId}/statement-drafts/${draftId}/cancel`, StatementDraftSchema, {
        method: 'POST',
      }),
    onSuccess: () => queryClient.invalidateQueries(),
  });
}

export const IdResponseSchema = z.object({ id: z.string() });
