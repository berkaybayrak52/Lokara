'use client';

import {
  Button,
  Card,
  CardContent,
  Select,
  StatusNote,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { PageHeader } from '@/features/portal/page-header';

import { useStatementRecords } from './queries';

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Entwurf',
  REVIEW_REQUIRED: 'Prüfung erforderlich',
  READY: 'Bereit',
  FINALIZED: 'Finalisiert',
  KORRIGIERT: 'Korrigiert',
};

function date(value: string): string {
  return new Intl.DateTimeFormat('de-DE').format(new Date(`${value}T12:00:00`));
}

function dateTime(value: string): string {
  return new Intl.DateTimeFormat('de-DE', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function StatementListPage({ accountId }: { accountId: string }) {
  const records = useStatementRecords(accountId);
  const [filter, setFilter] = useState('ALL');
  const visible = useMemo(
    () =>
      (records.data ?? []).filter((record) => (filter === 'ALL' ? true : record.status === filter)),
    [filter, records.data],
  );

  return (
    <main className="py-10">
      <PageHeader
        title="Abrechnungen"
        description="Betriebs- und Heizkostenabrechnungen vorbereiten, prüfen und abschließen."
        actions={
          <Button asChild>
            <Link href={`/a/${accountId}/abrechnung/neu`}>Abrechnung erstellen</Link>
          </Button>
        }
      />

      {records.isPending ? (
        <div className="h-72 animate-pulse rounded-2xl bg-mint/50 motion-reduce:animate-none" />
      ) : records.isError ? (
        <StatusNote kind="danger" label="Abrechnungen konnten nicht geladen werden.">
          Laden Sie die Seite neu oder versuchen Sie es später erneut.
        </StatusNote>
      ) : records.data?.length === 0 ? (
        <Card className="max-w-2xl">
          <CardContent className="flex flex-col items-start gap-4 py-10">
            <div>
              <h2 className="font-display text-xl font-semibold">Noch keine Abrechnung</h2>
              <p className="mt-1 text-sm text-slate">
                Beginnen Sie mit Objekt und Abrechnungszeitraum. Der Entwurf bleibt gespeichert.
              </p>
            </div>
            <Button asChild>
              <Link href={`/a/${accountId}/abrechnung/neu`}>Erste Abrechnung erstellen</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="space-y-5 py-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-slate">{visible.length} Abrechnungen</p>
              <Select
                aria-label="Abrechnungen nach Status filtern"
                className="w-56"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
              >
                <option value="ALL">Alle Status</option>
                <option value="DRAFT">Entwurf</option>
                <option value="REVIEW_REQUIRED">Prüfung erforderlich</option>
                <option value="READY">Bereit</option>
                <option value="FINALIZED">Finalisiert</option>
                <option value="KORRIGIERT">Korrigiert</option>
              </Select>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Titel</TableHead>
                    <TableHead>Objekt</TableHead>
                    <TableHead>Einheiten</TableHead>
                    <TableHead>Zeitraum</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Ergebnis</TableHead>
                    <TableHead>Zuletzt geändert</TableHead>
                    <TableHead>Aktion</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visible.map((record) => (
                    <TableRow key={`${record.kind}-${record.id}`}>
                      <TableCell className="min-w-64 font-medium">{record.title}</TableCell>
                      <TableCell>{record.buildingName}</TableCell>
                      <TableCell>{record.unitCount}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {date(record.periodStart)} - {date(record.periodEnd)}
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex rounded-full bg-mint px-2.5 py-1 text-xs font-semibold text-forest">
                          {STATUS_LABELS[record.status] ?? record.status}
                        </span>
                      </TableCell>
                      <TableCell>{record.resultSummary}</TableCell>
                      <TableCell className="whitespace-nowrap text-sm text-slate">
                        {dateTime(record.updatedAt)}
                      </TableCell>
                      <TableCell>
                        <Button asChild size="sm" variant="outline">
                          <Link
                            href={
                              record.kind === 'DRAFT'
                                ? `/a/${accountId}/abrechnung/${record.id}`
                                : `/a/${accountId}/abrechnung/archiv/${record.id}`
                            }
                          >
                            {record.kind === 'DRAFT' ? 'Weiterbearbeiten' : 'Öffnen'}
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
