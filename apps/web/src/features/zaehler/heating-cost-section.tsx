'use client';

import { Button, Select, StatusNote } from '@lokara/ui';
import { useState } from 'react';

import { ApiError } from '@/lib/api';
import type { MeterWorkspaceResponse } from '@/lib/contracts';
import { HEATING_COST_CATEGORIES } from '@/lib/contracts';
import { isoToGermanDate, parseEurToCents, parseMeterValueToX1000 } from '@/lib/format';

import {
  useConfirmMdlStatement,
  useCreateHeatingBillingMode,
  useCreateHeatingCost,
  useHeatingBillingModes,
  useHeatingCosts,
  useVoidHeatingCost,
} from './queries';

const CATEGORY_LABELS = {
  FUEL_OR_HEAT_SUPPLY: 'Brennstoff/Wärmelieferung',
  OPERATING_ELECTRICITY: 'Betriebsstrom',
  MAINTENANCE: 'Wartung',
  METERING_SERVICE: 'Mess-/Abrechnungsdienst',
  OTHER_ALLOWED: 'Sonstige zugelassene Heizkostenposition',
} as const;

type WorkspaceUnit = MeterWorkspaceResponse['buildings'][number]['units'][number];

function currentPeriod(): { from: string; to: string } {
  const year = new Date().getFullYear();
  return { from: `${year}-01-01`, to: `${year + 1}-01-01` };
}

