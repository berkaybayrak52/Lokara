'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from '@/lib/api';

const JsonObjectSchema = z.record(z.unknown());

export const GuardSchema = z.object({
  id: z.string(),
  guardCode: z.string(),
  subjectType: z.string(),
  subjectId: z.string(),
  buildingId: z.string(),
  unitId: z.string().nullable(),
  tenancyId: z.string().nullable(),
  renterId: z.string().nullable(),
  occurrenceKey: z.string(),
  inputSnapshot: JsonObjectSchema,
  resultSnapshot: JsonObjectSchema,
  ruleSnapshot: JsonObjectSchema,
  evaluatedAt: z.string(),
  resolutionEvents: z.array(JsonObjectSchema),
});
export const GuardListSchema = z.object({
  guards: z.array(GuardSchema),
  sourceIds: z.array(z.string().min(1)).min(1),
});

export const ScheduleSchema = z.object({
  id: z.string(),
  buildingId: z.string(),
  deliveryKind: z.string(),
  version: z.number(),
  enabled: z.boolean(),
  supersedesScheduleVersionId: z.string().nullable(),
  validFrom: z.string(),
  scheduleSnapshot: z.record(z.unknown()),
  createdAt: z.string().nullable().optional(),
});
export const ScheduleListSchema = z.object({ schedules: z.array(ScheduleSchema) });

export const ReminderSchema = z.object({
  id: z.string(),
  guardEvaluationId: z.string(),
  occurrenceKey: z.string(),
  buildingId: z.string(),
  channel: z.string(),
  dueAt: z.string(),
  idempotencyKey: z.string(),
  payloadSnapshot: JsonObjectSchema,
  createdAt: z.string(),
});
export const ReminderListSchema = z.object({ reminders: z.array(ReminderSchema) });

export const ChecklistEventSchema = z.object({
  id: z.string(),
  itemId: z.string(),
  eventType: z.string(),
  occurredAt: z.string(),
  actorMembershipId: z.string(),
  idempotencyKey: z.string(),
  eventSnapshot: JsonObjectSchema,
});
export const ChecklistSchema = z.object({
  id: z.string(),
  buildingId: z.string(),
  templateId: z.string(),
  templateVersion: z.number(),
  templateSnapshot: JsonObjectSchema,
  occurrenceKey: z.string(),
  events: z.array(ChecklistEventSchema),
});
export const ChecklistListSchema = z.object({
  checklists: z.array(ChecklistSchema),
  productionBlocked: z.boolean(),
  blocker: z.string().nullable(),
});

export const DeliverySchema = z.object({
  id: z.string(),
  renterId: z.string(),
  artifactId: z.string(),
  buildingId: z.string().nullable().optional(),
  occurrenceKey: z.string().nullable().optional(),
  deliveryKind: z.string().nullable().optional(),
  recipient: z.string().nullable().optional(),
  blockedReason: z.string().nullable(),
  blockedDetail: z.string().nullable().optional(),
  providerStatus: z.string().nullable(),
  attemptedAt: z.string().nullable(),
  statusOccurredAt: z.string().nullable(),
  suppressionEvents: z.array(
    z.object({
      id: z.string(),
      normalizedAddress: z.string(),
      reason: z.string(),
      occurredAt: z.string(),
    }),
  ),
  legallyConfirmed: z.boolean(),
  deliveredOn: z.string().nullable(),
  evidenceReference: z.string().nullable(),
});
export const DeliveryListSchema = z.object({ deliveries: z.array(DeliverySchema) });

export const GuardRunInputSchema = z.object({
  today: z.string().date(),
  now: z.string().datetime({ offset: true }),
  sourceIds: z.array(z.string().trim().min(1)).min(1),
});
const GuardRunResultSchema = z.object({
  accountId: z.string(),
  evaluatedOccurrences: z.number(),
  existingOccurrences: z.number(),
  createdReminders: z.number(),
  pushAvailable: z.boolean(),
  productionBlockers: z.array(z.string()),
});
export const ScheduleInputSchema = z.object({
  sourceId: z.string().trim().min(1),
  deliveryKind: z.enum(['ANNUAL_STATEMENT', 'UVI']),
  validFrom: z.string().date(),
  enabled: z.boolean(),
});
const ChecklistEventInputSchema = z.object({
  eventType: z.enum(['COMPLETED', 'REOPENED']),
  occurredAt: z.string().datetime({ offset: true }),
  idempotencyKey: z.string().min(1).max(300),
  eventSnapshot: JsonObjectSchema,
});
const DeliveryInputSchema = z.object({
  buildingId: z.string().min(1),
  renterId: z.string().min(1),
  artifactId: z.string().min(1),
  deliveryKind: z.enum(['ANNUAL_STATEMENT', 'UVI']),
  occurrenceKey: z.string().min(1),
});
const DeliveryConfirmationInputSchema = z.object({
  deliveredOn: z.string().date(),
  evidenceReference: z.string().trim().min(1).max(500),
});

