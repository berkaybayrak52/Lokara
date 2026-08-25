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
import { useState } from 'react';

import { PageHeader } from '@/features/portal/page-header';

import { BuildingMap } from './building-map';
import { useBuildings } from './queries';
import { useMe } from '../portal/queries';

export function showOwnerControls(role: string | undefined): boolean {
  return role === 'OWNER';
}

/** Objekte (docs/04 M3 page 2): list → detail; create Building. */
export function BuildingsPage({ accountId }: { accountId: string }) {
  const buildings = useBuildings(accountId);
  const { data: me } = useMe();
  const [view, setView] = useState<'list' | 'map'>('list');
  const ownerControls = showOwnerControls(
    me?.accounts.find((account) => account.id === accountId)?.role,
  );

  return (
    <main className="py-10">
      <PageHeader
        title="Objekte"
        description="Alle Objekte dieses Kontos. Ein Klick auf ein Objekt öffnet seine Einheiten."
        actions={
          ownerControls ? (
            <Button asChild>
              <Link href={`/a/${accountId}/objekte/neu`}>Objekt anlegen</Link>
            </Button>
          ) : undefined
        }
      />

      <div className="max-w-5xl">
        <div
          role="group"
          aria-label="Objektansicht"
          className="mb-6 inline-flex rounded-lg border border-slate/40 bg-card p-1"
        >
          <Button
            type="button"
            size="sm"
            variant={view === 'list' ? 'secondary' : 'ghost'}
            aria-pressed={view === 'list'}
            onClick={() => setView('list')}
          >
            Liste
          </Button>
          <Button
            type="button"
            size="sm"
            variant={view === 'map' ? 'secondary' : 'ghost'}
            aria-pressed={view === 'map'}
            onClick={() => setView('map')}
          >
            Karte
          </Button>
        </div>

        <section aria-label={view === 'list' ? 'Objektliste' : 'Objektkarte'}>
          {buildings.isPending ? (
            <div
              aria-hidden="true"
              className="h-48 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            />
          ) : buildings.isError ? (
            <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
              Laden Sie die Seite neu oder versuchen Sie es später erneut.
            </StatusNote>
          ) : view === 'map' ? (
            <BuildingMap accountId={accountId} buildings={buildings.data.buildings} />
          ) : buildings.data.buildings.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Noch keine Objekte</CardTitle>
                <CardDescription>
                  {ownerControls
                    ? 'Legen Sie Ihr erstes Objekt über „Objekt anlegen“ an — Einheiten und Mietverhältnisse folgen auf der Detailseite.'
                    : 'Ihnen ist kein Objekt zugewiesen.'}
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <Table>
                  <TableCaption>Alle Objekte dieses Kontos</TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Objekt</TableHead>
                      <TableHead>Adresse</TableHead>
                      <TableHead className="text-right">Einheiten</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {buildings.data.buildings.map((b) => (
                      <TableRow key={b.id}>
                        <TableCell>
                          <Link
                            href={`/a/${accountId}/objekte/${b.id}`}
                            className="font-semibold text-green underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                          >
                            {b.name}
                          </Link>
                        </TableCell>
                        <TableCell className="text-slate">
                          {b.street}, {b.postalCode} {b.city}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{b.unitCount}</TableCell>
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
