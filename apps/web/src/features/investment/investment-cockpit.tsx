'use client';

import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
  StatusNote,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  cn,
} from '@lokara/ui';
import { useRouter, useSearchParams } from 'next/navigation';
import React, { useEffect, useMemo, useState } from 'react';

import { useMe } from '@/features/portal/queries';
import { API_URL } from '@/lib/api';

import {
  type InvestmentCase,
  type InvestmentSensitivity,
  InvestmentCreateSchema,
  useCreateInvestmentCase,
  useInvestmentBankView,
  useInvestmentCase,
  useInvestmentEntitlement,
  useInvestmentSensitivity,
} from './queries';

const KPI_LABELS = [
  ['factor', 'Kaufpreisfaktor'],
  ['gross_yield', 'Bruttomietrendite'],
  ['net_yield', 'Nettomietrendite'],
  ['dscr', 'DSCR'],
  ['equity_return', 'Eigenkapitalrendite'],
  ['cashflow', 'Cashflow'],
  ['break_even', 'Break-Even-Miete'],
] as const;

const STEPS = [
  { short: 'Objekt', title: 'Das Prüfobjekt', description: 'Die Eckdaten für Ihre Bankübersicht.' },
  {
    short: 'Kauf & Miete',
    title: 'Kauf und Miete',
    description: 'Die Basis für Faktor und Mietrendite.',
  },
  {
    short: 'Kosten',
    title: 'Bewirtschaftung',
    description: 'Die jährlichen, nicht umlagefähigen Kosten.',
  },
  {
    short: 'Finanzierung',
    title: 'Finanzierung',
    description: 'Ihre Annahmen zu Eigenkapital und Darlehen.',
  },
  {
    short: 'Steuer & AfA',
    title: 'Steuer und AfA',
    description: 'Offengelegte Annahmen für die Nachsteuer-Sicht.',
  },
  {
    short: 'Prüfen',
    title: 'Angaben prüfen',
    description: 'Zusammenfassung und optionale PDF-Angaben.',
  },
] as const;

type KpiKey = (typeof KPI_LABELS)[number][0];
type KpiSlot = InvestmentCase['kpiSlots'][string];
type Entries = Record<string, string>;

function deNumber(value: number, divisor = 1, digits = 2): string {
  return new Intl.NumberFormat('de-DE', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value / divisor);
}

function money(value: unknown): string {
  return typeof value === 'number' ? `${deNumber(value, 100)} €` : '—';
}

function percent(value: unknown): string {
  return typeof value === 'number' ? `${deNumber(value, 100)} %` : '—';
}

function hundredths(value: unknown): string {
  return typeof value === 'number' ? deNumber(value, 100) : '—';
}

function value(row: Record<string, unknown>, key: string): unknown {
  return row[key];
}

function nestedRecord(source: Record<string, unknown>, key: string): Record<string, unknown> {
  const candidate = source[key];
  return candidate && typeof candidate === 'object' && !Array.isArray(candidate)
    ? (candidate as Record<string, unknown>)
    : {};
}

function inputEuro(raw: string | undefined): number | undefined {
  if (!raw || !/^\d+(?:[.,]\d{0,2})?$/.test(raw.trim())) return undefined;
  return Number(raw.replace(',', '.'));
}

function euroPreview(raw: string | undefined): string {
  const parsed = inputEuro(raw);
  return parsed === undefined
    ? '—'
    : `${new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parsed)}`;
}