export function HeatingCostSection({
  accountId,
  buildingId,
  units,
  canWrite,
}: {
  accountId: string;
  buildingId: string;
  units: WorkspaceUnit[];
  canWrite: boolean;
}) {
  const costs = useHeatingCosts(accountId, buildingId);
  const modes = useHeatingBillingModes(accountId, buildingId);
  const [showCostForm, setShowCostForm] = useState(false);
  const [showModeForm, setShowModeForm] = useState(false);
  const latestMode = modes.data?.[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="font-display text-lg font-bold text-ink">Abrechnungsweg</h3>
          <p className="mt-1 text-sm text-slate">
            {latestMode
              ? latestMode.mode === 'LOKARA'
                ? 'Mit Lokara abrechnen'
                : `Durch Messdienstleister abrechnen · ${latestMode.providerName} · ${latestMode.externalStatus}`
              : 'Noch kein versionierter Abrechnungsweg gewählt; bestehende Daten bleiben im bisherigen Modus.'}
          </p>
        </div>
        {canWrite && latestMode?.externalStatus !== 'UEBERNOMMEN' ? (
          <Button variant="outline" size="sm" onClick={() => setShowModeForm((value) => !value)}>
            Abrechnungsweg festlegen
          </Button>
        ) : null}
      </div>
      {showModeForm ? (
        <ModeForm
          accountId={accountId}
          buildingId={buildingId}
          onDone={() => setShowModeForm(false)}
        />
      ) : null}

      {latestMode?.mode === 'EXTERNAL_PROVIDER' ? (
        <ExternalBilling
          accountId={accountId}
          buildingId={buildingId}
          units={units}
          mode={latestMode}
          canWrite={canWrite}
        />
      ) : (
        <>
          <div>
            <h3 className="font-display text-lg font-bold text-ink">Heizkostenpositionen</h3>
            <p className="mt-1 text-sm text-slate">
              Positionen mit Belegreferenz und eindeutig zugeordneten CO₂-Angaben. Der Katalog kommt
              vom Backend-Vertrag; Umlageschlüssel werden hier nicht angeboten.
            </p>
          </div>
          {costs.isPending ? (
            <div aria-hidden="true" className="h-24 animate-pulse rounded-lg bg-mint/60" />
          ) : costs.isError ? (
            <StatusNote kind="danger" label="Heizkosten konnten nicht geladen werden.">
              <button className="underline" onClick={() => void costs.refetch()}>
                Erneut versuchen
              </button>
            </StatusNote>
          ) : (
            <>
              <StatusNote
                kind={costs.data.readiness === 'COMPLETE' ? 'success' : 'warning'}
                label={
                  costs.data.readiness === 'COMPLETE'
                    ? 'Vollständig.'
                    : costs.data.readiness === 'MISSING_INFORMATION'
                      ? 'Angaben fehlen.'
                      : 'Prüfung erforderlich.'
                }
              >
                {costs.data.findings.join(' ') ||
                  'Die erfassten Positionen enthalten die erforderlichen Quellenangaben.'}
              </StatusNote>
              <div className="overflow-x-auto rounded-xl border border-mint">
                <table className="w-full min-w-[760px] text-sm">
                  <thead className="bg-mint/40 text-left text-forest">
                    <tr>
                      <th className="px-4 py-3">Kategorie / Position</th>
                      <th className="px-4 py-3 text-right">Betrag</th>
                      <th className="px-4 py-3">Zeitraum</th>
                      <th className="px-4 py-3">Quelle</th>
                      <th className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-mint">
                    {costs.data.heatingCosts.map((cost) => (
                      <HeatingCostRow
                        key={cost.id}
                        accountId={accountId}
                        buildingId={buildingId}
                        cost={cost}
                        canWrite={canWrite}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {canWrite ? (
            showCostForm ? (
              <HeatingCostForm
                accountId={accountId}
                buildingId={buildingId}
                onDone={() => setShowCostForm(false)}
              />
            ) : (
              <Button variant="outline" onClick={() => setShowCostForm(true)}>
                Heizkostenposition erfassen
              </Button>
            )
          ) : null}
        </>
      )}
    </div>
  );
}

function ModeForm({
  accountId,
  buildingId,
  onDone,
}: {
  accountId: string;
  buildingId: string;
  onDone: () => void;
}) {
  const create = useCreateHeatingBillingMode(accountId, buildingId);
  const period = currentPeriod();
  const [mode, setMode] = useState<'LOKARA' | 'EXTERNAL_PROVIDER'>('LOKARA');
  const [periodFrom, setPeriodFrom] = useState(period.from);
  const [periodTo, setPeriodTo] = useState(period.to);
  const [provider, setProvider] = useState('');
  const [reference, setReference] = useState('');
  return (
    <div className="space-y-4 rounded-xl border border-mint bg-mint/20 p-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          label="Abrechnungsweg"
          value={mode}
          onChange={(value) => setMode(value as typeof mode)}
        >
          <option value="LOKARA">Mit Lokara abrechnen</option>
          <option value="EXTERNAL_PROVIDER">Durch Messdienstleister abrechnen</option>
        </SelectField>
        <InputField label="Zeitraum von" type="date" value={periodFrom} onChange={setPeriodFrom} />
        <InputField label="bis (exklusiv)" type="date" value={periodTo} onChange={setPeriodTo} />
        {mode === 'EXTERNAL_PROVIDER' ? (
          <InputField label="Messdienstleister" value={provider} onChange={setProvider} />
        ) : null}
        {mode === 'EXTERNAL_PROVIDER' ? (
          <InputField
            label="Vertrags-/Vorgangsnummer (optional)"
            value={reference}
            onChange={setReference}
          />
        ) : null}
      </div>
      <div className="flex gap-2">
        <Button
          disabled={
            !periodFrom ||
            !periodTo ||
            (mode === 'EXTERNAL_PROVIDER' && !provider.trim()) ||
            create.isPending
          }
          onClick={() =>
            create.mutate(
              {
                periodFrom,
                periodTo,
                mode,
                providerName: mode === 'EXTERNAL_PROVIDER' ? provider.trim() : null,
                providerReference: mode === 'EXTERNAL_PROVIDER' ? reference.trim() || null : null,
                externalStatus: mode === 'EXTERNAL_PROVIDER' ? 'BEAUFTRAGT' : null,
              },
              { onSuccess: onDone },
            )
          }
        >
          {create.isPending ? 'Wird gespeichert…' : 'Abrechnungsweg speichern'}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          Abbrechen
        </Button>
      </div>
      {create.isError ? (
        <StatusNote kind="danger" label="Speichern fehlgeschlagen.">
          {create.error instanceof ApiError && create.error.detail
            ? create.error.detail
            : 'Bitte erneut versuchen.'}
        </StatusNote>
      ) : null}
    </div>
  );
}

function ExternalBilling({
  accountId,
  buildingId,
  units,
  mode,
  canWrite,
}: {
  accountId: string;
  buildingId: string;
  units: WorkspaceUnit[];
  mode: NonNullable<ReturnType<typeof useHeatingBillingModes>['data']>[number];
  canWrite: boolean;
}) {
  return (
    <div className="space-y-5">
      <div
        className="inline-flex rounded-lg border border-mint bg-mint/30 p-1"
        aria-label="Übernahmeart"
      >
        <span className="rounded-md bg-paper px-4 py-2 text-sm font-semibold text-ink shadow-sm">
          Manuell erfassen
        </span>
        <button
          type="button"
          disabled
          className="cursor-not-allowed px-4 py-2 text-sm text-slate"
          tabIndex={-1}
        >
          Abrechnung automatisch übernehmen · Bald verfügbar
        </button>
      </div>
      <p className="max-w-3xl text-sm text-slate">
        Laden Sie künftig die Abrechnung Ihres Messdienstleisters hoch. Lokara erkennt Beträge,
        Zeiträume und Verbrauchsdaten und bereitet alles zur Prüfung für Sie vor.
      </p>
      {mode.externalStatus === 'UEBERNOMMEN' ? (
        <StatusNote kind="success" label="Externes Ergebnis übernommen.">
          Die bestätigte Messdienstleister-Abrechnung ist für diesen Zeitraum maßgeblich.
        </StatusNote>
      ) : canWrite ? (
        <ExternalResultForm
          accountId={accountId}
          buildingId={buildingId}
          units={units}
          mode={mode}
        />
      ) : (
        <StatusNote kind="warning" label="Ergebnis noch nicht übernommen.">
          Nur der Eigentümer kann die externe Abrechnung bestätigen.
        </StatusNote>
      )}
    </div>
  );
}

function ExternalResultForm({
  accountId,
  buildingId,
  units,
  mode,
}: {
  accountId: string;
  buildingId: string;
  units: WorkspaceUnit[];
  mode: NonNullable<ReturnType<typeof useHeatingBillingModes>['data']>[number];
}) {
  const confirm = useConfirmMdlStatement(accountId, buildingId);
  const adopt = useCreateHeatingBillingMode(accountId, buildingId);
  const [branch, setBranch] = useState<'NET' | 'GROSS'>('NET');
  const [total, setTotal] = useState('');
  const [owner, setOwner] = useState('');
  const [source, setSource] = useState(mode.providerReference ?? '');
  const [co2Kg, setCo2Kg] = useState('');
  const [co2Cost, setCo2Cost] = useState('');
  const [heatedArea, setHeatedArea] = useState('');
  const tenancies = units.flatMap((unit) =>
    unit.tenancies.map((tenancy) => ({ ...tenancy, unitLabel: unit.label })),
  );
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const periodToInclusive = new Date(`${mode.periodTo}T12:00:00`);
  periodToInclusive.setDate(periodToInclusive.getDate() - 1);
  const inclusive = `${periodToInclusive.getFullYear()}-${String(periodToInclusive.getMonth() + 1).padStart(2, '0')}-${String(periodToInclusive.getDate()).padStart(2, '0')}`;

  function submit() {
    const confirmedTotalCents = parseEurToCents(total);
    const ownerPositionCents = parseEurToCents(owner);
    const positions = tenancies
      .map((tenancy) => ({
        tenancyId: tenancy.id,
        amountCents: parseEurToCents(amounts[tenancy.id] ?? ''),
      }))
      .filter(
        (position): position is { tenancyId: string; amountCents: number } =>
          position.amountCents !== null,
      );
    if (
      confirmedTotalCents === null ||
      ownerPositionCents === null ||
      positions.length === 0 ||
      !source.trim()
    )
      return;
    confirm.mutate(
      {
        branch,
        periodFrom: mode.periodFrom,
        periodTo: inclusive,
        confirmedTotalCents,
        ownerPositionCents,
        positions,
        sourceRef: source.trim(),
        co2KgX1000: branch === 'GROSS' ? parseMeterValueToX1000(co2Kg) : null,
        co2CostCents: branch === 'GROSS' ? parseEurToCents(co2Cost) : null,
        heatedAreaSqmX100:
          branch === 'GROSS' ? Math.round(Number(heatedArea.replace(',', '.')) * 100) : null,
        co2EvidencePresent: true,
      },
      {
        onSuccess: (statement) =>
          adopt.mutate({
            periodFrom: mode.periodFrom,
            periodTo: mode.periodTo,
            mode: 'EXTERNAL_PROVIDER',
            providerName: mode.providerName,
            providerReference: mode.providerReference,
            externalStatus: 'UEBERNOMMEN',
            mdlStatementId: statement.id,
          }),
      },
    );
  }

  return (
    <div className="space-y-4 rounded-xl border border-mint p-4">
      <h4 className="font-display font-bold">Externes Ergebnis prüfen und übernehmen</h4>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          label="Dokumentart"
          value={branch}
          onChange={(value) => setBranch(value as typeof branch)}
        >
          <option value="NET">Netto – Vermieteranteil bereits abgezogen</option>
          <option value="GROSS">Brutto – CO₂-Aufteilung durch Lokara</option>
        </SelectField>
        <InputField label="Gesamtergebnis in €" value={total} onChange={setTotal} />
        <InputField label="Eigentümerposition in €" value={owner} onChange={setOwner} />
        <InputField label="Quelle/Referenz" value={source} onChange={setSource} />
        {branch === 'GROSS' ? (
          <>
            <InputField label="CO₂-Menge in kg" value={co2Kg} onChange={setCo2Kg} />
            <InputField label="CO₂-Kosten in €" value={co2Cost} onChange={setCo2Cost} />
            <InputField label="Beheizte Fläche in m²" value={heatedArea} onChange={setHeatedArea} />
          </>
        ) : null}
      </div>
      <div className="space-y-3">
        <p className="text-sm font-semibold text-ink">Einheiten-/Mietverhältniszuordnung</p>
        {tenancies.map((tenancy) => (
          <InputField
            key={tenancy.id}
            label={`${tenancy.unitLabel} · ${tenancy.label} (€)`}
            value={amounts[tenancy.id] ?? ''}
            onChange={(value) => setAmounts((current) => ({ ...current, [tenancy.id]: value }))}
          />
        ))}
      </div>
      <Button disabled={confirm.isPending || adopt.isPending} onClick={submit}>
        {confirm.isPending || adopt.isPending
          ? 'Wird geprüft…'
          : 'Prüfen und verbindlich übernehmen'}
      </Button>
      {confirm.isError || adopt.isError ? (
        <StatusNote kind="danger" label="Übernahme nicht möglich.">
          {(confirm.error instanceof ApiError && confirm.error.detail) ||
            (adopt.error instanceof ApiError && adopt.error.detail) ||
            'Bitte Kontrollsumme und Zuordnung prüfen.'}
        </StatusNote>
      ) : null}
    </div>
  );
}

function HeatingCostRow({
  accountId,
  buildingId,
  cost,
  canWrite,
}: {
  accountId: string;
  buildingId: string;
  cost: NonNullable<ReturnType<typeof useHeatingCosts>['data']>['heatingCosts'][number];
  canWrite: boolean;
}) {
  const [reason, setReason] = useState('');
  const [confirming, setConfirming] = useState(false);
  const voidCost = useVoidHeatingCost(accountId, buildingId);
  return (
    <tr className={cost.voidedAt ? 'text-slate line-through' : ''}>
      <td className="px-4 py-3">
        <span className="font-semibold">{CATEGORY_LABELS[cost.category]}</span>
        <span className="block text-xs text-slate">{cost.label}</span>
      </td>
      <td className="px-4 py-3 text-right tabular-nums">{cost.amountEur}</td>
      <td className="px-4 py-3">
        {isoToGermanDate(cost.periodFrom)} – {isoToGermanDate(cost.periodTo)}
      </td>
      <td className="px-4 py-3">{cost.sourceRef ?? 'Fehlt'}</td>
      <td className="px-4 py-3">
        {cost.voidedAt ? (
          `Storniert · ${cost.voidReason}`
        ) : confirming ? (
          <div className="flex min-w-52 gap-2">
            <input
              aria-label="Stornogrund"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="min-w-0 rounded border border-mint px-2"
            />
            <Button
              size="sm"
              disabled={!reason.trim() || voidCost.isPending}
              onClick={() => voidCost.mutate({ heatingCostId: cost.id, reason: reason.trim() })}
            >
              Stornieren
            </Button>
          </div>
        ) : canWrite ? (
          <Button variant="ghost" size="sm" onClick={() => setConfirming(true)}>
            Stornieren
          </Button>
        ) : (
          'Aktiv'
        )}
      </td>
    </tr>
  );
}

function HeatingCostForm({
  accountId,
  buildingId,
  onDone,
}: {
  accountId: string;
  buildingId: string;
  onDone: () => void;
}) {
  const create = useCreateHeatingCost(accountId, buildingId);
  const period = currentPeriod();
  const [category, setCategory] =
    useState<(typeof HEATING_COST_CATEGORIES)[number]>('FUEL_OR_HEAT_SUPPLY');
  const [label, setLabel] = useState('');
  const [amount, setAmount] = useState('');
  const [from, setFrom] = useState(period.from);
  const [to, setTo] = useState(period.to);
  const [source, setSource] = useState('');
  const [co2Kg, setCo2Kg] = useState('');
  const [co2Cost, setCo2Cost] = useState('');
  const submit = () => {
    const amountCents = parseEurToCents(amount);
    if (amountCents === null || !label.trim() || !source.trim()) return;
    create.mutate(
      {
        category,
        label: label.trim(),
        amountCents,
        periodFrom: from,
        periodTo: to,
        sourceRef: source.trim(),
        co2KgX1000: co2Kg ? parseMeterValueToX1000(co2Kg) : null,
        co2CostCents: co2Cost ? parseEurToCents(co2Cost) : null,
      },
      { onSuccess: onDone },
    );
  };
  return (
    <div className="space-y-4 rounded-xl border border-mint bg-mint/20 p-4">
      <h4 className="font-display font-bold">Heizkostenposition erfassen</h4>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          label="Kategorie"
          value={category}
          onChange={(value) => setCategory(value as typeof category)}
        >
          {HEATING_COST_CATEGORIES.map((value) => (
            <option key={value} value={value}>
              {CATEGORY_LABELS[value]}
            </option>
          ))}
        </SelectField>
        <InputField label="Position" value={label} onChange={setLabel} />
        <InputField label="Betrag in €" value={amount} onChange={setAmount} />
        <InputField label="Beleg-/Quellenreferenz" value={source} onChange={setSource} />
        <InputField label="Leistungszeitraum von" type="date" value={from} onChange={setFrom} />
        <InputField label="bis (exklusiv)" type="date" value={to} onChange={setTo} />
        {category === 'FUEL_OR_HEAT_SUPPLY' ? (
          <>
            <InputField label="CO₂-Menge in kg" value={co2Kg} onChange={setCo2Kg} />
            <InputField label="CO₂-Kosten in €" value={co2Cost} onChange={setCo2Cost} />
          </>
        ) : null}
      </div>
      <div className="flex gap-2">
        <Button disabled={create.isPending} onClick={submit}>
          {create.isPending ? 'Wird erfasst…' : 'Position erfassen'}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          Abbrechen
        </Button>
      </div>
      {create.isError ? (
        <StatusNote kind="danger" label="Erfassen fehlgeschlagen.">
          {create.error instanceof ApiError && create.error.detail
            ? create.error.detail
            : 'Bitte Eingaben prüfen.'}
        </StatusNote>
      ) : null}
    </div>
  );
}

function InputField({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
      {label}
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-lg border border-mint bg-paper px-3 py-2 font-normal"
      />
    </label>
  );
}
function SelectField({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-semibold text-ink">
      {label}
      <Select value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </Select>
    </label>
  );
}
