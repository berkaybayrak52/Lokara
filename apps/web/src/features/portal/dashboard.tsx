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

import { useAccountSummary, useLoadDemo, useMe, useResetDemo } from './queries';

export function showOwnerControls(role: string | undefined): boolean {
  return role === 'OWNER';
}

/** Dashboard (docs/04 M3 page 1): overview cards + one-click demo scenario. */
export function Dashboard({ accountId }: { accountId: string }) {
  const summary = useAccountSummary(accountId);
  const loadDemo = useLoadDemo();
  const { data: me } = useMe();
  const ownerControls = showOwnerControls(me?.accounts.find((account) => account.id === accountId)?.role);

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
                ? ownerControls
                  ? 'Dieses Konto enthält noch kein Objekt. Laden Sie das Demo-Szenario: ein Gebäude, drei Einheiten, ein Auszug zur Jahresmitte — die Grundlage für die Abrechnung.'
                  : 'Ihnen ist kein Objekt zugewiesen.'
                : 'Die Übersicht konnte nicht geladen werden. Läuft die API (uv run lokara-api)?'}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {!empty ? (
              <StatusNote kind="danger" label="Verbindungsfehler.">
                Bitte API und Datenbank prüfen, dann erneut versuchen.
              </StatusNote>
            ) : null}
            {ownerControls ? <div>
              <Button onClick={() => loadDemo.mutate()} disabled={loadDemo.isPending}>
                {loadDemo.isPending ? 'Wird geladen…' : 'Demo-Szenario laden'}
              </Button>
            </div> : null}
            {ownerControls && loadDemo.isError ? (
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

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
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
        {ownerControls ? <ResetDemoCard /> : null}
      </div>
    </PageFrame>
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
              ? 'Demo-Funktionen sind deaktiviert — API mit DEMO_SEED_ENABLED=true starten.'
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
