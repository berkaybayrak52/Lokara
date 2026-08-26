import React from 'react';
import { existsSync, readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import * as Contracts from '@/lib/contracts';

const DASHBOARD_URL = new URL('./dashboard.tsx', import.meta.url);
const QUERIES_URL = new URL('./queries.ts', import.meta.url);
const WIDGETS_URL = new URL('./dashboard-widgets.tsx', import.meta.url);
const DEMO_FINANCE_URL = new URL('./dashboard-demo.ts', import.meta.url);

const DASHBOARD_SOURCE = readFileSync(DASHBOARD_URL, 'utf8');
const QUERIES_SOURCE = readFileSync(QUERIES_URL, 'utf8');
const WIDGETS_SOURCE = existsSync(WIDGETS_URL) ? readFileSync(WIDGETS_URL, 'utf8') : '';
const DEMO_FINANCE_SOURCE = existsSync(DEMO_FINANCE_URL)
  ? readFileSync(DEMO_FINANCE_URL, 'utf8')
  : '';

const FIVE_FIELDS = [
  'buildingCount',
  'unitCount',
  'occupiedUnitCount',
  'vacantUnitCount',
  'mietSollCentsMonthly',
] as const;

type SchemaLike = {
  parse(value: unknown): Record<string, unknown>;
  safeParse(value: unknown): { success: boolean };
};

async function loadWidgets(): Promise<Record<string, unknown>> {
  if (!existsSync(WIDGETS_URL)) {
    expect.fail('UI-01 dashboard-widgets.tsx is missing');
  }
  const modulePath = './dashboard-widgets';
  return import(/* @vite-ignore */ modulePath);
}

function component(
  widgets: Record<string, unknown>,
  name: 'OccupancyCard' | 'UnavailableCard' | 'DashboardSkeleton',
): React.ComponentType<Record<string, unknown>> {
  const candidate = widgets[name];
  expect(candidate, `${name} export is missing`).toBeTypeOf('function');
  return candidate as React.ComponentType<Record<string, unknown>>;
}

describe('UI-01 portfolio response and query boundary', () => {
  it('validates the five integer fields supplied by the server read model', () => {
    const schema = (Contracts as Record<string, unknown>).PortfolioOverviewResponseSchema;
    expect(schema, 'PortfolioOverviewResponseSchema is missing').toBeDefined();

    const parsed = (schema as SchemaLike).parse({
      buildingCount: 2,
      unitCount: 4,
      occupiedUnitCount: 3,
      vacantUnitCount: 1,
      mietSollCentsMonthly: 271_500,
    });
    expect(Object.keys(parsed).sort()).toEqual([...FIVE_FIELDS].sort());
    expect(
      (schema as SchemaLike).safeParse({
        buildingCount: 2.5,
        unitCount: 4,
        occupiedUnitCount: 3,
        vacantUnitCount: 1,
        mietSollCentsMonthly: 271_500,
      }).success,
    ).toBe(false);
  });

  it('uses an account-keyed, non-retrying portfolio overview hook', () => {
    expect(QUERIES_SOURCE).toContain('usePortfolioOverview');
    expect(QUERIES_SOURCE).toContain("['account', accountId, 'portfolio-overview']");
    expect(QUERIES_SOURCE).toContain('`/a/${accountId}/portfolio/overview`');
    expect(QUERIES_SOURCE).toContain('PortfolioOverviewResponseSchema');
    expect(QUERIES_SOURCE).toMatch(/usePortfolioOverview[\s\S]*?retry:\s*false/);
  });
});

describe('UI-01 dashboard composition', () => {
  it('uses portfolio truth instead of the single-building summary', () => {
    expect(DASHBOARD_SOURCE).toContain('usePortfolioOverview');
    expect(DASHBOARD_SOURCE).not.toContain('useAccountSummary');
    expect(DASHBOARD_SOURCE).toContain('mietSollCentsMonthly');
    expect(DASHBOARD_SOURCE).toContain('occupiedUnitCount');
    expect(DASHBOARD_SOURCE).toContain('unitCount');
    expect(DASHBOARD_SOURCE).toContain('vacantUnitCount');
    expect(DASHBOARD_SOURCE).toContain('buildingCount');
    expect(DASHBOARD_SOURCE).toContain('href={`/a/${accountId}/objekte`}');
  });

  // Spec 01_Dashboard.md (Option B): das Dashboard zeigt bewusst als Demo
  // gekennzeichnete Finanz- und Ticket-Werte, aus dem echten Mietsoll abgeleitet.
  // (Löst die frühere "keine erfundenen Werte"-Prüfung ab; lokale Demo-Fassung.)
  it('wires clearly-labelled demo finance and task counters from the real Mietsoll', () => {
    const ui01Source = `${DASHBOARD_SOURCE}\n${WIDGETS_SOURCE}\n${DEMO_FINANCE_SOURCE}`;
    expect(ui01Source).toContain('Mieteinnahmen');
    expect(ui01Source).toContain('Offene Posten');
    expect(ui01Source).toContain('CashflowWidget');
    expect(ui01Source).toContain('Aufgaben & Tickets');

    // Demo-Finanz wird aus dem echten Mietsoll abgeleitet und lebt nur in dashboard-demo.ts.
    expect(DASHBOARD_SOURCE).toContain('deriveDemoFinance');
    expect(DASHBOARD_SOURCE).toContain('DEMO_TASK_COUNTS');
    expect(DEMO_FINANCE_SOURCE).not.toBe('');
    expect(DEMO_FINANCE_SOURCE).toContain('deriveDemoFinance');
    expect(DEMO_FINANCE_SOURCE).toMatch(/overdue:\s*5/);
    expect(DEMO_FINANCE_SOURCE).toMatch(/today:\s*10/);
    expect(DEMO_FINANCE_SOURCE).toMatch(/week:\s*20/);

    // Ehrliche Kennzeichnung: die Werte sind sichtbar als Demonstration markiert.
    expect(WIDGETS_SOURCE).toContain('Demonstrationswerte');
  });

  it('keeps German loading, empty, failure, statement and owner-only demo flows', () => {
    expect(DASHBOARD_SOURCE).toContain('Ihr Bestand auf einen Blick.');
    expect(DASHBOARD_SOURCE).toContain('Noch keine Daten');
    expect(DASHBOARD_SOURCE).toContain('Demo-Szenario laden');
    expect(DASHBOARD_SOURCE).toContain('Ihnen ist noch kein Objekt zugewiesen.');
    expect(DASHBOARD_SOURCE).toContain(
      'Wenden Sie sich an die Kontoinhaberin oder den Kontoinhaber.',
    );
    expect(DASHBOARD_SOURCE).not.toContain('Erstes Objekt anlegen');
    expect(DASHBOARD_SOURCE).not.toContain('Legen Sie das erste Objekt an');
    expect(DASHBOARD_SOURCE).toContain('Fehler beim Laden');
    expect(DASHBOARD_SOURCE).toContain('Verbindungsfehler.');
    expect(DASHBOARD_SOURCE).toContain('Abrechnung erstellen');
    expect(DASHBOARD_SOURCE).toContain('Demo zurücksetzen');
    expect(DASHBOARD_SOURCE).toContain('ownerControls');
  });

  it('uses wrapping, shrinkable dashboard surfaces without horizontal overflow', () => {
    const ui01Source = `${DASHBOARD_SOURCE}\n${WIDGETS_SOURCE}`;
    expect(ui01Source).toMatch(/grid-cols-1/);
    expect(ui01Source).toMatch(/(?:lg|xl):grid-cols-3/);
    expect(ui01Source).toContain('min-w-0');
    expect(ui01Source).toMatch(/overflow-(?:hidden|clip|x-hidden)/);
  });
});

describe('UI-01 static widget acceptance', () => {
  it('renders an occupancy ring only for a real numerator and denominator', async () => {
    const widgets = await loadWidgets();
    const OccupancyCard = component(widgets, 'OccupancyCard');
    const occupied = renderToStaticMarkup(
      <OccupancyCard
        accountId="acc-1"
        occupiedUnitCount={2}
        vacantUnitCount={1}
        unitCount={3}
      />,
    );
    expect(occupied).toContain('2 / 3');
    expect(occupied).toContain('Einheiten vermietet');
    expect(occupied).toContain('href="/a/acc-1/objekte"');
    expect(occupied).toContain('<svg');
    expect(occupied).toMatch(/2 von 3|67\s*%/);

    const noDenominator = renderToStaticMarkup(
      <OccupancyCard
        accountId="acc-1"
        occupiedUnitCount={0}
        vacantUnitCount={0}
        unitCount={0}
      />,
    );
    expect(noDenominator).not.toContain('<svg');
    expect(noDenominator).toContain('Noch keine Einheiten');
    expect(noDenominator).toContain('href="/a/acc-1/objekte"');
    expect(noDenominator).toContain('Erste Einheit anlegen');
    expect(noDenominator).not.toContain('Erstes Objekt anlegen');
  });

  it('renders unavailable finance as labelled text and never as a ring', async () => {
    const widgets = await loadWidgets();
    const UnavailableCard = component(widgets, 'UnavailableCard');
    const html = renderToStaticMarkup(
      <UnavailableCard
        title="Mieteinnahmen"
        description="Noch keine Zahlungsdaten verfügbar."
      />,
    );
    expect(html).toContain('Mieteinnahmen');
    expect(html).toContain('Noch keine Zahlungsdaten verfügbar.');
    expect(html).not.toContain('<svg');
  });

  it('renders a reduced-motion loading skeleton', async () => {
    const widgets = await loadWidgets();
    const DashboardSkeleton = component(widgets, 'DashboardSkeleton');
    const html = renderToStaticMarkup(<DashboardSkeleton />);
    const statusTag = html.match(/<[^>]*role="status"[^>]*>/)?.[0];
    expect(statusTag, 'DashboardSkeleton needs a role=status container').toBeDefined();
    expect(statusTag).toContain('aria-busy="true"');
    expect(statusTag).not.toContain('aria-hidden="true"');
    expect(html).toContain('Übersicht wird geladen');
    expect(html).toContain('aria-hidden="true"');
    expect(html).toContain('animate-pulse');
    expect(html).toContain('motion-reduce:animate-none');
  });
});
