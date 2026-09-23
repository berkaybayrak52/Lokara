'use client';

import { Button } from '@lokara/ui';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import React, { useEffect, useRef, useState } from 'react';

import type { MeAccount } from '@/lib/contracts';
import { endSession } from '@/lib/api';

import { useMe } from './queries';
import { ReminderSidebar } from './reminder-sidebar';

/**
 * The account context lives in the URL. The menu only reflects relationships
 * returned by /me; every destination remains independently authorized by the API.
 */

const SIDEBAR_PREFERENCE_KEY = 'lokara.sidebar.collapsed.v1';

function sidebarPreferenceKey(accountId: string): string {
  return `${SIDEBAR_PREFERENCE_KEY}:${accountId}`;
}

const ROLE_LABELS: Record<string, string> = {
  OWNER: 'Inhaber:in',
  EMPLOYEE: 'Mitarbeiter:in',
  TAX_ADVISOR: 'Steuerberater:in',
};

type IconName =
  | 'overview'
  | 'buildings'
  | 'payments'
  | 'costs'
  | 'receipts'
  | 'meters'
  | 'statements'
  | 'guards'
  | 'investment'
  | 'tax';

interface NavItem {
  href: (accountId: string) => string;
  label: string;
  icon: IconName;
  activePrefixes: string[];
  visibleFor?: (role: string) => boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: (id) => `/a/${id}`, label: 'Übersicht', icon: 'overview', activePrefixes: [] },
  {
    href: (id) => `/a/${id}/objekte`,
    label: 'Objekte',
    icon: 'buildings',
    activePrefixes: ['/objekte', '/einheiten'],
  },
  {
    href: (id) => `/a/${id}/zahlungen`,
    label: 'Zahlungen',
    icon: 'payments',
    activePrefixes: ['/zahlungen'],
    visibleFor: (role) => role === 'OWNER',
  },
  {
    href: (id) => `/a/${id}/kosten`,
    label: 'Kosten erfassen',
    icon: 'costs',
    activePrefixes: ['/kosten'],
  },
  {
    href: (id) => `/a/${id}/zaehler`,
    label: 'Zähler',
    icon: 'meters',
    activePrefixes: ['/zaehler'],
  },
  {
    href: (id) => `/a/${id}/uvi`,
    label: 'UVI',
    icon: 'statements',
    activePrefixes: ['/uvi'],
    visibleFor: (role) => role === 'OWNER',
  },
  {
    href: (id) => `/a/${id}/abrechnung`,
    label: 'Abrechnungen',
    icon: 'statements',
    activePrefixes: ['/abrechnung'],
  },
  {
    href: (id) => `/a/${id}/waechter`,
    label: 'Wächter',
    icon: 'guards',
    activePrefixes: ['/waechter'],
    visibleFor: (role) => role === 'OWNER' || role === 'EMPLOYEE',
  },
  {
    href: (id) => `/a/${id}/investment`,
    label: 'Investition',
    icon: 'investment',
    activePrefixes: ['/investment'],
    visibleFor: (role) => role === 'OWNER',
  },
  {
    href: (id) => `/a/${id}/steuern`,
    label: 'Steuern',
    icon: 'tax',
    activePrefixes: ['/steuern'],
    visibleFor: (role) => role === 'OWNER' || role === 'TAX_ADVISOR',
  },
];

function isKnownRole(role: string | undefined): boolean {
  return role === 'OWNER' || role === 'EMPLOYEE' || role === 'TAX_ADVISOR';
}

