'use client';

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  StatusNote,
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@lokara/ui';
import Link from 'next/link';

import { PageHeader } from '@/features/portal/page-header';
import { ApiError } from '@/lib/api';

import { useBuildingDetail } from './queries';

/** Objekt-Detail (docs/04): units of one building; create Unit. */
export function BuildingDetailPage({
  accountId,
  buildingId,
}: {
  accountId: string;
  buildingId: string;
}) {
  const detail = useBuildingDetail(accountId, buildingId);

  if (detail.isPending) {
    return (
      <main className="py-10">
        <div
          aria-hidden="true"
          className="h-64 max-w-5xl animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
        />
      </main>
    );
  }
  if (detail.isError) {
    const missing = detail.error instanceof ApiError && detail.error.status === 404;
    return (
      <main className="py-10">
        <StatusNote kind="danger" label={missing ? 'Objekt nicht gefunden.' : 'Fehler beim Laden.'}>
          {missing ? (
            <Link className="underline underline-offset-4" href={`/a/${accountId}/objekte`}>
              Zurück zur Objektliste
            </Link>
          ) : (
            'Laden Sie die Seite neu oder versuchen Sie es später erneut.'
          )}
        </StatusNote>
      </main>
    );
  }

  const building = detail.data;
  return (
    <main className="py-10">
      <PageHeader
        title={building.name}
        description={`${building.street}, ${building.postalCode} ${building.city}`}
        breadcrumb={
          <Link
            href={`/a/${accountId}/objekte`}
            className="text-green underline-offset-4 hover:underline"
          >
            Objekte
          </Link>
        }
        actions={
          <Button asChild>
            <Link href={`/a/${accountId}/objekte/${buildingId}/einheit/neu`}>Einheit anlegen</Link>
          </Button>
        }
      />

      <div className="max-w-5xl">
        <section aria-label="Einheiten">
          {building.units.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Noch keine Einheiten</CardTitle>
                <CardDescription>
                  Legen Sie die erste Wohneinheit über „Einheit anlegen“ an — Mietverhältnisse
                  folgen auf der Einheitenseite.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <Table>
                  <TableCaption>Einheiten in {building.name}</TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Einheit</TableHead>
                      <TableHead className="text-right">Wohnfläche</TableHead>
                      <TableHead>Status heute</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {building.units.map((unit) => (
                      <TableRow key={unit.id}>
                        <TableCell>
                          <Link
                            href={`/a/${accountId}/einheiten/${unit.id}`}
                            className="font-semibold text-green underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                          >
                            {unit.label}
                          </Link>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {unit.areaSqm.toLocaleString('de-DE')} m²
                        </TableCell>
                        <TableCell className={unit.occupiedToday ? 'text-success' : 'text-slate'}>
                          {unit.occupiedToday ? 'Vermietet' : 'Leerstand'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </section>
      </div>
    </main>
  );
}
