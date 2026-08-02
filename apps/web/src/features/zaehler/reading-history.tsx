'use client';

import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';

import type { MeterOut } from '@/lib/contracts';
import { READING_REASON_LABELS, READING_SOURCE_LABELS } from '@/lib/contracts';
import { isoToGermanDate } from '@/lib/format';

/**
 * The append-only log, shown as one. Superseded rows stay visible and struck
 * through rather than disappearing: that a wrong value was entered and then
 * corrected is part of the record, and hiding it would defeat the point of
 * never updating in place.
 */
export function ReadingHistory({ meter }: { meter: MeterOut }) {
  if (meter.readings.length === 0) {
    return (
      <p className="text-sm text-slate">
        Noch keine Ablesungen. Für einen Verbrauch werden zwei benötigt: Anfangs- und Endstand.
      </p>
    );
  }
  return (
    <Table>
      <TableCaption>
        Alle Ablesungen dieses Zählers, neueste zuerst. Durchgestrichene Werte wurden durch eine
        spätere Ablesung desselben Datums abgelöst — gelöscht wird nichts.
      </TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead>Datum</TableHead>
          <TableHead className="text-right">Zählerstand</TableHead>
          <TableHead>Grund</TableHead>
          <TableHead>Quelle</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {meter.readings.map((reading) => (
          <TableRow key={reading.id}>
            <TableCell className="tabular-nums">{isoToGermanDate(reading.readAt)}</TableCell>
            <TableCell
              className={`text-right font-semibold tabular-nums ${
                reading.superseded ? 'text-slate line-through' : ''
              }`}
            >
              {reading.valueDisplay} {meter.unitSymbol}
            </TableCell>
            <TableCell className="text-sm">
              {READING_REASON_LABELS[reading.reason]}
              {reading.note ? (
                <span className="block text-xs text-slate">{reading.note}</span>
              ) : null}
            </TableCell>
            <TableCell className="text-sm text-slate">
              {READING_SOURCE_LABELS[reading.source]}
            </TableCell>
            <TableCell className="text-sm">
              {/* The word carries the state; the strikethrough above only
                  reinforces it (never colour or styling alone). */}
              {reading.superseded ? (
                <span className="text-slate">Abgelöst</span>
              ) : (
                <span className="font-medium text-success">Gültig</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
