// @vitest-environment happy-dom

import React, { act } from 'react';
import { readFileSync } from 'node:fs';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { MeAccount } from '@/lib/contracts';

import { PortalShellContent } from './app-shell';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('next/image', () => ({
  default: ({
    priority: _priority,
    ...props
  }: React.ImgHTMLAttributes<HTMLImageElement> & { priority?: boolean }) => (
    // The native image is sufficient for shell semantics in happy-dom.
    <img {...props} />
  ),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => '/a/account-1',
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock('./queries', () => ({ useMe: vi.fn() }));

type Role = 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR';

const NAVIGATION_BY_ROLE: Record<Role, string[]> = {
  OWNER: [
    'Übersicht',
    'Objekte',
    'Zahlungen',
    'Kosten erfassen',
    'Zähler',
    'Abrechnungen',
    'Wächter',
    'Steuern',
  ],
  EMPLOYEE: ['Übersicht', 'Objekte', 'Kosten erfassen', 'Zähler', 'Abrechnungen', 'Wächter'],
  TAX_ADVISOR: ['Steuern'],
};

function account(id: string, role: Role = 'OWNER', name = `Konto ${id}`): MeAccount {
  return { id, role, name } as MeAccount;
}

function findButton(name: string): HTMLButtonElement {
  const button = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => candidate.getAttribute('aria-label') === name || candidate.textContent === name,
  );
  expect(button, `button "${name}" is missing`).toBeDefined();
  return button as HTMLButtonElement;
}

function press(target: Element, key: string): void {
  target.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key }));
}

