import React, { type ComponentType } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import * as Contracts from '@/lib/contracts';

import * as PortalEntryModule from '../portal/portal-entry';

type ImportMetaWithGlob = ImportMeta & {
  glob(patterns: string[], options: { eager: true }): Record<string, unknown>;
};

const FEATURE_MODULES = (import.meta as ImportMetaWithGlob).glob(['./*.tsx', '!./*.test.tsx'], {
  eager: true,
});
const PORTAL_ENTRY_SOURCE = readFileSync(
  new URL('../portal/portal-entry.tsx', import.meta.url),
  'utf8',
);
const RENTER_SHELL_SOURCE = readFileSync(new URL('./renter-shell.tsx', import.meta.url), 'utf8');

type Schema = { parse(input: unknown): unknown };

const OVERVIEW = {
  tenancyId: 'tenancy-current',
  validFrom: '2025-01-01',
  validTo: null,
  unitLabel: 'Wohnung 2',
  buildingName: 'Musterhaus',
  street: 'Musterstraße 12',
  postalCode: '10115',
  city: 'Berlin',
};

const STATEMENT_DOCUMENT = {
  id: 'publication-statement',
  tenancyId: 'tenancy-current',
  sourceKind: 'STATEMENT_ARCHIVE',
  documentType: 'TENANT_STATEMENT',
  filename: 'do-not-use-the-filename.pdf',
  mimeType: 'application/pdf',
  sha256: 'a'.repeat(64),
  publishedAt: '2026-09-11T12:00:00Z',
  supersedesPublicationId: null,
  periodStart: '2025-01-01',
  periodEnd: '2025-12-31',
  documentMonth: null,
  downloadUrl: '/renter/tenancy-current/documents/publication-statement/download',
};

const UVI_DOCUMENT = {
  id: 'publication-uvi',
  tenancyId: 'tenancy-current',
  sourceKind: 'UVI_ARTIFACT',
  documentType: 'UVI',
  filename: 'also-not-a-title.pdf',
  mimeType: 'application/pdf',
  sha256: 'b'.repeat(64),
  publishedAt: '2026-09-11T13:00:00Z',
  supersedesPublicationId: null,
  periodStart: null,
  periodEnd: null,
  documentMonth: '2026-04-01',
  downloadUrl: '/renter/tenancy-current/documents/publication-uvi/download',
};

function requiredExport<T>(file: string, name: string): T {
  const module = FEATURE_MODULES[file] as Record<string, unknown> | undefined;
  expect(module, `${file} is required by M10-R4`).toBeDefined();
  const value = module?.[name];
  expect(value, `${name} must be exported from ${file}`).toBeTypeOf('function');
  if (typeof value !== 'function') throw new Error(`${name} is not implemented`);
  return value as T;
}

function requiredSchema(name: string): Schema {
  const schema = (Contracts as Record<string, unknown>)[name] as Schema | undefined;
  expect(schema, `${name} must mirror the renter API response`).toBeDefined();
  if (!schema) throw new Error(`${name} is not implemented`);
  return schema;
}

