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
  email: z.string(),
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

export const TenancyPreviewChoiceSchema = z.object({
  id: z.string(),
  label: z.string(),
});

export const StatementProjectionResponseSchema = z.object({
  audience: z.enum(['OWNER', 'TENANT', 'TAX']),
  tenancyId: z.string().nullable(),
  subtotalCents: z.number().int().nullable(),
  actualAdvancesCents: z.number().int().nullable(),
  saldoCents: z.number().int().nullable(),
  advanceReconciliationState: z.enum(['MISSING', 'CONFIRMED']).nullable(),
  reconciliationId: z.string().nullable(),
  reconciliationVersion: z.number().int().nullable(),
});
export type StatementProjectionResponse = z.infer<typeof StatementProjectionResponseSchema>;

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

export const ALLOCATION_KEYS = [
  'AREA',
  'PERSONS',
  'CONSUMPTION',
  'UNITS',
  'DIRECT',
  'MEA',
] as const;
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

// ── Zähler (docs/04 M3 page 5) ───────────────────────────────────────────────

export const METER_KINDS = ['HEAT', 'WARM_WATER', 'COLD_WATER'] as const;
export const MeterKindSchema = z.enum(METER_KINDS);
export type MeterKind = z.infer<typeof MeterKindSchema>;

export const METER_KIND_LABELS: Record<MeterKind, string> = {
  HEAT: 'Wärme',
  WARM_WATER: 'Warmwasser',
  COLD_WATER: 'Kaltwasser',
};

export const MEASUREMENT_UNITS = ['KWH', 'CUBIC_METRE', 'HKV_UNITS'] as const;
export const MeasurementUnitSchema = z.enum(MEASUREMENT_UNITS);
export type MeasurementUnit = z.infer<typeof MeasurementUnitSchema>;

export const MEASUREMENT_UNIT_LABELS: Record<MeasurementUnit, string> = {
  KWH: 'Kilowattstunden (kWh)',
  CUBIC_METRE: 'Kubikmeter (m³)',
  HKV_UNITS: 'Einheiten (Heizkostenverteiler)',
};

/**
 * Which units a medium can be counted in — mirrors the API's validator. Water
 * is always m³; only a heat device counts kWh or HKV units, and mixing them up
 * would corrupt the § 9 HeizkostenV denominator.
 */
export const UNITS_BY_KIND: Record<MeterKind, readonly MeasurementUnit[]> = {
  HEAT: ['KWH', 'HKV_UNITS'],
  WARM_WATER: ['CUBIC_METRE'],
  COLD_WATER: ['CUBIC_METRE'],
};

export const READING_REASONS = [
  'PERIODIC',
  'INTERIM',
  'TENANT_CHANGE',
  'DEVICE_CHANGE',
  'CORRECTION',
] as const;
export const ReadingReasonSchema = z.enum(READING_REASONS);
export type ReadingReason = z.infer<typeof ReadingReasonSchema>;

export const READING_REASON_LABELS: Record<ReadingReason, string> = {
  PERIODIC: 'Turnusablesung',
  INTERIM: 'Zwischenablesung',
  TENANT_CHANGE: 'Nutzerwechsel',
  DEVICE_CHANGE: 'Gerätewechsel',
  CORRECTION: 'Korrektur',
};

export const ReadingSourceSchema = z.enum(['MANUAL', 'MDL', 'RADIO']);
export type ReadingSource = z.infer<typeof ReadingSourceSchema>;

export const READING_SOURCE_LABELS: Record<ReadingSource, string> = {
  MANUAL: 'Manuell erfasst',
  MDL: 'Messdienstleister',
  RADIO: 'Funkablesung',
};

export const MeterReadingOutSchema = z.object({
  id: z.string(),
  readAt: z.string(),
  valueX1000: z.number().int(),
  valueDisplay: z.string(),
  reason: ReadingReasonSchema,
  source: ReadingSourceSchema,
  note: z.string().nullable(),
  tenancyId: z.string().nullable(),
  estimatedConsumptionX1000: z.number().int().nullable(),
  estimationBasis: z.string().nullable(),
  provenanceRef: z.string().nullable(),
  recordedAt: z.string(),
  superseded: z.boolean(),
});
export type MeterReadingOut = z.infer<typeof MeterReadingOutSchema>;

export const CalibrationStatusSchema = z.enum([
  'EXPIRED',
  'EXPIRING_SOON',
  'VALID',
  'NOT_APPLICABLE',
]);
export type CalibrationStatus = z.infer<typeof CalibrationStatusSchema>;

export const MeterOutSchema = z.object({
  id: z.string(),
  unitId: z.string().nullable(),
  unitLabel: z.string().nullable(),
  kind: MeterKindSchema,
  kindLabel: z.string(),
  measurementUnit: MeasurementUnitSchema,
  unitSymbol: z.string(),
  serial: z.string(),
  label: z.string().nullable(),
  calibrationValidUntil: z.string().nullable(),
  valuationFactorX1000: z.number().int().nullable(),
  valuationFactorDisplay: z.string().nullable(),
  calibrationStatus: CalibrationStatusSchema,
  readings: z.array(MeterReadingOutSchema),
  periodConsumptionDisplay: z.string().nullable(),
});
export type MeterOut = z.infer<typeof MeterOutSchema>;

export const MeterListResponseSchema = z.object({
  meters: z.array(MeterOutSchema),
  periodLabel: z.string(),
});