function visibleNavigation(account: MeAccount): NavItem[] {
  if (!isKnownRole(account.role)) return [];
  return NAV_ITEMS.filter(
    (item) =>
      (item.visibleFor === undefined || item.visibleFor(account.role)) &&
      (account.role !== 'TAX_ADVISOR' || item.label === 'Steuern'),
  );
}

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
  const me = useMe();
  const account = me.data?.accounts.find((candidate) => candidate.id === accountId);
  const redirectPath = taxAdvisorRedirectPath(account?.role, accountId, pathname);

  useEffect(() => {
    if (redirectPath) router.replace(redirectPath);
  }, [redirectPath, router]);

  if (redirectPath) {
    return (
      <main className="px-6 py-16" role="status">
        Steuerbereich wird geöffnet …
      </main>
    );
  }

  return (
    <PortalShellContent
      accountId={accountId}
      account={account}
      accounts={me.data?.accounts ?? []}
      pathname={pathname}
      isLoading={me.isPending}
      isError={me.isError}
      onRetry={() => void me.refetch()}
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
  isError = false,
  onRetry,
  children,
}: {
  accountId: string;
  account: MeAccount | undefined;
  accounts: MeAccount[];
  pathname: string;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
  children: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState<boolean | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(sidebarPreferenceKey(accountId));
    setCollapsed(
      stored === null ? window.matchMedia('(max-width: 1439px)').matches : stored === 'true',
    );
  }, [accountId]);

  const toggleSidebar = () => {
    setCollapsed((current) => {
      const next = !(current ?? window.matchMedia('(max-width: 1439px)').matches);
      window.localStorage.setItem(sidebarPreferenceKey(accountId), String(next));
      return next;
    });
  };

  const collapsedNow = collapsed === true;
  const sidebarWidth =
    collapsed === null ? 'w-[248px] max-[1439px]:w-[72px]' : collapsed ? 'w-[72px]' : 'w-[248px]';
  const labelVisibility =
    collapsed === null ? 'max-[1439px]:sr-only' : collapsedNow ? 'sr-only' : '';
  const fullLogoVisibility =
    collapsed === null
      ? 'h-7 w-auto max-w-full max-[1439px]:hidden'
      : collapsedNow
        ? 'hidden'
        : 'h-7 w-auto max-w-full';
  const signetVisibility =
    collapsed === null ? 'hidden size-7 max-[1439px]:block' : collapsedNow ? 'size-7' : 'hidden';

  return (
    <div className="@container/lokara-shell flex min-h-dvh min-w-0 bg-paper text-ink">
      <aside
        className={`${sidebarWidth} max-md:w-[72px] sticky top-0 flex h-dvh shrink-0 flex-col overflow-visible border-r border-mint bg-white px-3 py-5 @max-[320px]/lokara-shell:w-12 @max-[320px]/lokara-shell:px-0`}
      >
        <div className="flex h-10 shrink-0 items-center">
          <Link
            href={`/a/${accountId}`}
            aria-label="Zur Übersicht"
            title="Zur Übersicht"
            className="flex h-10 min-w-0 flex-1 items-center justify-center rounded-lg px-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            <Image
              src="/lokara-logo.png"
              alt="Lokara"
              width={103}
              height={28}
              priority
              className={`${fullLogoVisibility} max-md:hidden`}
            />
            <Image
              src="/icon.png"
              alt=""
              width={28}
              height={28}
              className={`${signetVisibility} max-md:block`}
            />
          </Link>
        </div>

        {account && account.role !== 'TAX_ADVISOR' ? (
          <div className="@max-[320px]/lokara-shell:mt-2 @max-[320px]/lokara-shell:flex @max-[320px]/lokara-shell:shrink-0 @max-[320px]/lokara-shell:justify-center @max-[320px]/lokara-shell:[&>div]:relative @max-[320px]/lokara-shell:[&>div]:top-auto @max-[320px]/lokara-shell:[&>div]:right-auto @max-[320px]/lokara-shell:[&_[role=dialog]]:fixed @max-[320px]/lokara-shell:[&_[role=dialog]]:top-2 @max-[320px]/lokara-shell:[&_[role=dialog]]:right-2 @max-[320px]/lokara-shell:[&_[role=dialog]]:bottom-2 @max-[320px]/lokara-shell:[&_[role=dialog]]:left-14 @max-[320px]/lokara-shell:[&_[role=dialog]]:mt-0 @max-[320px]/lokara-shell:[&_[role=dialog]]:max-h-none @max-[320px]/lokara-shell:[&_[role=dialog]]:w-auto @max-[320px]/lokara-shell:[&_[role=dialog]]:p-2">
            <ReminderSidebar />
          </div>
        ) : null}

        {isLoading ? (
          <SidebarSkeleton />
        ) : account && isKnownRole(account.role) ? (
          <nav
            aria-label="Hauptnavigation"
            className="mt-7 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto overscroll-contain"
          >
            {visibleNavigation(account).map((item) => {
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
                  aria-label={item.label}
                  aria-current={active ? 'page' : undefined}
                  title={item.label}
                  className={
                    'flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors duration-150 ease-out @max-[320px]/lokara-shell:justify-center @max-[320px]/lokara-shell:px-1 @max-[320px]/lokara-shell:focus-visible:outline-offset-[-2px] ' +
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none ' +
                    (active ? 'bg-mint font-semibold text-forest' : 'text-ink hover:bg-mint/60')
                  }
                >
                  <NavIcon name={item.icon} />
                  <span
                    className={`${labelVisibility} max-md:sr-only truncate transition-opacity duration-[180ms] motion-reduce:transition-none`}
                  >
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </nav>
        ) : (
          <div className="flex-1" />
        )}

        {account && isKnownRole(account.role) ? (
          <AccountMenu
            account={account}
            accountId={accountId}
            accounts={accounts}
            collapsed={collapsedNow}
            defaultResponsive={collapsed === null}
          />
        ) : null}

        <button
          type="button"
          aria-label={collapsedNow ? 'Navigation ausklappen' : 'Navigation einklappen'}
          title={collapsedNow ? 'Navigation ausklappen' : 'Navigation einklappen'}
          onClick={toggleSidebar}
          className="mt-3 flex min-h-10 shrink-0 items-center justify-center rounded-lg text-slate transition-colors duration-150 hover:bg-mint hover:text-forest focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none max-md:hidden"
        >
          <CollapseIcon collapsed={collapsedNow} />
          <span className="sr-only">
            {collapsedNow ? 'Navigation ausklappen' : 'Navigation einklappen'}
          </span>
        </button>
      </aside>

      <div className="min-w-0 flex-1">
        <div className="mx-auto min-w-0 w-full max-w-[1440px] px-6 min-[1440px]:px-8 min-[1800px]:px-10 @max-[320px]/lokara-shell:px-2">
          {isLoading ? (
            <ShellLoadingState />
          ) : isError ? (
            <ShellStatus
              title="Lokara konnte nicht geladen werden"
              description="Bitte versuchen Sie es erneut."
              action={
                <Button onClick={onRetry} disabled={onRetry === undefined}>
                  Erneut versuchen
                </Button>
              }
            />
          ) : account === undefined || !isKnownRole(account.role) ? (
            <ShellStatus
              title="Kein Zugriff auf dieses Konto"
              description="Für dieses Konto besteht keine verfügbare Mitgliedschaft."
              action={
                <Button asChild>
                  <Link href="/">Zur Kontoauswahl</Link>
                </Button>
              }
            />
          ) : (
            children
          )}
        </div>
      </div>
    </div>
  );
}

function SidebarSkeleton() {
  return (
    <div className="mt-7 flex flex-1 flex-col gap-2" aria-hidden="true">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="h-11 animate-pulse rounded-lg bg-mint/60 motion-reduce:animate-none"
        />
      ))}
    </div>
  );
}