function visibleText(html: string): string {
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

describe('M10-R4 renter route group', () => {
  const routeFiles = [
    '../../app/renter/[tenancyId]/layout.tsx',
    '../../app/renter/[tenancyId]/page.tsx',
    '../../app/renter/[tenancyId]/abrechnungen/page.tsx',
    '../../app/renter/[tenancyId]/verbrauchsinformationen/page.tsx',
  ];

  it.each(routeFiles)('provides %s as a bounded renter route', (relativePath) => {
    const routeUrl = new URL(relativePath, import.meta.url);
    expect(existsSync(routeUrl), `${relativePath} is absent`).toBe(true);
    if (existsSync(routeUrl)) expect(readFileSync(routeUrl, 'utf8').trim()).not.toBe('');
  });
});

describe('M10-R4 web response boundaries', () => {
  it('accepts the exact dual membership and renter-context /me shape', () => {
    const response = {
      personId: 'person-1',
      email: 'mieter@example.test',
      accounts: [{ id: 'account-owner', name: 'Eigene Verwaltung', role: 'OWNER', shape: 'SOLO' }],
      renterContexts: [{ tenancyId: 'tenancy-current' }],
    };

    expect(requiredSchema('MeResponseSchema').parse(response)).toEqual(response);
  });

  it('accepts the exact renter overview shape without landlord identifiers or figures', () => {
    expect(requiredSchema('RenterOverviewResponseSchema').parse(OVERVIEW)).toEqual(OVERVIEW);
  });

  it('accepts the exact publication list shape including immutable display metadata', () => {
    const response = { documents: [STATEMENT_DOCUMENT, UVI_DOCUMENT] };
    expect(requiredSchema('RenterPublicationListResponseSchema').parse(response)).toEqual(response);
  });
});

type EntryRenterContext = {
  tenancyId: string;
  label?: string;
};

type AutoEntryDestination = (
  accounts: Array<{ id: string; name: string; role: string; shape: string }>,
  renterContexts: EntryRenterContext[],
) => string | undefined;

type ContextChooserProps = {
  accounts: Array<{ id: string; name: string; role: string; shape: string }>;
  renterContexts: EntryRenterContext[];
};

describe('M10-R4 renter portal entry regression', () => {
  const owner = { id: 'account-owner', name: 'Eigene Verwaltung', role: 'OWNER', shape: 'SOLO' };
  const renter = {
    tenancyId: 'tenancy-current',
    label: 'Mietverhältnis — Musterstraße 12, Wohnung 2',
  };

  function entryDestination(): AutoEntryDestination {
    const value = (PortalEntryModule as Record<string, unknown>).autoEntryDestination;
    expect(value, 'PortalEntry needs one destination resolver for all /me contexts').toBeTypeOf(
      'function',
    );
    if (typeof value !== 'function') throw new Error('autoEntryDestination is not implemented');
    return value as AutoEntryDestination;
  }

  function renderChooser(props: ContextChooserProps): string {
    const value = (PortalEntryModule as Record<string, unknown>).ContextChooser;
    expect(
      value,
      'PortalEntry needs a chooser that renders membership and renter contexts',
    ).toBeTypeOf('function');
    if (typeof value !== 'function') throw new Error('ContextChooser is not implemented');
    const ContextChooser = value as ComponentType<ContextChooserProps>;
    return renderToStaticMarkup(<ContextChooser {...props} />);
  }

  it('sends a renter-only /me result to the real renter destination and never to the demo', () => {
    expect(entryDestination()([], [renter])).toBe('/renter/tenancy-current');
    const html = renderChooser({ accounts: [], renterContexts: [renter] });
    expect(html).toContain('href="/renter/tenancy-current"');
    expect(html).not.toContain('Demo-Szenario');
    expect(PORTAL_ENTRY_SOURCE).toContain('autoEntryDestination');
  });

  it('does not auto-enter an owner destination when the same person also has a renter context', () => {
    expect(entryDestination()([owner], [renter])).toBeUndefined();
    const html = renderChooser({ accounts: [owner], renterContexts: [renter] });
    expect(html).toContain('href="/a/account-owner"');
    expect(html).toContain('href="/renter/tenancy-current"');
    expect(html).not.toContain('Demo-Szenario');
    const text = visibleText(html);
    expect({
      accountNamePreserved: text.includes(owner.name),
      renterLabelPreserved: text.includes(renter.label),
      genderPunctuatedRole: text.match(/\b\p{L}+:(?:in|innen)\b/iu),
    }).toEqual({
      accountNamePreserved: true,
      renterLabelPreserved: true,
      genderPunctuatedRole: null,
    });
  });
});

type ActivationProps = {
  state: 'entry' | 'success' | 'refused';
  tenancyId?: string;
  activationCode?: string;
  onActivationCodeChange?: (value: string) => void;
  onActivate?: () => void;
};

describe('M10-COPY-01..03 activation', () => {
  const renderActivation = (props: ActivationProps) => {
    const Activation = requiredExport<ComponentType<ActivationProps>>(
      './activation.tsx',
      'RenterActivationView',
    );
    return renderToStaticMarkup(<Activation {...props} />);
  };

  it('renders the approved activation entry verbatim', () => {
    const html = renderActivation({
      state: 'entry',
      activationCode: '',
      onActivationCodeChange: () => undefined,
      onActivate: () => undefined,
    });

    expect(html).toContain('Mieterzugang aktivieren');
    expect(html).toContain('Aktivierungscode');
    expect(html).toContain(
      'Geben Sie den Aktivierungscode ein, den Sie von Ihrer Vermieterin oder Ihrem Vermieter erhalten haben. Der Code gilt einmalig.',
    );
    expect(html).toContain('Zugang aktivieren');
  });

  it('renders the approved success and destination verbatim', () => {
    const html = renderActivation({ state: 'success', tenancyId: 'tenancy-current' });

    expect(html).toContain('Ihr Zugang ist aktiviert.');
    expect(html).toContain(
      'Sie sehen hier künftig Ihre Abrechnungen und Ihre monatlichen Verbrauchsinformationen, sobald Ihre Vermieterin oder Ihr Vermieter sie bereitstellt.',
    );
    expect(html).toContain('Zu meinen Unterlagen');
    expect(html).toContain('href="/renter/tenancy-current"');
  });

  it('uses one approved generic refusal without revealing the reason', () => {
    const html = renderActivation({ state: 'refused' });

    expect(html).toContain(
      'Die Aktivierung war nicht möglich. Bitte prüfen Sie den Code oder wenden Sie sich an Ihre Vermieterin oder Ihren Vermieter.',
    );
    expect(html).not.toMatch(/abgelaufen|verbraucht|unbekannt|falsch(?:es|er)? Konto/i);
  });
});

type RenterContext = {
  tenancyId: string;
  street: string;
  unitLabel: string;
};

type RenterShellProps = {
  tenancyId: string;
  pathname: string;
  accounts: Array<{ id: string; name: string; role: string; shape: string }>;
  renterContexts: RenterContext[];
  children: React.ReactNode;
};

describe('M10-COPY-04 renter shell and context switching', () => {
  const renderShell = (props: Omit<RenterShellProps, 'children'>) => {
    const Shell = requiredExport<ComponentType<RenterShellProps>>(
      './renter-shell.tsx',
      'RenterShellContent',
    );
    return renderToStaticMarkup(
      <Shell {...props}>
        <p>PORTAL_CONTENT</p>
      </Shell>,
    );
  };

  const currentContext = {
    tenancyId: 'tenancy-current',
    street: 'Musterstraße 12',
    unitLabel: 'Wohnung 2',
  };

  it('shows no switcher when membership plus renter contexts total one', () => {
    const html = renderShell({
      tenancyId: 'tenancy-current',
      pathname: '/renter/tenancy-current',
      accounts: [],
      renterContexts: [currentContext],
    });

    expect(html).not.toContain('Als Mieter');
    expect(html).not.toContain('Kontext wechseln');
  });

  it('shows the approved renter group and overview-derived labels only for multiple contexts', () => {
    const html = renderShell({
      tenancyId: 'tenancy-current',
      pathname: '/renter/tenancy-current',
      accounts: [{ id: 'account-owner', name: 'Eigene Verwaltung', role: 'OWNER', shape: 'SOLO' }],
      renterContexts: [currentContext],
    });

    expect(html).toContain('Als Mieter');
    expect(html).toContain('Mietverhältnis — Musterstraße 12, Wohnung 2');
  });

  it('preserves owner destinations without exposing the raw account id as visible text', () => {
    const html = renderShell({
      tenancyId: 'tenancy-current',
      pathname: '/renter/tenancy-current',
      accounts: [{ id: 'account-owner', name: 'Eigene Verwaltung', role: 'OWNER', shape: 'SOLO' }],
      renterContexts: [currentContext],
    });

    expect(html).toContain('href="/a/account-owner"');
    expect(visibleText(html)).not.toContain('account-owner');
  });

  it('gives the switcher a visible indicator and a contrast-safe component border', () => {
    const html = renderShell({
      tenancyId: 'tenancy-current',
      pathname: '/renter/tenancy-current',
      accounts: [{ id: 'account-owner', name: 'Eigene Verwaltung', role: 'OWNER', shape: 'SOLO' }],
      renterContexts: [currentContext],
    });
    const summary = html.match(/<summary\b[\s\S]*?<\/summary>/)?.[0];

    expect(summary, 'the context switcher control must render as a summary').toBeDefined();
    expect(summary).toContain('border-slate');
    expect(summary).not.toContain('border-mint');
    expect(summary).toMatch(/<svg\b|[\u2304\u25be\u25bc]/);
  });

  it('M10-F lets renter navigation, switcher labels and document headings reflow', () => {
    const longContext = {
      tenancyId: 'tenancy-current',
      street: 'Donaudampfschifffahrtsgesellschaftskapitänstraße 123',
      unitLabel: 'Wohnung mit sehr langer Bezeichnung',
    };
    const shellHtml = renderShell({
      tenancyId: 'tenancy-current',
      pathname: '/renter/tenancy-current/verbrauchsinformationen',
      accounts: [{ id: 'account-owner', name: 'Eigene Verwaltung', role: 'OWNER', shape: 'SOLO' }],
      renterContexts: [longContext],
    });
    const header = shellHtml.match(/<header\b[\s\S]*?<\/header>/)?.[0];
    const headerRowClasses = header?.match(/<div class="([^"]+)"/)?.[1];
    const detailsClasses = header?.match(/<details class="([^"]+)"/)?.[1];
    const summary = header?.match(/<summary\b[\s\S]*?<\/summary>/)?.[0];
    const switcherLabelClasses = summary?.match(/<span class="([^"]+)"/)?.[1];
    const contextLinkClasses = header?.match(
      /<a class="([^"]+)"[^>]*>Mietverhältnis — Donaudampfschifffahrtsgesellschaftskapitänstraße/,
    )?.[1];

    expect(header, 'the renter header must render').toBeDefined();
    expect(headerRowClasses).toMatch(/\bmin-w-0\b/);
    expect(headerRowClasses).toMatch(/\bflex-wrap\b/);
    expect(detailsClasses).toMatch(/\bmin-w-0\b/);
    expect(detailsClasses).toMatch(/\bmax-w-full\b/);
    expect(switcherLabelClasses).toMatch(/\bmin-w-0\b/);
    expect(switcherLabelClasses).toMatch(
      /(?:\bbreak-words\b|\bhyphens-auto\b|\[overflow-wrap:anywhere\])/,
    );
    expect(contextLinkClasses).toMatch(
      /(?:\bbreak-words\b|\bhyphens-auto\b|\[overflow-wrap:anywhere\])/,
    );

    const Documents = requiredExport<ComponentType<DocumentsProps>>(
      './renter-documents.tsx',
      'RenterDocumentsView',
    );
    const documentsHtml = renderToStaticMarkup(
      <Documents kind="UVI_ARTIFACT" state="ready" documents={[UVI_DOCUMENT]} />,
    );
    const pageHeadingClasses = documentsHtml.match(
      /<h1 class="([^"]+)">Verbrauchsinformationen<\/h1>/,
    )?.[1];
    const documentHeadingClasses = documentsHtml.match(
      /<h2 class="([^"]+)">Verbrauchsinformation April 2026<\/h2>/,
    )?.[1];

    expect(pageHeadingClasses).toMatch(
      /(?:\bbreak-words\b|\bhyphens-auto\b|\[overflow-wrap:anywhere\])/,
    );
    expect(documentHeadingClasses).toMatch(
      /(?:\bbreak-words\b|\bhyphens-auto\b|\[overflow-wrap:anywhere\])/,
    );
  });

  it('uses a design-system shadow token instead of a raw rgba shadow', () => {
    expect(RENTER_SHELL_SOURCE).not.toMatch(/rgba\s*\(/);
    expect(RENTER_SHELL_SOURCE).toMatch(/\bshadow-(?:sm|md|lg|xl|2xl)\b/);
  });

  it('renders only the three approved renter navigation destinations without private data', () => {
    const html = renderShell({
      tenancyId: 'tenancy-current',
      pathname: '/renter/tenancy-current',
      accounts: [],
      renterContexts: [currentContext],
    });

    expect(html).toContain('Meine Unterlagen');
    expect(html).toContain('href="/renter/tenancy-current"');
    expect(html).toContain('Mein Mietverhältnis');
    expect(html).toContain('href="/renter/tenancy-current/abrechnungen"');
    expect(html).toContain('Abrechnungen');
    expect(html).toContain('href="/renter/tenancy-current/verbrauchsinformationen"');
    expect(html).toContain('Verbrauchsinformationen');
    expect(html).not.toMatch(/\b\d+[,.]\d{2}\s?€/);
    expect(visibleText(html)).not.toContain('account-owner');
    expect(html).not.toContain('Andere Mietpartei');
  });
});