function normalizeDecimal(raw: string, fractionalDigits: number): number {
  const match = /^(\d+)(?:[.,](\d+))?$/.exec(raw.trim());
  if (!match || (match[2]?.length ?? 0) > fractionalDigits) {
    throw new Error('Bitte eine nicht negative Zahl mit höchstens zwei Nachkommastellen eingeben.');
  }
  const normalized = BigInt(`${match[1]}${(match[2] ?? '').padEnd(fractionalDigits, '0')}`);
  if (normalized > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('Die Zahl ist zu groß.');
  return Number(normalized);
}

const FACT_FIELDS = [
  ['purchasePriceEuros', 'purchasePriceCents'],
  ['acquisitionCostsEuros', 'acquisitionCostsCents'],
  ['monthlyActualRentEuros', 'monthlyActualRentCents'],
  ['vacancyPercent', 'vacancyBp'],
  ['administrationEuros', 'administrationCents'],
  ['maintenanceEuros', 'maintenanceCents'],
  ['reserveEuros', 'reserveCents'],
  ['vacancyRiskEuros', 'vacancyRiskCents'],
  ['equityEuros', 'equityCents'],
  ['loanEuros', 'loanCents'],
  ['interestPercent', 'interestBp'],
  ['initialRepaymentPercent', 'initialRepaymentBp'],
  ['fixedMonthlyAnnuityEuros', 'fixedMonthlyAnnuityCents'],
  ['marginalTaxPercent', 'marginalTaxBp'],
  ['buildingSharePercent', 'buildingShareBp'],
  ['afaRatePercent', 'afaRateBp'],
] as const;

const HEADER_FIELDS = [
  ['bankAddress', 'address', 'text'],
  ['bankPropertyType', 'propertyType', 'text'],
  ['bankYearBuilt', 'yearBuilt', 'integer'],
  ['bankAreaSqm', 'areaSqmX100', 'decimal'],
  ['bankUnitCount', 'unitCount', 'integer'],
  ['bankCreator', 'creator', 'text'],
  ['bankExportDate', 'exportDate', 'date'],
] as const;

function caseInput(entries: Entries) {
  const facts: Record<string, unknown> = { analysisPeriodMonths: 12 };
  for (const [name, key] of FACT_FIELDS) {
    const raw = entries[name]?.trim();
    if (raw) facts[key] = normalizeDecimal(raw, 2);
  }
  if (entries.financingProvenance) facts.financingProvenance = entries.financingProvenance;
  const header: Record<string, unknown> = {};
  for (const [name, key, kind] of HEADER_FIELDS) {
    const raw = entries[name]?.trim();
    if (!raw) continue;
    header[key] =
      kind === 'integer'
        ? normalizeDecimal(raw, 0)
        : kind === 'decimal'
          ? normalizeDecimal(raw, 2)
          : raw;
  }
  if (Object.keys(header).length > 0) facts.bankHeader = header;
  return InvestmentCreateSchema.parse({ facts });
}

const LIQUIDITY_TONES = {
  red: { className: 'border-danger bg-danger-tint text-danger', label: 'Liquidität: rot' },
  amber: { className: 'border-warning bg-warning-tint text-warning', label: 'Liquidität: gelb' },
  green: { className: 'border-green bg-mint text-forest', label: 'Liquidität: grün' },
} as const;

function liquidityTone(color: unknown) {
  return color === 'red' || color === 'amber' || color === 'green'
    ? LIQUIDITY_TONES[color]
    : undefined;
}

function StepIcon({ step }: { step: number }) {
  return (
    <span className="flex size-7 shrink-0 items-center justify-center rounded-full border border-current text-xs font-semibold">
      {step + 1}
    </span>
  );
}

function FormField({
  name,
  label,
  value: fieldValue,
  onChange,
  suffix,
  hint,
  type = 'text',
  inputMode = 'decimal',
  required = false,
}: {
  name: string;
  label: string;
  value: string;
  onChange: (name: string, raw: string) => void;
  suffix?: string;
  hint?: string;
  type?: string;
  inputMode?: React.HTMLAttributes<HTMLInputElement>['inputMode'];
  required?: boolean;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={`investment-${name}`}>
        {label}
        {required ? <span className="ml-1 text-danger">*</span> : null}
      </Label>
      <div className="relative">
        <Input
          id={`investment-${name}`}
          name={name}
          type={type}
          inputMode={inputMode}
          required={required}
          value={fieldValue}
          onChange={(event) => onChange(name, event.target.value)}
          className={suffix ? 'pr-12' : undefined}
        />
        {suffix ? (
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-slate">
            {suffix}
          </span>
        ) : null}
      </div>
      {hint ? <p className="text-xs leading-relaxed text-slate">{hint}</p> : null}
    </div>
  );
}

function SelectField({
  name,
  label,
  value: fieldValue,
  onChange,
  children,
  hint,
}: {
  name: string;
  label: string;
  value: string;
  onChange: (name: string, raw: string) => void;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={`investment-${name}`}>{label}</Label>
      <select
        id={`investment-${name}`}
        name={name}
        className="h-11 w-full rounded-md border border-slate bg-white px-3 text-base text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green"
        value={fieldValue}
        onChange={(event) => onChange(name, event.target.value)}
      >
        {children}
      </select>
      {hint ? <p className="text-xs leading-relaxed text-slate">{hint}</p> : null}
    </div>
  );
}

function ReviewLine({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate/20 py-3 last:border-b-0">
      <dt className="text-sm text-slate">{label}</dt>
      <dd className="text-right text-sm font-semibold text-ink">{children}</dd>
    </div>
  );
}

export function InvestmentCockpit({ accountId }: { accountId: string }) {
  const me = useMe();
  const account = me.data?.accounts.find((candidate) => candidate.id === accountId);

  return (
    <main className="min-w-0 space-y-8 py-8 [overflow-wrap:anywhere]">
      <header className="max-w-3xl space-y-3 pr-12">
        <div className="inline-flex rounded-full bg-mint px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-forest">
          Investmentcockpit
        </div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink [overflow-wrap:normal] sm:text-4xl">
          Investition prüfen
        </h1>
        <p className="max-w-2xl text-base leading-relaxed text-slate">
          Ein Prüfobjekt strukturiert erfassen, Finanzierungsszenarien vergleichen und eine
          bankfähige Übersicht erstellen.
        </p>
      </header>
      {me.isPending ? (
        <p role="status">Kontozugriff wird geladen …</p>
      ) : me.isError ? (
        <StatusNote kind="danger" label="Kontozugriff konnte nicht geladen werden." />
      ) : account?.role !== 'OWNER' ? (
        <StatusNote kind="warning" label="Nur für Inhaber:innen verfügbar." />
      ) : (
        <OwnerCockpit accountId={accountId} />
      )}
    </main>
  );
}

function OwnerCockpit({ accountId }: { accountId: string }) {
  const entitlement = useInvestmentEntitlement(accountId);
  if (entitlement.isPending) return <p role="status">Berechtigung wird geprüft …</p>;
  if (entitlement.isError || !entitlement.data) {
    return <StatusNote kind="danger" label="Investitionsmodul konnte nicht geladen werden." />;
  }
  if (!entitlement.data.enabled) {
    return (
      <StatusNote kind="warning" label="Investitionsmodul ist für dieses Konto nicht aktiviert." />
    );
  }
  return <EnabledCockpit accountId={accountId} />;
}

function EnabledCockpit({ accountId }: { accountId: string }) {
  const search = useSearchParams();
  const caseKey = search.get('caseKey');
  const selected = caseKey !== null && caseKey.length > 0;
  const [creating, setCreating] = useState(false);
  const investmentCase = useInvestmentCase(accountId, caseKey, selected);
  const sensitivity = useInvestmentSensitivity(accountId, caseKey, selected);
  const bankView = useInvestmentBankView(accountId, caseKey, selected);

  if (!selected) {
    return creating ? (
      <CreateCase accountId={accountId} onCancel={() => setCreating(false)} />
    ) : (
      <InvestmentDashboard onCreate={() => setCreating(true)} />
    );
  }
  if (investmentCase.isPending || sensitivity.isPending || bankView.isPending) {
    return <p role="status">Gespeichertes Prüfobjekt wird geladen …</p>;
  }
  if (
    investmentCase.isError ||
    sensitivity.isError ||
    bankView.isError ||
    !investmentCase.data ||
    !sensitivity.data ||
    !bankView.data
  ) {
    return <StatusNote kind="danger" label="Prüfobjekt konnte nicht geladen werden." />;
  }
  return (
    <CaseResult
      accountId={accountId}
      investmentCase={investmentCase.data}
      sensitivity={sensitivity.data}
      bankView={bankView.data.bankView}
    />
  );
}

function InvestmentDashboard({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-xl bg-forest text-white">
        <div className="grid gap-8 px-6 py-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end lg:px-8 lg:py-10">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-white/60">
              Investment-Dashboard
            </p>
            <h2 className="mt-3 font-display text-3xl font-semibold text-white sm:text-4xl">
              Prüfobjekte fundiert vergleichen
            </h2>
            <p className="mt-4 max-w-xl text-base leading-relaxed text-white/75">
              Erfassen Sie ein Kaufobjekt einmal strukturiert. Lokara berechnet die sieben
              Kennzahlen, zeigt die Wirkung von Zins und Tilgung und erstellt Ihre
              Finanzierungsübersicht.
            </p>
          </div>
          <Button type="button" onClick={onCreate} className="bg-white text-forest hover:bg-cream">
            Neues Prüfobjekt
          </Button>
        </div>
      </section>

      <section aria-labelledby="investment-dashboard-overview" className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-green">
            Auf einen Blick
          </p>
          <h2
            id="investment-dashboard-overview"
            className="mt-1 font-display text-2xl font-semibold text-ink"
          >
            Ihre Investitionsanalyse
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <p className="text-3xl font-semibold text-forest">7</p>
              <CardTitle className="text-base">Investment-Kennzahlen</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-slate">
                Faktor, Brutto- und Nettorendite sowie DSCR, Eigenkapitalrendite, Cashflow und
                Break-Even-Miete.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <p className="text-3xl font-semibold text-forest">2</p>
              <CardTitle className="text-base">Finanzierungsachsen</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-slate">
                Zins als Stress-Achse und Tilgung als Struktur-Trade-off zwischen Liquidität und
                Entschuldung.
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <p className="text-3xl font-semibold text-forest">12</p>
              <CardTitle className="text-base">Monate Annuitätenplan</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-slate">
                Zins, Tilgung und Restschuld werden für das erste normalisierte Finanzierungsjahr
                offengelegt.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card>
          <CardHeader>
            <CardTitle className="font-display text-xl">So entsteht Ihre Analyse</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="grid gap-5 sm:grid-cols-3">
              {[
                [
                  '1',
                  'Objekt erfassen',
                  'Kauf, Miete, Kosten und Finanzierung in sechs klaren Schritten.',
                ],
                [
                  '2',
                  'Szenarien prüfen',
                  'Kennzahlen und Finanzierungswirkung transparent nebeneinander.',
                ],
                [
                  '3',
                  'Übersicht exportieren',
                  'Das eingefrorene Ergebnis als deterministisches Bank-PDF.',
                ],
              ].map(([number, title, description]) => (
                <li key={number} className="flex gap-3">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-mint text-sm font-semibold text-forest">
                    {number}
                  </span>
                  <div>
                    <p className="font-semibold text-ink">{title}</p>
                    <p className="mt-1 text-sm leading-relaxed text-slate">{description}</p>
                  </div>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
        <div className="rounded-xl border border-warning/30 bg-warning-tint p-5">
          <p className="text-sm font-semibold text-ink">Planungsrechnung</p>
          <p className="mt-2 text-sm leading-relaxed text-slate">
            Ergebnisse beruhen auf Ihren Angaben und Annahmen. Sie sind keine Bewertung, Bankzusage
            oder Anlageempfehlung.
          </p>
        </div>
      </section>
    </div>
  );
}

function CreateCase({ accountId, onCancel }: { accountId: string; onCancel: () => void }) {
  const router = useRouter();
  const create = useCreateInvestmentCase(accountId);
  const [activeStep, setActiveStep] = useState(0);
  const [repaymentMode, setRepaymentMode] = useState<'percent' | 'annuity'>('percent');
  const [loanEdited, setLoanEdited] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const [entries, setEntries] = useState<Entries>({
    vacancyPercent: '0',
    financingProvenance: 'annahme',
    marginalTaxPercent: '42',
    buildingSharePercent: '75',
    afaRatePercent: '2',
  });
  const currentStep = STEPS[activeStep]!;

  const totalInvestment = useMemo(() => {
    const purchase = inputEuro(entries.purchasePriceEuros);
    const costs = inputEuro(entries.acquisitionCostsEuros);
    return purchase === undefined ? undefined : purchase + (costs ?? 0);
  }, [entries.acquisitionCostsEuros, entries.purchasePriceEuros]);

  const suggestedLoan = useMemo(() => {
    const equity = inputEuro(entries.equityEuros);
    return totalInvestment === undefined || equity === undefined
      ? undefined
      : Math.max(totalInvestment - equity, 0);
  }, [entries.equityEuros, totalInvestment]);

  useEffect(() => {
    if (loanEdited || suggestedLoan === undefined) return;
    setEntries((current) => ({ ...current, loanEuros: suggestedLoan.toFixed(2) }));
  }, [loanEdited, suggestedLoan]);

  let input: ReturnType<typeof caseInput> | undefined;
  try {
    input = caseInput(entries);
  } catch {
    /* Preserve entries for correction. */
  }
  const valid =
    input !== undefined &&
    Boolean(entries.purchasePriceEuros?.trim()) &&
    Boolean(entries.monthlyActualRentEuros?.trim());

  const update = (name: string, raw: string) => {
    if (name === 'loanEuros') setLoanEdited(true);
    setEntries((current) => ({ ...current, [name]: raw }));
  };

  const goTo = (next: number) => {
    setActiveStep(Math.max(0, Math.min(STEPS.length - 1, next)));
    window.scrollTo?.({ top: 0, behavior: 'smooth' });
  };

  return (
    <form
      className="space-y-6"
      onSubmit={(event) => {
        event.preventDefault();
        if (!valid || !input || create.isPending) {
          setInvalid(true);
          return;
        }
        setInvalid(false);
        create.mutate(input, {
          onSuccess: (created) => {
            router.replace(
              `/a/${encodeURIComponent(accountId)}/investment?caseKey=${encodeURIComponent(created.caseKey)}`,
            );
          },
        });
      }}
    >
      <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_19rem]">
        <Card className="min-w-0 overflow-hidden">
          <div className="border-b border-slate/20 bg-cream/40 px-5 py-4 sm:px-7">
            <ol aria-label="Fortschritt" className="grid grid-cols-3 gap-2 lg:grid-cols-6">
              {STEPS.map((step, index) => (
                <li key={step.short}>
                  <button
                    type="button"
                    aria-label={`Schritt ${index + 1}: ${step.title}`}
                    aria-current={activeStep === index ? 'step' : undefined}
                    onClick={() => goTo(index)}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs transition-colors',
                      activeStep === index
                        ? 'bg-forest text-white'
                        : index < activeStep
                          ? 'bg-mint text-forest'
                          : 'text-slate hover:bg-white',
                    )}
                  >
                    <StepIcon step={index} />
                    <span className="hidden leading-tight lg:block">{step.short}</span>
                  </button>
                </li>
              ))}
            </ol>
          </div>

          <CardHeader className="border-b border-slate/20 px-5 py-6 sm:px-7">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-green">
              Schritt {activeStep + 1} von {STEPS.length}
            </p>
            <CardTitle className="font-display text-2xl">{currentStep.title}</CardTitle>
            <p className="text-sm leading-relaxed text-slate">{currentStep.description}</p>
          </CardHeader>

          <CardContent className="px-5 py-7 sm:px-7">
            <fieldset disabled={create.isPending} hidden={activeStep !== 0} className="space-y-6">
              <legend className="sr-only">Objektdaten</legend>
              <div className="rounded-lg border border-green/20 bg-mint/50 p-4 text-sm leading-relaxed text-forest">
                Das Prüfobjekt bleibt von Ihrem bestehenden Immobilienbestand getrennt. Die Angaben
                hier füllen ausschließlich den Kopf der Finanzierungsübersicht.
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <FormField
                    name="bankAddress"
                    label="Objektadresse"
                    value={entries.bankAddress ?? ''}
                    onChange={update}
                    inputMode="text"
                  />
                </div>
                <FormField
                  name="bankPropertyType"
                  label="Objektart"
                  value={entries.bankPropertyType ?? ''}
                  onChange={update}
                  inputMode="text"
                  hint="Zum Beispiel Mehrfamilienhaus oder Eigentumswohnung."
                />
                <FormField
                  name="bankYearBuilt"
                  label="Baujahr"
                  value={entries.bankYearBuilt ?? ''}
                  onChange={update}
                  inputMode="numeric"
                />
                <FormField
                  name="bankAreaSqm"
                  label="Wohnfläche (m²)"
                  value={entries.bankAreaSqm ?? ''}
                  onChange={update}
                  suffix="m²"
                />
                <FormField
                  name="bankUnitCount"
                  label="Einheiten"
                  value={entries.bankUnitCount ?? ''}
                  onChange={update}
                  inputMode="numeric"
                />
              </div>
            </fieldset>

            <fieldset disabled={create.isPending} hidden={activeStep !== 1} className="space-y-7">
              <legend className="sr-only">Kauf und Miete</legend>
              <section className="space-y-4">
                <h3 className="font-semibold text-ink">Investition</h3>
                <div className="grid gap-5 sm:grid-cols-2">
                  <FormField
                    name="purchasePriceEuros"
                    label="Kaufpreis (€)"
                    value={entries.purchasePriceEuros ?? ''}
                    onChange={update}
                    suffix="€"
                    required
                  />
                  <FormField
                    name="acquisitionCostsEuros"
                    label="Erwerbsnebenkosten (€)"
                    value={entries.acquisitionCostsEuros ?? ''}
                    onChange={update}
                    suffix="€"
                    hint="Grunderwerbsteuer, Notar, Grundbuch und gegebenenfalls Makler zusammen."
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg bg-cream px-4 py-3">
                  <span className="text-sm text-slate">Gesamtinvestition</span>
                  <strong className="text-base text-ink">
                    {totalInvestment === undefined
                      ? '—'
                      : new Intl.NumberFormat('de-DE', {
                          style: 'currency',
                          currency: 'EUR',
                        }).format(totalInvestment)}
                  </strong>
                </div>
              </section>
              <section className="space-y-4 border-t border-slate/20 pt-6">
                <h3 className="font-semibold text-ink">Miete</h3>
                <div className="grid gap-5 sm:grid-cols-2">
                  <FormField
                    name="monthlyActualRentEuros"
                    label="Ist-Kaltmiete monatlich (€)"
                    value={entries.monthlyActualRentEuros ?? ''}
                    onChange={update}
                    suffix="€"
                    required
                  />
                  <FormField
                    name="vacancyPercent"
                    label="Leerstand (%)"
                    value={entries.vacancyPercent ?? ''}
                    onChange={update}
                    suffix="%"
                    hint="Faktor und Bruttorendite bleiben auf der Ist-Miete; alle weiteren Kennzahlen verwenden die effektive Miete."
                  />
                </div>
              </section>
            </fieldset>

            <fieldset disabled={create.isPending} hidden={activeStep !== 2} className="space-y-6">
              <legend className="sr-only">Bewirtschaftung</legend>
              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  name="administrationEuros"
                  label="Verwaltung pro Jahr (€)"
                  value={entries.administrationEuros ?? ''}
                  onChange={update}
                  suffix="€"
                  hint="Mindert Cashflow und Steuerbemessung."
                />
                <FormField
                  name="maintenanceEuros"
                  label="Instandhaltung pro Jahr (€)"
                  value={entries.maintenanceEuros ?? ''}
                  onChange={update}
                  suffix="€"
                  hint="Geplante tatsächliche Ausgaben; steuerlich berücksichtigt."
                />
                <FormField
                  name="reserveEuros"
                  label="Rücklage pro Jahr (€)"
                  value={entries.reserveEuros ?? ''}
                  onChange={update}
                  suffix="€"
                  hint="Mindert den Cashflow, nicht die Steuerbemessung."
                />
                <FormField
                  name="vacancyRiskEuros"
                  label="Mietausfallwagnis pro Jahr (€)"
                  value={entries.vacancyRiskEuros ?? ''}
                  onChange={update}
                  suffix="€"
                  hint="Kalkulatorisches Risiko; mindert den Cashflow."
                />
              </div>
              <div className="rounded-lg border border-slate/20 p-4">
                <p className="text-sm font-semibold text-ink">Bewirtschaftung offen ausgewiesen</p>
                <p className="mt-1 text-sm leading-relaxed text-slate">
                  Lokara trennt tatsächliche Ausgaben von Rücklage und Mietausfallwagnis, damit die
                  Steuer-Sicht nicht mit der Liquiditätsplanung vermischt wird.
                </p>
              </div>
            </fieldset>

            <fieldset disabled={create.isPending} hidden={activeStep !== 3} className="space-y-7">
              <legend className="sr-only">Finanzierung</legend>
              <div className="rounded-lg border border-warning/30 bg-warning-tint p-4 text-sm leading-relaxed text-ink">
                Vor einem Bankangebot sind diese Werte Annahmen. Jede davon abhängige Kennzahl wird
                entsprechend gekennzeichnet.
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  name="equityEuros"
                  label="Eigenkapital (€)"
                  value={entries.equityEuros ?? ''}
                  onChange={update}
                  suffix="€"
                />
                <FormField
                  name="loanEuros"
                  label="Darlehen (€)"
                  value={entries.loanEuros ?? ''}
                  onChange={update}
                  suffix="€"
                  hint={
                    loanEdited
                      ? 'Manuell überschrieben.'
                      : 'Automatisch aus Gesamtinvestition minus Eigenkapital.'
                  }
                />
                <FormField
                  name="interestPercent"
                  label="Sollzins (%)"
                  value={entries.interestPercent ?? ''}
                  onChange={update}
                  suffix="%"
                />
                <SelectField
                  name="financingProvenance"
                  label="Finanzierungsquelle"
                  value={entries.financingProvenance ?? ''}
                  onChange={update}
                >
                  <option value="annahme">Eigene Annahme</option>
                  <option value="indikativ">Indikative Finanzierung</option>
                  <option value="angebot">Finanzierungsangebot</option>
                </SelectField>
              </div>
              <div className="space-y-4 border-t border-slate/20 pt-6">
                <div
                  className="flex flex-wrap gap-2"
                  role="group"
                  aria-label="Art der Tilgungseingabe"
                >
                  <button
                    type="button"
                    onClick={() => {
                      setRepaymentMode('percent');
                      setEntries((current) => ({ ...current, fixedMonthlyAnnuityEuros: '' }));
                    }}
                    className={cn(
                      'rounded-full border px-4 py-2 text-sm font-semibold',
                      repaymentMode === 'percent'
                        ? 'border-forest bg-forest text-white'
                        : 'border-slate/30 text-slate',
                    )}
                  >
                    Tilgungssatz
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setRepaymentMode('annuity');
                      setEntries((current) => ({ ...current, initialRepaymentPercent: '' }));
                    }}
                    className={cn(
                      'rounded-full border px-4 py-2 text-sm font-semibold',
                      repaymentMode === 'annuity'
                        ? 'border-forest bg-forest text-white'
                        : 'border-slate/30 text-slate',
                    )}
                  >
                    Feste Monatsrate
                  </button>
                </div>
                {repaymentMode === 'percent' ? (
                  <FormField
                    name="initialRepaymentPercent"
                    label="Anfängliche Tilgung (%)"
                    value={entries.initialRepaymentPercent ?? ''}
                    onChange={update}
                    suffix="%"
                  />
                ) : (
                  <FormField
                    name="fixedMonthlyAnnuityEuros"
                    label="Feste Monatsrate (€)"
                    value={entries.fixedMonthlyAnnuityEuros ?? ''}
                    onChange={update}
                    suffix="€"
                  />
                )}
              </div>
            </fieldset>

            <fieldset disabled={create.isPending} hidden={activeStep !== 4} className="space-y-6">
              <legend className="sr-only">Steuer und AfA</legend>
              <div className="rounded-lg border border-green/20 bg-mint/50 p-4 text-sm leading-relaxed text-forest">
                Diese Werte sind Szenario-Annahmen. Lokara ermittelt weder Ihr Einkommen noch einen
                persönlichen Steuersatz.
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  name="marginalTaxPercent"
                  label="Grenzsteuersatz (%)"
                  value={entries.marginalTaxPercent ?? ''}
                  onChange={update}
                  suffix="%"
                  hint="Editierbare Annahme; Soli und Kirchensteuer sind nicht enthalten."
                />
                <FormField
                  name="buildingSharePercent"
                  label="Gebäudeanteil (%)"
                  value={entries.buildingSharePercent ?? ''}
                  onChange={update}
                  suffix="%"
                  hint="Annahme für die AfA-Basis, solange kein AfA-Datensatz verknüpft ist."
                />
                <FormField
                  name="afaRatePercent"
                  label="AfA-Satz (%)"
                  value={entries.afaRatePercent ?? ''}
                  onChange={update}
                  suffix="%"
                />
              </div>
              <div className="rounded-lg border border-slate/20 p-4">
                <p className="text-sm font-semibold text-ink">
                  Annahme 75 % Gebäudeanteil / 2 % AfA
                </p>
                <p className="mt-1 text-sm leading-relaxed text-slate">
                  Die Werte sind vollständig editierbar und werden im Ergebnis sowie im Bank-PDF als
                  Annahmen offengelegt.
                </p>
              </div>
            </fieldset>

            <fieldset disabled={create.isPending} hidden={activeStep !== 5} className="space-y-7">
              <legend className="sr-only">Angaben prüfen</legend>
              <div className="grid gap-5 sm:grid-cols-2">
                <Card className="border-slate/20 shadow-none">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Investition</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <dl>
                      <ReviewLine label="Kaufpreis">
                        {euroPreview(entries.purchasePriceEuros)}
                      </ReviewLine>
                      <ReviewLine label="Nebenkosten">
                        {euroPreview(entries.acquisitionCostsEuros)}
                      </ReviewLine>
                      <ReviewLine label="Kaltmiete / Monat">
                        {euroPreview(entries.monthlyActualRentEuros)}
                      </ReviewLine>
                    </dl>
                  </CardContent>
                </Card>
                <Card className="border-slate/20 shadow-none">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Finanzierung</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <dl>
                      <ReviewLine label="Eigenkapital">
                        {euroPreview(entries.equityEuros)}
                      </ReviewLine>
                      <ReviewLine label="Darlehen">{euroPreview(entries.loanEuros)}</ReviewLine>
                      <ReviewLine label="Sollzins">
                        {entries.interestPercent ? `${entries.interestPercent} %` : '—'}
                      </ReviewLine>
                    </dl>
                  </CardContent>
                </Card>
              </div>
              <section className="space-y-4 border-t border-slate/20 pt-6">
                <div>
                  <h3 className="font-semibold text-ink">Angaben für das Bank-PDF</h3>
                  <p className="mt-1 text-sm text-slate">
                    Optional. Fehlende Angaben bleiben im PDF offen.
                  </p>
                </div>
                <div className="grid gap-5 sm:grid-cols-2">
                  <FormField
                    name="bankCreator"
                    label="Erstellt von"
                    value={entries.bankCreator ?? ''}
                    onChange={update}
                    inputMode="text"
                  />
                  <FormField
                    name="bankExportDate"
                    label="Exportdatum"
                    value={entries.bankExportDate ?? ''}
                    onChange={update}
                    type="date"
                    inputMode="numeric"
                  />
                </div>
              </section>
              {invalid || (!input && Object.keys(entries).length > 0) ? (
                <StatusNote kind="danger" label="Bitte die Eingaben prüfen.">
                  Kaufpreis und Ist-Kaltmiete sind erforderlich. Zahlen müssen nicht negativ sein.
                  Prozentwerte müssen im zulässigen Bereich liegen. Ihre Eingaben bleiben erhalten.
                </StatusNote>
              ) : null}
              {create.isError ? (
                <StatusNote kind="danger" label="Prüfobjekt konnte nicht erstellt werden." />
              ) : null}
            </fieldset>

            <div className="mt-8 flex items-center justify-between border-t border-slate/20 pt-5">
              <Button
                type="button"
                variant="outline"
                disabled={create.isPending}
                onClick={() => (activeStep === 0 ? onCancel() : goTo(activeStep - 1))}
              >
                {activeStep === 0 ? 'Abbrechen' : 'Zurück'}
              </Button>
              {activeStep < STEPS.length - 1 ? (
                <Button type="button" onClick={() => goTo(activeStep + 1)}>
                  Weiter
                </Button>
              ) : (
                <Button type="submit" disabled={!valid || create.isPending}>
                  {create.isPending ? 'Prüfobjekt wird berechnet …' : 'Prüfobjekt berechnen'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <aside className="min-w-0 space-y-4 xl:sticky xl:top-6 xl:self-start">
          <Card className="border-green/20 bg-forest text-white">
            <CardHeader className="pb-3">
              <CardTitle className="text-base text-white">Ihre Kalkulation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-white/60">Gesamtinvestition</p>
                <p className="mt-1 text-xl font-semibold">
                  {totalInvestment === undefined
                    ? '—'
                    : new Intl.NumberFormat('de-DE', {
                        style: 'currency',
                        currency: 'EUR',
                        maximumFractionDigits: 0,
                      }).format(totalInvestment)}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 border-t border-white/15 pt-4">
                <div>
                  <p className="text-xs text-white/60">Kaltmiete</p>
                  <p className="mt-1 font-semibold">
                    {euroPreview(entries.monthlyActualRentEuros)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-white/60">Darlehen</p>
                  <p className="mt-1 font-semibold">{euroPreview(entries.loanEuros)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <div className="rounded-lg border border-slate/20 bg-white p-4 text-sm leading-relaxed text-slate">
            <p className="font-semibold text-ink">Was Sie erhalten</p>
            <ul className="mt-3 space-y-2">
              <li>✓ sieben Investment-Kennzahlen</li>
              <li>✓ Zins- und Tilgungsszenarien</li>
              <li>✓ Annuitätenplan für zwölf Monate</li>
              <li>✓ deterministisches Bank-PDF</li>
            </ul>
          </div>
        </aside>
      </div>
    </form>
  );
}

function KpiValue({ kpiKey, slot }: { kpiKey: KpiKey; slot: KpiSlot | undefined }) {
  if (slot?.status === 'not_applicable') {
    return (
      <>
        <p className="text-xl font-semibold text-ink">
          {typeof slot.value === 'string' ? slot.value : 'Nicht anwendbar'}
        </p>
        <p className="mt-2 text-sm text-slate">Kein Fremdkapital</p>
      </>
    );
  }
  if (!slot || slot.status !== 'available') {
    return (
      <>
        <p className="text-2xl font-semibold text-ink">—</p>
        <p className="mt-2 text-sm text-slate">Daten unvollständig</p>
      </>
    );
  }
  if (kpiKey === 'factor' || kpiKey === 'dscr')
    return <p className="text-2xl font-semibold text-ink">{hundredths(slot.value)}</p>;
  if (kpiKey === 'gross_yield' || kpiKey === 'net_yield')
    return <p className="text-2xl font-semibold text-ink">{percent(slot.value)}</p>;
  const format = kpiKey === 'equity_return' ? percent : money;
  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <p className="text-xs text-slate">vor Steuer</p>
        <p className="mt-1 text-lg font-semibold text-ink">{format(slot.before_tax)}</p>
      </div>
      <div className="border-l border-slate/20 pl-3">
        <p className="text-xs text-slate">nach Steuer</p>
        <p className="mt-1 text-lg font-semibold text-ink">{format(slot.after_tax)}</p>
      </div>
    </div>
  );
}

function CaseResult({
  accountId,
  investmentCase,
  sensitivity,
  bankView,
}: {
  accountId: string;
  investmentCase: InvestmentCase;
  sensitivity: InvestmentSensitivity;
  bankView: Record<string, unknown>;
}) {
  const router = useRouter();
  const [financingOpen, setFinancingOpen] = useState(false);
  const partial = KPI_LABELS.some(
    ([key]) => investmentCase.kpiSlots[key]?.status === 'unavailable',
  );
  const investment = nestedRecord(bankView, 'investment');
  const header = nestedRecord(bankView, 'header');
  const financing = nestedRecord(bankView, 'financing_ltv');
  const address = typeof header.address === 'string' ? header.address : 'Gespeichertes Prüfobjekt';

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-xl bg-forest text-white">
        <div className="grid gap-6 px-6 py-7 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-white/60">
              Prüfobjekt
            </p>
            <h2 className="mt-2 font-display text-2xl font-semibold text-white sm:text-3xl">
              {address}
            </h2>
            <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/75">
              <span>Kaufpreis {money(investment.purchase_price_cents)}</span>
              <span>Gesamtinvestition {money(investment.total_investment_cents)}</span>
              <span>Darlehen {money(financing.loan_cents)}</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              className="border-white/30 bg-transparent text-white hover:bg-white/10"
              onClick={() => router.replace(`/a/${encodeURIComponent(accountId)}/investment`)}
            >
              Neues Prüfobjekt
            </Button>
            <Button asChild className="bg-white text-forest hover:bg-cream">
              <a
                href={`${API_URL}/a/${encodeURIComponent(accountId)}/investment/cases/${encodeURIComponent(investmentCase.caseKey)}/bank-pdf`}
              >
                Bank-PDF herunterladen
              </a>
            </Button>
          </div>
        </div>
      </section>

      {investmentCase.productionBlocked ? (
        <StatusNote
          kind="warning"
          label="Planungsrechnung – nicht für den produktiven Einsatz freigegeben."
        >
          Rechtsstand {investmentCase.rechtsstand}. Annahmen und Schwellenwerte bleiben vor
          Produktion zu prüfen.
        </StatusNote>
      ) : null}
      {partial ? <StatusNote kind="warning" label="Daten unvollständig" /> : null}

      <section aria-labelledby="investment-kpis" className="space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-green">
            Entscheidungsgrundlage
          </p>
          <h2 id="investment-kpis" className="mt-1 font-display text-2xl font-semibold text-ink">
            Sieben Kennzahlen
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate">
            Drei Kennzahlen beschreiben das Objekt unabhängig von der Finanzierung. Vier weitere
            zeigen die Wirkung Ihrer Finanzierungsannahmen.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {KPI_LABELS.map(([key, label]) => {
            const slot = investmentCase.kpiSlots[key];
            const liquid = key === 'dscr' || key === 'cashflow';
            const tone =
              liquid && slot?.status === 'available' ? liquidityTone(slot.color) : undefined;
            return (
              <Card
                key={key}
                data-kpi-key={key}
                {...(tone
                  ? {
                      'data-liquidity-color': slot?.color,
                      'data-tax-basis': key === 'cashflow' ? 'after' : 'before',
                      className: tone.className,
                    }
                  : {})}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle className="text-base">{label}</CardTitle>
                    {tone ? (
                      <span className="rounded-full border border-current px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wide">
                        {tone.label}
                      </span>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <KpiValue kpiKey={key} slot={slot} />
                  {key === 'dscr' && slot?.status === 'available' ? (
                    <button
                      type="button"
                      onClick={() => setFinancingOpen(true)}
                      className="text-sm font-semibold text-green underline-offset-4 hover:underline"
                    >
                      Finanzierung simulieren
                    </button>
                  ) : null}
                </CardContent>
              </Card>
            );
          })}
        </div>
        <p className="text-sm leading-relaxed text-slate">
          Liquiditätsindikator unter Ihren Annahmen – keine Risikobewertung und keine Bankzusage.
        </p>
      </section>

      <FinancingLab
        sensitivity={sensitivity}
        open={financingOpen}
        onToggle={() => setFinancingOpen((current) => !current)}
      />
      <ScheduleTable schedule={investmentCase.calculatedValues.schedule} />
    </div>
  );
}

function LiquidityMetric({
  kpi,
  color,
  label,
  children,
}: {
  kpi: 'dscr' | 'cashflow';
  color: unknown;
  label: string;
  children: React.ReactNode;
}) {
  const tone = liquidityTone(color);
  return (
    <div
      data-kpi-key={kpi}
      data-tax-basis={kpi === 'cashflow' ? 'after' : 'before'}
      {...(tone
        ? {
            'data-liquidity-color': String(color),
            className: cn('rounded-lg border p-4', tone.className),
          }
        : { className: 'rounded-lg border border-slate/20 p-4' })}
    >
      <p className="text-xs text-slate">{label}</p>
      <p className="mt-1 text-xl font-semibold text-ink">{children}</p>
      {tone ? <p className="mt-1 text-xs">{tone.label}</p> : null}
    </div>
  );
}

function LiquidityTableCell({
  kpi,
  color,
  children,
}: {
  kpi: 'dscr' | 'cashflow';
  color: unknown;
  children: React.ReactNode;
}) {
  const tone = liquidityTone(color);
  return (
    <TableCell
      data-kpi-key={kpi}
      data-tax-basis={kpi === 'cashflow' ? 'after' : 'before'}
      {...(tone ? { 'data-liquidity-color': String(color), className: tone.className } : {})}
    >
      {children}
    </TableCell>
  );
}

function FinancingLab({
  sensitivity,
  open,
  onToggle,
}: {
  sensitivity: InvestmentSensitivity;
  open: boolean;
  onToggle: () => void;
}) {
  const [axis, setAxis] = useState<'interest' | 'repayment'>('interest');
  const rows =
    axis === 'interest' ? sensitivity.interestSensitivity : sensitivity.repaymentSensitivity;
  const baseIndex =
    axis === 'interest'
      ? Math.max(
          0,
          rows.findIndex((row) => value(row, 'is_base') === true),
        )
      : Math.min(1, Math.max(0, rows.length - 1));
  const [interestIndex, setInterestIndex] = useState(baseIndex);
  const [repaymentIndex, setRepaymentIndex] = useState(
    Math.min(1, Math.max(0, sensitivity.repaymentSensitivity.length - 1)),
  );
  const selectedIndex =
    axis === 'interest'
      ? Math.min(interestIndex, Math.max(rows.length - 1, 0))
      : Math.min(repaymentIndex, Math.max(rows.length - 1, 0));
  const selected = rows[selectedIndex] ?? {};
  const rateKey = axis === 'interest' ? 'interest_bp' : 'initial_repayment_bp';

  return (
    <section
      aria-labelledby="investment-sensitivity"
      className="overflow-hidden rounded-xl border border-green/20 bg-white"
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left sm:px-7"
      >
        <span>
          <span className="block text-xs font-semibold uppercase tracking-[0.14em] text-green">
            Finanzierungslabor
          </span>
          <span
            id="investment-sensitivity"
            className="mt-1 block font-display text-2xl font-semibold text-ink"
          >
            Was verändert Zins und Tilgung?
          </span>
          <span className="mt-1 block text-sm font-normal text-slate">
            Zins-Stresstest und Tilgung als Struktur-Trade-off.
          </span>
        </span>
        <span aria-hidden="true" className="text-2xl text-green">
          {open ? '−' : '+'}
        </span>
      </button>
      {open ? (
        <div className="border-t border-green/20 px-5 py-6 sm:px-7">
          {rows.length === 0 ? (
            <p className="text-sm text-slate">
              Daten unvollständig – keine Finanzierungssensitivität verfügbar.
            </p>
          ) : (
            <div className="space-y-7">
              <div
                className="inline-flex rounded-lg bg-cream p-1"
                role="tablist"
                aria-label="Finanzierungsachse"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={axis === 'interest'}
                  onClick={() => setAxis('interest')}
                  className={cn(
                    'rounded-md px-4 py-2 text-sm font-semibold',
                    axis === 'interest' ? 'bg-white text-forest shadow-sm' : 'text-slate',
                  )}
                >
                  Zins-Stresstest
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={axis === 'repayment'}
                  onClick={() => setAxis('repayment')}
                  className={cn(
                    'rounded-md px-4 py-2 text-sm font-semibold',
                    axis === 'repayment' ? 'bg-white text-forest shadow-sm' : 'text-slate',
                  )}
                >
                  Tilgungsstruktur
                </button>
              </div>

              <div className="grid gap-7 lg:grid-cols-[minmax(0,1fr)_16rem]">
                <div className="space-y-4">
                  <div className="flex items-end justify-between gap-4">
                    <div>
                      <Label htmlFor={`investment-${axis}-slider`}>
                        {axis === 'interest' ? 'Sollzins' : 'Anfängliche Tilgung'}
                      </Label>
                      <p className="mt-1 text-sm text-slate">
                        {axis === 'interest'
                          ? 'Zins ist die Stress-Achse.'
                          : 'Tilgung verändert Liquidität und Entschuldung gleichzeitig.'}
                      </p>
                    </div>
                    <output className="text-2xl font-semibold text-forest">
                      {percent(value(selected, rateKey))}
                    </output>
                  </div>
                  <input
                    id={`investment-${axis}-slider`}
                    type="range"
                    min={0}
                    max={Math.max(rows.length - 1, 0)}
                    step={1}
                    value={selectedIndex}
                    onChange={(event) =>
                      axis === 'interest'
                        ? setInterestIndex(Number(event.target.value))
                        : setRepaymentIndex(Number(event.target.value))
                    }
                    className="h-2 w-full cursor-pointer accent-green"
                    aria-label={axis === 'interest' ? 'Sollzins-Szenario' : 'Tilgungs-Szenario'}
                  />
                  <div className="flex justify-between text-xs text-slate">
                    {rows.map((row, index) => (
                      <span key={index}>
                        {deNumber(Number(value(row, rateKey) ?? 0), 100, 1)} %
                      </span>
                    ))}
                  </div>
                </div>
                <div className="rounded-lg bg-cream p-4 text-sm leading-relaxed text-slate">
                  <strong className="text-ink">
                    {axis === 'interest' ? 'Stress' : 'Struktur'}
                  </strong>
                  <p className="mt-1">
                    {axis === 'interest'
                      ? 'Ein höherer Zins belastet die Liquidität. Die Objektkennzahlen Faktor, Brutto und Netto bleiben unverändert.'
                      : 'Mehr Tilgung senkt die laufende Liquidität und erhöht zugleich die Entschuldung. Das ist keine Risiko-Achse.'}
                  </p>
                </div>
              </div>

              <div aria-live="polite" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <LiquidityMetric kpi="dscr" color={value(selected, 'dscr_color')} label="DSCR">
                  {hundredths(value(selected, 'dscr_hundredths'))}
                </LiquidityMetric>
                <LiquidityMetric
                  kpi="cashflow"
                  color={value(selected, 'cashflow_color')}
                  label="Cashflow nach Steuer / Monat"
                >
                  {money(value(selected, 'cashflow_after_month_cents'))}
                </LiquidityMetric>
                <div className="rounded-lg border border-slate/20 p-4">
                  <p className="text-xs text-slate">EK-Rendite nach Steuer</p>
                  <p className="mt-1 text-xl font-semibold text-ink">
                    {percent(value(selected, 'equity_return_after_bp'))}
                  </p>
                </div>
                <div className="rounded-lg border border-slate/20 p-4">
                  <p className="text-xs text-slate">Break-Even nach Steuer</p>
                  <p className="mt-1 text-xl font-semibold text-ink">
                    {money(value(selected, 'break_even_after_month_cents'))}
                  </p>
                </div>
                <div className="rounded-lg border border-slate/20 p-4">
                  <p className="text-xs text-slate">Restschuld Jahr 1</p>
                  <p className="mt-1 text-xl font-semibold text-ink">
                    {axis === 'repayment' ? money(value(selected, 'closing_balance_cents')) : '—'}
                  </p>
                </div>
              </div>

              <p className="text-sm leading-relaxed text-slate">
                Die Auswahl zeigt gespeicherte Ergebnisse der serverseitigen Rechenlogik. Sie
                verändert das eingefrorene Prüfobjekt nicht.
              </p>
            </div>
          )}
        </div>
      ) : null}
      <SensitivityTables sensitivity={sensitivity} />
    </section>
  );
}

function SensitivityTables({ sensitivity }: { sensitivity: InvestmentSensitivity }) {
  return (
    <div className="sr-only">
      <div data-sensitivity-axis="interest">
        <Table aria-label="Zins-Stresstest">
          <TableHeader>
            <TableRow>
              <TableHead>Sollzins</TableHead>
              <TableHead>DSCR</TableHead>
              <TableHead>Cashflow nach Steuer</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sensitivity.interestSensitivity.map((row, index) => (
              <TableRow key={index}>
                <TableCell>{percent(value(row, 'interest_bp'))}</TableCell>
                <LiquidityTableCell kpi="dscr" color={value(row, 'dscr_color')}>
                  {hundredths(value(row, 'dscr_hundredths'))}
                </LiquidityTableCell>
                <LiquidityTableCell kpi="cashflow" color={value(row, 'cashflow_color')}>
                  {money(value(row, 'cashflow_after_month_cents'))}
                </LiquidityTableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div data-sensitivity-axis="repayment">
        <Table aria-label="Tilgung: Struktur-Trade-off">
          <TableHeader>
            <TableRow>
              <TableHead>Tilgung</TableHead>
              <TableHead>DSCR</TableHead>
              <TableHead>Cashflow nach Steuer</TableHead>
              <TableHead>Restschuld</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sensitivity.repaymentSensitivity.map((row, index) => (
              <TableRow key={index}>
                <TableCell>{percent(value(row, 'initial_repayment_bp'))}</TableCell>
                <LiquidityTableCell kpi="dscr" color={value(row, 'dscr_color')}>
                  {hundredths(value(row, 'dscr_hundredths'))}
                </LiquidityTableCell>
                <LiquidityTableCell kpi="cashflow" color={value(row, 'cashflow_color')}>
                  {money(value(row, 'cashflow_after_month_cents'))}
                </LiquidityTableCell>
                <TableCell>{money(value(row, 'closing_balance_cents'))}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function ScheduleTable({ schedule }: { schedule: number[][] }) {
  const [open, setOpen] = useState(false);
  return (
    <section
      aria-labelledby="investment-schedule"
      className="overflow-hidden rounded-xl border border-slate/20 bg-white"
    >
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left sm:px-7"
      >
        <span>
          <span className="block text-xs font-semibold uppercase tracking-[0.14em] text-green">
            Darlehensverlauf
          </span>
          <span
            id="investment-schedule"
            className="mt-1 block font-display text-2xl font-semibold text-ink"
          >
            Annuitätenplan Jahr 1
          </span>
        </span>
        <span aria-hidden="true" className="text-2xl text-green">
          {open ? '−' : '+'}
        </span>
      </button>
      {open ? (
        <div className="border-t border-slate/20 p-4 sm:p-6">
          {schedule.length === 0 ? (
            <p className="text-sm text-slate">
              Daten unvollständig – kein Annuitätenplan verfügbar.
            </p>
          ) : (
            <Table
              aria-label="Annuitätenplan Jahr 1"
              tabIndex={0}
              className="min-w-[40rem] whitespace-nowrap [overflow-wrap:normal] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-green"
            >
              <TableHeader>
                <TableRow>
                  <TableHead>Monat</TableHead>
                  <TableHead>Anfangsschuld</TableHead>
                  <TableHead>Zins</TableHead>
                  <TableHead>Tilgung</TableHead>
                  <TableHead>Restschuld</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {schedule.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell>{index + 1}</TableCell>
                    <TableCell>{money(row[0])}</TableCell>
                    <TableCell>{money(row[1])}</TableCell>
                    <TableCell>{money(row[2])}</TableCell>
                    <TableCell>{money(row[3])}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      ) : null}
      {!open && schedule.length > 0 ? (
        <div className="sr-only">
          <Table aria-label="Annuitätenplan Jahr 1">
            <TableBody>
              {schedule.map((row, index) => (
                <TableRow key={index}>
                  <TableCell>{index + 1}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </section>
  );
}
