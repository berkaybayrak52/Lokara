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

import { ApiError } from '@/lib/api';

import { useAccountSummary, useLoadDemo } from './queries';

/** Dashboard (docs/04 M3 page 1): overview cards + one-click demo scenario. */
export function Dashboard({ accountId }: { accountId: string }) {
  const summary = useAccountSummary(accountId);
  const loadDemo = useLoadDemo();

  if (summary.isPending) {
    return (
      <PageFrame>
        <div aria-hidden="true" className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-mint/60" />
          ))}
        </div>
      </PageFrame>
    );
  }

  if (summary.isError) {
    const empty = summary.error instanceof ApiError && summary.error.status === 404;
    return (
      <PageFrame>
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle>{empty ? 'Noch keine Daten' : 'Fehler beim Laden'}</CardTitle>
            <CardDescription>
              {empty
                ? 'Dieses Konto enthält noch kein Objekt. Laden Sie das Demo-Szenario: ein Gebäude, drei Einheiten, ein Auszug zur Jahresmitte — die Grundlage für die Abrechnung.'
                : 'Die Übersicht konnte nicht geladen werden. Läuft die API (uv run lokara-api)?'}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {!empty ? (
              <StatusNote kind="danger" label="Verbindungsfehler.">
                Bitte API und Datenbank prüfen, dann erneut versuchen.
              </StatusNote>
            ) : null}
            <div>
              <Button onClick={() => loadDemo.mutate()} disabled={loadDemo.isPending}>
                {loadDemo.isPending ? 'Wird geladen…' : 'Demo-Szenario laden'}
              </Button>
            </div>
            {loadDemo.isError ? (
              <StatusNote kind="danger" label="Laden fehlgeschlagen.">
                Bitte erneut versuchen.
              </StatusNote>
            ) : null}
          </CardContent>
        </Card>
      </PageFrame>
    );
  }

  const data = summary.data;
  const tenancyCount = data.tenancies.length;

  return (
    <PageFrame>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Objekt</CardDescription>
            <CardTitle className="font-display text-xl">{data.buildingName}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate">{data.buildingAddress}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Einheiten</CardDescription>
            <CardTitle className="font-display text-3xl tabular-nums">{data.unitCount}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate">Wohneinheiten im Objekt</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Mietverhältnisse</CardDescription>
            <CardTitle className="font-display text-3xl tabular-nums">{tenancyCount}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate">
            inkl. Auszug zur Jahresmitte — Leerstand fällt dem Vermieter zu
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6 max-w-xl">
        <CardHeader>
          <CardTitle>Abrechnung 2025</CardTitle>
          <CardDescription>
            Betriebs- und Heizkostenabrechnung für {data.buildingName} — centgenau, mit
            CO₂-Aufteilung und Rechtsstand.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href={`/a/${accountId}/abrechnung`}>Abrechnung erstellen</Link>
          </Button>
        </CardContent>
      </Card>
    </PageFrame>
  );
}

function PageFrame({ children }: { children: React.ReactNode }) {
  return (
    <main className="px-8 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold">Übersicht</h1>
        <p className="mt-2 max-w-prose text-slate">
          Ihr Bestand auf einen Blick. Kontext kommt aus der URL — jede Anfrage wird serverseitig
          neu autorisiert.
        </p>
      </header>
      {children}
    </main>
  );
}
