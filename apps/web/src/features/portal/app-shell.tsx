'use client';

import { Button } from '@lokara/ui';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React from 'react';

import type { MeAccount } from '@/lib/contracts';

import { useMe } from './queries';

/**
 * The Vermieter-portal shell (docs/04): context lives in the URL
 * (/a/{accountId}/…), the left menu is DERIVED from the Person's relationships
 * and is navigation only — the API re-authorizes every request independently.
 */

const ROLE_LABELS: Record<string, string> = {
  OWNER: 'Inhaber:in',
  EMPLOYEE: 'Mitarbeiter:in',
  TAX_ADVISOR: 'Steuerberater:in',
};

interface NavItem {
  href: (accountId: string) => string;
  label: string;
  /** Path prefixes (relative to /a/{id}) that count as "inside" this item. */
  activePrefixes: string[];
}

const NAV_ITEMS: NavItem[] = [
  { href: (id) => `/a/${id}`, label: 'Übersicht', activePrefixes: [] },
  // Einheiten pages belong to the Objekte section (list → detail → unit).
  {
    href: (id) => `/a/${id}/objekte`,
    label: 'Objekte',
    activePrefixes: ['/objekte', '/einheiten'],
  },
  { href: (id) => `/a/${id}/kosten`, label: 'Kosten erfassen', activePrefixes: ['/kosten'] },
  { href: (id) => `/a/${id}/beleg`, label: 'Beleg-Upload', activePrefixes: ['/beleg'] },
  { href: (id) => `/a/${id}/zaehler`, label: 'Zähler', activePrefixes: ['/zaehler'] },
  {
    href: (id) => `/a/${id}/abrechnung`,
    label: 'Abrechnung erstellen',
    activePrefixes: ['/abrechnung'],
  },
];

// Pages that exist in the plan but not yet in the app — an honest roadmap
// beats dead links (and hiding them would misrepresent scope). M3 and M4 are
// complete, so this is empty; the next entries arrive with M5.
const UPCOMING: string[] = [];

export function AppShell({
  accountId,
  children,
}: {
  accountId: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { data: me } = useMe();
  const account = me?.accounts.find((a) => a.id === accountId);

  return (
    <PortalShellContent
      accountId={accountId}
      account={account}
      accounts={me?.accounts ?? []}
      pathname={pathname}
      isLoading={me === undefined}
    >
      {children}
    </PortalShellContent>
  );
}

export function PortalShellContent({
  accountId,
  account,
  accounts,
  pathname,
  isLoading = false,
  children,
}: {
  accountId: string;
  account: MeAccount | undefined;
  accounts: MeAccount[];
  pathname: string;
  isLoading?: boolean;
  children: React.ReactNode;
}) {
  const taxAdvisor = account?.role === 'TAX_ADVISOR';

  return (
    <div className="flex min-h-dvh">
      {/* sticky + h-dvh, not the stretched default: without it the aside grows
          to the full DOCUMENT height on a long page (Zähler is ~2700px), which
          parks the account block far below the fold and scrolls the nav away. */}
      <aside className="sticky top-0 flex h-dvh w-64 shrink-0 flex-col overflow-y-auto border-r border-mint bg-white px-4 py-6">
        <Link href="/" className="mb-8 flex items-center gap-2 px-2">
          <span
            aria-hidden="true"
            className="grid size-8 shrink-0 grid-cols-2 gap-0.5 rounded-lg bg-ink p-1.5"
          >
            <span className="rounded-[2px] bg-green" />
            <span className="rounded-[2px] bg-paper/90" />
            <span className="rounded-[2px] bg-paper/90" />
            <span className="rounded-[2px] bg-green" />
          </span>
          <span className="font-display text-lg font-bold">Lokara</span>
        </Link>

        {!taxAdvisor && account ? <nav aria-label="Hauptnavigation" className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const href = item.href(accountId);
            const active =
              item.activePrefixes.length === 0
                ? pathname === href
                : item.activePrefixes.some((prefix) =>
                    pathname.startsWith(`/a/${accountId}${prefix}`),
                  );
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? 'page' : undefined}
                className={
                  'rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150 ease-out ' +
                  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ' +
                  (active ? 'bg-mint font-semibold text-forest' : 'text-ink hover:bg-mint/60')
                }
              >
                {item.label}
              </Link>
            );
          })}

          {UPCOMING.length > 0 ? (
            <p className="mt-6 mb-1 px-3 text-xs font-semibold tracking-wide text-slate uppercase">
              In Arbeit
            </p>
          ) : null}
          {UPCOMING.map((label) => (
            <span
              key={label}
              aria-disabled="true"
              className="cursor-not-allowed rounded-lg px-3 py-2 text-sm text-slate"
            >
              {label}
              <span className="ml-2 rounded bg-mint px-1.5 py-0.5 text-[10px] font-semibold text-forest">
                bald
              </span>
            </span>
          ))}
        </nav> : <div className="flex-1" />}

        {account ? (
          // shrink-0 so a long nav never squeezes it, and truncate so a long
          // Hausverwaltung name clips cleanly instead of pushing the role line
          // out of the box (title keeps the full name reachable).
          <div className="mt-8 shrink-0 rounded-lg bg-paper px-3 py-2.5">
            <p className="truncate text-sm font-semibold" title={account.name}>
              {account.name}
            </p>
            <p className="truncate text-xs text-slate">
              {ROLE_LABELS[account.role] ?? account.role}
            </p>
            {accounts.length > 1 ? (
              <div className="mt-3 border-t border-mint pt-3">
                <p className="text-xs font-semibold text-slate">Konto wechseln</p>
                <ul className="mt-1 space-y-1" aria-label="Konto wechseln">
                  {accounts.filter((candidate) => candidate.id !== accountId).map((candidate) => (
                    <li key={candidate.id}>
                      <Link
                        href={`/a/${candidate.id}`}
                        className="block rounded px-1 py-1 text-xs text-green underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                      >
                        {candidate.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}
      </aside>

      {/* One centered measure for every page instead of full-bleed: on a wide
          screen the tables otherwise run to the far edge and the eye loses the
          row. Set here, once, so no page can drift from it. */}
      <div className="mx-auto min-w-0 w-full max-w-[1100px] flex-1">
        {isLoading ? (
          <main className="mx-auto max-w-2xl px-8 py-16">
            <div aria-hidden="true" className="h-32 animate-pulse rounded-xl bg-mint/60" />
          </main>
        ) : account === undefined ? (
          <main className="mx-auto max-w-2xl px-8 py-16">
            <h1 className="font-display text-2xl font-bold">Kein Zugriff auf dieses Konto</h1>
            <p className="mt-3 max-w-prose text-slate">
              Für dieses Konto besteht keine aktive Mitgliedschaft. Die Navigation zeigt nur, was
              existiert — jeder Zugriff wird serverseitig unabhängig geprüft.
            </p>
            <Button asChild className="mt-6">
              <Link href="/">Zur Kontoauswahl</Link>
            </Button>
          </main>
        ) : taxAdvisor ? (
          <main className="mx-auto max-w-2xl px-8 py-16">
            <h1 className="font-display text-2xl font-bold">Steuerfunktionen werden vorbereitet</h1>
            <p className="mt-3 max-w-prose text-slate">
              Dieser Bereich ist noch nicht verfügbar. Bitte wählen Sie ein anderes Konto aus.
            </p>
            <Button asChild className="mt-6">
              <Link href="/">Zur Kontoauswahl</Link>
            </Button>
          </main>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
