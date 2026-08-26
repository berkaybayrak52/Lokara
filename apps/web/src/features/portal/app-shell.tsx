'use client';

import { Button } from '@lokara/ui';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import React, { useEffect, useState } from 'react';

import type { MeAccount } from '@/lib/contracts';

import { useMe } from './queries';
import { ReminderSidebar } from './reminder-sidebar';

/**
 * The Vermieter-portal shell (docs/04, Spec 02/09): context lives in the URL
 * (/a/{accountId}/…), the left menu is DERIVED from the Person's relationships
 * and is navigation only — the API re-authorizes every request independently.
 *
 * Desktop/Laptop only. The sidebar collapses to a 72px icon rail; the choice is
 * remembered locally as a pure display preference. No mobile drawer/bottom-nav
 * (post-pitch, own spec).
 */

const ROLE_LABELS: Record<string, string> = {
  OWNER: 'Inhaber:in',
  EMPLOYEE: 'Mitarbeiter:in',
  TAX_ADVISOR: 'Steuerberater:in',
};

const COLLAPSE_KEY = 'lokara:nav-collapsed';

type IconKey =
  | 'overview'
  | 'objekte'
  | 'zahlungen'
  | 'kosten'
  | 'belege'
  | 'zaehler'
  | 'abrechnungen'
  | 'steuern';

/** Simple line icons, drawn locally as inline SVG — no icon dependency (S4). */
function NavIcon({ name }: { name: IconKey }) {
  const common = {
    width: 20,
    height: 20,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.75,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
    className: 'shrink-0',
  };
  switch (name) {
    case 'overview':
      return (
        <svg {...common}>
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      );
    case 'objekte':
      return (
        <svg {...common}>
          <path d="M3 21h18" />
          <path d="M5 21V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16" />
          <path d="M15 21V9h3a2 2 0 0 1 2 2v10" />
          <path d="M8 7h2M8 11h2M8 15h2" />
        </svg>
      );
    case 'zahlungen':
      return (
        <svg {...common}>
          <rect x="2.5" y="5" width="19" height="14" rx="2.5" />
          <path d="M2.5 10h19" />
          <path d="M6 15h4" />
        </svg>
      );
    case 'kosten':
      return (
        <svg {...common}>
          <path d="M6 3h9l3 3v15l-2.2-1.4L13.6 21l-2.1-1.4L9.4 21l-2.2-1.4L5 21V4a1 1 0 0 1 1-1Z" />
          <path d="M8.5 8h6M8.5 12h6" />
        </svg>
      );
    case 'belege':
      return (
        <svg {...common}>
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
          <path d="M14 3v5h5" />
          <path d="M9 13h6M9 17h4" />
        </svg>
      );
    case 'zaehler':
      return (
        <svg {...common}>
          <path d="M4 20a8 8 0 1 1 16 0" />
          <path d="M12 20 15 12" />
          <circle cx="12" cy="20" r="1" />
        </svg>
      );
    case 'abrechnungen':
      return (
        <svg {...common}>
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
          <path d="M14 3v5h5" />
          <path d="M8.5 12h7M8.5 16h7M8.5 8h2" />
        </svg>
      );
    case 'steuern':
      return (
        <svg {...common}>
          <rect x="4" y="3" width="16" height="18" rx="2" />
          <path d="M8 7h8" />
          <path d="M8 11h2M12 11h2M16 11h.01M8 15h2M12 15h2M16 15h.01M8 18h2M12 18h4" />
        </svg>
      );
  }
}

interface NavItem {
  href: (accountId: string) => string;
  label: string;
  icon: IconKey;
  /** Path prefixes (relative to /a/{id}) that count as "inside" this item. */
  activePrefixes: string[];
  /**
   * Nav-only visibility, NOT authorization. The API re-authorizes every request
   * independently (CLAUDE.md § 3.3) and a hidden link protects nothing; this
   * predicate only keeps the menu honest, so it never offers a route that is
   * guaranteed to answer 403 for the caller's role.
   */
  visibleFor?: (role: string) => boolean;
}

// Module navigation (S4): stable module names, one icon each, existing routes only.
const NAV_ITEMS: NavItem[] = [
  { href: (id) => `/a/${id}`, label: 'Übersicht', icon: 'overview', activePrefixes: [] },
  {
    href: (id) => `/a/${id}/objekte`,
    label: 'Objekte',
    icon: 'objekte',
    // Einheiten pages belong to the Objekte section (list → detail → unit).
    activePrefixes: ['/objekte', '/einheiten'],
  },
  {
    href: (id) => `/a/${id}/zahlungen`,
    label: 'Zahlungen',
    icon: 'zahlungen',
    activePrefixes: ['/zahlungen'],
    // Every payment route is behind `require_owner` (`routers/payments.py`), so
    // for an EMPLOYEE this entry could only ever dead-end in an error page.
    visibleFor: (role) => role === 'OWNER',
  },
  { href: (id) => `/a/${id}/kosten`, label: 'Kosten', icon: 'kosten', activePrefixes: ['/kosten'] },
  { href: (id) => `/a/${id}/beleg`, label: 'Belege', icon: 'belege', activePrefixes: ['/beleg'] },
  {
    href: (id) => `/a/${id}/zaehler`,
    label: 'Zähler',
    icon: 'zaehler',
    activePrefixes: ['/zaehler'],
  },
  {
    href: (id) => `/a/${id}/abrechnung`,
    label: 'Abrechnungen',
    icon: 'abrechnungen',
    activePrefixes: ['/abrechnung'],
  },
  {
    href: (id) => `/a/${id}/steuern`,
    label: 'Steuern',
    icon: 'steuern',
    activePrefixes: ['/steuern'],
    visibleFor: (role) => role === 'OWNER' || role === 'TAX_ADVISOR',
  },
];

