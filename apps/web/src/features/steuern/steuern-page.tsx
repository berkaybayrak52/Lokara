'use client';

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Select,
  StatusNote,
} from '@lokara/ui';
import React, { useEffect, useState } from 'react';

import { PageHeader } from '@/features/portal/page-header';
import { useMe } from '@/features/portal/queries';
import {
  taxArtifactUrl,
  useTaxActions,
  useTaxAdviserProfile,
  useTaxAfaHistory,
  useTaxBuildings,
  useTaxExportHistory,
  useTaxMapping,
} from './queries';

type TaxRole = 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR';
type ExportKind = 'anlage_v_pdf' | 'anlage_v_csv' | 'datev_extf';
type AfaFacts = Record<string, unknown>;
type FieldErrors = Record<string, string>;
interface AfaPreviewAmounts {
  taxYearAfaCents: number;
  deductibleAfaCents: number;
  nonDeductibleAfaCents: number;
}
interface BuildingChoice {
  id: string;
  label: string;
}
interface ReadinessFinding {
  severity: 'rot' | 'gelb' | 'gruen';
  message: string;
}
interface ArchiveArtifact {
  id?: string;
  filename: string;
  sha256: string;
}
interface ExportHistoryItem {
  id: string;
  version: number;
  filename: string;
  generatedAt?: string;
  sha256?: string;
  readiness?: string;
  readinessFindings?: Record<string, unknown>[];
  blockers?: string[];
  artifacts?: ArchiveArtifact[];
  afaRechtsstand?: string;
  exportRechtsstand?: string;
  buildingId?: string;
  taxYear?: number;
  exportKind?: ExportKind;
}
interface StoredVersion {
  id: string;
  version: number;
  label: string;
}
interface AdviserProfileForm {
  beraternummer: string;
  mandantennummer: string;
  kontenrahmen: 'SKR03' | 'SKR04';
  sachkontenlaenge: number;
  wirtschaftsjahresbeginn: string;
}
interface MappingForm {
  sourceCategory: string;
  direction: 'einnahme' | 'ausgabe' | 'clearing' | 'sachbuchung';
  anlageVLine: string;
  skr03Account: string;
  skr04Account: string;
}
interface TaxWorkspaceProps {
  accountId: string;
  role: TaxRole;
  buildings: BuildingChoice[];
  selectedBuildingId: string;
  selectedTaxYear: number;
  selectedExportKind?: ExportKind;
  supportedTaxYears?: number[];
  readiness: { productionBlocked: boolean; findings: ReadinessFinding[] };
  readinessError?: string;
  afaMutationError?: string;
  afaPreviewAnnualCents?: number;
  afaPreview?: AfaPreviewAmounts;
  afaFacts?: AfaFacts;
  validationErrors?: FieldErrors;
  afaHistory: { id: string; version: number; annualCents: number }[];
  exportHistory: ExportHistoryItem[];
  adviserProfile: object | null;
  mappings: object[];
  adviserProfiles?: StoredVersion[];
  mappingVersions?: StoredVersion[];
  selectedAdviserProfileVersionId?: string;
  selectedMappingVersionId?: string;
  adviserProfileForm?: AdviserProfileForm;
  mappingForm?: MappingForm;
  rechtsstandEvidence?: { afa: string; export: string };
  onBuildingChange?: (id: string) => void;
  onTaxYearChange?: (year: number) => void;
  onExportKindChange?: (kind: ExportKind) => void;
  onAdviserProfileVersionChange?: (id: string) => void;
  onMappingVersionChange?: (id: string) => void;
  onAfaFactChange?: (name: string, value: string) => void;
  onSelfUsePeriodChange?: (index: number, name: string, value: string) => void;
  onAddSelfUsePeriod?: () => void;
  onMeasureChange?: (index: number, name: string, value: string) => void;
  onAddMeasure?: () => void;
  onLoanChange?: (index: number, name: string, value: string) => void;
  onAddLoan?: () => void;
  onProfileFieldChange?: (name: keyof AdviserProfileForm, value: string) => void;
  onMappingFieldChange?: (name: keyof MappingForm, value: string) => void;
  onPreviewAfa?: () => void;
  onSaveAfa?: () => void;
  onCheckReadiness?: () => void;
  onSaveProfile?: () => void;
  onSaveMapping?: () => void;
  onGenerate?: () => void;
}

const DISCLAIMER = 'Lokara ist ein Werkzeug: rechtskonform, keine Rechts- oder Steuerberatung.';
const DEFAULT_AFA_FACTS: AfaFacts = {
  erwerbsart: 'kauf',
  gebaeudetyp: 'mfh',
  fertigstellungsjahr: '',
  uebergangNutzenLastenDatum: '',
  wohnflaecheGesamt: '',
  grundstuecksflaecheM2: '',
  kaufpreisCent: '',
  grunderwerbsteuerCent: '',
  notarGrundbuchCent: '',
  grundschuldkostenCent: '',
  maklerprovisionCent: '',
  sonstigeAnkCent: '',
  beweglicheWgCent: '',
  aufteilungsWeg: 'vertrag',
  vertragGebaeudeCent: '',
  vertragBodenCent: '',
  herstellungskostenCent: '',
  grundstueckskostenCent: '',
  aussenanlagenCent: '',
  fertigstellungsdatum: '',
  notarvertragsDatum: '',
  veraeusserungsDatum: '',
  gutachtenGebaeudeanteilBp: '',
  gutachtenDokumentId: '',
  rndGutachtenJahre: '',
  rndGutachtenQualifikation: '',
  rndGutachtenDatum: '',
  bemessungsgrundlageCent: '',
  afaSatzBp: '',
  kumulierteAfaCent: '',
  vorgaengerMonate: '',
  massnahmen: [],
  darlehen: [],
  selfUsePeriods: [],
};
const DEFAULT_PROFILE: AdviserProfileForm = {
  beraternummer: '',
  mandantennummer: '',
  kontenrahmen: 'SKR04',
  sachkontenlaenge: 4,
  wirtschaftsjahresbeginn: '2025-01-01',
};
const DEFAULT_MAPPING: MappingForm = {
  sourceCategory: 'kaltmiete',
  direction: 'einnahme',
  anlageVLine: 'income_rent',
  skr03Account: '4100',
  skr04Account: '4400',
};

