'use client';

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  StatusNote,
} from '@lokara/ui';
import Link from 'next/link';
import { useState } from 'react';

import { ApiError } from '@/lib/api';

import {
  DashboardSkeleton,
  MietSollCard,
  OccupancyCard,
  UnavailableCard,
} from './dashboard-widgets';
import { PageHeader } from './page-header';
import { useLoadDemo, useMe, usePortfolioOverview, useResetDemo } from './queries';

export function showOwnerControls(role: string | undefined): boolean {
  return role === 'OWNER';
}

/** Portfolio dashboard (UI-01): server-owned rent and occupancy truth. */
export function Dashboard({ accountId }: { accountId: string }) {
  const overview = usePortfolioOverview(accountId);
  const loadDemo = useLoadDemo();
  const { data: me } = useMe();
  const ownerControls = showOwnerControls(
    me?.accounts.find((account) => account.id === accountId)?.role,
  );

  if (overview.isPending) {
    return (
      <PageFrame>
        <DashboardSkeleton />
      </PageFrame>
    );
  }

  if (overview.isError) {
    const empty = overview.error instanceof ApiError && overview.error.status === 404;
    if (empty) {
      return (
        <PageFrame>
          <EmptyPortfolioCard
            ownerControls={ownerControls}
            loadPending={loadDemo.isPending}
            loadFailed={loadDemo.isError}
            onLoad={() => loadDemo.mutate()}
          />
        </PageFrame>
      );
    }
    return (
      <PageFrame>
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>Fehler beim Laden</CardTitle>
            <CardDescription>
              Die Übersicht konnte nicht geladen werden. Bitte versuchen Sie es später erneut.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <StatusNote kind="danger" label="Verbindungsfehler.">
              Laden Sie die Seite neu oder versuchen Sie es später erneut.
            </StatusNote>
          </CardContent>
        </Card>
      </PageFrame>
    );
  }

  const data = overview.data;
  if (data.buildingCount === 0) {
    return (
      <PageFrame>
        <EmptyPortfolioCard
          ownerControls={ownerControls}
          loadPending={loadDemo.isPending}
          loadFailed={loadDemo.isError}
          onLoad={() => loadDemo.mutate()}
        />
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <div className="grid min-w-0 grid-cols-1 items-start gap-4 overflow-hidden lg:grid-cols-3">
        <MietSollCard
          buildingCount={data.buildingCount}
          mietSollCentsMonthly={data.mietSollCentsMonthly}
        />
        <OccupancyCard
          accountId={accountId}
          href={`/a/${accountId}/objekte`}
          occupiedUnitCount={data.occupiedUnitCount}
          vacantUnitCount={data.vacantUnitCount}
          unitCount={data.unitCount}
        />
        <UnavailableCard
          title="Mieteinnahmen"
          description="Noch keine Zahlungsdaten verfügbar. Der monatliche Zahlungseingang folgt mit der Finanzübersicht."
        />
      </div>

      <div className="mt-6 grid min-w-0 grid-cols-1 items-start gap-4 overflow-hidden lg:grid-cols-3">
        <UnavailableCard
          title="Offene Posten"
          description="Noch keine Zahlungsdaten verfügbar. Offene Mieten werden erst nach Einrichtung des Zahlungsabgleichs angezeigt."
        />
        <UnavailableCard
          title="Cashflow"
          description="Einrichtung ausstehend. Für den Verlauf fehlen noch echte Einnahmen- und Ausgabendaten."
        />
        <UnavailableCard
          title="Aufgaben & Tickets"
          description="Noch nicht verfügbar. Aufgaben und Tickets erhalten später eine eigene verlässliche Datenquelle."
        />
      </div>

      <div className="mt-6 grid min-w-0 grid-cols-1 items-start gap-4 overflow-hidden lg:grid-cols-2">
        <Card className="min-w-0 overflow-hidden">
          <CardHeader>
            <CardTitle>Abrechnung erstellen</CardTitle>
            <CardDescription>
              Betriebs- und Heizkostenabrechnung — centgenau, mit CO₂-Aufteilung und Rechtsstand.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href={`/a/${accountId}/abrechnung`}>Abrechnung erstellen</Link>
            </Button>
          </CardContent>
        </Card>
        {ownerControls ? <ResetDemoCard /> : null}
      </div>
    </PageFrame>
  );
}

function EmptyPortfolioCard({
  ownerControls,
  loadPending,
  loadFailed,
  onLoad,
}: {
  ownerControls: boolean;
  loadPending: boolean;
  loadFailed: boolean;
  onLoad: () => void;
}) {
  return (
    <Card className="max-w-xl min-w-0 overflow-hidden">
      <CardHeader>
        <CardTitle>Noch keine Daten</CardTitle>
        <CardDescription>
          {ownerControls
            ? 'Dieses Konto enthält noch kein Objekt. Laden Sie das Demo-Szenario als Grundlage für die Abrechnung.'
            : 'Ihnen ist noch kein Objekt zugewiesen. Wenden Sie sich an die Kontoinhaberin oder den Kontoinhaber.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {ownerControls ? (
          <div>
            <Button onClick={onLoad} disabled={loadPending}>
              {loadPending ? 'Wird geladen…' : 'Demo-Szenario laden'}
            </Button>
          </div>
        ) : null}
        {ownerControls && loadFailed ? (
          <StatusNote kind="danger" label="Laden fehlgeschlagen.">
            Bitte erneut versuchen.
          </StatusNote>
        ) : null}
      </CardContent>
    </Card>
  );
}

