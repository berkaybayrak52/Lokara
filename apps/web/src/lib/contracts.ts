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

export const PortfolioOverviewResponseSchema = z.object({
  buildingCount: z.number().int().nonnegative(),
  unitCount: z.number().int().nonnegative(),
  occupiedUnitCount: z.number().int().nonnegative(),
  vacantUnitCount: z.number().int().nonnegative(),
  mietSollCentsMonthly: z.number().int().nonnegative(),
});
export type PortfolioOverviewResponse = z.infer<typeof PortfolioOverviewResponseSchema>;

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
  buildingType: z.string(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
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

// UI-04 Objekt-Dashboard. Mirrors the server projection field for field: the
// page renders these values and derives no money, state or priority of its own.
export const BuildingDashboardOccupancySchema = z.object({
  rented: z.number().int(),
  vacant: z.number().int(),
  selfUse: z.number().int(),
  total: z.number().int(),
});

export const BuildingDashboardKpisSchema = z.object({
  coldRentCentsMonthly: z.number().int(),
  coldRentEurMonthly: z.string(),
  totalAreaSqmX100: z.number().int(),
  totalAreaSqm: z.number(),
  rentedAreaSqmX100: z.number().int(),
  rentedAreaSqm: z.number(),
  avgColdRentCentsPerSqm: z.number().int().nullable(),
  avgColdRentEurPerSqm: z.string().nullable(),
  occupancy: BuildingDashboardOccupancySchema,
});

export const BuildingDashboardFactSchema = z.object({
  id: z.string(),
  category: z.enum(['OPEN_RECEIVABLE', 'MOVE_OUT', 'MOVE_IN']),
  severity: z.enum(['info', 'attention']),
  text: z.string(),
  unitId: z.string().nullable(),
  unitLabel: z.string().nullable(),
  actionLabel: z.string().nullable(),
  actionHref: z.string().nullable(),
  eventDate: z.string().nullable(),
});
export type BuildingDashboardFact = z.infer<typeof BuildingDashboardFactSchema>;

export const BuildingDashboardBalanceSchema = z.object({
  status: z.enum(['SETTLED', 'OPEN', 'NONE']),
  openCents: z.number().int(),
  openEur: z.string(),
  label: z.string(),
});

export const BuildingDashboardNextEventSchema = z.object({
  kind: z.enum(['MOVE_IN', 'MOVE_OUT']),
  eventDate: z.string(),
  label: z.string(),
});

export const BuildingDashboardUnitSchema = z.object({
  id: z.string(),
  label: z.string(),
  areaSqmX100: z.number().int(),
  areaSqm: z.number(),
  state: z.enum(['RENTED', 'VACANT', 'SELF_USE', 'GRATUITOUS']),
  stateLabel: z.string(),
  partyNames: z.array(z.string()),
  hasTenancyOverlap: z.boolean(),
  coldRentCents: z.number().int().nullable(),
  coldRentEur: z.string().nullable(),
  balance: BuildingDashboardBalanceSchema.nullable(),
  nextEvent: BuildingDashboardNextEventSchema.nullable(),
});
export type BuildingDashboardUnit = z.infer<typeof BuildingDashboardUnitSchema>;

export const BuildingDashboardModuleSchema = z.object({
  key: z.enum(['payments', 'costs_and_statement', 'meters']),
  title: z.string(),
  available: z.boolean(),
  unavailableReason: z.string().nullable(),
  facts: z.array(z.object({ label: z.string(), value: z.string() })),
  actionLabel: z.string().nullable(),
  actionHref: z.string().nullable(),
});
export type BuildingDashboardModule = z.infer<typeof BuildingDashboardModuleSchema>;

export const BuildingDashboardResponseSchema = z.object({
  asOf: z.string(),
  id: z.string(),
  name: z.string(),
  street: z.string(),
  postalCode: z.string(),
  city: z.string(),
  country: z.string(),
  buildingType: z.string(),
  buildingTypeLabel: z.string(),
  isResidential: z.boolean(),
  unitCount: z.number().int(),
  kpis: BuildingDashboardKpisSchema,
  facts: z.array(BuildingDashboardFactSchema),
  factsTotal: z.number().int(),
  units: z.array(BuildingDashboardUnitSchema),
  modules: z.array(BuildingDashboardModuleSchema),
  permissions: z.object({
    canEdit: z.boolean(),
    canCreateUnit: z.boolean(),
    canExportPdf: z.boolean(),
  }),
});
export type BuildingDashboardResponse = z.infer<typeof BuildingDashboardResponseSchema>;

export const AdvancePaymentPeriodOutSchema = z.object({
  id: z.string(),
  amountCents: z.number().int(),
  amountEur: z.string(),
  validFrom: z.string(),
  validTo: z.string().nullable(),
  predecessorId: z.string().nullable(),
  declarationRef: z.string(),
});
export type AdvancePaymentPeriodOut = z.infer<typeof AdvancePaymentPeriodOutSchema>;

export const TenancyOutSchema = z.object({
  id: z.string(),
  renterNames: z.array(z.string()),
  validFrom: z.string(),
  validTo: z.string().nullable(),
  baseRentCents: z.number().int(),
  baseRentEur: z.string(),
  advancePaymentSchedule: z.array(AdvancePaymentPeriodOutSchema),
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

// ── M6-B finalization archives (owner-only) ─────────────────────────────────

export const DeliveryAddressSchema = z.object({
  id: z.string(),
  version: z.number().int(),
  addressee: z.string(),
  street: z.string(),
  postalCode: z.string(),
  city: z.string(),
  country: z.string(),
  validFrom: z.string(),
});

export const PaymentInstructionSchema = z.object({
  id: z.string(),
  version: z.number().int(),
  instructionText: z.string(),
  validFrom: z.string(),
});

export const FinalizedDocumentSchema = z.object({
  id: z.string(),
  audience: z.enum(['OWNER', 'TENANT']),
  tenancyId: z.string().nullable(),
  documentType: z.enum(['OWNER_OVERVIEW', 'COVER_LETTER', 'TENANT_STATEMENT']),
  filename: z.string(),
  sha256: z.string(),
});

export const StatementHistorySchema = z.object({
  id: z.string(),
  version: z.number().int(),
  status: z.enum(['FINALIZED', 'SUPERSEDED']),
  periodStart: z.string(),
  periodEnd: z.string(),
  contentHash: z.string().nullable(),
  finalizedAt: z.string().nullable(),
  supersedesStatementId: z.string().nullable(),
  documents: z.array(FinalizedDocumentSchema),
});

export const FinalizeStatementSchema = StatementHistorySchema.extend({
  settlements: z.array(
    z.object({
      tenancy_id: z.string(),
      saldo_cents: z.number().int(),
      kind: z.string(),
    }),
  ),
});

export const StatementDraftSchema = z.object({
  id: z.string(),
  buildingId: z.string(),
  buildingName: z.string(),
  title: z.string(),
  periodStart: z.string(),
  periodEnd: z.string(),
  status: z.enum(['DRAFT', 'REVIEW_REQUIRED', 'READY', 'FINALIZED', 'CANCELLED']),
  currentStep: z.number().int().min(1).max(6),
  version: z.number().int().positive(),
  selectedUnitIds: z.array(z.string()),
  overrides: z.record(z.string(), z.unknown()),
  finalStatementId: z.string().nullable(),
  correctionOfStatementId: z.string().nullable(),
  correctionReason: z.string().nullable(),
  createdAt: z.string(),
  updatedAt: z.string(),
});
export type StatementDraft = z.infer<typeof StatementDraftSchema>;

export const StatementRecordSchema = z.object({
  id: z.string(),
  kind: z.enum(['DRAFT', 'FINAL']),
  buildingId: z.string(),
  buildingName: z.string(),
  title: z.string(),
  unitCount: z.number().int().nonnegative(),
  periodStart: z.string(),
  periodEnd: z.string(),
  status: z.string(),
  resultSummary: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
});
export type StatementRecord = z.infer<typeof StatementRecordSchema>;

export const StatementPeriodSuggestionSchema = z.object({
  periodStart: z.string(),
  periodEnd: z.string(),
  label: z.string(),
  reason: z.string(),
});

export const StatementReadinessFindingSchema = z.object({
  code: z.string(),
  area: z.string(),
  severity: z.enum(['INFO', 'WARNING', 'BLOCKER']),
  entityType: z.string().nullable(),
  entityId: z.string().nullable(),
  message: z.string(),
  correctionRoute: z.string().nullable(),
  allowedActions: z.array(z.string()),
  provenance: z.string().nullable(),
});

export const StatementDraftUnitSchema = z.object({
  unitId: z.string(),
  tenancyId: z.string().nullable(),
  label: z.string(),
  usage: z.string(),
  party: z.string(),
  periodLabel: z.string(),
  personCount: z.string(),
  areaSqm: z.string(),
  contractualAdvanceCents: z.number().int().nullable(),
  actualAdvancesCents: z.number().int().nullable(),
  saldoCents: z.number().int().nullable(),
  included: z.boolean(),
  status: z.enum(['READY', 'WARNING', 'BLOCKER']),
});

export const StatementDraftCostSchema = z.object({
  costId: z.string(),
  label: z.string(),
  periodLabel: z.string(),
  amountCents: z.number().int(),
  allocableCents: z.number().int(),
  allocationKey: z.string(),
  status: z.enum(['READY', 'WARNING', 'BLOCKER']),
});

export const StatementDraftDocumentSchema = z.object({
  key: z.string(),
  tenancyId: z.string().nullable(),
  recipient: z.string(),
  documentType: z.string(),
  readiness: z.enum(['READY', 'BLOCKED']),
});

export const StatementDraftReadinessSchema = z.object({
  draft: StatementDraftSchema,
  overallStatus: z.enum(['DRAFT', 'REVIEW_REQUIRED', 'READY', 'FINALIZED']),
  findings: z.array(StatementReadinessFindingSchema),
  units: z.array(StatementDraftUnitSchema),
  costs: z.array(StatementDraftCostSchema),
  documents: z.array(StatementDraftDocumentSchema),
  nkTotalCents: z.number().int().nullable(),
  heatingTotalCents: z.number().int().nullable(),
  allocableTotalCents: z.number().int().nullable(),
  ownerTotalCents: z.number().int().nullable(),
  heatingPath: z.string().nullable(),
});
export type StatementDraftReadiness = z.infer<typeof StatementDraftReadinessSchema>;

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

// ── Zahlungen / Bank-Matching (docs/15; M6-C2 routes + M6-C3a matching) ──────
//
// These five payloads are snake_case ON THE WIRE, unlike every other schema in
// this file. That is not a mistake to "fix" here: apps/api routers/payments.py
// declares its response models on plain pydantic `BaseModel` instead of the
// camelCasing `ApiModel` in schemas.py, and matching_service.py returns raw
// dicts that never pass through an alias generator at all. Verified against
// apps/api/tests/test_m6c2_bank_api.py:371 and
// apps/api/tests/test_m6c3a_matching_service.py:920.
//
// The mirror must match what the server actually sends; renaming these to
// camelCase would make every response fail to parse. Aligning the SERVER on
// ApiModel is a C3a/C2 change, not a client one.

/** docs/15 § 4 decision — the Decision StrEnum, lowercase on the wire. */
export const MatchDecisionSchema = z.enum(['auto_match', 'needs_review', 'unmatched', 'deduped']);
export type MatchDecision = z.infer<typeof MatchDecisionSchema>;

/** The landlord's final answer to a Needs-Review proposal, lowercase. */
export const MatchOutcomeSchema = z.enum(['confirmed', 'rejected', 'duplicate']);
export type MatchOutcome = z.infer<typeof MatchOutcomeSchema>;

/** Each value is 0 (signal not met) or its docs/15 § 4 weight. */
export const MatchSignalsSchema = z.object({
  iban: z.number().int(),
  amount: z.number().int(),
  code_or_surname: z.number().int(),
  end_to_end: z.number().int(),
  period: z.number().int(),
});

export const MatchCandidateSchema = z.object({
  proposal_id: z.string(),
  rank: z.number().int(),
  /** NULL on the engine's rank-1 "no candidate" evidence row. */
  receivable_id: z.string().nullable(),
  renter_id: z.string().nullable(),
  signals: MatchSignalsSchema,
  /** min(100, sum(signals)) — already capped by the server. */
  confidence: z.number().int(),
});

export const MatchConfirmationSchema = z.object({
  outcome: MatchOutcomeSchema,
  confirmed_by: z.string(),
  confirmed_at: z.string(),
});

export const MatchProposalGroupSchema = z.object({
  transaction_id: z.string(),
  decision: MatchDecisionSchema,
  /** Authored by the server; the client shows it verbatim. */
  reason_de: z.string().nullable(),
  candidates: z.array(MatchCandidateSchema),
  confirmation: MatchConfirmationSchema.nullable(),
  ledger_entry_id: z.string().nullable(),
  created_at: z.string(),
});
export type MatchProposalGroup = z.infer<typeof MatchProposalGroupSchema>;

export const MatchProposalListResponseSchema = z.object({
  transactions: z.array(MatchProposalGroupSchema),
});

export const BankTransactionOutSchema = z.object({
  id: z.string(),
  bank_account_id: z.string(),
  provider_transaction_id: z.string(),
  amount_cents: z.number().int(),
  bank_booking_date: z.string(),
  counterpart_name: z.string().nullable(),
  purpose: z.string().nullable(),
  is_potential_duplicate: z.boolean(),
});
export type BankTransactionOut = z.infer<typeof BankTransactionOutSchema>;

export const BankTransactionListResponseSchema = z.object({
  transactions: z.array(BankTransactionOutSchema),
});

export const ReceivableOutSchema = z.object({
  id: z.string(),
  renter_id: z.string(),
  tenancy_id: z.string(),
  source_type: z.string(),
  source_id: z.string().nullable(),
  /** "2026-03" or a free label — opaque to the client. */
  period: z.string(),
  due_date: z.string(),
  expected_cents: z.number().int(),
  open_cents: z.number().int(),
  status: z.string(),
  category: z.string(),
});
export type ReceivableOut = z.infer<typeof ReceivableOutSchema>;

export const ReceivableListResponseSchema = z.object({
  receivables: z.array(ReceivableOutSchema),
});

/** The open amounts of one receivable immediately before/after an allocation. */
export const PaymentAllocationSnapshotSchema = z.object({
  open_costs_cents: z.number().int(),
  open_interest_cents: z.number().int(),
  open_principal_cents: z.number().int(),
  open_cents: z.number().int(),
  status: z.string(),
});

export const PaymentAllocationSchema = z.object({
  id: z.string(),
  receivable_id: z.string(),
  /** § 367 BGB order: costs, then interest, then principal. */
  costs_cents: z.number().int(),
  interest_cents: z.number().int(),
  principal_cents: z.number().int(),
  components: z.object({
    base_rent_cents: z.number().int(),
    nk_advance_cents: z.number().int(),
    heating_advance_cents: z.number().int(),
    garage_cents: z.number().int(),
  }),
  resulting_status: z.string(),
  before: PaymentAllocationSnapshotSchema,
  after: PaymentAllocationSnapshotSchema,
});

export const PaymentLedgerEntrySchema = z.object({
  id: z.string(),
  bank_transaction_id: z.string(),
  match_proposal_id: z.string(),
  kind: z.enum(['payment', 'reversal']),
  /** >= 0 for a payment, < 0 for a reversal. */
  amount_cents: z.number().int(),
  /** Renter credit from an overpayment; 0 for a reversal. Never paid out (docs/15 § 9). */
  credit_cents: z.number().int(),
  ordering_version: z.number().int(),
  /** Non-null exactly when kind === 'reversal'. */
  reverses_entry_id: z.string().nullable(),
  created_at: z.string(),
  allocations: z.array(PaymentAllocationSchema),
});
export type PaymentLedgerEntry = z.infer<typeof PaymentLedgerEntrySchema>;

export const PaymentLedgerListResponseSchema = z.object({
  entries: z.array(PaymentLedgerEntrySchema),
});

/** POST …/decision — 200. A 409 carries a German `detail` instead. */
export const MatchDecisionResultSchema = z.object({
  transaction_id: z.string(),
  outcome: MatchOutcomeSchema,
  selected_rank: z.number().int().nullable(),
  ledger_entry_id: z.string().nullable(),
});
