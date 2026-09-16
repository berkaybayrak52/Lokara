'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { api } from '@/lib/api';

const KpiSlotSchema = z
  .object({
    status: z.enum(['available', 'unavailable']),
    value: z.union([z.number().int(), z.literal('—')]).optional(),
    before_tax: z.number().int().optional(),
    after_tax: z.number().int().optional(),
    color: z.enum(['red', 'amber', 'green']).optional(),
  })
  .passthrough();

export const InvestmentEntitlementSchema = z.object({ enabled: z.boolean() }).passthrough();
export const InvestmentCaseSchema = z
  .object({
    caseKey: z.string().min(1),
    version: z.number().int().positive(),
    resultId: z.string().min(1),
    outcome: z.string(),
    calculatedValues: z
      .object({ schedule: z.array(z.array(z.number().int())).default([]) })
      .passthrough(),
    kpiSlots: z.record(z.string(), KpiSlotSchema),
    rechtsstand: z.string(),
    productionBlocked: z.boolean(),
    findings: z.array(z.string()),
    warnings: z.array(z.string()),
  })
  .strict();
export const InvestmentSensitivitySchema = z
  .object({
    interestSensitivity: z.array(z.record(z.string(), z.unknown())),
    repaymentSensitivity: z.array(z.record(z.string(), z.unknown())),
    repaymentAxisMeaning: z.string(),
  })
  .strict();
export const InvestmentBankViewSchema = z.object({ bankView: z.record(z.string(), z.unknown()) });
const IntegerFact = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
const OptionalIntegerFact = IntegerFact.nullable().optional();
const OptionalTextFact = z.string().min(1).nullable().optional();
const AfaReferenceSchema = z
  .object({
    afaBasisCents: OptionalIntegerFact,
    annualFullAfaCents: OptionalIntegerFact,
    source: OptionalTextFact,
    recordVersion: OptionalTextFact,
  })
  .strict();
export const BankHeaderSchema = z
  .object({
    address: OptionalTextFact,
    propertyType: OptionalTextFact,
    yearBuilt: IntegerFact.min(1).nullable().optional(),
    areaSqmX100: OptionalIntegerFact,
    unitCount: OptionalIntegerFact,
    creator: OptionalTextFact,
    exportDate: OptionalTextFact,
    layoutVersion: OptionalTextFact,
  })
  .strict();
export const InvestmentCreateSchema = z
  .object({
    facts: z
      .object({
        purchasePriceCents: OptionalIntegerFact,
        acquisitionCostsCents: OptionalIntegerFact,
        monthlyActualRentCents: OptionalIntegerFact,
        vacancyBp: IntegerFact.max(10_000).nullable().optional(),
        administrationCents: OptionalIntegerFact,
        maintenanceCents: OptionalIntegerFact,
        reserveCents: OptionalIntegerFact,
        vacancyRiskCents: OptionalIntegerFact,
        equityCents: OptionalIntegerFact,
        loanCents: OptionalIntegerFact,
        interestBp: OptionalIntegerFact,
        initialRepaymentBp: OptionalIntegerFact,
        fixedMonthlyAnnuityCents: OptionalIntegerFact,
        marginalTaxBp: IntegerFact.max(9_999).nullable().optional(),
        buildingShareBp: IntegerFact.max(10_000).nullable().optional(),
        afaRateBp: OptionalIntegerFact,
        annualFullAfaCents: OptionalIntegerFact,
        afaRecordVersion: OptionalTextFact,
        analysisPeriodMonths: OptionalIntegerFact,
        financingProvenance: z.enum(['annahme', 'indikativ', 'angebot']).nullable().optional(),
        afaReference: AfaReferenceSchema.nullable().optional(),
        bankHeader: BankHeaderSchema.nullable().optional(),
      })
      .strict()
      .superRefine((facts, context) => {
        if (facts.initialRepaymentBp != null && facts.fixedMonthlyAnnuityCents != null) {
          context.addIssue({
            code: 'custom',
            path: ['initialRepaymentBp'],
            message: 'Nur eine Tilgungseingabe ist zulässig.',
          });
        }
        if (facts.annualFullAfaCents != null && facts.afaRecordVersion == null) {
          context.addIssue({
            code: 'custom',
            path: ['afaRecordVersion'],
            message: 'AfA-Version erforderlich.',
          });
        }
        const reference = facts.afaReference;
        if (
          reference &&
          (reference.afaBasisCents != null || reference.annualFullAfaCents != null) &&
          (reference.source == null || reference.recordVersion == null)
        ) {
          context.addIssue({
            code: 'custom',
            path: ['afaReference'],
            message: 'AfA-Quelle und Version erforderlich.',
          });
        }
      }),
    layoutVersionId: OptionalTextFact,
  })
  .strict();

export type InvestmentCase = z.infer<typeof InvestmentCaseSchema>;
export type InvestmentSensitivity = z.infer<typeof InvestmentSensitivitySchema>;

export function useInvestmentEntitlement(accountId: string) {
  return useQuery({
    queryKey: ['account', accountId, 'investment', 'entitlement'],
    queryFn: () =>
      api(
        `/a/${encodeURIComponent(accountId)}/investment/entitlement`,
        InvestmentEntitlementSchema,
      ),
    retry: false,
  });
}

export function useInvestmentCase(accountId: string, caseKey: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['account', accountId, 'investment', 'case', caseKey],
    queryFn: () =>
      api(
        `/a/${encodeURIComponent(accountId)}/investment/cases/${encodeURIComponent(caseKey ?? '')}`,
        InvestmentCaseSchema,
      ),
    enabled: enabled && caseKey !== null,
    retry: false,
  });
}

export function useInvestmentSensitivity(
  accountId: string,
  caseKey: string | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['account', accountId, 'investment', 'sensitivity', caseKey],
    queryFn: () =>
      api(
        `/a/${encodeURIComponent(accountId)}/investment/cases/${encodeURIComponent(caseKey ?? '')}/sensitivity`,
        InvestmentSensitivitySchema,
      ),
    enabled: enabled && caseKey !== null,
    retry: false,
  });
}

export function useInvestmentBankView(accountId: string, caseKey: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['account', accountId, 'investment', 'bank-view', caseKey],
    queryFn: () =>
      api(
        `/a/${encodeURIComponent(accountId)}/investment/cases/${encodeURIComponent(caseKey ?? '')}/bank-view`,
        InvestmentBankViewSchema,
      ),
    enabled: enabled && caseKey !== null,
    retry: false,
  });
}

export function useCreateInvestmentCase(accountId: string) {
  return useMutation({
    mutationFn: (input: z.infer<typeof InvestmentCreateSchema>) =>
      api(`/a/${encodeURIComponent(accountId)}/investment/cases`, InvestmentCaseSchema, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(InvestmentCreateSchema.parse(input)),
      }),
  });
}