type OverviewProps = {
  state: 'loading' | 'empty' | 'error' | 'ready';
  overview?: typeof OVERVIEW;
  onRetry?: () => void;
};

describe('M10-COPY-05..06 renter overview', () => {
  const renderOverview = (props: OverviewProps) => {
    const Overview = requiredExport<ComponentType<OverviewProps>>(
      './renter-overview.tsx',
      'RenterOverviewView',
    );
    return renderToStaticMarkup(<Overview {...props} />);
  };

  it('renders only the approved overview facts', () => {
    const html = renderOverview({ state: 'ready', overview: OVERVIEW });

    expect(html).toContain('Mein Mietverhältnis');
    expect(html).toContain('Musterhaus');
    expect(html).toContain('Musterstraße 12');
    expect(html).toContain('Wohnung 2');
    expect(html).not.toMatch(/€|Kontonummer|Mietpartei|Vermieterkonto/);
  });

  it.each([
    ['loading', 'Wird geladen …'],
    [
      'empty',
      'Zu Ihrem Zugang ist derzeit kein Mietverhältnis hinterlegt. Bitte wenden Sie sich an Ihre Vermieterin oder Ihren Vermieter.',
    ],
    ['error', 'Die Daten konnten nicht geladen werden. Bitte versuchen Sie es später erneut.'],
  ] as const)('renders the approved %s state', (state, copy) => {
    const html = renderOverview({ state, onRetry: () => undefined });
    expect(html).toContain(copy);
    if (state === 'error') expect(html).toContain('Erneut versuchen');
  });
});

