import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import { showOwnerControls as showBuildingOwnerControls } from '../objekte/buildings-page';

import * as AppShellModule from './app-shell';
import { showOwnerControls as showDashboardOwnerControls } from './dashboard';
import { AccountChooser, autoEntryAccount } from './portal-entry';

const { PortalShellContent } = AppShellModule;
const ACCOUNT_ROOT_SOURCE = readFileSync(
  new URL('../../app/a/[accountId]/page.tsx', import.meta.url),
  'utf8',
);
const APP_SHELL_SOURCE = readFileSync(new URL('./app-shell.tsx', import.meta.url), 'utf8');
const DASHBOARD_SOURCE = readFileSync(new URL('./dashboard.tsx', import.meta.url), 'utf8');
const PORTAL_ENTRY_SOURCE = readFileSync(new URL('./portal-entry.tsx', import.meta.url), 'utf8');
const PAYMENTS_PAGE_SOURCE = readFileSync(
  new URL('../zahlungen/zahlungen-page.tsx', import.meta.url),
  'utf8',
);
const STYLEGUIDE_SOURCE = readFileSync(
  new URL('../../app/styleguide/page.tsx', import.meta.url),
  'utf8',
);
const ROOT_LAYOUT_SOURCE = readFileSync(new URL('../../app/layout.tsx', import.meta.url), 'utf8');
const ERROR_SOURCE = readFileSync(new URL('../../app/error.tsx', import.meta.url), 'utf8');
const GLOBAL_ERROR_SOURCE = readFileSync(
  new URL('../../app/global-error.tsx', import.meta.url),
  'utf8',
);
const NOT_FOUND_SOURCE = readFileSync(new URL('../../app/not-found.tsx', import.meta.url), 'utf8');
const LOADING_SOURCE = readFileSync(new URL('../../app/loading.tsx', import.meta.url), 'utf8');

type Context = {
  id: string;
  name: string;
  role: 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR';
  shape: string;
};

const OWNER: Context = { id: 'owner-1', name: 'Eigene Verwaltung', role: 'OWNER', shape: 'SOLO' };
const EMPLOYEE: Context = {
  id: 'employee-1',
  name: 'Verwaltung Nord',
  role: 'EMPLOYEE',
  shape: 'HAUSVERWALTUNG',
};
const TAX_ADVISOR: Context = {
  id: 'advisor-1',
  name: 'Kanzlei Süd',
  role: 'TAX_ADVISOR',
  shape: 'HAUSVERWALTUNG',
};

