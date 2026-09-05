'use client';

import { Button, Select, StatusNote } from '@lokara/ui';
import { useEffect, useMemo, useRef, useState } from 'react';

import type { MeterOut } from '@/lib/contracts';
import { isoToGermanDate } from '@/lib/format';

import { CalibrationBadge } from './calibration-badge';
import { CreateReadingForm } from './create-reading-form';
import { ReadingHistory } from './reading-history';
import { useEndMeter } from './queries';

const REMOTE_LABEL = {
  REMOTE_READABLE: 'Fernablesbar',
  NOT_REMOTE_READABLE: 'Nicht fernablesbar',
  UNKNOWN: 'Fernablesbarkeit unbekannt',
} as const;

export function MeterList({
  accountId,
  buildingId,
  meters,
  periodLabel,
  canWrite,
  focusMeterId,
}: {
  accountId: string;
  buildingId: string;
  meters: MeterOut[];
  periodLabel: string;
  canWrite: boolean;
  focusMeterId?: string | null;
}) {
  return (
    <div className="divide-y divide-mint rounded-xl border border-mint bg-paper">
      {meters.map((meter) => (
        <MeterRow
          key={meter.id}
          accountId={accountId}
          buildingId={buildingId}
          meter={meter}
          periodLabel={periodLabel}
          canWrite={canWrite}
          focusRequested={focusMeterId === meter.id}
        />
      ))}
    </div>
  );
}

