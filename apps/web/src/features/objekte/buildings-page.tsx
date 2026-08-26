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
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useState } from 'react';

import { PageHeader } from '@/features/portal/page-header';
import { BUILDING_TYPE_LABELS } from '@/lib/contracts';

import { useBuildings } from './queries';
import { useMe } from '../portal/queries';

// Leaflet touches `window`, so the map is client-only (dynamic, ssr:false).
const BuildingMap = dynamic(() => import('./building-map').then((m) => m.BuildingMap), {
  ssr: false,
  loading: () => (
    <div aria-hidden="true" className="h-[520px] w-full animate-pulse rounded-xl bg-mint/60" />
  ),
});

export function showOwnerControls(role: string | undefined): boolean {
  return role === 'OWNER';
}

type View = 'liste' | 'karte';

/** Objekte (docs/04 M3 page 2): list ⇄ map; create runs through Wizard-A (/neu). */
export function BuildingsPage({ accountId }: { accountId: string }) {
  const buildings = useBuildings(accountId);
  const { data: me } = useMe();
  const ownerControls = showOwnerControls(
    me?.accounts.find((account) => account.id === accountId)?.role,
  );
  const [view, setView] = useState<View>('liste');

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

      <div className="mb-6 flex rounded-lg border border-mint p-0.5" role="group" aria-label="Ansicht">
        {(['liste', 'karte'] as View[]).map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={view === option}
            onClick={() => setView(option)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${
              view === option ? 'bg-green text-white' : 'text-slate hover:text-ink'
            }`}
          >
            {option === 'liste' ? 'Liste' : 'Karte'}
          </button>
        ))}
      </div>

      {buildings.isPending ? (
        <div aria-hidden="true" className="h-64 w-full max-w-5xl animate-pulse rounded-xl bg-mint/60" />
      ) : buildings.isError ? (
        <StatusNote kind="danger" label="Objekte konnten nicht geladen werden.">
          Laden Sie die Seite neu oder versuchen Sie es später erneut.
        </StatusNote>
      ) : buildings.data.buildings.length === 0 ? (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Noch keine Objekte</CardTitle>
            <CardDescription>
              {ownerControls
                ? 'Legen Sie Ihr erstes Objekt über „Objekt anlegen" an — Einheiten und Mietverhältnisse folgen auf der Detailseite.'
                : 'Ihnen ist kein Objekt zugewiesen.'}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : view === 'karte' ? (
        <div className="max-w-5xl">
          <BuildingMap accountId={accountId} buildings={buildings.data.buildings} />
          <p className="mt-2 text-xs text-slate">© OpenStreetMap-Mitwirkende</p>
        </div>
      ) : (
        <Card className="max-w-5xl">
          <CardContent className="pt-6">
            <Table>
              <TableCaption>Alle Objekte dieses Kontos</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>Objekt</TableHead>
                  <TableHead>Adresse</TableHead>
                  <TableHead>Art</TableHead>
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
                    <TableCell className="text-slate">
                      {BUILDING_TYPE_LABELS[b.buildingType] ?? b.buildingType}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{b.unitCount}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
