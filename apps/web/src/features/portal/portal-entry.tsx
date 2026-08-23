'use client';

import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, StatusNote } from '@lokara/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import React, { useEffect } from 'react';

import type { MeAccount } from '@/lib/contracts';

import { useLoadDemo, useMe } from './queries';

/**
 * The portal entry: resolves the Person's relationships and enters the first
 * account's portal. With no relationship yet, the one action is loading the
 * demo scenario (docs/06 — one click, no typing live on stage).
 */
/** Only a sole owner or employee context is safe to enter without a choice. */
export function autoEntryAccount(accounts: MeAccount[]): MeAccount | undefined {
  const account = accounts[0];
  return accounts.length === 1 && (account?.role === 'OWNER' || account?.role === 'EMPLOYEE')
    ? account
    : undefined;
}

/** URL links deliberately carry the context: the API authorizes every target again. */
export function AccountChooser({ accounts }: { accounts: MeAccount[] }) {
  return (
    <Card className="mt-8">
      <CardHeader>
        <CardTitle>Konto auswählen</CardTitle>
        <CardDescription>Wählen Sie den Bereich, den Sie öffnen möchten.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-2" aria-label="Verfügbare Konten">
          {accounts.map((account) => (
            <li key={account.id}>
              <Link
                href={`/a/${account.id}`}
                className="flex rounded-lg border border-mint px-4 py-3 text-left transition-colors duration-150 hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <span>
                  <span className="block font-semibold">{account.name}</span>
                  <span className="text-sm text-slate">{roleLabel(account.role)}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function roleLabel(role: string) {
  return { OWNER: 'Inhaber:in', EMPLOYEE: 'Mitarbeiter:in', TAX_ADVISOR: 'Steuerberater:in' }[role] ?? role;
}

export function PortalEntry() {
  const router = useRouter();
  const me = useMe();
  const loadDemo = useLoadDemo();

  const entryAccount = me.data ? autoEntryAccount(me.data.accounts) : undefined;
  useEffect(() => {
    if (entryAccount) {
      router.replace(`/a/${entryAccount.id}`);
    }
  }, [entryAccount, router]);

  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center px-6 py-16">
      <p className="mb-2 font-sans text-sm font-semibold text-green">Lokara</p>
      <h1 className="font-display text-3xl font-bold">Vermieter-Portal</h1>

      {me.isPending || entryAccount ? (
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
      ) : me.data && me.data.accounts.length > 0 ? (
        <AccountChooser accounts={me.data.accounts} />
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