function MeterRow({
  accountId,
  buildingId,
  meter,
  periodLabel,
  canWrite,
  focusRequested,
}: {
  accountId: string;
  buildingId: string;
  meter: MeterOut;
  periodLabel: string;
  canWrite: boolean;
  focusRequested: boolean;
}) {
  const [open, setOpen] = useState(focusRequested);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!focusRequested) return;
    setOpen(true);
    requestAnimationFrame(() => {
      buttonRef.current?.focus();
      buttonRef.current?.scrollIntoView({
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
        block: 'center',
      });
    });
  }, [focusRequested]);

  return (
    <article
      id={`meter-${meter.id}`}
      className={meter.lifecycleStatus === 'ACTIVE' ? '' : 'bg-mint/20'}
    >
      <button
        ref={buttonRef}
        type="button"
        className="flex w-full items-start justify-between gap-4 px-4 py-4 text-left outline-none transition hover:bg-mint/30 focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-inset"
        aria-expanded={open}
        aria-controls={`meter-details-${meter.id}`}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-display font-bold text-ink">{meter.deviceTypeLabel}</span>
            {meter.lifecycleStatus !== 'ACTIVE' ? (
              <span className="rounded-full bg-mint px-2 py-0.5 text-xs font-semibold text-forest">
                {meter.lifecycleStatus === 'REPLACED'
                  ? 'Ersetzt'
                  : meter.lifecycleStatus === 'REMOVED'
                    ? 'Ausgebaut'
                    : 'Storniert'}
              </span>
            ) : null}
          </span>
          <span className="mt-1 block text-sm text-slate">
            {[meter.label, meter.location].filter(Boolean).join(' · ')}
            {meter.label || meter.location ? ' · ' : ''}Nr. {meter.serial} ·{' '}
            {meter.readings.find((reading) => !reading.superseded)
              ? `letzter Stand ${meter.readings.find((reading) => !reading.superseded)?.valueDisplay} ${meter.unitSymbol}`
              : 'noch keine Ablesung'}
          </span>
          <span className="mt-1 block text-xs text-slate">
            {REMOTE_LABEL[meter.remoteReadability]}
          </span>
        </span>
        <span className="flex shrink-0 flex-col items-end gap-2">
          <CalibrationBadge
            status={meter.calibrationStatus}
            validUntil={meter.calibrationValidUntil}
          />
          <span aria-hidden="true" className="text-lg text-slate">
            {open ? '−' : '+'}
          </span>
        </span>
      </button>
      <div id={`meter-details-${meter.id}`} hidden={!open}>
        {open ? (
          <div className="space-y-6 border-t border-mint px-4 py-5">
            <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <Fact label="Einbaudatum" value={isoToGermanDate(meter.installedOn)} />
              <Fact label="Maßeinheit" value={meter.unitSymbol} />
              <Fact label="Einbauort/Raum" value={meter.location ?? 'Nicht erfasst'} />
              <Fact
                label="Hersteller / Modell"
                value={
                  [meter.manufacturer, meter.model].filter(Boolean).join(' · ') || 'Nicht erfasst'
                }
              />
            </dl>
            <ConsumptionSummary meter={meter} fallbackPeriodLabel={periodLabel} />
            {meter.remoteReadability === 'REMOTE_READABLE' ? (
              <StatusNote kind="success" label="Fernablesbares Gerät.">
                Die automatische Übertragung von Funkablesungen an Lokara ist für eine spätere
                Version vorgesehen. Ablesungen werden derzeit manuell erfasst.
              </StatusNote>
            ) : null}
            {meter.calibrationMessage ? (
              <p className="text-sm text-slate">
                {meter.calibrationMessage}
                {meter.calibrationRechtsstand ? ` · ${meter.calibrationRechtsstand}` : ''}
              </p>
            ) : null}
            {canWrite && meter.lifecycleStatus === 'ACTIVE' ? (
              <CreateReadingForm accountId={accountId} buildingId={buildingId} meter={meter} />
            ) : null}
            <ReadingHistory meter={meter} />
            {meter.lifecycleEvents.length > 1 ? (
              <div>
                <h3 className="font-display text-sm font-bold">Geräteverlauf</h3>
                <ul className="mt-2 space-y-1 text-sm text-slate">
                  {meter.lifecycleEvents.map((event) => (
                    <li key={event.id}>
                      {isoToGermanDate(event.effectiveOn)} ·{' '}
                      {event.eventType === 'INSTALLED'
                        ? 'Eingebaut'
                        : event.eventType === 'REPLACED'
                          ? 'Ersetzt'
                          : event.eventType === 'REMOVED'
                            ? 'Ausgebaut'
                            : 'Storniert'}
                      {event.reason ? ` · ${event.reason}` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {canWrite && meter.lifecycleStatus === 'ACTIVE' ? (
              <LifecycleActions accountId={accountId} buildingId={buildingId} meter={meter} />
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function ConsumptionSummary({
  meter,
  fallbackPeriodLabel,
}: {
  meter: MeterOut;
  fallbackPeriodLabel: string;
}) {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const periods = meter.consumptionPeriods;
  const selected = useMemo(
    () =>
      periods.find((period) => `${period.periodFrom}:${period.periodTo}` === selectedKey) ??
      periods[0],
    [periods, selectedKey],
  );

  if (!selected) {
    return (
      <StatusNote kind="warning" label={`Verbrauch ${fallbackPeriodLabel}`}>
        Für diesen Zähler ist noch kein Abrechnungszeitraum verfügbar.
      </StatusNote>
    );
  }

  const statusLabel =
    selected.status === 'MEASURED'
      ? 'Gemessen'
      : selected.status === 'ESTIMATED'
        ? 'Geschätzt'
        : selected.status === 'NOT_APPLICABLE'
          ? 'Nicht anwendbar'
          : 'Unvollständig';

  return (
    <section className="rounded-xl border border-mint bg-mint/20 p-4" aria-label="Verbrauch">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="font-display text-sm font-bold text-ink">Verbrauchsentwicklung</h3>
          <p className="mt-1 text-xs text-slate">{statusLabel} · serverseitig projiziert</p>
        </div>
        <label className="text-sm font-semibold text-ink">
          Abrechnungszeitraum
          <Select
            className="mt-1 min-w-64"
            value={`${selected.periodFrom}:${selected.periodTo}`}
            onChange={(event) => setSelectedKey(event.target.value)}
          >
            {periods.map((period) => (
              <option
                key={`${period.periodFrom}:${period.periodTo}`}
                value={`${period.periodFrom}:${period.periodTo}`}
              >
                {period.periodLabel}
              </option>
            ))}
          </Select>
        </label>
      </div>
      <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
        <Fact
          label="Anfangsablesung"
          value={
            selected.openingReading
              ? `${selected.openingReading.valueDisplay} ${meter.unitSymbol} · ${isoToGermanDate(selected.openingReading.readAt)}`
              : 'Fehlt'
          }
        />
        <Fact
          label="Endablesung"
          value={
            selected.closingReading
              ? `${selected.closingReading.valueDisplay} ${meter.unitSymbol} · ${isoToGermanDate(selected.closingReading.readAt)}`
              : 'Fehlt'
          }
        />
        <Fact
          label={selected.status === 'ESTIMATED' ? 'Geschätzter Verbrauch' : 'Differenz'}
          value={selected.consumptionDisplay ?? 'Nicht verfügbar'}
        />
      </dl>
      {selected.finding ? <p className="mt-3 text-sm text-slate">{selected.finding}</p> : null}
      {selected.estimationBasis ? (
        <p className="mt-1 text-sm text-slate">
          Grundlage: {selected.estimationBasis}
          {selected.provenanceRef ? ` · Quelle: ${selected.provenanceRef}` : ''}
        </p>
      ) : null}
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate">{label}</dt>
      <dd className="mt-1 font-semibold text-ink">{value}</dd>
    </div>
  );
}

function LifecycleActions({
  accountId,
  buildingId,
  meter,
}: {
  accountId: string;
  buildingId: string;
  meter: MeterOut;
}) {
  const [action, setAction] = useState<'remove' | 'void' | null>(null);
  const [effectiveOn, setEffectiveOn] = useState(new Date().toISOString().slice(0, 10));
  const [reason, setReason] = useState('');
  const remove = useEndMeter(accountId, buildingId, 'remove');
  const voidMeter = useEndMeter(accountId, buildingId, 'void');
  const mutation = action === 'void' ? voidMeter : remove;

  if (action === null) {
    return (
      <div className="flex flex-wrap gap-2 border-t border-mint pt-4">
        <Button variant="outline" size="sm" onClick={() => setAction('remove')}>
          Zähler ausbauen
        </Button>
        {meter.readings.length === 0 ? (
          <Button variant="ghost" size="sm" onClick={() => setAction('void')}>
            Falsch angelegt – stornieren
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-mint bg-mint/20 p-4">
      <h3 className="font-display text-sm font-bold">
        {action === 'remove' ? 'Zähler ausbauen' : 'Zähler stornieren'}
      </h3>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-semibold text-ink">
          Datum
          <input
            type="date"
            value={effectiveOn}
            onChange={(event) => setEffectiveOn(event.target.value)}
            className="mt-1 w-full rounded-lg border border-mint bg-paper px-3 py-2"
          />
        </label>
        <label className="text-sm font-semibold text-ink">
          Begründung
          <input
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className="mt-1 w-full rounded-lg border border-mint bg-paper px-3 py-2"
          />
        </label>
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          disabled={!effectiveOn || !reason.trim() || mutation.isPending}
          onClick={() =>
            mutation.mutate(
              { meterId: meter.id, effectiveOn, reason: reason.trim() },
              { onSuccess: () => setAction(null) },
            )
          }
        >
          {mutation.isPending ? 'Wird gespeichert…' : 'Verbindlich speichern'}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setAction(null)}>
          Abbrechen
        </Button>
      </div>
      {mutation.isError ? (
        <StatusNote kind="danger" label="Aktion nicht möglich.">
          {mutation.error instanceof Error ? mutation.error.message : 'Bitte erneut versuchen.'}
        </StatusNote>
      ) : null}
    </div>
  );
}