function ShellLoadingState() {
  return (
    <main className="py-10" role="status" aria-busy="true">
      <span className="sr-only">Lokara wird geladen …</span>
      <div aria-hidden="true" className="space-y-8">
        <div className="space-y-3">
          <div className="h-9 w-56 animate-pulse rounded-lg bg-mint/60 motion-reduce:animate-none" />
          <div className="h-5 max-w-xl animate-pulse rounded bg-mint/60 motion-reduce:animate-none" />
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="h-40 animate-pulse rounded-xl bg-mint/60 motion-reduce:animate-none"
            />
          ))}
        </div>
      </div>
    </main>
  );
}

function ShellStatus({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action: React.ReactNode;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => headingRef.current?.focus(), []);

  return (
    <main className="py-16">
      <h1 ref={headingRef} tabIndex={-1} className="font-display text-3xl font-bold outline-none">
        {title}
      </h1>
      <p className="mt-3 max-w-prose text-slate">{description}</p>
      <div className="mt-6">{action}</div>
    </main>
  );
}

function AccountMenu({
  account,
  accountId,
  accounts,
  collapsed,
  defaultResponsive,
}: {
  account: MeAccount;
  accountId: string;
  accounts: MeAccount[];
  collapsed: boolean;
  defaultResponsive: boolean;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const initials = account.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toLocaleUpperCase('de-DE'))
    .join('');

  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', closeOutside);
    return () => document.removeEventListener('mousedown', closeOutside);
  }, [open]);

  const focusMenuItem = (position: 'first' | 'last') => {
    window.requestAnimationFrame(() => {
      const items = menuRef.current?.querySelectorAll<HTMLElement>(
        '[role="menuitem"]:not([aria-disabled="true"])',
      );
      const target = position === 'first' ? items?.[0] : items?.[items.length - 1];
      target?.focus();
    });
  };

  return (
    <div ref={rootRef} className="relative mt-8 shrink-0">
      <div
        ref={menuRef}
        role="menu"
        aria-label="Konten"
        hidden={!open}
        className="absolute bottom-[calc(100%+0.5rem)] left-0 z-20 min-w-64 rounded-xl border border-mint bg-white p-2 shadow-lg @max-[320px]/lokara-shell:min-w-0 @max-[320px]/lokara-shell:w-[calc(100cqw-1rem)] @max-[320px]/lokara-shell:[overflow-wrap:anywhere]"
        onKeyDown={(event) => {
          const items = Array.from(
            event.currentTarget.querySelectorAll<HTMLElement>(
              '[role="menuitem"]:not([aria-disabled="true"])',
            ),
          );
          const current = items.indexOf(document.activeElement as HTMLElement);
          if (event.key === 'Escape') {
            event.preventDefault();
            setOpen(false);
            triggerRef.current?.focus();
          } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            items[(current + 1 + items.length) % items.length]?.focus();
          } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            items[(current - 1 + items.length) % items.length]?.focus();
          }
        }}
      >
        <p className="px-3 pt-2 pb-1 text-xs font-semibold tracking-wide text-slate uppercase">
          Konten
        </p>
        {accounts.map((candidate) =>
          candidate.id === accountId ? (
            <span
              key={candidate.id}
              role="menuitem"
              aria-current="page"
              aria-disabled="true"
              className="flex rounded-lg bg-mint px-3 py-2 text-sm font-semibold text-forest"
            >
              {candidate.name}
            </span>
          ) : (
            <Link
              key={candidate.id}
              role="menuitem"
              tabIndex={open ? 0 : -1}
              href={`/a/${candidate.id}`}
              className="flex rounded-lg px-3 py-2 text-sm hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              {candidate.name}
            </Link>
          ),
        )}
        <div className="my-2 border-t border-mint" />
        <Link
          href="/"
          role="menuitem"
          tabIndex={open ? 0 : -1}
          className="flex rounded-lg px-3 py-2 text-sm font-semibold text-green hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          Zur Kontoauswahl
        </Link>
        <button
          type="button"
          role="menuitem"
          tabIndex={open ? 0 : -1}
          onClick={() => void endSession()}
          className="flex w-full rounded-lg px-3 py-2 text-left text-sm font-semibold text-ink hover:bg-mint/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          Abmelden
        </button>
      </div>

      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={accounts.length > 1 ? 'Konto wechseln' : 'Kontomenü öffnen'}
        title={account.name}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === 'Escape' && open) {
            event.preventDefault();
            setOpen(false);
            triggerRef.current?.focus();
          } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            setOpen(true);
            focusMenuItem(event.key === 'ArrowDown' ? 'first' : 'last');
          }
        }}
        className="flex min-h-14 w-full items-center gap-3 rounded-xl bg-paper px-3 text-left transition-colors duration-150 hover:bg-mint focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none @max-[320px]/lokara-shell:justify-center @max-[320px]/lokara-shell:px-1 @max-[320px]/lokara-shell:focus-visible:outline-offset-[-2px]"
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-mint font-display text-xs font-bold text-forest">
          {initials || 'K'}
        </span>
        <span
          className={`${defaultResponsive ? 'max-[1439px]:sr-only' : collapsed ? 'sr-only' : ''} max-md:sr-only min-w-0 flex-1`}
        >
          <span className="block truncate text-sm font-semibold" title={account.name}>
            {account.name}
          </span>
          <span className="block truncate text-xs text-slate">
            {ROLE_LABELS[account.role] ?? account.role}
          </span>
        </span>
        <ChevronIcon
          className={`${defaultResponsive ? 'max-[1439px]:hidden' : collapsed ? 'hidden' : ''} max-md:hidden`}
        />
      </button>
    </div>
  );
}

