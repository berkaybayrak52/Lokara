'use client';

import { Button } from '@lokara/ui';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

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
  { href: (id) => `/a/${id}/objekte`, label: 'Objekte', activePrefixes: ['/objekte', '/einheiten'] },
  { href: (id) => `/a/${id}/abrechnung`, label: 'Abrechnung erstellen', activePrefixes: ['/abrechnung'] },
];

// The rest of the M3 pages, visible but explicitly not yet available — an
// honest roadmap beats dead links (and hiding them would misrepresent scope).
const UPCOMING = ['Kosten erfassen', 'Zähler'];

export function AppShell({ accountId, children }: { accountId: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: me } = useMe();
  const account = me?.accounts.find((a) => a.id === accountId);

  return (
    <div className="flex min-h-dvh">
      <aside className="flex w-64 shrink-0 flex-col border-r border-mint bg-white px-4 py-6">
        <Link href="/" className="mb-8 flex items-center gap-2 px-2">
          <span aria-hidden="true" className="grid size-8 shrink-0 grid-cols-2 gap-0.5 rounded-lg bg-ink p-1.5">
            <span className="rounded-[2px] bg-green" />
            <span className="rounded-[2px] bg-paper/90" />
            <span className="rounded-[2px] bg-paper/90" />
            <span className="rounded-[2px] bg-green" />
          </span>
          <span className="font-display text-lg font-bold">Lokara</span>
        </Link>

        <nav aria-label="Hauptnavigation" className="flex flex-1 flex-col gap-1">
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

          <p className="mt-6 mb-1 px-3 text-xs font-semibold tracking-wide text-slate uppercase">
            In Arbeit
          </p>
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
        </nav>

        {account ? (
          <div className="mt-8 rounded-lg bg-paper px-3 py-3">
            <p className="text-sm font-semibold">{account.name}</p>
            <p className="text-xs text-slate">{ROLE_LABELS[account.role] ?? account.role}</p>
          </div>
        ) : null}
      </aside>

      <div className="min-w-0 flex-1">
        {account === undefined && me !== undefined ? (
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
        ) : (
          children
        )}
      </div>
    </div>
  );
}
