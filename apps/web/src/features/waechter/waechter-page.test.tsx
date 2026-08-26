import React from 'react';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { PortalShellContent } from '../portal/app-shell';

type Role = 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR';

const OWNER = { id: 'acc-1', name: 'Eigene Verwaltung', role: 'OWNER' as const, shape: 'SOLO' };
const EMPLOYEE = {
  id: 'acc-1',
  name: 'Verwaltung Nord',
  role: 'EMPLOYEE' as const,
  shape: 'HAUSVERWALTUNG',
};
const ADVISOR = {
  id: 'acc-1',
  name: 'Kanzlei Süd',
  role: 'TAX_ADVISOR' as const,
  shape: 'SOLO',
};

const FEATURE_SOURCE = readdirSync(new URL('.', import.meta.url))
  .filter((name) => /\.(ts|tsx)$/.test(name) && !name.endsWith('.test.tsx'))
  .map((name) => readFileSync(new URL(name, import.meta.url), 'utf8'))
  .join('\n');
const PAGE_SOURCE = readFileSync(new URL('./waechter-page.tsx', import.meta.url), 'utf8');
const QUERY_SOURCE = readFileSync(new URL('./queries.ts', import.meta.url), 'utf8');

async function waechterModule() {
  const modulePath: string = './waechter-page';
  try {
    return await import(modulePath);
  } catch {
    return undefined;
  }
}

async function queryModule() {
  const modulePath: string = './queries';
  try {
    return await import(modulePath);
  } catch {
    return undefined;
  }
}

const GUARDS = Array.from({ length: 8 }, (_, index) => ({
  id: `guard-${index + 1}`,
  code: `W${index + 1}`,
  stage: index === 0 ? 'EXPIRED' : 'NOTICE',
  warningDe:
    index === 0
      ? 'Frist abgelaufen: Eine Nachforderung ist in der Regel ausgeschlossen.'
      : `Deutscher Wächterhinweis W${index + 1}`,
  boundaryOn: `2026-${String(index + 1).padStart(2, '0')}-28`,
  source: index === 6 ? 'GENESIS 61111 (Test-/Demo-Stub)' : 'Page 05 · Wächter Fristen',
  rechtsstand: index === 1 ? '08/2026' : '07/2026',
  productionBlockers:
    index === 0
      ? ['W1-RENTER-DELIVERY-CONTEXT-MISSING']
      : index === 1
        ? ['W2-APPROVED-RULE-BUNDLE-MISSING']
        : index === 3
          ? ['§ 6a HeizkostenV / EED: verify-before-production']
          : index === 6
            ? ['GENESIS 61111: verify-before-production']
            : [],
}));

const FIXTURE = {
  accountId: 'acc-1',
  role: 'OWNER' as Role,
  guards: GUARDS,
  reminders: [
    {
      id: 'reminder-1',
      guardCode: 'W1',
      dueOn: '2026-12-31',
      channel: 'EMAIL',
      status: 'Offen',
    },
    {
      id: 'reminder-2',
      guardCode: 'W4',
      dueOn: '2026-08-31',
      channel: 'IN_APP',
      status: 'Offen',
    },
  ],
  schedules: [
    {
      id: 'schedule-1',
      kind: 'Jahresabrechnung',
      enabled: false,
      nextOccurrenceOn: null,
      blocker: 'Automatische Zustellung ist standardmäßig deaktiviert.',
    },
    {
      id: 'schedule-2',
      kind: 'UVI',
      enabled: false,
      nextOccurrenceOn: null,
      blocker: 'UVI-Zustellung ist wegen offener Produktionsprüfung gesperrt.',
    },
  ],
  deliveries: [
    { id: 'delivery-1', recipient: 'anna@example.de', status: 'DELIVERED', sentAt: '2026-01-05' },
    { id: 'delivery-2', recipient: 'berta@example.de', status: 'QUEUED', sentAt: '2026-01-06' },
    { id: 'delivery-3', recipient: 'carla@example.de', status: 'BOUNCED', sentAt: '2026-01-07' },
    { id: 'delivery-4', recipient: 'dora@example.de', status: 'COMPLAINED', sentAt: '2026-01-08' },
    { id: 'delivery-5', recipient: 'eva@example.de', status: 'FAILED', sentAt: '2026-01-09' },
    {
      id: 'delivery-6',
      recipient: 'fiona@example.de',
      status: 'BLOCKED',
      sentAt: null,
      blocker:
        'Fiktivbelegung bei Leerstand: verify-before-production; W1-RENTER-DELIVERY-CONTEXT-MISSING',
    },
    { id: 'delivery-7', recipient: 'greta@example.de', status: 'UNSENT', sentAt: null },
  ],
  suppressions: [
    { normalizedAddress: 'fiona@example.de', reason: 'COMPLAINED', occurredAt: '2026-01-08' },
    { normalizedAddress: 'carla@example.de', reason: 'BOUNCED', occurredAt: '2026-01-07' },
  ],
  checklists: [
    {
      id: 'checklist-1',
      title: 'Testvorlage Wohnungsübergabe',
      templateVersion: 'test-only-v1',
      items: [
        {
          id: 'item-1',
          label: 'Zählerstände dokumentieren',
          status: 'OFFEN',
          events: [],
        },
      ],
    },
  ],
  productionChecklistTemplates: [],
  checklistLibraryBlocker:
    'Keine freigegebene Produktionsvorlage: Page 05 liefert keinen Checklisten-Katalog.',
};

