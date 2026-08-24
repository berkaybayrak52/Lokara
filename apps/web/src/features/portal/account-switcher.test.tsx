import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { showOwnerControls as showBuildingOwnerControls } from '../objekte/buildings-page';

import { PortalShellContent } from './app-shell';
import { showOwnerControls as showDashboardOwnerControls } from './dashboard';
import { AccountChooser, autoEntryAccount } from './portal-entry';

type Context = { id: string; name: string; role: 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR'; shape: string };

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

  it('shows the tax-adviser preparation state instead of the owner portal', () => {
    const html = renderToStaticMarkup(
      <PortalShellContent
        accountId={TAX_ADVISOR.id}
        account={TAX_ADVISOR}
        accounts={[TAX_ADVISOR, OWNER]}
        pathname="/a/advisor-1"
      >
        <p>OWNER_SCREEN_MUST_NOT_RENDER</p>
      </PortalShellContent>,
    );

    expect(html).toContain('Steuerfunktionen werden vorbereitet');
    expect(html).toContain('href="/"');
    expect(html).not.toContain('OWNER_SCREEN_MUST_NOT_RENDER');
    expect(html).not.toContain('Abrechnung erstellen');
  });

  it('limits employees to the assigned-building surface and removes owner-only actions', () => {
    expect(showBuildingOwnerControls('EMPLOYEE')).toBe(false);
    expect(showDashboardOwnerControls('EMPLOYEE')).toBe(false);
    expect(showBuildingOwnerControls('OWNER')).toBe(true);
    expect(showDashboardOwnerControls('OWNER')).toBe(true);
  });
});
