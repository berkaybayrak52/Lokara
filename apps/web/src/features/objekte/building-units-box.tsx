'use client';

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';
import Link from 'next/link';
import { useState } from 'react';

import type { BuildingDashboardResponse, BuildingDashboardUnit } from '@/lib/contracts';

type Filter = 'ALL' | 'RENTED' | 'VACANT' | 'SELF_USE' | 'OPEN_BALANCE';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'ALL', label: 'Alle' },
  { key: 'RENTED', label: 'Vermietet' },
  { key: 'VACANT', label: 'Leerstand' },
  { key: 'SELF_USE', label: 'Eigennutzung' },
  { key: 'OPEN_BALANCE', label: 'Mit offenem Saldo' },
];

function matches(unit: BuildingDashboardUnit, filter: Filter): boolean {
  switch (filter) {
    case 'ALL':
      return true;
    case 'RENTED':
      return unit.state === 'RENTED';
    case 'VACANT':
      return unit.state === 'VACANT';
    case 'SELF_USE':
      return unit.state === 'SELF_USE' || unit.state === 'GRATUITOUS';
    case 'OPEN_BALANCE':
      return unit.balance?.status === 'OPEN';
  }
}

/**
 * The central Einheiten box (OD8). Filters only hide server-delivered rows —
 * they never re-derive a state, and the row values are printed as received.
 */
export function BuildingUnitsBox({
  accountId,
  dashboard,
}: {
  accountId: string;
  dashboard: BuildingDashboardResponse;
}) {
  const [filter, setFilter] = useState<Filter>('ALL');
  const visible = dashboard.units.filter((unit) => matches(unit, filter));

  if (dashboard.units.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Noch keine Einheiten</CardTitle>
          <CardDescription>
            Legen Sie die erste Einheit über „Einheit anlegen“ an — Mietverhältnisse folgen auf der
            Einheitenseite.
          </CardDescription>
        </CardHeader>
        {dashboard.permissions.canCreateUnit ? (
          <CardContent>
            <Button asChild>
              <Link href={`/a/${accountId}/objekte/${dashboard.id}/einheit/neu`}>
                Einheit anlegen
              </Link>
            </Button>
          </CardContent>
        ) : null}
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <CardTitle>Einheiten</CardTitle>
            <CardDescription>
              {visible.length} von {dashboard.units.length} angezeigt
            </CardDescription>
          </div>
          {dashboard.permissions.canCreateUnit ? (
            <Button asChild>
              <Link href={`/a/${accountId}/objekte/${dashboard.id}/einheit/neu`}>
                Einheit anlegen
              </Link>
            </Button>
          ) : null}
        </div>
        <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Einheiten filtern">
          {FILTERS.map((option) => (
            <button
              key={option.key}
              type="button"
              aria-pressed={filter === option.key}
              onClick={() => setFilter(option.key)}
              className={
                filter === option.key
                  ? 'rounded-md border border-green bg-mint px-3 py-1.5 text-sm font-semibold text-forest transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none'
                  : 'rounded-md border border-slate/40 px-3 py-1.5 text-sm text-ink transition-colors duration-200 hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none'
              }
            >
              {option.label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Einheit</TableHead>
              <TableHead>Zustand</TableHead>
              <TableHead>Mietpartei</TableHead>
              <TableHead className="text-right">Fläche</TableHead>
              <TableHead className="text-right">Kaltmiete</TableHead>
              <TableHead className="text-right">Saldo</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.map((unit) => (
              <TableRow key={unit.id}>
                <TableCell>
                  <Link
                    href={`/a/${accountId}/einheiten/${unit.id}`}
                    className="font-semibold text-green underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  >
                    {unit.label}
                  </Link>
                </TableCell>
                <TableCell>
                  <span className="text-ink">{unit.stateLabel}</span>
                  {unit.nextEvent ? (
                    <span className="block text-xs text-slate">{unit.nextEvent.label}</span>
                  ) : null}
                  {unit.hasTenancyOverlap ? (
                    <span className="block text-xs text-danger">
                      Überschneidende Mietverhältnisse
                    </span>
                  ) : null}
                </TableCell>
                <TableCell className="text-slate">
                  {unit.partyNames.length > 0 ? unit.partyNames.join(', ') : '–'}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {unit.areaSqm.toLocaleString('de-DE')} m²
                </TableCell>
                <TableCell className="text-right tabular-nums">{unit.coldRentEur ?? '–'}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {unit.balance ? unit.balance.label : '–'}
                </TableCell>
              </TableRow>
            ))}
            {visible.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-slate">
                  Keine Einheit entspricht diesem Filter.
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