function statusFragment(html: string, status: string): string {
  const marker = `data-delivery-status="${status}"`;
  const start = html.indexOf(marker);
  expect(start, `Zustellstatus ${status} fehlt`).toBeGreaterThan(-1);
  const end = html.indexOf('</li>', start);
  return html.slice(start, end === -1 ? html.length : end + 5);
}

function guardFragment(html: string, stage: string): string {
  const marker = `data-guard-stage="${stage}"`;
  const start = html.indexOf(marker);
  expect(start, `Wächterstufe ${stage} fehlt`).toBeGreaterThan(-1);
  const end = html.indexOf('</span>', start);
  return html.slice(start, end === -1 ? html.length : end + 7);
}

describe('M9 Wächter workspace', () => {
  it('renders the three semantic sections and every W1-W8 evidence row', async () => {
    const module = await waechterModule();
    expect(module, 'RED M9: waechter-page.tsx is missing').toBeDefined();
    const WaechterWorkspace = module?.WaechterWorkspace;
    expect(WaechterWorkspace, 'RED M9: WaechterWorkspace is missing').toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9: WaechterWorkspace is missing');

    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} />);
    expect(html).toMatch(/<h1[^>]*>[^<]*Wächter/);
    for (const heading of ['Fristen', 'Zustellung', 'Checklisten']) {
      expect(html).toMatch(new RegExp(`<h2[^>]*>[^<]*${heading}`));
    }
    for (let number = 1; number <= 8; number += 1) {
      expect(html).toContain(`W${number}`);
      expect(html).toContain(GUARDS[number - 1]!.warningDe);
    }
    for (const evidence of [
      'Frist abgelaufen',
      'Grenzdatum',
      'Quelle',
      'Rechtsstand',
      'Produktionssperre',
      'GENESIS 61111 (Test-/Demo-Stub)',
    ]) {
      expect(html).toContain(evidence);
    }
    expect(html).toMatch(/(?:role="status"|aria-label="Wächterstatus W1")/);
  });

  it('shows opt-in schedules, history and suppression while keeping automation default-off', async () => {
    const module = await waechterModule();
    const WaechterWorkspace = module?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9: WaechterWorkspace is missing');
    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} />);

    for (const copy of [
      'Jahresabrechnung',
      'UVI',
      'Deaktiviert',
      'Automatische Zustellung ist standardmäßig deaktiviert.',
      'Versandverlauf',
      'Unterdrückte Empfänger',
      'fiona@example.de',
      'Beschwerde',
    ]) {
      expect(html).toContain(copy);
    }
    expect(html).not.toMatch(/checked(?:=""|="true")/);
  });

  it('uses labelled, accessible icons and the required colours only for delivery states', async () => {
    const module = await waechterModule();
    const WaechterWorkspace = module?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9: WaechterWorkspace is missing');
    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} />);

    const expected = {
      DELIVERED: ['Zugestellt', /(?:text-green|bg-green|text-forest|bg-mint)/],
      QUEUED: ['In Warteschlange', /(?:yellow|amber)/],
      BOUNCED: ['Unzustellbar', /(?:text-red|bg-red|text-danger|bg-danger)/],
      COMPLAINED: ['Beschwerde', /(?:text-red|bg-red|text-danger|bg-danger)/],
      FAILED: ['Fehlgeschlagen', /(?:text-red|bg-red|text-danger|bg-danger)/],
    } as const;
    for (const [status, [label, colour]] of Object.entries(expected)) {
      const fragment = statusFragment(html, status);
      expect(fragment).toContain(label);
      expect(fragment).toMatch(colour);
      expect(fragment).toMatch(/(?:<svg|role="img"|aria-hidden="true")/);
    }
    for (const [status, label] of [
      ['BLOCKED', 'Gesperrt'],
      ['UNSENT', 'Nicht versendet'],
    ] as const) {
      const fragment = statusFragment(html, status);
      expect(fragment).toContain(label);
      expect(fragment).not.toMatch(
        /(?:text-green|bg-green|text-forest|bg-mint|yellow|amber|text-red|bg-red|text-danger|bg-danger)/,
      );
    }
    expect(html).toContain(
      'Provider-Status „Zugestellt“ ist kein Nachweis des rechtlichen Zugangs.',
    );
  });

  it('renders data-driven checklist instances, append-only actions, and the blocked empty catalogue', async () => {
    const module = await waechterModule();
    const WaechterWorkspace = module?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9: WaechterWorkspace is missing');
    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} />);

    for (const copy of [
      'Testvorlage Wohnungsübergabe',
      'Zählerstände dokumentieren',
      'Als erledigt protokollieren',
      'Ereignisse werden unveränderlich ergänzt.',
      'Keine freigegebene Produktionsvorlage',
      'Page 05 liefert keinen Checklisten-Katalog.',
    ]) {
      expect(html).toContain(copy);
    }
    expect(html).not.toContain('Produktionsvorlage auswählen');
    expect(html).toMatch(/<button[^>]*>[^<]*Als erledigt protokollieren/);
  });

  it('maps every M9 client operation to its account-scoped API endpoint', async () => {
    const module = await queryModule();
    expect(module, 'RED M9: queries.ts is missing').toBeDefined();
    const buildM9ApiPaths = module?.buildM9ApiPaths;
    expect(buildM9ApiPaths, 'RED M9: buildM9ApiPaths is missing').toBeTypeOf('function');
    if (!buildM9ApiPaths) throw new Error('RED M9: buildM9ApiPaths is missing');

    expect(
      buildM9ApiPaths('acc-1', {
        checklistId: 'check-1',
        itemId: 'item-1',
        deliveryId: 'delivery-1',
      }),
    ).toEqual({
      guards: '/a/acc-1/guards',
      guardRuns: '/a/acc-1/guard-runs',
      deliverySchedules: '/a/acc-1/delivery-schedules',
      reminders: '/a/acc-1/reminders',
      checklists: '/a/acc-1/checklists',
      checklistItemEvents: '/a/acc-1/checklists/check-1/items/item-1/events',
      deliveries: '/a/acc-1/deliveries',
      deliveryConfirmation: '/a/acc-1/deliveries/delivery-1/confirm',
    });
    for (const mutationPath of [
      'guard-runs',
      'delivery-schedules',
      'items/${itemId}/events',
      'deliveries',
      '${deliveryId}/confirm',
    ]) {
      expect(FEATURE_SOURCE).toContain(mutationPath);
    }
    expect(FEATURE_SOURCE.match(/method:\s*['"]POST['"]/g)?.length ?? 0).toBeGreaterThanOrEqual(5);
  });

  it('adds the real account route and navigation for owner and employee, never tax adviser', () => {
    const routeUrl = new URL('../../app/a/[accountId]/waechter/page.tsx', import.meta.url);
    expect(existsSync(routeUrl), 'RED M9: /a/{accountId}/waechter route is missing').toBe(true);
    if (existsSync(routeUrl)) {
      const route = readFileSync(routeUrl, 'utf8');
      expect(route).toContain('accountId');
      expect(route).toMatch(/Waechter(?:Workspace)?Page/);
    }

    const renderShell = (account: typeof OWNER | typeof EMPLOYEE | typeof ADVISOR) =>
      renderToStaticMarkup(
        <PortalShellContent
          accountId="acc-1"
          account={account}
          accounts={[account]}
          pathname="/a/acc-1/waechter"
        >
          <p>Wächterinhalt</p>
        </PortalShellContent>,
      );
    expect(renderShell(OWNER)).toContain('href="/a/acc-1/waechter"');
    expect(renderShell(EMPLOYEE)).toContain('href="/a/acc-1/waechter"');
    expect(renderShell(ADVISOR)).not.toContain('/waechter');
  });

  it('keeps controls accessible, focused, scalable, and limited to one primary action per context', () => {
    expect(FEATURE_SOURCE).toMatch(/focus-visible:/);
    expect(FEATURE_SOURCE).toMatch(/(?:min-w-0|flex-wrap|grid-cols-1|overflow-x-auto)/);
    expect(FEATURE_SOURCE).not.toMatch(/(?:h-\[\d+px\]|overflow-hidden[\s\S]{0,80}h-\[)/);
    expect(FEATURE_SOURCE).not.toMatch(/<(?:div|span)[^>]*role=['"]button['"]/);
    expect(FEATURE_SOURCE).toContain('data-action-context');
    expect(FEATURE_SOURCE).toContain('data-primary-action');
  });
});

describe('M9 statement-reviewer contracts', () => {
  it('loads only assigned guards and checklists for employees, while owners receive owner-only data', async () => {
    const queries = await queryModule();
    const m9ResourcesForRole = queries?.m9ResourcesForRole;
    expect(m9ResourcesForRole, 'RED M9 review: role-scoped loader contract is missing').toBeTypeOf(
      'function',
    );
    if (!m9ResourcesForRole) throw new Error('RED M9 review: role-scoped loader is missing');

    expect(m9ResourcesForRole('EMPLOYEE')).toEqual(['guards', 'checklists']);
    expect(m9ResourcesForRole('OWNER')).toEqual([
      'guards',
      'delivery-schedules',
      'reminders',
      'checklists',
      'deliveries',
    ]);
    expect(PAGE_SOURCE).toMatch(/useM9Data\(accountId,\s*role\)/);

    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 review: workspace missing');
    const html = renderToStaticMarkup(
      <WaechterWorkspace
        {...FIXTURE}
        role="EMPLOYEE"
        reminders={[]}
        schedules={[]}
        deliveries={[]}
        suppressions={[]}
      />,
    );
    expect(html).toContain('W1');
    expect(html).toContain('Testvorlage Wohnungsübergabe');
    expect(html).toContain('Als erledigt protokollieren');
    expect(html).not.toContain('Wächter neu auswerten');
  });

  it('requires real source identities for guard runs and schedules without client-authored snapshots', async () => {
    const queries = await queryModule();
    const GuardRunInputSchema = queries?.GuardRunInputSchema;
    const ScheduleInputSchema = queries?.ScheduleInputSchema;
    expect(GuardRunInputSchema, 'RED M9 review: GuardRunInputSchema must be public').toBeDefined();
    expect(ScheduleInputSchema, 'RED M9 review: ScheduleInputSchema must be public').toBeDefined();
    if (!GuardRunInputSchema || !ScheduleInputSchema)
      throw new Error('RED M9 review: request schemas missing');

    expect(
      GuardRunInputSchema.safeParse({
        today: '2026-08-25',
        now: '2026-08-25T10:00:00+02:00',
        sourceIds: [],
      }).success,
    ).toBe(false);
    expect(
      GuardRunInputSchema.parse({
        today: '2026-08-25',
        now: '2026-08-25T10:00:00+02:00',
        sourceIds: ['building-1'],
      }),
    ).toEqual({
      today: '2026-08-25',
      now: '2026-08-25T10:00:00+02:00',
      sourceIds: ['building-1'],
    });
    expect(
      ScheduleInputSchema.parse({
        sourceId: 'building-1',
        deliveryKind: 'ANNUAL_STATEMENT',
        validFrom: '2026-08-25',
        enabled: true,
      }),
    ).toEqual({
      sourceId: 'building-1',
      deliveryKind: 'ANNUAL_STATEMENT',
      validFrom: '2026-08-25',
      enabled: true,
    });
    expect(QUERY_SOURCE).not.toContain('scheduleSnapshot: JsonObjectSchema');
    expect(PAGE_SOURCE).toContain('sourceIds:');
    expect(PAGE_SOURCE).not.toContain('occurrences: []');
    expect(PAGE_SOURCE).toContain('sourceId: schedule.buildingId');
    expect(PAGE_SOURCE).not.toContain('scheduleSnapshot: {}');
  });

  it('maps source-missing guards to German blocked evidence without invented fallback copy', async () => {
    const page = await waechterModule();
    const guardView = page?.guardView;
    expect(guardView, 'RED M9 review: guard evidence mapper must be testable').toBeTypeOf(
      'function',
    );
    if (!guardView) throw new Error('RED M9 review: guardView export missing');
    const mapped = guardView({
      id: 'guard-blocked',
      guardCode: 'W7',
      subjectType: 'building',
      subjectId: 'building-1',
      buildingId: 'building-1',
      unitId: null,
      tenancyId: null,
      renterId: null,
      occurrenceKey: 'w7:building-1:2026-08-25',
      inputSnapshot: {},
      resultSnapshot: {
        stage: 'source_missing',
        warning_de: null,
        production_blockers: ['VPI-Quelle fehlt; Auswertung ist gesperrt.'],
      },
      ruleSnapshot: {
        evidence: [
          {
            source: 'GENESIS 61111',
            rechtsstand: '07/2026',
            verificationStatus: 'verify-before-production',
          },
        ],
      },
      evaluatedAt: '2026-08-25T10:00:00Z',
      resolutionEvents: [],
    });
    expect(mapped).toMatchObject({
      stage: 'Gesperrt',
      warningDe: 'VPI-Quelle fehlt; Auswertung ist gesperrt.',
      source: 'GENESIS 61111',
      rechtsstand: '07/2026',
      productionBlockers: ['VPI-Quelle fehlt; Auswertung ist gesperrt.'],
    });

    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 review: workspace missing');
    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} guards={[mapped]} />);
    expect(html).toContain('Gesperrt');
    expect(html).toContain('VPI-Quelle fehlt; Auswertung ist gesperrt.');
    expect(html).toContain('GENESIS 61111');
    expect(html).toContain('07/2026');
    expect(html).not.toContain('source_missing');
    expect(html).not.toContain('Kein aktiver Hinweis');
  });

  it('offers owner legal confirmation for every unconfirmed provider status and captures both fields', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 review: workspace missing');
    const html = renderToStaticMarkup(
      <WaechterWorkspace {...FIXTURE} onConfirmDelivery={() => undefined} />,
    );
    for (const status of [
      'DELIVERED',
      'QUEUED',
      'BOUNCED',
      'COMPLAINED',
      'FAILED',
      'BLOCKED',
      'UNSENT',
    ]) {
      expect(statusFragment(html, status)).toContain('Zugang bestätigen');
    }
    expect(html).toMatch(/name="deliveredOn"[^>]*required/);
    expect(html).toMatch(/name="evidenceReference"[^>]*required/);
  });

  it('uses append-only attempt, provider-event, and suppression-event timestamps', () => {
    for (const field of [
      'attemptedAt',
      'statusOccurredAt',
      'suppressionEvents',
      'occurredAt',
      'normalizedAddress',
      'reason',
    ]) {
      expect(QUERY_SOURCE).toContain(field);
    }
    expect(PAGE_SOURCE).not.toContain('sentAt: row.providerDeliveredAt');
    expect(PAGE_SOURCE).not.toMatch(/suppressions=\{deliveries\s*\.filter/);
    expect(PAGE_SOURCE).toMatch(/suppressionEvents/);
  });

  it('shows real blocked-send reasons and mutation pending/error state without inventing missing email', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 review: workspace missing');
    const html = renderToStaticMarkup(
      <WaechterWorkspace
        {...FIXTURE}
        deliveries={[
          {
            id: 'missing-email',
            recipient: 'Nicht hinterlegt',
            status: 'BLOCKED',
            sentAt: null,
            blocker: 'E-Mail-Adresse fehlt. Versand wurde nicht gestartet.',
          },
          {
            id: 'plain-unsent',
            recipient: 'noch-nicht-versendet@example.de',
            status: 'UNSENT',
            sentAt: null,
          },
          {
            id: 'hash-blocked',
            recipient: 'hash@example.de',
            status: 'BLOCKED',
            sentAt: null,
            blocker: 'Dokument-Hash stimmt nicht überein.',
            mutationError: 'Versand gesperrt: Dokument-Hash stimmt nicht überein.',
          },
          {
            id: 'provider-blocked',
            recipient: 'provider@example.de',
            status: 'BLOCKED',
            sentAt: null,
            blocker: 'E-Mail-Anbieter ist nicht konfiguriert.',
          },
          {
            id: 'artifact-blocked',
            recipient: 'artifact@example.de',
            status: 'BLOCKED',
            sentAt: null,
            blocker: 'Zustellungsdokument fehlt.',
          },
          {
            id: 'pending',
            recipient: 'pending@example.de',
            status: 'UNSENT',
            sentAt: null,
            mutationPending: true,
          },
        ]}
        onSendDelivery={() => undefined}
      />,
    );
    expect(html).toContain('E-Mail-Adresse fehlt. Versand wurde nicht gestartet.');
    expect(html).toContain('Versand gesperrt: Dokument-Hash stimmt nicht überein.');
    expect(html).toContain('E-Mail-Anbieter ist nicht konfiguriert.');
    expect(html).toContain('Zustellungsdokument fehlt.');
    expect(html).toContain('Versand wird vorbereitet …');
    expect(statusFragment(html, 'UNSENT')).not.toContain('E-Mail-Adresse fehlt');
    expect(PAGE_SOURCE).not.toContain("recipient ?? 'E-Mail-Adresse fehlt'");
  });

  it('distinguishes expired, warning, and blocked guard severity with labels, icons, and non-success styling', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 review: workspace missing');
    const html = renderToStaticMarkup(
      <WaechterWorkspace
        {...FIXTURE}
        guards={[
          { ...GUARDS[0]!, id: 'expired', code: 'W1', stage: 'EXPIRED' },
          { ...GUARDS[1]!, id: 'warning', code: 'W2', stage: 'NOTICE' },
          { ...GUARDS[6]!, id: 'blocked', code: 'W7', stage: 'source_missing' },
        ]}
      />,
    );
    const expired = guardFragment(html, 'EXPIRED');
    const warning = guardFragment(html, 'NOTICE');
    const blocked = guardFragment(html, 'source_missing');
    expect(expired).toContain('Abgelaufen');
    expect(warning).toContain('Warnung');
    expect(blocked).toContain('Gesperrt');
    for (const fragment of [expired, warning, blocked]) {
      expect(fragment).toMatch(/(?:<svg|role="img"|aria-hidden="true")/);
    }
    expect(
      new Set([
        expired.match(/class="([^"]+)/)?.[1],
        warning.match(/class="([^"]+)/)?.[1],
        blocked.match(/class="([^"]+)/)?.[1],
      ]).size,
    ).toBe(3);
    expect(expired).not.toMatch(/(?:bg-mint|text-forest)/);
    expect(blocked).not.toMatch(/(?:bg-mint|text-forest)/);
  });

  it('keeps the global run as the sole primary action and row actions secondary', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 review: workspace missing');
    const html = renderToStaticMarkup(
      <WaechterWorkspace
        {...FIXTURE}
        onRunGuards={() => undefined}
        onScheduleChange={() => undefined}
        onChecklistEvent={() => undefined}
        onSendDelivery={() => undefined}
        onConfirmDelivery={() => undefined}
      />,
    );
    expect(html.match(/data-primary-action/g)).toHaveLength(1);
    expect(html).toMatch(/data-primary-action[^>]*>[\s\S]{0,120}Wächter neu auswerten/);
    for (const action of [
      'Opt-in aktivieren',
      'Einzeln versenden',
      'Zugang bestätigen',
      'Als erledigt protokollieren',
    ]) {
      const at = html.indexOf(action);
      expect(at, `${action} fehlt`).toBeGreaterThan(-1);
      expect(html.slice(Math.max(0, at - 240), at)).not.toContain('data-primary-action');
    }
  });
});

