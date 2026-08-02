'use client';

import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, StatusNote } from '@lokara/ui';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { useLoadDemo, useMe } from './queries';

/**
 * The portal entry: resolves the Person's relationships and enters the first
 * account's portal. With no relationship yet, the one action is loading the
 * demo scenario (docs/06 — one click, no typing live on stage).
 */
export function PortalEntry() {
  const router = useRouter();
  const me = useMe();
  const loadDemo = useLoadDemo();

  const firstAccountId = me.data?.accounts[0]?.id;
  useEffect(() => {
    if (firstAccountId) {
      router.replace(`/a/${firstAccountId}`);
    }
  }, [firstAccountId, router]);

  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center px-6 py-16">
      <p className="mb-2 font-sans text-sm font-semibold text-green">Lokara</p>
      <h1 className="font-display text-3xl font-bold">Vermieter-Portal</h1>

      {me.isPending || firstAccountId ? (
        <div aria-hidden="true" className="mt-8 h-40 animate-pulse rounded-xl bg-mint/60" />
      ) : me.isError ? (
        <div className="mt-8 space-y-4">
          <StatusNote kind="danger" label="Keine Verbindung zur API.">
            Läuft der Server? <code className="font-mono text-xs">uv run lokara-api</code>
          </StatusNote>
          <Button variant="outline" onClick={() => me.refetch()}>
            Erneut versuchen
          </Button>
        </div>
      ) : (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Demo-Szenario laden</CardTitle>
            <CardDescription>
              Noch kein Konto verknüpft. Ein Klick lädt das Pitch-Szenario: Musterstraße 12 mit
              drei Einheiten, einem Auszug zur Jahresmitte und der Abrechnung 2025.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
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
      )}
    </main>
  );
}