export const HeatingCostOutSchema = z.object({
  id: z.string(),
  label: z.string(),
  amountCents: z.number().int(),
  amountEur: z.string(),
  periodFrom: z.string(),
  periodTo: z.string(),
  co2KgX1000: z.number().int().nullable(),
  co2KgDisplay: z.string().nullable(),
  co2CostCents: z.number().int().nullable(),
  co2CostEur: z.string().nullable(),
});
export type HeatingCostOut = z.infer<typeof HeatingCostOutSchema>;

export const HeatingCostListResponseSchema = z.object({
  heatingCosts: z.array(HeatingCostOutSchema),
});

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
  /** Null on a confirmed Messdienstleister passthrough: that document states a
   * total per party and no §§ 7/8/9 column split, and Lokara does not compute
   * one for it (docs/03 H7). Null rather than "0,00 €", so a missing figure can
   * never be mistaken for a real zero. */
  heatingBaseEur: z.string().nullable(),
  heatingConsumptionEur: z.string().nullable(),
  wwBaseEur: z.string().nullable(),
  wwConsumptionEur: z.string().nullable(),
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

export const StatementFindingSchema = z.object({
  code: z.string(),
  message: z.string(),
  severity: z.enum(['NOTICE', 'WARNING', 'BLOCKER']),
  dismissible: z.boolean(),
});

export const StatementProvenanceSchema = z.object({
  code: z.string(),
  source: z.string(),
  detail: z.string(),
});

export const StatementDeviceEvidenceSchema = z.object({
  deviceId: z.string(),
  unitId: z.string(),
  room: z.string(),
  measurementUnit: MeasurementUnitSchema,
  valuationFactor: z.string(),
  allocationKind: z.enum(['PARTY', 'OWNER', 'ANNUAL_UNSEGMENTED']),
  targetId: z.string().nullable(),
  opening: z.string().nullable(),
  closing: z.string().nullable(),
  units: z.string(),
  estimated: z.boolean(),
  estimationBasis: z.string().nullable(),
  readingReasons: z.array(z.string()),
  readingSources: z.array(z.string()),
  provenanceRefs: z.array(z.string()),
});

export const StatementReductionRiskSchema = z.object({
  code: z.string(),
  percent: z.string(),
  amountsEur: z.array(z.string()),
  message: z.string(),
});

export const StatementAnnualComparisonSchema = z.object({
  state: z.enum(['READY', 'RAW_FALLBACK', 'NO_PRIOR']),
  currentHeat: z.string(),
  previousHeat: z.string().nullable(),
  currentHeatAdjusted: z.string().nullable(),
  previousHeatAdjusted: z.string().nullable(),
  currentWarmWater: z.string().nullable(),
  previousWarmWater: z.string().nullable(),
  rawChangePercent: z.string().nullable(),
  adjustedChangePercent: z.string().nullable(),
  graphRequired: z.boolean(),
  note: z.string().nullable(),
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
  heatingMissingReason: z.string().nullable(),
  /** Which input produced the heating figures — a calculated self-billing run,
   * or a confirmed Messdienstleister statement passed through unchanged. */
  heatingPath: z.enum(['SELF_BILLING', 'MDL_NET', 'MDL_GROSS']).nullable(),
  heatingSourceNote: z.string().nullable(),
  heatingReadiness: z.enum(['READY', 'BLOCKED']),
  heatingFindings: z.array(StatementFindingSchema),
  heatingProvenance: z.array(StatementProvenanceSchema),
  heatingDeviceEvidence: z.array(StatementDeviceEvidenceSchema),
  heatingReductionRisks: z.array(StatementReductionRiskSchema),
  annualComparison: StatementAnnualComparisonSchema.nullable(),
  co2: StatementCo2Schema.nullable(),
  rechtsstaende: z.array(z.string()),
  disclaimer: z.string(),
});
export type DemoStatementResponse = z.infer<typeof DemoStatementResponseSchema>;

// ── Beleg-Upload / Extraktion (docs/04 M4, canned) ───────────────────────────

export const ExtractionFieldSchema = z.object({
  id: z.string(),
  label: z.string(),
  value: z.string(),
  confidencePercent: z.number().int(),
  /** Decided by the API — one threshold, not one per client. */
  needsReview: z.boolean(),
  /** False for values the confirm step cannot persist yet (vendor, date). */
  stored: z.boolean(),
  note: z.string().nullable().optional(),
});
export type ExtractionField = z.infer<typeof ExtractionFieldSchema>;

/** Exactly the CostCreate shape — the review form starts here and submits it
 * through the ordinary Kosten erfassen endpoint. */
export const ExtractionPrefillSchema = z.object({
  label: z.string(),
  amountCents: z.number().int(),
  periodFrom: z.string(),
  periodTo: z.string(),
  key: AllocationKeySchema,
});
export type ExtractionPrefill = z.infer<typeof ExtractionPrefillSchema>;

export const ExtractionDuplicateSchema = z.object({
  costId: z.string(),
  label: z.string(),
  amountEur: z.string(),
});

export const ExtractionResponseSchema = z.object({
  documentName: z.string(),
  providerLabel: z.string(),
  documentConfidencePercent: z.number().int(),
  fields: z.array(ExtractionFieldSchema),
  prefill: ExtractionPrefillSchema,
  notExtracted: z.array(z.string()),
  duplicate: ExtractionDuplicateSchema.nullable(),
});
export type ExtractionResponse = z.infer<typeof ExtractionResponseSchema>;