export type GuardApi = z.infer<typeof GuardSchema>;
export type ScheduleApi = z.infer<typeof ScheduleSchema>;
export type ReminderApi = z.infer<typeof ReminderSchema>;
export type ChecklistApi = z.infer<typeof ChecklistSchema>;
export type DeliveryApi = z.infer<typeof DeliverySchema>;

export function buildM9ApiPaths(
  accountId: string,
  ids: { checklistId: string; itemId: string; deliveryId: string },
) {
  const root = `/a/${accountId}`;
  return {
    guards: `${root}/guards`,
    guardRuns: `${root}/guard-runs`,
    deliverySchedules: `${root}/delivery-schedules`,
    reminders: `${root}/reminders`,
    checklists: `${root}/checklists`,
    checklistItemEvents: `${root}/checklists/${ids.checklistId}/items/${ids.itemId}/events`,
    deliveries: `${root}/deliveries`,
    deliveryConfirmation: `${root}/deliveries/${ids.deliveryId}/confirm`,
  };
}

const accountKey = (accountId: string) => ['account', accountId, 'm9'] as const;

export type M9Role = 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR';

export function m9ResourcesForRole(role: M9Role): string[] {
  if (role === 'EMPLOYEE') return ['guards', 'checklists'];
  if (role === 'OWNER') {
    return ['guards', 'delivery-schedules', 'reminders', 'checklists', 'deliveries'];
  }
  return [];
}

export function useM9Data(accountId: string, role: M9Role) {
  const root = `/a/${accountId}`;
  const resources = m9ResourcesForRole(role);
  return {
    guards: useQuery({
      queryKey: [...accountKey(accountId), 'guards'],
      queryFn: () => api(`${root}/guards`, GuardListSchema),
      enabled: resources.includes('guards'),
      retry: false,
    }),
    schedules: useQuery({
      queryKey: [...accountKey(accountId), 'delivery-schedules'],
      queryFn: () => api(`${root}/delivery-schedules`, ScheduleListSchema),
      enabled: resources.includes('delivery-schedules'),
      retry: false,
    }),
    reminders: useQuery({
      queryKey: [...accountKey(accountId), 'reminders'],
      queryFn: () => api(`${root}/reminders`, ReminderListSchema),
      enabled: resources.includes('reminders'),
      retry: false,
    }),
    checklists: useQuery({
      queryKey: [...accountKey(accountId), 'checklists'],
      queryFn: () => api(`${root}/checklists`, ChecklistListSchema),
      enabled: resources.includes('checklists'),
      retry: false,
    }),
    deliveries: useQuery({
      queryKey: [...accountKey(accountId), 'deliveries'],
      queryFn: () => api(`${root}/deliveries`, DeliveryListSchema),
      enabled: resources.includes('deliveries'),
      retry: false,
    }),
  };
}

function useM9Invalidation(accountId: string) {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: accountKey(accountId) });
}

export function useM9Actions(accountId: string) {
  const invalidate = useM9Invalidation(accountId);
  return {
    runGuards: useMutation({
      mutationFn: (body: z.input<typeof GuardRunInputSchema>) =>
        api(`/a/${accountId}/guard-runs`, GuardRunResultSchema, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(GuardRunInputSchema.parse(body)),
        }),
      onSuccess: invalidate,
    }),
    saveSchedule: useMutation({
      mutationFn: (body: z.input<typeof ScheduleInputSchema>) =>
        api(`/a/${accountId}/delivery-schedules`, ScheduleSchema, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(ScheduleInputSchema.parse(body)),
        }),
      onSuccess: invalidate,
    }),
    recordChecklistEvent: useMutation({
      mutationFn: ({
        checklistId,
        itemId,
        body,
      }: {
        checklistId: string;
        itemId: string;
        body: z.input<typeof ChecklistEventInputSchema>;
      }) =>
        api(
          `/a/${accountId}/checklists/${checklistId}/items/${itemId}/events`,
          ChecklistEventSchema,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ChecklistEventInputSchema.parse(body)),
          },
        ),
      onSuccess: invalidate,
    }),
    sendDelivery: useMutation({
      mutationFn: (body: z.input<typeof DeliveryInputSchema>) =>
        api(`/a/${accountId}/deliveries`, DeliverySchema, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(DeliveryInputSchema.parse(body)),
        }),
      onSuccess: invalidate,
    }),
    confirmDelivery: useMutation({
      mutationFn: ({
        deliveryId,
        body,
      }: {
        deliveryId: string;
        body: z.input<typeof DeliveryConfirmationInputSchema>;
      }) =>
        api(`/a/${accountId}/deliveries/${deliveryId}/confirm`, DeliverySchema, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(DeliveryConfirmationInputSchema.parse(body)),
        }),
      onSuccess: invalidate,
    }),
  };
}