describe('M5 account contexts', () => {
  it.each([OWNER, EMPLOYEE])('auto-enters its only $role context', (context) => {
    expect(autoEntryAccount([context])).toEqual(context);
  });

  it('does not auto-enter a tax-adviser context', () => {
    expect(autoEntryAccount([TAX_ADVISOR])).toBeUndefined();
  });

  it('shows every live context as an ordinary URL link when a choice is needed', () => {
    const html = renderToStaticMarkup(<AccountChooser accounts={[OWNER, EMPLOYEE, TAX_ADVISOR]} />);

    expect(html).toContain('Konto auswählen');
    expect(html).toContain('href="/a/owner-1"');
    expect(html).toContain('href="/a/employee-1"');
    expect(html).toContain('href="/a/advisor-1"');
    expect(html).toContain('Steuerberater:in');
  });

  it('offers the same URL-based switcher in a multi-context portal shell', () => {
    const html = renderToStaticMarkup(
      <PortalShellContent
        accountId={OWNER.id}
        account={OWNER}
        accounts={[OWNER, EMPLOYEE]}
        pathname="/a/owner-1"
      >
        <p>Inhalt</p>
      </PortalShellContent>,
    );

    expect(html).toContain('Konto wechseln');
    expect(html).toContain('href="/a/employee-1"');
  });

  it('uses the supplied wordmark and the 1440px content frame', () => {
    const html = renderToStaticMarkup(
      <PortalShellContent
        accountId={OWNER.id}
        account={OWNER}
        accounts={[OWNER]}
        pathname="/a/owner-1"
      >
        <p>Inhalt</p>
      </PortalShellContent>,
    );

    expect(html).toContain('alt="Lokara"');
    expect(APP_SHELL_SOURCE).toContain('src="/lokara-logo.png"');
    // Container-Deckel bewusst über den 00-A3-Default (1440) angehoben (lokale
    // Demo-Fassung: weniger Totraum auf breiten Monitoren).
    expect(APP_SHELL_SOURCE).toContain('max-w-[1800px]');
    expect(APP_SHELL_SOURCE).not.toContain('max-w-[1100px]');
    expect(APP_SHELL_SOURCE).not.toContain('grid size-8 shrink-0 grid-cols-2');
  });

  it('keeps the shell free of a switcher for exactly one context', () => {
    const html = renderToStaticMarkup(
      <PortalShellContent
        accountId={OWNER.id}
        account={OWNER}
        accounts={[OWNER]}
        pathname="/a/owner-1"
      >
        <p>Inhalt</p>
      </PortalShellContent>,
    );

    expect(html).not.toContain('Konto wechseln');
  });

  // Every route behind the Zahlungen screen is `require_owner`
  // (`apps/api/src/lokara_api/routers/payments.py`), so for an EMPLOYEE the nav
  // entry could only ever dead-end in a 403. Hiding it is honesty about scope,
  // not authorization — the API decides that independently (CLAUDE.md § 3.3).
  it('offers the payments screen to an owner', () => {
    const html = renderToStaticMarkup(
      <PortalShellContent
        accountId={OWNER.id}
        account={OWNER}
        accounts={[OWNER]}
        pathname="/a/owner-1"
      >
        <p>Inhalt</p>
      </PortalShellContent>,
    );

    expect(html).toContain('href="/a/owner-1/zahlungen"');
  });

  it('withholds the payments screen from an employee', () => {
    const html = renderToStaticMarkup(
      <PortalShellContent
        accountId={EMPLOYEE.id}
        account={EMPLOYEE}
        accounts={[EMPLOYEE]}
        pathname="/a/employee-1"
      >
        <p>Inhalt</p>
      </PortalShellContent>,
    );

    // Non-vacuity: the employee shell does render a navigation, it just omits
    // this one entry.
    expect(html).toContain('href="/a/employee-1/objekte"');
    expect(html).not.toContain('/zahlungen');
  });

  it('shows the restricted tax workspace for a tax adviser', () => {
    const html = renderToStaticMarkup(
      <PortalShellContent
        accountId={TAX_ADVISOR.id}
        account={TAX_ADVISOR}
        accounts={[TAX_ADVISOR, OWNER]}
        pathname="/a/advisor-1/steuern"
      >
        <p>RESTRICTED_TAX_WORKSPACE</p>
      </PortalShellContent>,
    );

    expect(html).toContain('RESTRICTED_TAX_WORKSPACE');
    expect(html).toContain('href="/a/advisor-1/steuern"');
    expect(html).toContain('href="/"');
    expect(html).not.toContain('Steuerfunktionen werden vorbereitet');
    expect(html).not.toContain('Abrechnung erstellen');
  });

  it('redirects every tax-adviser landing and non-tax path through the shared helper', () => {
    const redirectPath = (AppShellModule as Record<string, unknown>).taxAdvisorRedirectPath;
    expect(redirectPath).toBeTypeOf('function');
    if (typeof redirectPath !== 'function') throw new Error('taxAdvisorRedirectPath is missing');
    expect(redirectPath('TAX_ADVISOR', 'advisor-1', '/a/advisor-1')).toBe('/a/advisor-1/steuern');
    expect(redirectPath('TAX_ADVISOR', 'advisor-1', '/a/advisor-1/objekte')).toBe(
      '/a/advisor-1/steuern',
    );
    expect(redirectPath('TAX_ADVISOR', 'advisor-1', '/a/advisor-1/steuern')).toBeNull();
    expect(redirectPath('OWNER', 'owner-1', '/a/owner-1')).toBeNull();
    expect(ACCOUNT_ROOT_SOURCE).toContain('taxAdvisorLandingPath');
    expect(ACCOUNT_ROOT_SOURCE).toMatch(/redirect\([^)]*taxAdvisorLandingPath/);
    expect(APP_SHELL_SOURCE).toContain('taxAdvisorRedirectPath');
  });

  it('limits employees to the assigned-building surface and removes owner-only actions', () => {
    expect(showBuildingOwnerControls('EMPLOYEE')).toBe(false);
    expect(showDashboardOwnerControls('EMPLOYEE')).toBe(false);
    expect(showBuildingOwnerControls('OWNER')).toBe(true);
    expect(showDashboardOwnerControls('OWNER')).toBe(true);
  });

  it('keeps UI-00 free of development copy and adds the global states', () => {
    expect(
      `${APP_SHELL_SOURCE}\n${DASHBOARD_SOURCE}\n${PORTAL_ENTRY_SOURCE}\n${PAYMENTS_PAGE_SOURCE}\n${STYLEGUIDE_SOURCE}`,
    ).not.toMatch(
      /serverseitig|Kontext kommt aus der URL|uv run lokara-api|API und Datenbank prüfen|Migration Phase F|Auth-Interceptor/,
    );
    expect(ROOT_LAYOUT_SOURCE).toContain(
      'Vermieten leicht gemacht — Verwaltung über den ganzen Lebenszyklus.',
    );
    expect(ERROR_SOURCE).toContain('Etwas ist schiefgelaufen');
    expect(ERROR_SOURCE).toContain('Erneut versuchen');
    expect(GLOBAL_ERROR_SOURCE).toContain('Etwas ist schiefgelaufen');
    expect(GLOBAL_ERROR_SOURCE).toContain('<html lang="de"');
    expect(GLOBAL_ERROR_SOURCE).toContain('montserrat.variable');
    expect(GLOBAL_ERROR_SOURCE).toContain('manrope.variable');
    expect(NOT_FOUND_SOURCE).toContain('Seite nicht gefunden');
    expect(NOT_FOUND_SOURCE).toContain('OverviewLink');
    expect(LOADING_SOURCE).toContain('Seite wird geladen');
    expect(LOADING_SOURCE).toContain('motion-reduce:animate-none');
  });
});