export function buildAfaRequest(
  facts: AfaFacts,
  context: {
    buildingId: string;
    taxYear: number;
    generatedAt: string;
    /** Accepted only to keep older callers source-compatible; authority is never serialized. */
    rules?: object;
  },
) {
  return {
    buildingId: context.buildingId,
    taxYear: context.taxYear,
    facts,
    generatedAt: context.generatedAt,
  };
}
export function validateAfaForm(facts: AfaFacts): FieldErrors {
  const errors: FieldErrors = {};
  const commonRequired = ['fertigstellungsjahr'];
  const acquisitionRequired =
    facts.erwerbsart === 'neubau'
      ? ['fertigstellungsdatum', 'herstellungskostenCent', 'grundstueckskostenCent']
      : facts.erwerbsart === 'unentgeltlich'
        ? ['uebergangNutzenLastenDatum', 'bemessungsgrundlageCent', 'afaSatzBp', 'kumulierteAfaCent']
        : [
            'uebergangNutzenLastenDatum',
            'kaufpreisCent',
            'grunderwerbsteuerCent',
            'notarGrundbuchCent',
            'grundschuldkostenCent',
            'maklerprovisionCent',
            'sonstigeAnkCent',
            'beweglicheWgCent',
            'aufteilungsWeg',
          ];
  for (const field of [...commonRequired, ...acquisitionRequired])
    if (facts[field] === undefined || facts[field] === null || facts[field] === '')
      errors[field] = 'Dieses AfA-Feld ist erforderlich.';
  if (facts.aufteilungsWeg === 'vertrag') {
    for (const field of ['vertragGebaeudeCent', 'vertragBodenCent']) {
      if (facts[field] === undefined || facts[field] === null || facts[field] === '')
        errors[field] = 'Für die vertragliche Aufteilung ist dieses Feld erforderlich.';
    }
  } else if (facts.aufteilungsWeg === 'bmf') {
    for (const field of [
      'bodenrichtwertCentProM2',
      'nhkCentProM2Bgf',
      'baupreisindexBp',
      'gesamtnutzungsdauerJahre',
    ]) {
      if (facts[field] === undefined || facts[field] === null || facts[field] === '')
        errors[field] = 'Für die BMF-Aufteilung ist dieses Feld erforderlich.';
    }
  } else if (facts.aufteilungsWeg === 'gutachten') {
    if (facts.gutachtenGebaeudeanteilBp === undefined || facts.gutachtenGebaeudeanteilBp === '')
      errors.gutachtenGebaeudeanteilBp = 'Der Gebäudeanteil aus dem Gutachten ist erforderlich.';
  }
  return errors;
}
export function allocationRouteForFacts(facts: AfaFacts): string | undefined {
  return typeof facts.aufteilungsWeg === 'string' ? facts.aufteilungsWeg : undefined;
}
export function buildAdviserProfileRequest(form: AdviserProfileForm, generatedAt: string) {
  return {
    profile: {
      beraternummer: form.beraternummer || null,
      mandantennummer: form.mandantennummer || null,
      kontenrahmen: form.kontenrahmen,
      sachkontenlaenge: form.sachkontenlaenge,
      wjBeginn: form.wirtschaftsjahresbeginn,
    },
    generatedAt,
  };
}
export function buildTaxMappingRequest(form: MappingForm, taxYear: number, generatedAt: string) {
  const fallbackDirection = ['kaltmiete', 'nk_vorauszahlung', 'nk_nachzahlung'].includes(
    form.sourceCategory,
  )
    ? 'einnahme'
    : 'ausgabe';
  return {
    taxYear,
    mapping: [
      {
        taxYear,
        category: form.sourceCategory,
        anlageVLine: form.anlageVLine,
        skr03Account: form.skr03Account,
        skr04Account: form.skr04Account,
        direction: form.direction ?? fallbackDirection,
        validFrom: `${taxYear}-01-01`,
        validTo: null,
        verificationFlag: 'verify-before-production',
        sourceVersion: `lokara-${taxYear}`,
        accountOverride: null,
        overrideByTaxAdvisor: true,
        overrideAt: generatedAt,
      },
    ],
    sourceVersion: `lokara-${taxYear}`,
    rechtsstand: '07/2026',
    generatedAt,
  };
}
export function buildReadinessRequest<T extends Record<string, unknown>>(selection: T): T {
  return { ...selection };
}
export function buildExportRequest<T extends Record<string, unknown>>(selection: T): T {
  return { ...selection };
}
export function supportedTaxYears(_referenceYear?: number): number[] {
  return [2024, 2025, 2026];
}
export function savedTaxVersionTransition(
  kind: 'profile' | 'mapping',
  response: { id: string },
  accountId: string,
  taxYear: number,
) {
  return {
    selectedVersionId: response.id,
    invalidateQueryKey:
      kind === 'profile'
        ? ['account', accountId, 'tax', 'adviser-profile']
        : ['account', accountId, 'tax', 'mapping', taxYear],
  };
}
export function scopeExportHistory<T extends { buildingId?: string; taxYear?: number }>(
  rows: T[],
  buildingId: string,
  taxYear: number,
  exportKind?: ExportKind,
): T[] {
  return rows.filter(
    (row) =>
      row.buildingId === buildingId &&
      row.taxYear === taxYear &&
      (!exportKind || (row as T & { exportKind?: ExportKind }).exportKind === exportKind),
  );
}
export function mapAfaHistoryResponse(
  response: {
    records: {
      id: string | null;
      version: number | null;
      buildingId: string;
      taxYear: number;
      annualAfaCents: number;
    }[];
  },
  buildingId: string,
  taxYear: number,
) {
  return response.records
    .filter((record) => record.buildingId === buildingId && record.taxYear === taxYear)
    .map((record) => ({
      id: record.id ?? `version-${record.version ?? 0}`,
      version: record.version ?? 0,
      annualCents: record.annualAfaCents,
    }));
}
export function mapExportHistoryResponse(response: {
  exports: Record<string, unknown>[];
}): ExportHistoryItem[] {
  return response.exports.map((raw) => {
    const artifacts = Array.isArray(raw.artifacts) ? (raw.artifacts as ArchiveArtifact[]) : [];
    const findings = Array.isArray(raw.readinessFindings)
      ? (raw.readinessFindings as Record<string, unknown>[])
      : [];
    return {
      id: String(raw.id),
      version: Number(raw.version),
      filename: artifacts[0]?.filename ?? 'Archiv',
      generatedAt: String(raw.generatedAt ?? ''),
      sha256: String(raw.sha256 ?? ''),
      artifacts,
      readinessFindings: findings,
      readiness: findings
        .map((finding) => String(finding.message ?? ''))
        .filter(Boolean)
        .join(' · '),
      blockers: Array.isArray(raw.blockers) ? raw.blockers.map(String) : [],
      afaRechtsstand: String(raw.afaRechtsstand ?? ''),
      exportRechtsstand: String(raw.exportRechtsstand ?? ''),
      buildingId: typeof raw.buildingId === 'string' ? raw.buildingId : undefined,
      taxYear: typeof raw.taxYear === 'number' ? raw.taxYear : undefined,
      exportKind:
        raw.exportKind === 'anlage_v_pdf' ||
        raw.exportKind === 'anlage_v_csv' ||
        raw.exportKind === 'datev_extf'
          ? raw.exportKind
          : undefined,
    };
  });
}
function euro(cents: number) {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(cents / 100);
}
function dateDe(value?: string) {
  if (!value) return 'Zeitpunkt fehlt';
  const date = new Date(value);
  return [date.getUTCDate(), date.getUTCMonth() + 1, date.getUTCFullYear()]
    .map((part, index) => (index < 2 ? String(part).padStart(2, '0') : String(part)))
    .join('.');
}
function factValue(facts: AfaFacts, name: string): string | number {
  const value = facts[name];
  return typeof value === 'number' || typeof value === 'string' ? value : '';
}
function afaFormValue(name: string, value: string): string | number {
  const textFields = [
    'erwerbsart',
    'gebaeudetyp',
    'aufteilungsWeg',
    'fertigstellungsdatum',
    'uebergangNutzenLastenDatum',
    'notarvertragsDatum',
    'veraeusserungsDatum',
    'gutachtenDokumentId',
    'rndGutachtenQualifikation',
    'rndGutachtenDatum',
  ];
  return textFields.includes(name) ? value : Number(value);
}

