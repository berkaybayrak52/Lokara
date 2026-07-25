import { z } from 'zod';

/**
 * Zod mirror of the FastAPI contract (apps/api schemas.py) — "never trust the
 * server either": every response is parsed at the boundary, so an API drift
 * fails loudly here instead of rendering garbage. camelCase to match the wire.
 */

export const HealthResponseSchema = z.object({
  status: z.literal('ok'),
  service: z.literal('lokara-api'),
  timestamp: z.string(),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

export const SessionResponseSchema = z.object({ ok: z.literal(true) });

export const DemoTenancySummarySchema = z.object({
  unitLabel: z.string(),
  areaSqm: z.number(),
  renterNames: z.array(z.string()),
  validFrom: z.string(),
  validTo: z.string().nullable(),
  baseRentEur: z.string(),
});

export const DemoSummaryResponseSchema = z.object({
  accountName: z.string(),
  buildingName: z.string(),
  buildingAddress: z.string(),
  unitCount: z.number().int(),
  tenancies: z.array(DemoTenancySummarySchema),
});
export type DemoSummaryResponse = z.infer<typeof DemoSummaryResponseSchema>;

export const MeAccountSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: z.string(),
  shape: z.string(),
});
export type MeAccount = z.infer<typeof MeAccountSchema>;

export const MeResponseSchema = z.object({
  personId: z.string(),
  accounts: z.array(MeAccountSchema),
});
export type MeResponse = z.infer<typeof MeResponseSchema>;

export const DemoLoadResponseSchema = z.object({
  ok: z.literal(true),
  accountId: z.string(),
});

export const BuildingSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  street: z.string(),
  postalCode: z.string(),
  city: z.string(),
  unitCount: z.number().int(),
});
export type BuildingSummary = z.infer<typeof BuildingSummarySchema>;

export const BuildingListResponseSchema = z.object({
  buildings: z.array(BuildingSummarySchema),
});

export const UnitSummarySchema = z.object({
  id: z.string(),
  label: z.string(),
  areaSqm: z.number(),
  tenancyCount: z.number().int(),
  occupiedToday: z.boolean(),
});

export const BuildingDetailResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  street: z.string(),
  postalCode: z.string(),
  city: z.string(),
  units: z.array(UnitSummarySchema),
});
export type BuildingDetailResponse = z.infer<typeof BuildingDetailResponseSchema>;

export const TenancyOutSchema = z.object({
  id: z.string(),
  renterNames: z.array(z.string()),
  validFrom: z.string(),
  validTo: z.string().nullable(),
  baseRentCents: z.number().int(),
  baseRentEur: z.string(),
  advancePaymentCents: z.number().int(),
  advancePaymentEur: z.string(),
  activeToday: z.boolean(),
});
export type TenancyOut = z.infer<typeof TenancyOutSchema>;

export const SelfUsePeriodOutSchema = z.object({
  kind: z.string(),
  validFrom: z.string(),
  validTo: z.string().nullable(),
});
export type SelfUsePeriodOut = z.infer<typeof SelfUsePeriodOutSchema>;

export const UnitDetailResponseSchema = z.object({
  id: z.string(),
  label: z.string(),
  areaSqm: z.number(),
  buildingId: z.string(),
  buildingName: z.string(),
  tenancies: z.array(TenancyOutSchema),
  selfUsePeriods: z.array(SelfUsePeriodOutSchema),
});
export type UnitDetailResponse = z.infer<typeof UnitDetailResponseSchema>;

export const ALLOCATION_KEYS = ['AREA', 'PERSONS', 'CONSUMPTION', 'UNITS', 'DIRECT', 'MEA'] as const;
export const AllocationKeySchema = z.enum(ALLOCATION_KEYS);
export type AllocationKey = z.infer<typeof AllocationKeySchema>;

/** German Umlageschlüssel labels — mirrors the API's labels (docs/03). */
export const ALLOCATION_KEY_LABELS: Record<AllocationKey, string> = {
  AREA: 'Wohnfläche (m²·Tage)',
  PERSONS: 'Personenzahl (Personen·Tage)',
  CONSUMPTION: 'Verbrauch',
  UNITS: 'Einheiten (Einheiten·Tage)',
  DIRECT: 'Direktzuordnung',
  MEA: 'Miteigentumsanteile (MEA·Tage)',
};

export const CostEntryOutSchema = z.object({
  id: z.string(),
  label: z.string(),
  amountCents: z.number().int(),
  amountEur: z.string(),
  periodFrom: z.string(),
  periodTo: z.string(),
  key: AllocationKeySchema,
  keyLabel: z.string(),
  directUnitId: z.string().nullable(),
  directTenancyId: z.string().nullable(),
  assignmentCount: z.number().int(),
});
export type CostEntryOut = z.infer<typeof CostEntryOutSchema>;

export const CostListResponseSchema = z.object({ costs: z.array(CostEntryOutSchema) });

export const StatementNkLineSchema = z.object({
  partyLabel: z.string(),
  isLandlord: z.boolean(),
  weightDisplay: z.string(),
  amountCents: z.number().int(),
  amountEur: z.string(),
});

export const StatementNkCostSchema = z.object({
  label: z.string(),
  keyLabel: z.string(),
  amountCents: z.number().int(),
  amountEur: z.string(),
  lines: z.array(StatementNkLineSchema),
});

export const StatementHeatingLineSchema = z.object({
  partyLabel: z.string(),
  isLandlord: z.boolean(),
  heatingBaseEur: z.string(),
  heatingConsumptionEur: z.string(),
  wwBaseEur: z.string(),
  wwConsumptionEur: z.string(),
  totalCents: z.number().int(),
  totalEur: z.string(),
});

export const StatementCo2Schema = z.object({
  intensityDisplay: z.string(),
  landlordSharePercent: z.number().int(),
  landlordAmountEur: z.string(),
  renterAmountEur: z.string(),
  rechtsstand: z.string(),
});

export const DemoStatementResponseSchema = z.object({
  buildingName: z.string(),
  buildingAddress: z.string(),
  periodLabel: z.string(),
  nkCosts: z.array(StatementNkCostSchema),
  nkTotalCents: z.number().int(),
  nkTotalEur: z.string(),
  nkInputTotalCents: z.number().int(),
  heatingLines: z.array(StatementHeatingLineSchema),
  heatingTotalCents: z.number().int(),
  heatingTotalEur: z.string(),
  heatingInputTotalCents: z.number().int(),
  co2: StatementCo2Schema.nullable(),
  rechtsstaende: z.array(z.string()),
  disclaimer: z.string(),
});
export type DemoStatementResponse = z.infer<typeof DemoStatementResponseSchema>;