/**
 * Demo zurücksetzen (docs/06): after a rehearsal the account carries stray
 * objects and readings, and the demo then opens on a list of test rows. One
 * click puts it back to exactly the seeded scenario.
 *
 * Two-step, because it deletes — the same pattern as every other destructive
 * action here: a quiet trigger, and the filled destructive button IS the
 * confirmation.
 */
function ResetDemoCard() {
  const reset = useResetDemo();
  const [confirming, setConfirming] = useState(false);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Demo zurücksetzen</CardTitle>
        <CardDescription>
          Setzt dieses Konto auf das ursprüngliche Demo-Szenario zurück: Musterstraße 12 mit drei
          Einheiten, den erfassten Kosten und Zählerständen.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {confirming ? (
          <>
            <StatusNote
              kind="warning"
              label="Alle eigenen Eingaben in diesem Konto gehen verloren."
            >
              Objekte, Einheiten, Mietverhältnisse, Kosten und Ablesungen werden gelöscht und durch
              das Demo-Szenario ersetzt.
            </StatusNote>
            <div className="flex gap-2">
              <Button
                variant="destructive"
                disabled={reset.isPending}
                onClick={() => reset.mutate(undefined, { onSuccess: () => setConfirming(false) })}
              >
                {reset.isPending ? 'Wird zurückgesetzt…' : 'Zurücksetzen'}
              </Button>
              <Button variant="ghost" onClick={() => setConfirming(false)}>
                Abbrechen
              </Button>
            </div>
          </>
        ) : (
          <div>
            <Button variant="outline" onClick={() => setConfirming(true)}>
              Demo zurücksetzen
            </Button>
          </div>
        )}
        {reset.isError ? (
          <StatusNote kind="danger" label="Zurücksetzen fehlgeschlagen.">
            {reset.error instanceof ApiError && reset.error.status === 403
              ? 'Demo-Funktionen sind derzeit nicht verfügbar.'
              : 'Bitte erneut versuchen.'}
          </StatusNote>
        ) : null}
        {reset.isSuccess ? (
          <StatusNote kind="success" label="Demo-Szenario wiederhergestellt.">
            Das Konto entspricht wieder genau dem gespeicherten Szenario.
          </StatusNote>
        ) : null}
      </CardContent>
    </Card>
  );
}

function PageFrame({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-w-0 overflow-x-hidden py-10">
      <PageHeader title="Übersicht" description="Ihr Bestand auf einen Blick." />
      {children}
    </main>
  );
}
