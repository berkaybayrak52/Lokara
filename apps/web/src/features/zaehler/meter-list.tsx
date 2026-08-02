'use client';

import { Button, Card, CardContent, CardHeader, CardTitle } from '@lokara/ui';
import { useState } from 'react';

import type { MeterOut } from '@/lib/contracts';
import { isoToGermanDate } from '@/lib/format';

import { CalibrationBadge } from './calibration-badge';
import { CreateReadingForm } from './create-reading-form';
import { ReadingHistory } from './reading-history';
import { useDeleteMeter } from './queries';

/** One card per meter: what it is, whether it is still geeicht, what it
 *  consumed in the period, and its full reading history. */
export function MeterList({
  accountId,
  buildingId,
  meters,
  periodLabel,
}: {
  accountId: string;
  buildingId: string;
  meters: MeterOut[];
  periodLabel: string;
}) {
  return (
    <div className="flex flex-col gap-4">
      {meters.map((meter) => (
        <MeterCard
          key={meter.id}
          meter={meter}
          accountId={accountId}
          buildingId={buildingId}
          periodLabel={periodLabel}
        />
      ))}
    </div>
  );
}

function MeterCard({
  meter,
  accountId,
  buildingId,
  periodLabel,
}: {
  meter: MeterOut;
  accountId: string;
  buildingId: string;
  periodLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const remove = useDeleteMeter(accountId, buildingId);
  const location = meter.unitLabel ?? 'Gebäude (Hauptzähler)';

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">
              {meter.kindLabel} · {location}
            </CardTitle>
            <p className="mt-1 text-sm text-slate">
              Nr. {meter.serial}
              {meter.label ? ` · ${meter.label}` : ''} · Zählt in {meter.unitSymbol}
            </p>
          </div>
          <CalibrationBadge
            status={meter.calibrationStatus}
            validUntil={meter.calibrationValidUntil}
          />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div>
            <dt className="text-slate">Verbrauch {periodLabel}</dt>
            <dd className="font-semibold tabular-nums">
              {meter.periodConsumptionDisplay ?? (
                // Not a zero: a missing pair means the heating engine estimates
                // this unit per § 9a, and saying "0" would be a lie.
                <span className="font-medium text-warning">
                  Kein vollständiges Ablesepaar — Schätzung nach § 9a
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-slate">Ablesungen</dt>
            <dd className="font-semibold tabular-nums">{meter.readings.length}</dd>
          </div>
          {meter.calibrationValidUntil ? (
            <div>
              <dt className="text-slate">Eichfrist bis</dt>
              <dd className="font-semibold tabular-nums">
                {isoToGermanDate(meter.calibrationValidUntil)}
              </dd>
            </div>
          ) : null}
        </dl>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            aria-expanded={open}
            aria-controls={`readings-${meter.id}`}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? 'Ablesungen ausblenden' : 'Ablesungen & Erfassung'}
          </Button>
          {confirmingDelete ? (
            <span className="flex items-center gap-2">
              <span className="text-xs font-medium text-danger">
                Zähler und alle Ablesungen löschen?
              </span>
              <Button
                variant="destructive"
                size="sm"
                disabled={remove.isPending}
                onClick={() => remove.mutate(meter.id)}
              >
                {remove.isPending ? 'Löscht…' : 'Löschen'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirmingDelete(false)}>
                Abbrechen
              </Button>
            </span>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="text-danger hover:bg-danger-tint"
              onClick={() => setConfirmingDelete(true)}
            >
              Zähler löschen
            </Button>
          )}
        </div>

        <div id={`readings-${meter.id}`} hidden={!open}>
          {open ? (
            <div className="flex flex-col gap-5 border-t border-mint pt-5">
              <CreateReadingForm accountId={accountId} buildingId={buildingId} meter={meter} />
              <ReadingHistory meter={meter} />
            </div>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