describe('UI-02 rendered app shell', () => {
  let container: HTMLDivElement;
  let root: Root;

  function renderShell({
    accountId = 'account-1',
    activeAccount = account(accountId),
    accounts,
    pathname = `/a/${accountId}`,
    isLoading = false,
    isError = false,
    onRetry,
  }: {
    accountId?: string;
    activeAccount?: MeAccount | null;
    accounts?: MeAccount[];
    pathname?: string;
    isLoading?: boolean;
    isError?: boolean;
    onRetry?: () => void;
  } = {}): void {
    const availableAccounts = accounts ?? (activeAccount ? [activeAccount] : []);
    act(() => {
      root.render(
        <PortalShellContent
          accountId={accountId}
          account={activeAccount ?? undefined}
          accounts={availableAccounts}
          pathname={pathname}
          isLoading={isLoading}
          isError={isError}
          onRetry={onRetry}
        >
          <main>Fachinhalt</main>
        </PortalShellContent>,
      );
    });
  }

  beforeEach(() => {
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
    window.localStorage.clear();
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: false }),
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.restoreAllMocks();
  });

  it('restores and persists independent collapse preferences for two accounts', () => {
    window.localStorage.setItem('lokara.sidebar.collapsed.v1:account-1', 'true');
    window.localStorage.setItem('lokara.sidebar.collapsed.v1:account-2', 'false');

    renderShell({ accountId: 'account-1', activeAccount: account('account-1') });
    const firstToggle = findButton('Navigation ausklappen');
    act(() => firstToggle.click());
    expect(firstToggle.getAttribute('aria-label')).toBe('Navigation einklappen');
    expect(window.localStorage.getItem('lokara.sidebar.collapsed.v1:account-1')).toBe('false');
    expect(window.localStorage.getItem('lokara.sidebar.collapsed.v1:account-2')).toBe('false');

    renderShell({ accountId: 'account-2', activeAccount: account('account-2') });
    const secondToggle = findButton('Navigation einklappen');
    act(() => secondToggle.click());
    expect(secondToggle.getAttribute('aria-label')).toBe('Navigation ausklappen');
    expect(window.localStorage.getItem('lokara.sidebar.collapsed.v1:account-1')).toBe('false');
    expect(window.localStorage.getItem('lokara.sidebar.collapsed.v1:account-2')).toBe('true');
  });

  it.each(Object.entries(NAVIGATION_BY_ROLE) as [Role, string[]][])(
    'renders the %s navigation matrix',
    (role, expectedLabels) => {
      renderShell({ activeAccount: account('account-1', role) });
      const nav = document.querySelector('nav[aria-label="Hauptnavigation"]');
      expect(nav).not.toBeNull();
      expect(
        Array.from(nav?.querySelectorAll('a') ?? [], (link) => link.getAttribute('aria-label')),
      ).toEqual(expectedLabels);
    },
  );

  it('marks Objekte active on an Einheiten detail route', () => {
    renderShell({ pathname: '/a/account-1/einheiten/unit-1' });
    const current = document.querySelectorAll('nav [aria-current="page"]');

    expect(current).toHaveLength(1);
    expect(current[0]?.getAttribute('aria-label')).toBe('Objekte');
  });

  it('closes a click-opened account menu with Escape while focus stays on the trigger', () => {
    renderShell({ accounts: [account('account-1'), account('account-2')] });
    const trigger = findButton('Konto wechseln');
    trigger.focus();

    act(() => trigger.click());
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    expect(document.activeElement).toBe(trigger);

    act(() => press(trigger, 'Escape'));
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(trigger);
  });

  it('opens the account menu with ArrowDown and restores trigger focus after Escape', async () => {
    renderShell({
      accounts: [account('account-1'), account('account-2', 'OWNER', 'Zweites Konto')],
    });
    const trigger = findButton('Konto wechseln');
    trigger.focus();

    await act(async () => {
      press(trigger, 'ArrowDown');
      await new Promise((resolve) => window.requestAnimationFrame(() => resolve(undefined)));
    });

    const alternateAccount = document.querySelector<HTMLAnchorElement>(
      '[role="menuitem"][href="/a/account-2"]',
    );
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    expect(document.activeElement).toBe(alternateAccount);

    act(() => press(alternateAccount as HTMLAnchorElement, 'Escape'));
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(trigger);
  });

  it('renders the German loading state without role navigation', () => {
    renderShell({ isLoading: true });

    const status = document.querySelector('[role="status"][aria-busy="true"]');
    expect(status?.textContent).toContain('Lokara wird geladen …');
    expect(document.querySelector('nav[aria-label="Hauptnavigation"]')).toBeNull();
  });

  it('renders the German error state, focuses its heading and retries', () => {
    const onRetry = vi.fn();
    renderShell({ isError: true, onRetry });

    const heading = document.querySelector('h1');
    expect(heading?.textContent).toBe('Lokara konnte nicht geladen werden');
    expect(document.activeElement).toBe(heading);

    act(() => findButton('Erneut versuchen').click());
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('renders the German no-access state and account-selection action', () => {
    renderShell({ activeAccount: null, accounts: [] });

    expect(document.querySelector('h1')?.textContent).toBe('Kein Zugriff auf dieses Konto');
    const selection = document.querySelector<HTMLAnchorElement>('a[href="/"]');
    expect(selection?.textContent).toContain('Zur Kontoauswahl');
  });
});

const REDUCED_MOTION_FILES = [
  '../beleg/beleg-page.tsx',
  '../kosten/costs-page.tsx',
  '../objekte/buildings-page.tsx',
  '../objekte/building-detail-page.tsx',
  '../objekte/unit-detail-page.tsx',
  './statement.tsx',
  '../zaehler/meters-page.tsx',
  '../zahlungen/zahlungen-page.tsx',
] as const;

describe('UI-02 migrated loading motion', () => {
  it.each(REDUCED_MOTION_FILES)('%s disables every pulse under reduced motion', (relativePath) => {
    const source = readFileSync(new URL(relativePath, import.meta.url), 'utf8');
    const pulseCount = source.match(/animate-pulse/g)?.length ?? 0;
    const pulseClasses = Array.from(
      source.matchAll(/className="([^"]*\banimate-pulse\b[^"]*)"/g),
      (match) => match[1] ?? '',
    );

    expect(pulseCount, `${relativePath} should contain a loading pulse`).toBeGreaterThan(0);
    expect(pulseClasses, `${relativePath} has an uninspectable pulse class`).toHaveLength(pulseCount);
    for (const className of pulseClasses) {
      expect(className, `${relativePath} leaves a pulse active under reduced motion`).toContain(
        'motion-reduce:animate-none',
      );
    }
  });
});