export function taxAdvisorLandingPath(accountId: string): string {
  return `/a/${accountId}/steuern`;
}

export function taxAdvisorRedirectPath(
  role: string | undefined,
  accountId: string,
  pathname: string,
): string | null {
  const landing = taxAdvisorLandingPath(accountId);
  return role === 'TAX_ADVISOR' && !pathname.startsWith(landing) ? landing : null;
}

export function AppShell({
  accountId,
  children,
}: {
  accountId: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: me } = useMe();
  const account = me?.accounts.find((a) => a.id === accountId);
  const redirectPath = taxAdvisorRedirectPath(account?.role, accountId, pathname);
  useEffect(() => {
    if (redirectPath) router.replace(redirectPath);
  }, [redirectPath, router]);

  if (redirectPath) {
    return (
      <main className="px-8 py-16" role="status">
        Steuerbereich wird geöffnet …
      </main>
    );
  }

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

  // Collapsible rail (S3). Default expanded on the server + first client render
  // (stable, no hydration mismatch); after mount, a stored preference wins, else
  // the viewport width decides (<1440 → collapsed). `ready` gates the width
  // transition so the initial adjustment does not visibly animate.
  const [collapsed, setCollapsed] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let next = false;
    try {
      const stored = window.localStorage.getItem(COLLAPSE_KEY);
      if (stored === '1') next = true;
      else if (stored === '0') next = false;
      else next = window.innerWidth < 1440;
    } catch {
      next = false;
    }
    setCollapsed(next);
    setReady(true);
  }, []);
  const toggleCollapsed = () => {
    setCollapsed((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0');
      } catch {
        /* preference is best-effort */
      }
      return next;
    });
  };

  const visibleItems = account
    ? NAV_ITEMS.filter(
        (item) =>
          (item.visibleFor === undefined || item.visibleFor(account.role)) &&
          (!taxAdvisor || item.label === 'Steuern'),
      )
    : [];
  const overviewHref = account ? `/a/${accountId}` : '/';

  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      {/* sticky + h-dvh, not the stretched default: without it the aside grows
          to the full DOCUMENT height on a long page (Zähler is ~2700px), which
          parks the account block far below the fold and scrolls the nav away. */}
      <aside
        className={
          'sticky top-0 hidden h-dvh shrink-0 flex-col overflow-x-hidden overflow-y-auto border-r border-mint bg-white py-6 md:flex ' +
          (collapsed ? 'w-[72px] px-2' : 'w-[248px] px-4') +
          (ready ? ' transition-[width] duration-200 ease-out motion-reduce:transition-none' : '')
        }
      >
        <Link
          href={overviewHref}
          aria-label="Zur Übersicht"
          title="Zur Übersicht"
          className={
            'mb-8 flex items-center rounded px-2 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring ' +
            (collapsed ? 'justify-center' : 'gap-2')
          }
        >
          {collapsed ? (
            <Image
              src="/lokara-favicon.png"
              alt="Lokara"
              width={36}
              height={36}
              className="h-8 w-8 rounded-lg"
              priority
            />
          ) : (
            <Image
              src="/lokara-logo.png"
              alt="Lokara"
              width={103}
              height={28}
              className="h-7 w-auto"
              priority
            />
          )}
        </Link>

        {account ? (
          <nav aria-label="Hauptnavigation" className="flex flex-1 flex-col gap-1">
            {visibleItems.map((item) => {
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
                  aria-label={collapsed ? item.label : undefined}
                  title={collapsed ? item.label : undefined}
                  className={
                    'flex items-center rounded-lg py-2 text-sm font-medium transition-colors duration-150 ease-out ' +
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ' +
                    (collapsed ? 'justify-center px-2' : 'gap-3 px-3') +
                    (active ? ' bg-mint font-semibold text-forest' : ' text-ink hover:bg-mint/60')
                  }
                >
                  <NavIcon name={item.icon} />
                  {collapsed ? (
                    <span className="sr-only">{item.label}</span>
                  ) : (
                    <span>{item.label}</span>
                  )}
                </Link>
              );
            })}
          </nav>
        ) : (
          <div className="flex-1" />
        )}

        {/* Collapse toggle (S3) — keyboard + mouse; label announces the action. */}
        <button
          type="button"
          onClick={toggleCollapsed}
          aria-label={collapsed ? 'Navigation ausklappen' : 'Navigation einklappen'}
          title={collapsed ? 'Navigation ausklappen' : 'Navigation einklappen'}
          aria-pressed={collapsed}
          className={
            'mt-6 flex items-center rounded-lg py-2 text-sm font-medium text-slate transition-colors hover:bg-mint/60 hover:text-ink ' +
            'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ' +
            (collapsed ? 'justify-center px-2' : 'gap-3 px-3')
          }
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className={'shrink-0 transition-transform duration-200 ' + (collapsed ? 'rotate-180' : '')}
          >
            <path d="M15 6l-6 6 6 6" />
          </svg>
          {collapsed ? null : <span>Einklappen</span>}
        </button>

        {account ? (
          <AccountMenu
            accountId={accountId}
            account={account}
            accounts={accounts}
            collapsed={collapsed}
          />
        ) : null}
      </aside>

      {/* One centered content frame with shared responsive air (S7 / 00-A3). */}
      <div className="mx-auto min-w-0 w-full max-w-[1800px] flex-1 px-6 xl:px-8">
        {isLoading ? (
          <main className="mx-auto max-w-2xl px-8 py-16">
            <div
              aria-hidden="true"
              className="h-32 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            />
          </main>
        ) : account === undefined ? (
          <main className="mx-auto max-w-2xl px-8 py-16" role="status">
            <h1 className="font-display text-2xl font-bold">Kein Zugriff auf dieses Konto</h1>
            <p className="mt-3 max-w-prose text-slate">
              Für dieses Konto besteht keine aktive Mitgliedschaft. Die Navigation zeigt nur, was
              für Sie verfügbar ist.
            </p>
            <Button asChild className="mt-6">
              <Link href="/">Zur Kontoauswahl</Link>
            </Button>
          </main>
        ) : (
          children
        )}
      </div>

      {/* Rechte Reminder-/Wächter-Leiste (Demo). Nur bei aktivem Konto und nicht
          für die eingeschränkte Steuerberater-Sicht; ab xl eingeblendet, damit
          schmale Laptops die Inhaltsbreite behalten. */}
      {account && !taxAdvisor ? <ReminderSidebar /> : null}
    </div>
  );
}