export function TaxWorkspace(props: TaxWorkspaceProps) {
  const {
    accountId,
    role,
    buildings,
    selectedBuildingId,
    selectedTaxYear,
    selectedExportKind = 'anlage_v_pdf',
    readiness,
    afaHistory,
    exportHistory,
    supportedTaxYears = [selectedTaxYear],
    readinessError,
    afaMutationError,
    afaPreviewAnnualCents,
    afaPreview,
    afaFacts = DEFAULT_AFA_FACTS,
    validationErrors = {},
    adviserProfiles = [],
    mappingVersions = [],
    selectedAdviserProfileVersionId = '',
    selectedMappingVersionId = '',
    adviserProfileForm = DEFAULT_PROFILE,
    mappingForm = DEFAULT_MAPPING,
    rechtsstandEvidence = { afa: '08/2026', export: '07/2026' },
  } = props;
  const owner = role === 'OWNER';
  const canConfigure = owner || role === 'TAX_ADVISOR';
  const afaLabels: Record<string, string> = {
    erwerbsart: 'Erwerbsart',
    gebaeudetyp: 'Gebäudetyp',
    fertigstellungsjahr: 'Fertigstellungsjahr',
    uebergangNutzenLastenDatum: 'Übergang von Nutzen und Lasten',
    wohnflaecheGesamt: 'Wohnfläche gesamt',
    grundstuecksflaecheM2: 'Grundstücksfläche',
    kaufpreisCent: 'Kaufpreis in Cent',
    grunderwerbsteuerCent: 'Grunderwerbsteuer in Cent',
    notarGrundbuchCent: 'Notar und Grundbuch in Cent',
    grundschuldkostenCent: 'Grundschuldkosten in Cent',
    maklerprovisionCent: 'Maklerprovision in Cent',
    sonstigeAnkCent: 'Sonstige Anschaffungskosten in Cent',
    beweglicheWgCent: 'Bewegliche Wirtschaftsgüter in Cent',
    aufteilungsWeg: 'Aufteilungsweg',
    vertragGebaeudeCent: 'Vertragsanteil Gebäude in Cent',
    vertragBodenCent: 'Vertragsanteil Boden in Cent',
    bodenrichtwertCentProM2: 'Bodenrichtwert je m² in Cent',
    nhkCentProM2Bgf: 'NHK je m² BGF in Cent',
    baupreisindexBp: 'Baupreisindex in Basispunkten',
    gesamtnutzungsdauerJahre: 'Gesamtnutzungsdauer in Jahren',
    gutachtenGebaeudeanteilBp: 'Gebäudeanteil laut Gutachten in Basispunkten',
    gutachtenDokumentId: 'Dokument zum Gutachten',
    fertigstellungsdatum: 'Fertigstellungsdatum',
    notarvertragsDatum: 'Notarvertragsdatum',
    veraeusserungsDatum: 'Veräußerungsdatum',
    herstellungskostenCent: 'Herstellungskosten in Cent',
    grundstueckskostenCent: 'Grundstückskosten in Cent',
    aussenanlagenCent: 'Außenanlagen in Cent',
    rndGutachtenJahre: 'Restnutzungsdauer laut Gutachten',
    rndGutachtenQualifikation: 'Qualifikation des Gutachters',
    rndGutachtenDatum: 'Datum des Restnutzungsdauer-Gutachtens',
    bemessungsgrundlageCent: 'Bemessungsgrundlage des Vorgängers in Cent',
    afaSatzBp: 'AfA-Satz des Vorgängers in Basispunkten',
    kumulierteAfaCent: 'Kumulierte AfA des Vorgängers in Cent',
    vorgaengerMonate: 'Monate beim Vorgänger im Steuerjahr',
  };
  const commonAfaFields = [
    'erwerbsart',
    'gebaeudetyp',
    'fertigstellungsjahr',
    'wohnflaecheGesamt',
    'grundstuecksflaecheM2',
    'notarvertragsDatum',
    'veraeusserungsDatum',
  ];
  const purchaseFields = [
    'uebergangNutzenLastenDatum',
    'kaufpreisCent',
    'grunderwerbsteuerCent',
    'notarGrundbuchCent',
    'grundschuldkostenCent',
    'maklerprovisionCent',
    'sonstigeAnkCent',
    'beweglicheWgCent',
    'aufteilungsWeg',
  ];
  const newBuildFields = [
    'fertigstellungsdatum',
    'herstellungskostenCent',
    'grundstueckskostenCent',
    'aussenanlagenCent',
  ];
  const predecessorFields = [
    'uebergangNutzenLastenDatum',
    'bemessungsgrundlageCent',
    'afaSatzBp',
    'kumulierteAfaCent',
    'vorgaengerMonate',
  ];
  const routeFields: Record<string, string[]> = {
    vertrag: ['vertragGebaeudeCent', 'vertragBodenCent'],
    bmf: [
      'bodenrichtwertCentProM2',
      'nhkCentProM2Bgf',
      'baupreisindexBp',
      'gesamtnutzungsdauerJahre',
    ],
    gutachten: ['gutachtenGebaeudeanteilBp', 'gutachtenDokumentId'],
  };
  const allocationRoute = allocationRouteForFacts(afaFacts) ?? 'vertrag';
  const acquisitionFields =
    afaFacts.erwerbsart === 'neubau'
      ? newBuildFields
      : afaFacts.erwerbsart === 'unentgeltlich'
        ? predecessorFields
        : [...purchaseFields, ...(routeFields[allocationRoute] ?? [])];
  const afaFieldNames = [
    ...commonAfaFields,
    ...acquisitionFields,
    'rndGutachtenJahre',
    'rndGutachtenQualifikation',
    'rndGutachtenDatum',
  ];
  const selfUsePeriods = Array.isArray(afaFacts.selfUsePeriods)
    ? afaFacts.selfUsePeriods.filter((period): period is Record<string, unknown> =>
        Boolean(period && typeof period === 'object'),
      )
    : [];
  const measures = Array.isArray(afaFacts.massnahmen)
    ? afaFacts.massnahmen.filter((item): item is Record<string, unknown> =>
        Boolean(item && typeof item === 'object'),
      )
    : [];
  const loans = Array.isArray(afaFacts.darlehen)
    ? afaFacts.darlehen.filter((item): item is Record<string, unknown> =>
        Boolean(item && typeof item === 'object'),
      )
    : [];
  const selfUseFields = [
    { name: 'vonDatum', label: 'Von', type: 'date' },
    { name: 'bisDatum', label: 'Bis', type: 'date' },
    { name: 'selbstgenutzteFlaeche', label: 'Selbstgenutzte Fläche', type: 'number' },
  ] as const;
  const field = (name: string, label: string, type = 'text') => (
    <div key={name} className="space-y-2">
      <Label htmlFor={`afa-${name}`}>{label}</Label>
      <Input
        id={`afa-${name}`}
        name={name}
        type={type}
        value={factValue(afaFacts, name)}
        aria-invalid={Boolean(validationErrors[name])}
        aria-describedby={validationErrors[name] ? `afa-${name}-error` : undefined}
        onChange={(event) => props.onAfaFactChange?.(name, event.target.value)}
      />
      {validationErrors[name] ? (
        <p id={`afa-${name}-error`} className="text-sm text-danger">
          {validationErrors[name]}
        </p>
      ) : null}
    </div>
  );
  return (
    <main className="py-10">
      <PageHeader
        title="Steuern"
        description="AfA-Nachweise und unveränderliche Steuerexporte für Objekt und Steuerjahr."
      />
      <nav aria-label="Steuernavigation" className="mb-6 flex gap-2 overflow-x-auto pb-2 sm:hidden">
        {['Auswahl', 'AfA-Assistent', 'Exportbereitschaft', 'Einstellungen', 'Exporthistorie'].map(
          (section) => (
            <a
              key={section}
              href={`#tax-${section.toLowerCase().replaceAll(' ', '-')}`}
              className="shrink-0 rounded-lg bg-mint px-3 py-2 text-sm font-medium text-forest focus-visible:outline-2 focus-visible:outline-ring"
            >
              {section}
            </a>
          ),
        )}
      </nav>
      <div className="max-w-5xl space-y-8">
        <Card id="tax-auswahl">
          <CardHeader>
            <CardTitle>Auswahl</CardTitle>
            <CardDescription>
              Objekt und Steuerjahr steuern alle folgenden Nachweise.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="tax-building">Objekt</Label>
              <Select
                id="tax-building"
                value={selectedBuildingId}
                onChange={(event) => props.onBuildingChange?.(event.target.value)}
              >
                {buildings.map((building) => (
                  <option key={building.id} value={building.id}>
                    {building.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="tax-export-kind">Exportformat</Label>
              <Select
                id="tax-export-kind"
                value={selectedExportKind}
                onChange={(event) =>
                  props.onExportKindChange?.(event.target.value as ExportKind)
                }
              >
                <option value="anlage_v_pdf">Anlage-V PDF</option>
                <option value="anlage_v_csv">Anlage-V CSV</option>
                <option value="datev_extf">DATEV-Format</option>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="tax-year">Steuerjahr</Label>
              <Select
                id="tax-year"
                value={String(selectedTaxYear)}
                onChange={(event) => props.onTaxYearChange?.(Number(event.target.value))}
              >
                {supportedTaxYears.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </Select>
            </div>
          </CardContent>
        </Card>
        <section id="tax-afa-assistent" className="space-y-4">
          <h2 className="font-display text-2xl font-bold">AfA-Assistent</h2>
          <p className="text-slate">
            Vorschau und versionierter Nachweis bleiben getrennte Schritte.
          </p>
          <Card>
            <CardContent className="space-y-5 pt-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {afaFieldNames.map((name) =>
                  field(
                    name,
                    afaLabels[name] ?? name,
                    name.endsWith('Cent') ||
                      name.includes('flaeche') ||
                      name === 'fertigstellungsjahr'
                      ? 'number'
                      : name.endsWith('Datum')
                        ? 'date'
                        : 'text',
                  ),
                )}
              </div>
              <fieldset className="space-y-4 rounded-lg border border-mint p-4">
                <legend className="px-1 font-semibold">Zeitliche Selbstnutzung</legend>
                {selfUsePeriods.map((period, index) => (
                  <div key={index} className="grid gap-4 sm:grid-cols-3">
                    {selfUseFields.map((field) => (
                      <div key={field.name} className="space-y-2">
                        <Label htmlFor={`self-use-${index}-${field.name}`}>{field.label}</Label>
                        <Input
                          id={`self-use-${index}-${field.name}`}
                          name={`selfUsePeriods.${index}.${field.name}`}
                          type={field.type}
                          value={factValue(period, field.name)}
                          onChange={(event) =>
                            props.onSelfUsePeriodChange?.(index, field.name, event.target.value)
                          }
                        />
                      </div>
                    ))}
                  </div>
                ))}
                <Button type="button" variant="secondary" onClick={props.onAddSelfUsePeriod}>
                  Zeitraum hinzufügen
                </Button>
              </fieldset>
              <fieldset className="space-y-4 rounded-lg border border-mint p-4">
                <legend className="px-1 font-semibold">Spätere Kosten und 15-%-Prüfung</legend>
                {measures.map((measure, index) => (
                  <div key={index} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {([
                      ['nettoCent', 'Nettobetrag in Cent', 'number'],
                      ['leistungBis', 'Leistung bis', 'date'],
                      ['klasse', 'Maßnahmenklasse', 'text'],
                      ['belegId', 'Belegnachweis', 'text'],
                    ] satisfies [string, string, string][]).map(([name, label, type]) => (
                      <div key={name} className="space-y-2">
                        <Label htmlFor={`measure-${index}-${name}`}>{label}</Label>
                        <Input
                          id={`measure-${index}-${name}`}
                          name={`massnahmen.${index}.${name}`}
                          type={type}
                          value={factValue(measure, name)}
                          onChange={(event) =>
                            props.onMeasureChange?.(index, name, event.target.value)
                          }
                        />
                      </div>
                    ))}
                  </div>
                ))}
                <Button type="button" variant="secondary" onClick={props.onAddMeasure}>
                  Maßnahme hinzufügen
                </Button>
              </fieldset>
              <fieldset className="space-y-4 rounded-lg border border-mint p-4">
                <legend className="px-1 font-semibold">Darlehen, Zinsen und Disagio</legend>
                {loans.map((loan, index) => (
                  <div key={index} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {([
                      ['nominalbetragCent', 'Nominalbetrag in Cent', 'number'],
                      ['auszahlungsbetragCent', 'Auszahlungsbetrag in Cent', 'number'],
                      ['sollzinsBpProJahr', 'Sollzins in Basispunkten', 'number'],
                      ['anfaenglicheTilgungBp', 'Anfängliche Tilgung in Basispunkten', 'number'],
                      ['ratenAnzahl', 'Anzahl Monatsraten', 'number'],
                      ['zinsbindungJahre', 'Zinsbindung in Jahren', 'number'],
                      ['ersteRateDatum', 'Datum der ersten Rate', 'date'],
                      ['zuordnung', 'Zuordnung', 'text'],
                      ['bankZinsbestaetigungCent', 'Bank-Zinsbestätigung in Cent', 'number'],
                      ['marktueblichesDisagioCent', 'Marktübliches Disagio in Cent', 'number'],
                      [
                        'nichtMarktueblichesDisagioCent',
                        'Nicht marktübliches Disagio in Cent',
                        'number',
                      ],
                      ['disagioErstjahrMonate', 'Disagio-Monate im ersten Jahr', 'number'],
                    ] satisfies [string, string, string][]).map(([name, label, type]) => (
                      <div key={name} className="space-y-2">
                        <Label htmlFor={`loan-${index}-${name}`}>{label}</Label>
                        <Input
                          id={`loan-${index}-${name}`}
                          name={`darlehen.${index}.${name}`}
                          type={type}
                          value={factValue(loan, name)}
                          onChange={(event) =>
                            props.onLoanChange?.(index, name, event.target.value)
                          }
                        />
                      </div>
                    ))}
                  </div>
                ))}
                <Button type="button" variant="secondary" onClick={props.onAddLoan}>
                  Darlehen hinzufügen
                </Button>
              </fieldset>
              {afaPreview ? (
                <dl className="grid gap-3 rounded-lg bg-mint p-4 sm:grid-cols-3">
                  <div>
                    <dt className="text-sm text-slate">AfA im Steuerjahr</dt>
                    <dd className="font-semibold">{euro(afaPreview.taxYearAfaCents)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-slate">Abziehbare AfA</dt>
                    <dd className="font-semibold">{euro(afaPreview.deductibleAfaCents)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-slate">Nicht abziehbare AfA (Selbstnutzung)</dt>
                    <dd className="font-semibold">{euro(afaPreview.nonDeductibleAfaCents)}</dd>
                  </div>
                </dl>
              ) : afaPreviewAnnualCents !== undefined ? (
                <StatusNote kind="success" label="AfA im Steuerjahr">
                  {euro(afaPreviewAnnualCents)} AfA im gewählten Steuerjahr
                </StatusNote>
              ) : null}
              {afaMutationError ? (
                <StatusNote kind="danger" label="AfA konnte nicht berechnet werden">
                  {afaMutationError}
                </StatusNote>
              ) : null}
              {afaHistory.length ? (
                <ul className="space-y-2">
                  {afaHistory.map((record) => (
                    <li
                      key={record.id}
                      className="flex justify-between rounded-lg bg-mint px-4 py-3"
                    >
                      <span>Unveränderliche Version {record.version}</span>
                      <strong>{euro(record.annualCents)}</strong>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>Noch kein AfA-Datensatz vorhanden.</p>
              )}
              {owner ? (
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={props.onPreviewAfa}>
                    AfA-Vorschau berechnen
                  </Button>
                  <Button onClick={props.onSaveAfa}>AfA-Datensatz speichern</Button>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </section>
        <section id="tax-exportbereitschaft" className="space-y-4">
          <h2 className="font-display text-2xl font-bold">Exportbereitschaft</h2>
          {readinessError ? (
            <StatusNote kind="danger" label="Prüfung fehlgeschlagen">
              {readinessError}
            </StatusNote>
          ) : null}
          {readiness.findings.map((finding) => (
            <StatusNote
              key={finding.message}
              kind={
                finding.severity === 'rot'
                  ? 'danger'
                  : finding.severity === 'gelb'
                    ? 'warning'
                    : 'success'
              }
              label={
                finding.severity === 'rot'
                  ? 'Gesperrt'
                  : finding.severity === 'gelb'
                    ? 'Prüfung nötig'
                    : 'Bereit'
              }
            >
              {finding.message}
            </StatusNote>
          ))}
          {owner ? (
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={props.onCheckReadiness}>
                Bereitschaft prüfen
              </Button>
              {readiness.productionBlocked ? (
                <button
                  type="button"
                  disabled
                  className="h-10 rounded-lg bg-green px-4 py-2 font-semibold text-white opacity-50"
                >
                  Export erzeugen
                </button>
              ) : (
                <button
                  type="button"
                  className="h-10 rounded-lg bg-green px-4 py-2 font-semibold text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  onClick={props.onGenerate}
                >
                  Export erzeugen
                </button>
              )}
            </div>
          ) : null}
          {readiness.productionBlocked ? (
            <p className="text-sm font-medium text-danger">
              Download ist gesperrt, solange die Quellen nicht verifiziert sind.
            </p>
          ) : null}
        </section>
        <div id="tax-einstellungen" className="grid gap-8 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Steuerberaterprofil</CardTitle>
              <CardDescription>Versionierte Kanzlei- und Mandantendaten.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Label htmlFor="profile-version">Gespeicherte Profilversion</Label>
              <Select
                id="profile-version"
                value={selectedAdviserProfileVersionId}
                onChange={(event) => props.onAdviserProfileVersionChange?.(event.target.value)}
              >
                <option value="">Keine Version gewählt</option>
                {adviserProfiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.label}
                  </option>
                ))}
              </Select>
              <Label htmlFor="beraternummer">Beraternummer</Label>
              <Input
                id="beraternummer"
                name="beraternummer"
                value={adviserProfileForm.beraternummer}
                onChange={(event) =>
                  props.onProfileFieldChange?.('beraternummer', event.target.value)
                }
              />
              <Label htmlFor="mandantennummer">Mandantennummer</Label>
              <Input
                id="mandantennummer"
                name="mandantennummer"
                value={adviserProfileForm.mandantennummer}
                onChange={(event) =>
                  props.onProfileFieldChange?.('mandantennummer', event.target.value)
                }
              />
              <Label htmlFor="kontenrahmen">Kontenrahmen</Label>
              <Select
                id="kontenrahmen"
                name="kontenrahmen"
                value={adviserProfileForm.kontenrahmen}
                onChange={(event) =>
                  props.onProfileFieldChange?.('kontenrahmen', event.target.value)
                }
              >
                <option value="SKR03">SKR03</option>
                <option value="SKR04">SKR04</option>
              </Select>
              <Label htmlFor="sachkontenlaenge">Sachkontenlänge</Label>
              <Input
                id="sachkontenlaenge"
                name="sachkontenlaenge"
                type="number"
                value={adviserProfileForm.sachkontenlaenge}
                onChange={(event) =>
                  props.onProfileFieldChange?.('sachkontenlaenge', event.target.value)
                }
              />
              <Label htmlFor="wirtschaftsjahresbeginn">Wirtschaftsjahresbeginn</Label>
              <Input
                id="wirtschaftsjahresbeginn"
                name="wirtschaftsjahresbeginn"
                type="date"
                value={adviserProfileForm.wirtschaftsjahresbeginn}
                onChange={(event) =>
                  props.onProfileFieldChange?.('wirtschaftsjahresbeginn', event.target.value)
                }
              />
              {canConfigure ? (
                <Button variant="secondary" onClick={props.onSaveProfile}>
                  Neue Profilversion speichern
                </Button>
              ) : null}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Zuordnungen</CardTitle>
              <CardDescription>
                Anlage-V-Zeilen und Konten für das gewählte Steuerjahr.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Label htmlFor="mapping-version">Gespeicherte Zuordnungsversion</Label>
              <Select
                id="mapping-version"
                value={selectedMappingVersionId}
                onChange={(event) => props.onMappingVersionChange?.(event.target.value)}
              >
                <option value="">Keine Version gewählt</option>
                {mappingVersions.map((mapping) => (
                  <option key={mapping.id} value={mapping.id}>
                    {mapping.label}
                  </option>
                ))}
              </Select>
              <Label htmlFor="sourceCategory">Quellkategorie</Label>
              <Input
                id="sourceCategory"
                name="sourceCategory"
                value={mappingForm.sourceCategory}
                onChange={(event) =>
                  props.onMappingFieldChange?.('sourceCategory', event.target.value)
                }
              />
              <Label htmlFor="anlageVLine">Anlage-V-Zeile</Label>
              <Input
                id="anlageVLine"
                name="anlageVLine"
                value={mappingForm.anlageVLine}
                onChange={(event) =>
                  props.onMappingFieldChange?.('anlageVLine', event.target.value)
                }
              />
              <Label htmlFor="direction">Buchungsrichtung</Label>
              <Select
                id="direction"
                name="direction"
                value={mappingForm.direction}
                onChange={(event) => props.onMappingFieldChange?.('direction', event.target.value)}
              >
                <option value="einnahme">Einnahme</option>
                <option value="ausgabe">Ausgabe</option>
                <option value="clearing">Verrechnung</option>
                <option value="sachbuchung">Sachbuchung</option>
              </Select>
              <Label htmlFor="skr03Account">SKR03-Konto</Label>
              <Input
                id="skr03Account"
                name="skr03Account"
                value={mappingForm.skr03Account}
                onChange={(event) =>
                  props.onMappingFieldChange?.('skr03Account', event.target.value)
                }
              />
              <Label htmlFor="skr04Account">SKR04-Konto</Label>
              <Input
                id="skr04Account"
                name="skr04Account"
                value={mappingForm.skr04Account}
                onChange={(event) =>
                  props.onMappingFieldChange?.('skr04Account', event.target.value)
                }
              />
              <Label htmlFor="account">Ausgewähltes Konto</Label>
              <Input id="account" name="account" value={mappingForm.skr04Account} readOnly />
              {canConfigure ? (
                <Button variant="secondary" onClick={props.onSaveMapping}>
                  Neue Zuordnungsversion speichern
                </Button>
              ) : null}
            </CardContent>
          </Card>
        </div>
        <section id="tax-exporthistorie" className="space-y-4">
          <h2 className="font-display text-2xl font-bold">Exporthistorie</h2>
          <Card>
            <CardContent className="pt-6">
              {exportHistory.length ? (
                <ul className="space-y-4">
                  {exportHistory.map((item) => (
                    <li key={item.id} className="rounded-lg border border-mint p-4">
                      <p className="font-semibold">
                        Unveränderliche Version {item.version}: {item.filename}
                      </p>
                      <p className="mt-1 text-sm">
                        Erstellt am {dateDe(item.generatedAt)} · Prüfsumme {item.sha256 ?? 'fehlt'}
                      </p>
                      <p className="mt-1 text-sm">
                        Bereitschaft: {item.readiness || 'Keine gespeicherte Meldung'}
                      </p>
                      {item.blockers?.map((blocker) => (
                        <p key={blocker} className="mt-1 text-sm text-danger">
                          {blocker}
                        </p>
                      ))}
                      {item.afaRechtsstand || item.exportRechtsstand ? (
                        <p className="mt-1 text-sm">
                          Rechtsstand AfA {item.afaRechtsstand} · Export {item.exportRechtsstand}
                        </p>
                      ) : null}
                      <ul className="mt-3 space-y-2">
                        {item.artifacts?.map((artifact) => {
                          const artifactId = artifact.id ?? encodeURIComponent(artifact.filename);
                          return (
                            <li key={artifact.filename}>
                              <span>
                                {artifact.filename} · {artifact.sha256}
                              </span>
                              {readiness.productionBlocked ? (
                                <button
                                  type="button"
                                  disabled
                                  className="ml-2 rounded px-2 py-1 text-sm"
                                >
                                  Herunterladen
                                </button>
                              ) : (
                                <a
                                  className="ml-2 rounded px-2 py-1 text-sm font-medium text-green underline"
                                  href={taxArtifactUrl(accountId, item.id, artifactId)}
                                >
                                  Herunterladen
                                </a>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>Noch kein unveränderlicher Export vorhanden.</p>
              )}
            </CardContent>
          </Card>
        </section>
        <footer className="border-t border-mint pt-6 text-sm text-slate">
          <p>
            Rechtsstand AfA {rechtsstandEvidence.afa} · Export {rechtsstandEvidence.export}
          </p>
          <p className="mt-2">{DISCLAIMER}</p>
        </footer>
      </div>
    </main>
  );
}

function findingMessage(finding: Record<string, unknown>): string {
  if (typeof finding.message === 'string' && finding.message) return finding.message;
  const messages: Record<string, string> = {
    authority_unverified: 'Die Exportquellen sind noch nicht verifiziert.',
    mapping_unverified: 'Die Kontenzuordnung ist noch nicht verifiziert.',
    missing_date: 'Bei einem Zahlungsvorgang fehlt das Datum.',
    missing_category: 'Bei einem Zahlungsvorgang fehlt die Kategorie.',
  };
  return messages[String(finding.code)] ?? 'Die Exportbereitschaft muss geprüft werden.';
}

export function TaxWorkspacePage({ accountId }: { accountId: string }) {
  const me = useMe();
  const buildings = useTaxBuildings(accountId);
  const afa = useTaxAfaHistory(accountId);
  const exports = useTaxExportHistory(accountId);
  const actions = useTaxActions(accountId);
  const [selectedBuildingId, setSelectedBuildingId] = useState('');
  const [selectedTaxYear, setSelectedTaxYear] = useState(new Date().getFullYear());
  const [selectedExportKind, setSelectedExportKind] =
    useState<ExportKind>('anlage_v_pdf');
  const [facts, setFacts] = useState<AfaFacts>(DEFAULT_AFA_FACTS);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [profileForm, setProfileForm] = useState<AdviserProfileForm>(DEFAULT_PROFILE);
  const [mappingForm, setMappingForm] = useState<MappingForm>(DEFAULT_MAPPING);
  const profile = useTaxAdviserProfile(accountId);
  const mapping = useTaxMapping(accountId, selectedTaxYear);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedMappingId, setSelectedMappingId] = useState('');
  const account = me.data?.accounts.find((item) => item.id === accountId);
  const choices = buildings.data?.buildings ?? [];
  useEffect(() => {
    if (!selectedBuildingId && choices[0]) setSelectedBuildingId(choices[0].id);
  }, [choices, selectedBuildingId]);
  useEffect(() => {
    if (profile.data?.id) setSelectedProfileId(profile.data.id);
  }, [profile.data?.id]);
  useEffect(() => {
    if (mapping.data?.id) setSelectedMappingId(mapping.data.id);
  }, [mapping.data?.id]);
  if (me.isPending || buildings.isPending)
    return (
      <main className="py-10" role="status">
        Steuerbereich wird geladen …
      </main>
    );
  if (account?.role !== 'OWNER' && account?.role !== 'TAX_ADVISOR')
    return (
      <main className="py-10">
        <h1 className="font-display text-2xl font-bold">Kein Zugriff auf Steuern</h1>
      </main>
    );
  const now = () => new Date().toISOString();
  const afaBody = () =>
    buildAfaRequest(facts, {
      buildingId: selectedBuildingId,
      taxYear: selectedTaxYear,
      generatedAt: now(),
    });
  const selectedAfa = (afa.data?.records ?? []).find(
    (row) => row.buildingId === selectedBuildingId && row.taxYear === selectedTaxYear,
  );
  const readinessBody = () => ({
    exportKind: selectedExportKind,
    buildingId: selectedBuildingId,
    taxYear: selectedTaxYear,
    generatedAt: now(),
    afaRecordVersionId: selectedAfa?.id ?? null,
    adviserProfileVersionId: selectedProfileId || null,
    mappingVersionId: selectedMappingId,
  });
  const runAfa = (save: boolean) => {
    const next = validateAfaForm(facts);
    setErrors(next);
    if (!Object.keys(next).length) (save ? actions.saveAfa : actions.previewAfa).mutate(afaBody());
  };
  const afaRows = mapAfaHistoryResponse(
    { records: afa.data?.records ?? [] },
    selectedBuildingId,
    selectedTaxYear,
  );
  const exportRows = scopeExportHistory(
    exports.data ? mapExportHistoryResponse(exports.data) : [],
    selectedBuildingId,
    selectedTaxYear,
    selectedExportKind,
  );
  const selectedEvidence = exportRows[0];
  const readinessFindings = (actions.checkReadiness.data?.findings ?? []).map(
    (finding: Record<string, unknown>) => ({
      severity: String(finding.severity) === 'gelb' ? ('gelb' as const) : ('rot' as const),
      message: findingMessage(finding),
    }),
  );
  const readiness = actions.checkReadiness.data
    ? {
        productionBlocked: actions.checkReadiness.data.productionBlocked,
        findings: readinessFindings,
      }
    : {
        productionBlocked: true,
        findings: [
          { severity: 'rot' as const, message: 'Die Exportquellen sind noch nicht verifiziert.' },
        ],
      };
  return (
    <TaxWorkspace
      accountId={accountId}
      role={account.role}
      buildings={choices}
      selectedBuildingId={selectedBuildingId}
      selectedTaxYear={selectedTaxYear}
      selectedExportKind={selectedExportKind}
      supportedTaxYears={supportedTaxYears()}
      onBuildingChange={setSelectedBuildingId}
      onTaxYearChange={setSelectedTaxYear}
      onExportKindChange={setSelectedExportKind}
      readiness={readiness}
      readinessError={
        actions.checkReadiness.isError ? 'Bereitschaft konnte nicht geprüft werden.' : undefined
      }
      afaFacts={facts}
      afaPreview={
        actions.previewAfa.data
          ? {
              taxYearAfaCents: actions.previewAfa.data.taxYearAfaCents,
              deductibleAfaCents: actions.previewAfa.data.deductibleAfaCents,
              nonDeductibleAfaCents: actions.previewAfa.data.nonDeductibleAfaCents,
            }
          : undefined
      }
      afaMutationError={
        actions.previewAfa.isError || actions.saveAfa.isError
          ? 'Die AfA-Vorschau konnte nicht berechnet werden.'
          : undefined
      }
      validationErrors={errors}
      onAfaFactChange={(name, value) =>
        setFacts((current) => ({
          ...current,
          [name]: afaFormValue(name, value),
        }))
      }
      onSelfUsePeriodChange={(index, name, value) =>
        setFacts((current) => {
          const periods = Array.isArray(current.selfUsePeriods)
            ? current.selfUsePeriods.map((period) => ({ ...(period as Record<string, unknown>) }))
            : [];
          periods[index] = {
            ...periods[index],
            [name]: name === 'selbstgenutzteFlaeche' ? Number(value) : value,
          };
          return { ...current, selfUsePeriods: periods };
        })
      }
      onAddSelfUsePeriod={() =>
        setFacts((current) => ({
          ...current,
          selfUsePeriods: [
            ...(Array.isArray(current.selfUsePeriods) ? current.selfUsePeriods : []),
            { vonDatum: '', bisDatum: '', selbstgenutzteFlaeche: '', einheitIds: [] },
          ],
        }))
      }
      onMeasureChange={(index, name, value) =>
        setFacts((current) => {
          const measures = Array.isArray(current.massnahmen)
            ? current.massnahmen.map((item) => ({ ...(item as Record<string, unknown>) }))
            : [];
          measures[index] = {
            ...measures[index],
            [name]: name === 'nettoCent' ? Number(value) : value,
          };
          return { ...current, massnahmen: measures };
        })
      }
      onAddMeasure={() =>
        setFacts((current) => ({
          ...current,
          massnahmen: [
            ...(Array.isArray(current.massnahmen) ? current.massnahmen : []),
            { nettoCent: '', leistungBis: '', klasse: '', belegId: '' },
          ],
        }))
      }
      onLoanChange={(index, name, value) =>
        setFacts((current) => {
          const loans = Array.isArray(current.darlehen)
            ? current.darlehen.map((item) => ({ ...(item as Record<string, unknown>) }))
            : [];
          const textFields = ['ersteRateDatum', 'zuordnung'];
          loans[index] = {
            ...loans[index],
            [name]: textFields.includes(name) ? value : Number(value),
          };
          return { ...current, darlehen: loans };
        })
      }
      onAddLoan={() =>
        setFacts((current) => ({
          ...current,
          darlehen: [
            ...(Array.isArray(current.darlehen) ? current.darlehen : []),
            {
              nominalbetragCent: '',
              auszahlungsbetragCent: '',
              sollzinsBpProJahr: '',
              anfaenglicheTilgungBp: '',
              ratenAnzahl: 12,
              zinsbindungJahre: '',
              ersteRateDatum: '',
              zuordnung: 'objektAnteilig',
            },
          ],
        }))
      }
      afaHistory={afaRows}
      exportHistory={exportRows}
      adviserProfile={profile.data ?? null}
      mappings={mapping.data?.mapping ?? []}
      adviserProfiles={
        profile.data
          ? [
              {
                id: profile.data.id,
                version: profile.data.version,
                label: `Profilversion ${profile.data.version}`,
              },
            ]
          : []
      }
      mappingVersions={
        mapping.data
          ? [
              {
                id: mapping.data.id,
                version: mapping.data.version,
                label: `Zuordnungsversion ${mapping.data.version}`,
              },
            ]
          : []
      }
      selectedAdviserProfileVersionId={selectedProfileId}
      selectedMappingVersionId={selectedMappingId}
      onAdviserProfileVersionChange={setSelectedProfileId}
      onMappingVersionChange={setSelectedMappingId}
      adviserProfileForm={profileForm}
      mappingForm={mappingForm}
      onProfileFieldChange={(name, value) =>
        setProfileForm((current) => ({
          ...current,
          [name]: name === 'sachkontenlaenge' ? Number(value) : value,
        }))
      }
      onMappingFieldChange={(name, value) =>
        setMappingForm((current) => ({ ...current, [name]: value }))
      }
      rechtsstandEvidence={{
        afa: selectedEvidence?.afaRechtsstand ?? selectedAfa?.rechtsstand ?? '08/2026',
        export: selectedEvidence?.exportRechtsstand ?? mapping.data?.rechtsstand ?? '07/2026',
      }}
      onPreviewAfa={() => runAfa(false)}
      onSaveAfa={() => runAfa(true)}
      onCheckReadiness={() => actions.checkReadiness.mutate(readinessBody())}
      onSaveProfile={() =>
        actions.saveProfile.mutate(buildAdviserProfileRequest(profileForm, now()), {
          onSuccess: (response) => setSelectedProfileId(response.id),
        })
      }
      onSaveMapping={() =>
        actions.saveMapping.mutate(
          {
            taxYear: selectedTaxYear,
            body: buildTaxMappingRequest(mappingForm, selectedTaxYear, now()),
          },
          { onSuccess: (response) => setSelectedMappingId(response.id) },
        )
      }
      onGenerate={() => actions.generate.mutate(buildExportRequest(readinessBody()))}
    />
  );
}
