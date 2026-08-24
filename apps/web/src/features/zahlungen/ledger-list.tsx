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

import type { PaymentLedgerEntry, ReceivableOut } from '@/lib/contracts';
import { centsToEurDisplay, isoToGermanDate } from '@/lib/format';

import { periodToGerman } from './proposal-view';

/**
 * The Zahlungsjournal (docs/15 § 5) — read-only by design.
 *
 * Every entry is an immutable record of what was actually booked, so there is
 * no edit, no delete and no reversal control here. A correction is a new entry
 * written by the server, never a rewrite of an old one.
 *
 * The allocation order shown per entry is § 367 BGB (Kosten, Zinsen,
 * Hauptforderung). That is statutory and independent of the § 4 matching
 * points, which never influence how a confirmed amount is applied.
 */

const KIND_LABELS: Record<PaymentLedgerEntry['kind'], string> = {
  payment: 'Zahlung',
  reversal: 'Storno',
};

const STATUS_LABELS: Record<string, string> = {
  open: 'offen',
  partial: 'teilweise ausgeglichen',
  settled: 'ausgeglichen',
};

const CATEGORY_LABELS: Record<string, string> = {
  rent: 'Miete',
  nk_nachzahlung: 'Nachzahlung Betriebskosten',
};

/**
 * Which Forderung an amount settled — § 259 BGB evidence needs the debt named,
 * not just the sum. The allocation carries `receivable_id`; the receivable list
 * is already loaded for the review half of the screen, so the name is a join,
 * never a second request and never an invented label. No renter is named: no
 * route resolves `renter_id` to a legal name.
 */
function receivableLabel(receivable: ReceivableOut | undefined): string | null {
  if (receivable === undefined) return null;
  const category = CATEGORY_LABELS[receivable.category.toLowerCase()] ?? receivable.category;
  return `${category} ${periodToGerman(receivable.period)}`;
}

export function LedgerList({
  entries,
  receivables,
}: {
  entries: PaymentLedgerEntry[];
  receivables: ReceivableOut[];
}) {
  const receivableById = new Map(receivables.map((row) => [row.id, row]));

  return (
    <Table>
      {/* sr-only; the visible version of the „Erfasst am“ caveat sits in the
          section description, so it is not read out twice. */}
      <TableCaption>
        Zahlungsjournal: alle gebuchten Zahlungen und Stornos, neueste zuerst.
      </TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">Erfasst am</TableHead>
          <TableHead scope="col">Art</TableHead>
          <TableHead scope="col" className="text-right">
            Betrag
          </TableHead>
          <TableHead scope="col">Verrechnung</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => (
          <TableRow key={entry.id}>
            <TableCell className="align-top text-sm tabular-nums">
              {isoToGermanDate(entry.created_at.slice(0, 10))}
            </TableCell>
            <TableCell className="align-top text-sm">
              <span className="font-semibold">{KIND_LABELS[entry.kind]}</span>
              {entry.reverses_entry_id ? (
                <span className="block text-slate">Storniert eine frühere Buchung.</span>
              ) : null}
            </TableCell>
            <TableCell className="align-top text-right text-sm font-semibold tabular-nums">
              {centsToEurDisplay(entry.amount_cents)}
              {entry.credit_cents > 0 ? (
                <span className="block font-medium text-slate">
                  davon {centsToEurDisplay(entry.credit_cents)} Guthaben (keine Auszahlung)
                </span>
              ) : null}
            </TableCell>
            <TableCell className="align-top text-sm">
              {entry.allocations.length === 0 ? (
                <span className="text-slate">Keine Forderung verrechnet.</span>
              ) : (
                <ul className="flex flex-col gap-2">
                  {entry.allocations.map((allocation) => (
                    <li key={allocation.id}>
                      <span className="block font-semibold">
                        {receivableLabel(receivableById.get(allocation.receivable_id)) ??
                          'Forderung nicht in dieser Liste'}
                      </span>
                      <span className="tabular-nums">
                        Kosten {centsToEurDisplay(allocation.costs_cents)} · Zinsen{' '}
                        {centsToEurDisplay(allocation.interest_cents)} · Hauptforderung{' '}
                        {centsToEurDisplay(allocation.principal_cents)}
                      </span>
                      <span className="block text-slate tabular-nums">
                        Offen {centsToEurDisplay(allocation.before.open_cents)} →{' '}
                        {centsToEurDisplay(allocation.after.open_cents)} ·{' '}
                        {STATUS_LABELS[allocation.resulting_status.toLowerCase()] ??
                          allocation.resulting_status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