describe('M9 statement re-review contracts', () => {
  it('shows an explicit German title for every W1-W8 card', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 final review: workspace missing');
    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} />);

    for (const title of [
      'W1 · Abrechnungsfrist',
      'W2 · Eichfrist',
      'W3 · Mietrückstand',
      'W4 · Verbrauchsinformation',
      'W5 · Vergleichsmiete',
      'W6 · Staffelmiete',
      'W7 · Indexmiete',
      'W8 · Leerstand',
    ]) {
      expect(html).toContain(title);
    }
  });

  it('explains internal guard blockers in German without exposing codes or verification markers', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 final review: workspace missing');
    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} />);

    for (const explanation of [
      'Zustellkontext für die Betriebskostenabrechnung fehlt.',
      'Freigegebenes Regelwerk für die Eichfrist fehlt.',
      'Die Rechts- oder Regelgrundlage muss vor dem Produktiveinsatz geprüft werden.',
    ]) {
      expect(html).toContain(explanation);
    }
    for (const internalValue of [
      'W1-RENTER-DELIVERY-CONTEXT-MISSING',
      'W2-APPROVED-RULE-BUNDLE-MISSING',
      'verify-before-production',
    ]) {
      expect(html).not.toContain(internalValue);
    }
  });

  it('renders reminder channels and suppression reasons in German, never as API enums', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 final review: workspace missing');
    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} deliveries={[]} />);

    for (const label of ['E-Mail', 'In der Anwendung', 'Unzustellbar', 'Beschwerde']) {
      expect(html).toContain(label);
    }
    for (const internalValue of ['EMAIL', 'IN_APP', 'BOUNCED', 'COMPLAINED']) {
      expect(html).not.toContain(internalValue);
    }
  });

  it('replaces joined delivery blockers with one safe German explanation', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 final review: workspace missing');
    const internalBlocker =
      'Fiktivbelegung bei Leerstand: verify-before-production; W1-RENTER-DELIVERY-CONTEXT-MISSING';
    const html = renderToStaticMarkup(
      <WaechterWorkspace
        {...FIXTURE}
        guards={[]}
        deliveries={[
          {
            id: 'internal-blocker',
            recipient: 'gesperrt@example.de',
            status: 'BLOCKED',
            sentAt: null,
            blocker: internalBlocker,
          },
        ]}
      />,
    );

    expect(html).toContain(
      'Zustellung gesperrt: Das Dokument ist noch nicht für den Versand freigegeben.',
    );
    expect(html).not.toContain(internalBlocker);
    expect(html).not.toContain('verify-before-production');
  });

  it('keeps a valid server-discovered first run available when no evaluation exists yet', async () => {
    const queries = await queryModule();
    const GuardListSchema = queries?.GuardListSchema;
    expect(GuardListSchema).toBeDefined();
    if (!GuardListSchema) throw new Error('RED M9 re-review: GuardListSchema missing');
    const parsed = GuardListSchema.parse({
      guards: [],
      sourceIds: ['account-scope:acc-1'],
    });
    expect(parsed.sourceIds).toEqual(['account-scope:acc-1']);

    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 re-review: workspace missing');
    const html = renderToStaticMarkup(
      <WaechterWorkspace {...FIXTURE} guards={[]} onRunGuards={() => undefined} />,
    );
    expect(html).toContain('Noch keine Wächterauswertung vorhanden.');
    expect(html).toContain('Wächter neu auswerten');
    expect(PAGE_SOURCE).toMatch(/data\.guards\.data\?\.sourceIds/);
    expect(PAGE_SOURCE).not.toMatch(/mappedGuards\.map\([^)]*sourceId/);
    expect(PAGE_SOURCE).not.toContain('inputSnapshot:');
    expect(PAGE_SOURCE).not.toContain('ruleSnapshot:');
  });

  it('classifies every active Page-05 stage as German warning or danger with an icon', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 re-review: workspace missing');
    const expected = {
      notice: 'Warnung',
      expiry_month: 'Warnung',
      exceeded: 'Warnung',
      last_day: 'Dringend',
      reminder_30_days: 'Warnung',
      '3a': 'Dringend',
      '3b': 'Dringend',
      adjustment_due: 'Warnung',
      opportunity: 'Warnung',
      vacancy: 'Warnung',
    } as const;
    const guards = Object.keys(expected).map((stage, index) => ({
      ...GUARDS[index % GUARDS.length]!,
      id: `stage-${stage}`,
      code: `W${(index % 8) + 1}`,
      stage,
    }));
    const html = renderToStaticMarkup(<WaechterWorkspace {...FIXTURE} guards={guards} />);
    for (const [stage, label] of Object.entries(expected)) {
      const fragment = guardFragment(html, stage);
      expect(fragment).toContain(label);
      expect(fragment).toMatch(/(?:bg-warning-tint|text-warning|bg-danger-tint|text-danger)/);
      expect(fragment).toMatch(/(?:<svg|role="img"|aria-hidden="true")/);
      expect(fragment).not.toMatch(/border border-slate/);
    }
  });

  it('treats basis-year mismatch and invalid input as German blocked or error states, never neutral', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 re-review: workspace missing');
    const html = renderToStaticMarkup(
      <WaechterWorkspace
        {...FIXTURE}
        guards={[
          { ...GUARDS[6]!, id: 'basis', stage: 'basis_year_mismatch' },
          { ...GUARDS[5]!, id: 'invalid', stage: 'invalid' },
        ]}
      />,
    );
    const basis = guardFragment(html, 'basis_year_mismatch');
    const invalid = guardFragment(html, 'invalid');
    expect(basis).toContain('Gesperrt');
    expect(invalid).toContain('Fehler');
    for (const fragment of [basis, invalid]) {
      expect(fragment).toMatch(/(?:bg-warning-tint|text-warning|bg-danger-tint|text-danger)/);
      expect(fragment).toMatch(/(?:<svg|role="img"|aria-hidden="true")/);
      expect(fragment).not.toMatch(/border border-slate/);
      expect(fragment).not.toContain('Hinweis');
    }
  });

  it('locks schedule, checklist, and confirmation mutations while pending and reports success or error', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 re-review: workspace missing');
    const renderMutationState = (state: 'pending' | 'success' | 'error') =>
      renderToStaticMarkup(
        <WaechterWorkspace
          {...FIXTURE}
          schedules={[
            {
              ...FIXTURE.schedules[0]!,
              mutationPending: state === 'pending',
              mutationSuccess: state === 'success' ? 'Zeitplan wurde gespeichert.' : undefined,
              mutationError:
                state === 'error' ? 'Zeitplan konnte nicht gespeichert werden.' : undefined,
            },
          ]}
          checklists={[
            {
              ...FIXTURE.checklists[0]!,
              items: [
                {
                  ...FIXTURE.checklists[0]!.items[0]!,
                  mutationPending: state === 'pending',
                  mutationSuccess:
                    state === 'success' ? 'Checklisten-Ereignis wurde gespeichert.' : undefined,
                  mutationError:
                    state === 'error'
                      ? 'Checklisten-Ereignis konnte nicht gespeichert werden.'
                      : undefined,
                },
              ],
            },
          ]}
          deliveries={[
            {
              ...FIXTURE.deliveries[0]!,
              confirmationPending: state === 'pending',
              confirmationSuccess:
                state === 'success' ? 'Rechtlicher Zugang wurde bestätigt.' : undefined,
              confirmationError:
                state === 'error'
                  ? 'Zugangsbestätigung konnte nicht gespeichert werden.'
                  : undefined,
            },
          ]}
          onScheduleChange={() => undefined}
          onChecklistEvent={() => undefined}
          onConfirmDelivery={() => undefined}
        />,
      );
    const pendingHtml = renderMutationState('pending');
    const successHtml = renderMutationState('success');
    const errorHtml = renderMutationState('error');
    const html = `${pendingHtml}${successHtml}${errorHtml}`;
    for (const feedback of [
      'Zeitplan wird gespeichert …',
      'Zeitplan wurde gespeichert.',
      'Zeitplan konnte nicht gespeichert werden.',
      'Checklisten-Ereignis wird gespeichert …',
      'Checklisten-Ereignis wurde gespeichert.',
      'Checklisten-Ereignis konnte nicht gespeichert werden.',
      'Zugangsbestätigung wird gespeichert …',
      'Rechtlicher Zugang wurde bestätigt.',
      'Zugangsbestätigung konnte nicht gespeichert werden.',
    ]) {
      expect(html).toContain(feedback);
    }
    for (const action of [
      'Opt-in aktivieren',
      'Als erledigt protokollieren',
      'Zugang bestätigen',
    ]) {
      const at = pendingHtml.indexOf(action);
      expect(at, `${action} fehlt`).toBeGreaterThan(-1);
      const opening = pendingHtml.slice(
        pendingHtml.lastIndexOf('<button', at),
        pendingHtml.indexOf('>', at) + 1,
      );
      expect(opening, `${action} muss während der Speicherung gesperrt sein`).toContain('disabled');
    }
    expect(html.match(/role="alert"/g)?.length ?? 0).toBeGreaterThanOrEqual(3);
    expect(html.match(/role="status"/g)?.length ?? 0).toBeGreaterThanOrEqual(3);
  });

  it('announces a successful guard run explicitly alongside pending and error states', async () => {
    const page = await waechterModule();
    const WaechterWorkspace = page?.WaechterWorkspace;
    expect(WaechterWorkspace).toBeTypeOf('function');
    if (!WaechterWorkspace) throw new Error('RED M9 final review: workspace missing');
    const pending = renderToStaticMarkup(
      <WaechterWorkspace {...FIXTURE} onRunGuards={() => undefined} runPending />,
    );
    const failed = renderToStaticMarkup(
      <WaechterWorkspace
        {...FIXTURE}
        onRunGuards={() => undefined}
        runError="Wächterauswertung konnte nicht gespeichert werden."
      />,
    );
    const succeeded = renderToStaticMarkup(
      <WaechterWorkspace {...FIXTURE} onRunGuards={() => undefined} runSuccess />,
    );
    expect(pending).toContain('Wächter werden ausgewertet …');
    expect(pending).toMatch(/<button[^>]*disabled/);
    expect(failed).toContain('Auswertung fehlgeschlagen');
    expect(failed).toContain('Wächterauswertung konnte nicht gespeichert werden.');
    expect(succeeded).toMatch(
      /role="status"[^>]*>[\s\S]{0,300}(?:Wächterauswertung abgeschlossen|Wächter wurden ausgewertet)/,
    );
    expect(PAGE_SOURCE).toMatch(/runSuccess=\{actions\.runGuards\.isSuccess\}/);
  });
});
