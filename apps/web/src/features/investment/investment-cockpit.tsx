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
} from '@lokara/ui';
import { useRouter, useSearchParams } from 'next/navigation';
import React, { useState } from 'react';

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

type KpiKey = (typeof KPI_LABELS)[number][0];
type KpiSlot = InvestmentCase['kpiSlots'][string];

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

function kpiText(key: KpiKey, slot: KpiSlot | undefined): string {
  if (!slot || slot.status !== 'available') return '—';
  if (key === 'factor' || key === 'dscr') return hundredths(slot.value);
  if (key === 'gross_yield' || key === 'net_yield') return percent(slot.value);
  if (key === 'equity_return') {
    return `vor Steuer ${percent(slot.before_tax)} · nach Steuer ${percent(slot.after_tax)}`;
  }
  return `vor Steuer ${money(slot.before_tax)} · nach Steuer ${money(slot.after_tax)}`;
}

function value(row: Record<string, unknown>, key: string): unknown {
  return row[key];
}

const LIQUIDITY_TONES = {
  red: { className: 'border-danger bg-danger-tint text-danger', label: '× Liquidität: rot' },
  amber: { className: 'border-warning bg-warning-tint text-warning', label: '! Liquidität: gelb' },
  green: { className: 'border-green bg-mint text-forest', label: '✓ Liquidität: grün' },
} as const;

function liquidityTone(color: unknown) {
  return color === 'red' || color === 'amber' || color === 'green'
    ? LIQUIDITY_TONES[color]
    : undefined;
}

function LiquidityCell({
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
      {tone ? <span className="mt-1 block text-xs">{tone.label}</span> : null}
    </TableCell>
  );
}