type DocumentsProps = {
  kind: 'STATEMENT_ARCHIVE' | 'UVI_ARTIFACT';
  state: 'loading' | 'empty' | 'error' | 'ready';
  documents?: Array<typeof STATEMENT_DOCUMENT | typeof UVI_DOCUMENT>;
  onRetry?: () => void;
};

describe('M10-COPY-05..06 published renter documents', () => {
  const renderDocuments = (props: DocumentsProps) => {
    const Documents = requiredExport<ComponentType<DocumentsProps>>(
      './renter-documents.tsx',
      'RenterDocumentsView',
    );
    return renderToStaticMarkup(<Documents {...props} />);
  };

  it('derives statement titles only from periodStart and periodEnd', () => {
    const html = renderDocuments({
      kind: 'STATEMENT_ARCHIVE',
      state: 'ready',
      documents: [STATEMENT_DOCUMENT, UVI_DOCUMENT],
    });

    expect(html).toContain('Abrechnungen');
    expect(html).toContain('Abrechnung');
    expect(html).toContain('01.01.2025');
    expect(html).toContain('31.12.2025');
    expect(html).toContain('Als PDF speichern');
    expect(html).toContain(`href="${STATEMENT_DOCUMENT.downloadUrl}"`);
    expect(html).not.toContain(STATEMENT_DOCUMENT.filename);
    expect(html).not.toContain(UVI_DOCUMENT.downloadUrl);
  });

  it('derives UVI titles only from documentMonth', () => {
    const html = renderDocuments({
      kind: 'UVI_ARTIFACT',
      state: 'ready',
      documents: [STATEMENT_DOCUMENT, UVI_DOCUMENT],
    });

    expect(html).toContain('Verbrauchsinformationen');
    expect(html).toContain('Verbrauchsinformation April 2026');
    expect(html).toContain('Als PDF speichern');
    expect(html).toContain(`href="${UVI_DOCUMENT.downloadUrl}"`);
    expect(html).not.toContain(UVI_DOCUMENT.filename);
    expect(html).not.toContain(STATEMENT_DOCUMENT.downloadUrl);
  });

  it.each([
    ['STATEMENT_ARCHIVE', 'loading', 'Wird geladen …'],
    ['STATEMENT_ARCHIVE', 'empty', 'Es liegen noch keine Abrechnungen für Sie bereit.'],
    ['UVI_ARTIFACT', 'empty', 'Es liegen noch keine Verbrauchsinformationen für Sie bereit.'],
    [
      'UVI_ARTIFACT',
      'error',
      'Die Daten konnten nicht geladen werden. Bitte versuchen Sie es später erneut.',
    ],
  ] as const)('renders the approved %s %s state', (kind, state, copy) => {
    const html = renderDocuments({ kind, state, onRetry: () => undefined });
    expect(html).toContain(copy);
    if (state === 'error') expect(html).toContain('Erneut versuchen');
  });
});