/**
 * Compact account switcher at the sidebar foot (S6). One account: name + role,
 * no switcher. Multiple accounts: a native disclosure whose menu lists the other
 * contexts and "Zur Kontoauswahl" — links stay in the DOM (honest, testable),
 * Escape closes and returns focus to the summary. Collapsed rail: a neutral
 * initial with the full name as accessible text/tooltip (no menu when collapsed).
 */
function AccountMenu({
  accountId,
  account,
  accounts,
  collapsed,
}: {
  accountId: string;
  account: MeAccount;
  accounts: MeAccount[];
  collapsed: boolean;
}) {
  const others = accounts.filter((candidate) => candidate.id !== accountId);
  const roleText = ROLE_LABELS[account.role] ?? account.role;
  const initial = account.name.trim().charAt(0).toUpperCase() || 'K';

  if (collapsed) {
    return (
      <div className="mt-4 flex justify-center" title={`${account.name} · ${roleText}`}>
        <span
          aria-hidden="true"
          className="flex h-9 w-9 items-center justify-center rounded-full bg-mint font-semibold text-forest"
        >
          {initial}
        </span>
        <span className="sr-only">
          Aktives Konto: {account.name}, {roleText}
        </span>
      </div>
    );
  }

  if (others.length === 0) {
    return (
      <div className="mt-4 shrink-0 rounded-lg bg-paper px-3 py-2.5">
        <p className="truncate text-sm font-semibold" title={account.name}>
          {account.name}
        </p>
        <p className="truncate text-xs text-slate">{roleText}</p>
      </div>
    );
  }

  return (
    <details
      className="group mt-4 shrink-0"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          const el = event.currentTarget;
          if (el.open) {
            el.open = false;
            el.querySelector('summary')?.focus();
          }
        }
      }}
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg bg-paper px-3 py-2.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold" title={account.name}>
            {account.name}
          </span>
          <span className="block truncate text-xs text-slate">{roleText}</span>
        </span>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="shrink-0 text-slate transition-transform duration-150 group-open:rotate-180"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </summary>
      <div className="mt-1 rounded-lg border border-mint bg-white p-2">
        <p className="px-1 pb-1 text-xs font-semibold text-slate">Konto wechseln</p>
        <ul className="space-y-1" aria-label="Konto wechseln">
          {others.map((candidate) => (
            <li key={candidate.id}>
              <Link
                href={`/a/${candidate.id}`}
                className="block rounded px-2 py-1.5 text-sm text-ink hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <span className="block truncate font-medium" title={candidate.name}>
                  {candidate.name}
                </span>
                <span className="block truncate text-xs text-slate">
                  {ROLE_LABELS[candidate.role] ?? candidate.role}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <Link
          href="/"
          className="mt-1 block rounded px-2 py-1.5 text-sm font-semibold text-green underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          Zur Kontoauswahl
        </Link>
      </div>
    </details>
  );
}