function NavIcon({ name }: { name: IconName }) {
  const paths: Record<IconName, React.ReactNode> = {
    overview: <path d="M4 13h6V4H4v9Zm10 7h6V11h-6v9ZM4 20h6v-3H4v3Zm10-13h6V4h-6v3Z" />,
    buildings: (
      <>
        <path d="M4 21V7l8-4 8 4v14" />
        <path d="M2 21h20M8 10h2m4 0h2m-8 4h2m4 0h2m-5 7v-4h2v4" />
      </>
    ),
    payments: (
      <>
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <path d="M3 9h18M7 15h4" />
      </>
    ),
    costs: (
      <>
        <path d="M7 3h10v18l-2.5-1.5L12 21l-2.5-1.5L7 21V3Z" />
        <path d="M10 8h4m-4 4h4" />
      </>
    ),
    receipts: (
      <>
        <path d="M6 3h9l3 3v15H6V3Z" />
        <path d="M15 3v4h4M9 11h6m-6 4h6" />
      </>
    ),
    meters: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m12 12 4-3M8 17h8" />
      </>
    ),
    statements: (
      <>
        <path d="M5 3h14v18H5V3Z" />
        <path d="M8 8h8m-8 4h8m-8 4h5" />
      </>
    ),
    guards: (
      <>
        <path d="M12 3 5 6v5c0 4.6 2.8 8.1 7 10 4.2-1.9 7-5.4 7-10V6l-7-3Z" />
        <path d="M12 8v5m0 3h.01" />
      </>
    ),
    investment: (
      <>
        <path d="M4 20V10m5 10V4m6 16v-7m5 7V7" />
        <path d="m3 8 6-5 6 8 6-6" />
      </>
    ),
    tax: (
      <>
        <path d="M4 8h16M6 8V6l6-3 6 3v2M7 8v9m5-9v9m5-9v9M4 21h16v-4H4v4Z" />
      </>
    ),
  };
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="size-5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

function CollapseIcon({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="size-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={collapsed ? 'm9 6 6 6-6 6' : 'm15 6-6 6 6 6'} />
    </svg>
  );
}

function ChevronIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={`size-4 shrink-0 ${className}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m7 10 5 5 5-5" />
    </svg>
  );
}