export function InvestmentCockpit({ accountId }: { accountId: string }) {
  const me = useMe();
  const account = me.data?.accounts.find((candidate) => candidate.id === accountId);

  return (
    <main className="min-w-0 space-y-8 py-8 [overflow-wrap:anywhere]">
      <header className="max-w-3xl space-y-2 pr-12">
        <h1 className="font-display text-2xl font-semibold text-ink [overflow-wrap:normal] sm:text-3xl">
          Investition prüfen
        </h1>
        <p className="text-base leading-relaxed text-slate">
          Ein Prüfobjekt erfassen und die gespeicherten Kennzahlen sowie das Bank-PDF öffnen.
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
  const investmentCase = useInvestmentCase(accountId, caseKey, selected);
  const sensitivity = useInvestmentSensitivity(accountId, caseKey, selected);
  const bankView = useInvestmentBankView(accountId, caseKey, selected);

  if (!selected) return <CreateCase accountId={accountId} />;
  if (investmentCase.isPending || sensitivity.isPending || bankView.isPending) {
    return <p role="status">Gespeichertes Prüfobjekt wird geladen …</p>;
  }
  if (
    investmentCase.isError ||
    sensitivity.isError ||
    bankView.isError ||
    !investmentCase.data ||
    !sensitivity.data
  ) {
    return <StatusNote kind="danger" label="Prüfobjekt konnte nicht geladen werden." />;
  }
  return (
    <CaseResult
      accountId={accountId}
      investmentCase={investmentCase.data}
      sensitivity={sensitivity.data}
    />
  );
}

const FACT_FIELDS = [
  ['purchasePriceEuros', 'purchasePriceCents', 'Kaufpreis (€)'],
  ['acquisitionCostsEuros', 'acquisitionCostsCents', 'Erwerbsnebenkosten (€)'],
  ['monthlyActualRentEuros', 'monthlyActualRentCents', 'Ist-Kaltmiete monatlich (€)'],
  ['vacancyPercent', 'vacancyBp', 'Leerstand (%)'],
  ['administrationEuros', 'administrationCents', 'Verwaltung pro Jahr (€)'],
  ['maintenanceEuros', 'maintenanceCents', 'Instandhaltung pro Jahr (€)'],
  ['reserveEuros', 'reserveCents', 'Rücklage pro Jahr (€)'],
  ['vacancyRiskEuros', 'vacancyRiskCents', 'Mietausfallwagnis pro Jahr (€)'],
  ['equityEuros', 'equityCents', 'Eigenkapital (€)'],
  ['loanEuros', 'loanCents', 'Darlehen (€)'],
  ['interestPercent', 'interestBp', 'Sollzins (%)'],
  ['initialRepaymentPercent', 'initialRepaymentBp', 'Anfängliche Tilgung (%)'],
  ['marginalTaxPercent', 'marginalTaxBp', 'Grenzsteuersatz (%)'],
  ['buildingSharePercent', 'buildingShareBp', 'Gebäudeanteil (%)'],
  ['afaRatePercent', 'afaRateBp', 'AfA-Satz (%)'],
] as const;

const HEADER_FIELDS = [
  ['bankAddress', 'address', 'Objektadresse', 'text'],
  ['bankPropertyType', 'propertyType', 'Objektart', 'text'],
  ['bankYearBuilt', 'yearBuilt', 'Baujahr', 'integer'],
  ['bankAreaSqm', 'areaSqmX100', 'Wohnfläche (m²)', 'decimal'],
  ['bankUnitCount', 'unitCount', 'Einheiten', 'integer'],
  ['bankCreator', 'creator', 'Erstellt von', 'text'],
  ['bankExportDate', 'exportDate', 'Exportdatum', 'date'],
] as const;

// Decimal-string normalization only: never round money through binary floating point.
function normalizeDecimal(raw: string, fractionalDigits: number): number {
  const match = /^(\d+)(?:[.,](\d+))?$/.exec(raw.trim());
  if (!match || (match[2]?.length ?? 0) > fractionalDigits) {
    throw new Error('Bitte eine nicht negative Zahl mit höchstens zwei Nachkommastellen eingeben.');
  }
  const normalized = BigInt(`${match[1]}${(match[2] ?? '').padEnd(fractionalDigits, '0')}`);
  if (normalized > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('Die Zahl ist zu groß.');
  return Number(normalized);
}

function caseInput(entries: Record<string, string>) {
  const facts: Record<string, unknown> = { analysisPeriodMonths: 12 };
  for (const [name, key] of FACT_FIELDS) {
    const raw = entries[name]?.trim();
    if (raw) facts[key] = normalizeDecimal(raw, 2);
  }
  if (entries.financingProvenance) facts.financingProvenance = entries.financingProvenance;
  const header: Record<string, unknown> = {};
  for (const [name, key, , kind] of HEADER_FIELDS) {
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

function CreateCase({ accountId }: { accountId: string }) {
  const router = useRouter();
  const create = useCreateInvestmentCase(accountId);
  const [entries, setEntries] = useState<Record<string, string>>({});
  const [invalid, setInvalid] = useState(false);
  let input: ReturnType<typeof caseInput> | undefined;
  try {
    input = caseInput(entries);
  } catch {
    /* Keep every entered value for correction. */
  }
  const valid =
    input !== undefined &&
    Boolean(entries.purchasePriceEuros?.trim()) &&
    Boolean(entries.monthlyActualRentEuros?.trim());
  const update = (name: string, raw: string) =>
    setEntries((current) => ({ ...current, [name]: raw }));

  return (
    <Card className="max-w-3xl">
      <CardHeader>
        <CardTitle>Prüfobjekt erfassen</CardTitle>
      </CardHeader>
      <CardContent>
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
          <p className="text-sm leading-relaxed text-slate">
            Kaufpreis und Ist-Kaltmiete sind Pflichtfelder. Weitere Angaben sind optional; fehlende
            Angaben bleiben offen. Zahlen ohne Tausendertrennzeichen, mit Komma oder Punkt und
            höchstens zwei Nachkommastellen eingeben. Analysezeitraum: zwölf Monate.
          </p>
          <fieldset className="space-y-4" disabled={create.isPending}>
            <legend className="font-semibold text-ink">Kauf, Miete und Annahmen</legend>
            <div className="grid gap-6 sm:grid-cols-2">
              {FACT_FIELDS.map(([name, , label]) => (
                <div key={name} className="space-y-2">
                  <Label htmlFor={`investment-${name}`}>{label}</Label>
                  <Input
                    id={`investment-${name}`}
                    name={name}
                    inputMode="decimal"
                    required={name === 'purchasePriceEuros' || name === 'monthlyActualRentEuros'}
                    value={entries[name] ?? ''}
                    onChange={(event) => update(name, event.target.value)}
                  />
                </div>
              ))}
              <div className="space-y-2">
                <Label htmlFor="investment-financing-source">Finanzierungsquelle</Label>
                <select
                  id="investment-financing-source"
                  name="financingProvenance"
                  className="h-11 w-full rounded-md border border-slate bg-white px-3 text-base text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green"
                  value={entries.financingProvenance ?? ''}
                  onChange={(event) => update('financingProvenance', event.target.value)}
                >
                  <option value="">Nicht angegeben</option>
                  <option value="annahme">Eigene Annahme</option>
                  <option value="indikativ">Indikative Finanzierung</option>
                  <option value="angebot">Finanzierungsangebot</option>
                </select>
              </div>
            </div>
          </fieldset>
          <fieldset className="space-y-4" disabled={create.isPending}>
            <legend className="font-semibold text-ink">Angaben für das Bank-PDF (optional)</legend>
            <div className="grid gap-6 sm:grid-cols-2">
              {HEADER_FIELDS.map(([name, , label, kind]) => (
                <div key={name} className="space-y-2">
                  <Label htmlFor={`investment-${name}`}>{label}</Label>
                  <Input
                    id={`investment-${name}`}
                    name={name}
                    type={kind === 'date' ? 'date' : 'text'}
                    inputMode={
                      kind === 'integer' ? 'numeric' : kind === 'decimal' ? 'decimal' : undefined
                    }
                    value={entries[name] ?? ''}
                    onChange={(event) => update(name, event.target.value)}
                  />
                </div>
              ))}
            </div>
          </fieldset>
          {invalid || (!input && Object.keys(entries).length > 0) ? (
            <StatusNote kind="danger" label="Bitte die Eingaben prüfen.">
              Zahlen müssen nicht negativ sein. Leerstand und Gebäudeanteil dürfen höchstens 100 %
              betragen, der Grenzsteuersatz muss unter 100 % liegen. Baujahr und Einheiten sind
              ganze Zahlen. Ihre Eingaben bleiben erhalten.
            </StatusNote>
          ) : null}
          <Button type="submit" disabled={!valid || create.isPending}>
            {create.isPending ? 'Prüfobjekt wird berechnet …' : 'Prüfobjekt berechnen'}
          </Button>
          {create.isError ? (
            <StatusNote kind="danger" label="Prüfobjekt konnte nicht erstellt werden." />
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}

function CaseResult({
  accountId,
  investmentCase,
  sensitivity,
}: {
  accountId: string;
  investmentCase: InvestmentCase;
  sensitivity: InvestmentSensitivity;
}) {
  const partial = KPI_LABELS.some(([key]) => investmentCase.kpiSlots[key]?.status !== 'available');
  return (
    <div className="space-y-8">
      {investmentCase.productionBlocked ? (
        <StatusNote kind="warning" label="Nicht für den produktiven Einsatz freigegeben.">
          Rechtsstand {investmentCase.rechtsstand}. Alle Annahmen und Schwellenwerte bleiben vor
          Produktion zu prüfen.
        </StatusNote>
      ) : null}
      {partial ? <StatusNote kind="warning" label="Daten unvollständig" /> : null}
      <section aria-labelledby="investment-kpis" className="space-y-4">
        <h2 id="investment-kpis" className="font-display text-xl font-semibold text-ink">
          Sieben Kennzahlen
        </h2>
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
                  <CardTitle className="text-base">{label}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-lg font-semibold text-ink [overflow-wrap:normal]">
                    {kpiText(key, slot)}
                  </p>
                  {tone ? (
                    <p className="mt-2 text-sm">
                      {tone.label}
                      {key === 'cashflow' ? ' · nach Steuer' : ''}
                    </p>
                  ) : null}
                  {slot?.status !== 'available' ? (
                    <p className="mt-2 text-sm text-slate">Daten unvollständig</p>
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

      <SensitivityTables sensitivity={sensitivity} />
      <ScheduleTable schedule={investmentCase.calculatedValues.schedule} />

      <div>
        <Button asChild>
          <a
            href={`${API_URL}/a/${encodeURIComponent(accountId)}/investment/cases/${encodeURIComponent(investmentCase.caseKey)}/bank-pdf`}
          >
            Bank-PDF herunterladen
          </a>
        </Button>
      </div>
    </div>
  );
}

function SensitivityTables({ sensitivity }: { sensitivity: InvestmentSensitivity }) {
  return (
    <section aria-labelledby="investment-sensitivity" className="space-y-6">
      <h2 id="investment-sensitivity" className="font-display text-xl font-semibold text-ink">
        Sensitivität
      </h2>
      <div className="space-y-3" data-sensitivity-axis="interest">
        <h3 className="font-semibold text-ink">Zins-Stresstest</h3>
        {sensitivity.interestSensitivity.length === 0 ? (
          <p className="text-sm text-slate">
            Daten unvollständig – keine Zinssensitivität verfügbar.
          </p>
        ) : (
          <Table
            aria-label="Zins-Stresstest"
            tabIndex={0}
            className="min-w-[32rem] whitespace-nowrap [overflow-wrap:normal] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-green"
          >
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
                  <LiquidityCell kpi="dscr" color={value(row, 'dscr_color')}>
                    {hundredths(value(row, 'dscr_hundredths'))}
                  </LiquidityCell>
                  <LiquidityCell kpi="cashflow" color={value(row, 'cashflow_color')}>
                    {money(value(row, 'cashflow_after_month_cents'))}
                  </LiquidityCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
      <div className="space-y-3" data-sensitivity-axis="repayment">
        <h3 className="font-semibold text-ink">Tilgung: Struktur-Trade-off</h3>
        <p className="text-sm text-slate">
          Struktur-Trade-off zwischen Liquidität und Restschuld – keine Stress- oder Risikoachse.
        </p>
        {sensitivity.repaymentSensitivity.length === 0 ? (
          <p className="text-sm text-slate">
            Daten unvollständig – keine Tilgungssensitivität verfügbar.
          </p>
        ) : (
          <Table
            aria-label="Tilgung: Struktur-Trade-off"
            tabIndex={0}
            className="min-w-[40rem] whitespace-nowrap [overflow-wrap:normal] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-green"
          >
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
                  <LiquidityCell kpi="dscr" color={value(row, 'dscr_color')}>
                    {hundredths(value(row, 'dscr_hundredths'))}
                  </LiquidityCell>
                  <LiquidityCell kpi="cashflow" color={value(row, 'cashflow_color')}>
                    {money(value(row, 'cashflow_after_month_cents'))}
                  </LiquidityCell>
                  <TableCell>{money(value(row, 'closing_balance_cents'))}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </section>
  );
}

function ScheduleTable({ schedule }: { schedule: number[][] }) {
  return (
    <section aria-labelledby="investment-schedule" className="space-y-4">
      <h2 id="investment-schedule" className="font-display text-xl font-semibold text-ink">
        Annuitätenplan Jahr 1
      </h2>
      {schedule.length === 0 ? (
        <p className="text-sm text-slate">Daten unvollständig – kein Annuitätenplan verfügbar.</p>
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
    </section>
  );
}
