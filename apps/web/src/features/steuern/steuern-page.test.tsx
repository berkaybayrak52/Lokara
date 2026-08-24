import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { readFileSync, readdirSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import * as PortalShellModule from '../portal/app-shell';

const { PortalShellContent } = PortalShellModule;

type Role = 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR';

const OWNER = { id: 'acc-1', name: 'Eigene Verwaltung', role: 'OWNER' as const, shape: 'SOLO' };
const ADVISOR = {
  id: 'acc-1',
  name: 'Kanzlei Süd',
  role: 'TAX_ADVISOR' as const,
  shape: 'SOLO',
};
const EMPLOYEE = {
  id: 'acc-1',
  name: 'Verwaltung Nord',
  role: 'EMPLOYEE' as const,
  shape: 'HAUSVERWALTUNG',
};

const FEATURE_SOURCE = readdirSync(new URL('.', import.meta.url))
  .filter((name) => /\.(ts|tsx)$/.test(name) && !name.endsWith('.test.tsx'))
  .map((name) => readFileSync(new URL(name, import.meta.url), 'utf8'))
  .join('\n');

async function taxModule() {
  const modulePath: string = './steuern-page';
  try {
    return await import(modulePath);
  } catch {
    return undefined;
  }
}

function exportedFunction(module: unknown, name: string): (...args: unknown[]) => unknown {
  const candidate = (module as Record<string, unknown> | undefined)?.[name];
  expect(candidate, `RED M7-E: ${name} is missing`).toBeTypeOf('function');
  if (typeof candidate !== 'function') throw new Error(`RED M7-E: ${name} is missing`);
  return candidate as (...args: unknown[]) => unknown;
}

const FIXTURE = {
  accountId: 'acc-1',
  role: 'OWNER' as Role,
  buildings: [{ id: 'building-1', label: 'Musterstraße 12' }],
  selectedBuildingId: 'building-1',
  selectedTaxYear: 2025,
  supportedTaxYears: [2024, 2025, 2026],
  readiness: {
    productionBlocked: true,
    findings: [
      { severity: 'rot', message: 'DATEV-Parameter sind nicht verifiziert.' },
      { severity: 'gelb', message: 'AfA-Nachweis prüfen.' },
    ],
  },
  afaHistory: [{ id: 'afa-1', version: 1, annualCents: 540103 }],
  exportHistory: [{
    id: 'export-1',
    version: 1,
    filename: 'anlage-v-2025.pdf',
    generatedAt: '2025-01-02T03:04:05Z',
    sha256: 'sha256:abc123def456',
    readiness: 'Gesperrt - Quellenprüfung offen',
    blockers: ['DATEV-Parameter sind nicht verifiziert.'],
    artifacts: [
      { filename: 'anlage-v-2025.pdf', sha256: 'sha256:pdf123' },
      { filename: 'anlage-v-2025.csv', sha256: 'sha256:csv123' },
    ],
  }],
  adviserProfile: null,
  mappings: [],
  adviserProfiles: [{ id: 'profile-2', version: 2, label: 'Kanzlei 2025' }],
  mappingVersions: [{ id: 'mapping-3', version: 3, label: 'SKR04 2025' }],
  selectedAdviserProfileVersionId: 'profile-2',
  selectedMappingVersionId: 'mapping-3',
  rechtsstandEvidence: { afa: '08/2026', export: '07/2026' },
};

describe('M7 tax workspace', () => {
  it('renders object/year selection, AfA, readiness, settings and immutable history', async () => {
    const module = await taxModule();
    expect(module, 'RED M7-E: steuern-page.tsx is missing').toBeDefined();
    const TaxWorkspace = module?.TaxWorkspace;
    expect(TaxWorkspace).toBeTypeOf('function');
    if (!TaxWorkspace) throw new Error('RED M7-E: TaxWorkspace is missing');
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} />);

    for (const copy of [
      'Steuern',
      'Objekt',
      'Steuerjahr',
      'AfA-Assistent',
      'Exportbereitschaft',
      'Steuerberaterprofil',
      'Zuordnungen',
      'Exporthistorie',
      'Rechtsstand',
      'rechtskonform, keine Rechts- oder Steuerberatung',
    ]) {
      expect(html).toContain(copy);
    }
    expect(html).toContain('Musterstraße 12');
    expect(html).toContain('2025');
    expect(html).toContain('DATEV-Parameter sind nicht verifiziert.');
    expect(html).toContain('disabled');
    expect(html).toContain('AfA 08/2026');
    expect(html).toContain('Export 07/2026');
    expect(html).not.toContain('Mieter');
    expect(html).not.toContain('renter');
  });

  it('keeps object and year controlled and wires every M7 workflow to the tax API', () => {
    expect(FEATURE_SOURCE).toMatch(/value=\{selectedBuildingId\}/);
    expect(FEATURE_SOURCE).toMatch(/value=\{(?:String\()?selectedTaxYear/);
    expect(FEATURE_SOURCE).toMatch(/onChange/);
    for (const path of [
      '/tax/buildings',
      '/tax/afa/preview',
      '/tax/afa',
      '/tax/afa/history',
      '/tax/readiness',
      '/tax/adviser-profile',
      '/tax/mappings/',
      '/tax/exports',
      '/artifacts/',
    ]) {
      expect(FEATURE_SOURCE).toContain(path);
    }
  });

  it('shows immutable archive evidence and keeps blocked artifact downloads disabled', async () => {
    const module = await taxModule();
    const TaxWorkspace = module?.TaxWorkspace;
    expect(TaxWorkspace).toBeTypeOf('function');
    if (!TaxWorkspace) throw new Error('RED M7-E: TaxWorkspace is missing');
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} />);
    for (const evidence of [
      '02.01.2025',
      'sha256:abc123def456',
      'Gesperrt - Quellenprüfung offen',
      'DATEV-Parameter sind nicht verifiziert.',
      'anlage-v-2025.pdf',
      'anlage-v-2025.csv',
    ]) {
      expect(html).toContain(evidence);
    }
    expect(html).toMatch(/anlage-v-2025\.pdf[\s\S]*disabled/);
  });

  it('shows each workflow action, one disclaimer, and a mobile tax navigation', async () => {
    const module = await taxModule();
    const TaxWorkspace = module?.TaxWorkspace;
    expect(TaxWorkspace).toBeTypeOf('function');
    if (!TaxWorkspace) throw new Error('RED M7-E: TaxWorkspace is missing');
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} />);
    for (const action of [
      'AfA-Vorschau berechnen',
      'AfA-Datensatz speichern',
      'Bereitschaft prüfen',
      'Neue Profilversion speichern',
      'Neue Zuordnungsversion speichern',
      'Export erzeugen',
    ]) {
      expect(html).toContain(action);
    }
    expect(html.match(/keine Rechts- oder Steuerberatung/g)).toHaveLength(1);
    expect(html).toContain('aria-label="Steuernavigation"');
    expect(FEATURE_SOURCE).toMatch(/(?:sm:hidden|lg:hidden|overflow-x-auto)/);
  });

  it('gives the adviser a restricted tax workspace and no owner write actions', async () => {
    const module = await taxModule();
    expect(module, 'RED M7-E: steuern-page.tsx is missing').toBeDefined();
    const TaxWorkspace = module?.TaxWorkspace;
    expect(TaxWorkspace).toBeTypeOf('function');
    if (!TaxWorkspace) throw new Error('RED M7-E: TaxWorkspace is missing');
    const html = renderToStaticMarkup(
      <TaxWorkspace {...FIXTURE} role="TAX_ADVISOR" />,
    );
    expect(html).toContain('Steuerberaterprofil');
    expect(html).toContain('Zuordnungen');
    expect(html).not.toContain('AfA-Datensatz speichern');
    expect(html).not.toContain('Export erzeugen');
  });

  it('adds /steuern navigation for owner and adviser, never employee or placeholder copy', () => {
    const ownerHtml = renderToStaticMarkup(
      <PortalShellContent accountId="acc-1" account={OWNER} accounts={[OWNER]} pathname="/a/acc-1/steuern">
        <p>Steuerinhalt</p>
      </PortalShellContent>,
    );
    const adviserHtml = renderToStaticMarkup(
      <PortalShellContent accountId="acc-1" account={ADVISOR} accounts={[ADVISOR]} pathname="/a/acc-1/steuern">
        <p>Steuerinhalt</p>
      </PortalShellContent>,
    );
    const employeeHtml = renderToStaticMarkup(
      <PortalShellContent accountId="acc-1" account={EMPLOYEE} accounts={[EMPLOYEE]} pathname="/a/acc-1">
        <p>Mitarbeiterinhalt</p>
      </PortalShellContent>,
    );
    expect(ownerHtml).toContain('href="/a/acc-1/steuern"');
    expect(adviserHtml).toContain('href="/a/acc-1/steuern"');
    expect(adviserHtml).toContain('Steuerinhalt');
    expect(adviserHtml).not.toContain('Steuerfunktionen werden vorbereitet');
    expect(employeeHtml).not.toContain('/steuern');
  });

  it('builds a real normalized AfA request and displays field validation errors', async () => {
    const module = await taxModule();
    const buildAfaRequest = exportedFunction(module, 'buildAfaRequest');
    const validateAfaForm = exportedFunction(module, 'validateAfaForm');
    const facts = {
      erwerbsart: 'kauf', gebaeudetyp: 'mfh', fertigstellungsjahr: 1978,
      uebergangNutzenLastenDatum: '2024-03-15', wohnflaecheGesamt: 19400,
      grundstuecksflaecheM2: 420, kaufpreisCent: 48000000,
      grunderwerbsteuerCent: 3120000, notarGrundbuchCent: 720000,
      grundschuldkostenCent: 45000, maklerprovisionCent: 1713600,
      sonstigeAnkCent: 0, beweglicheWgCent: 0, aufteilungsWeg: 'vertrag',
      vertragGebaeudeCent: 27005129, vertragBodenCent: 26548471,
    };
    const request = buildAfaRequest(facts, {
      buildingId: 'building-1', taxYear: 2025,
      generatedAt: '2025-01-02T03:04:05Z',
      rules: { registerRows: [], rechtsstand: '08/2026' },
    }) as Record<string, unknown>;
    expect(request).toMatchObject({ buildingId: 'building-1', taxYear: 2025, facts });
    expect(request).not.toHaveProperty('fixtureId');
    expect(request.facts).not.toEqual({});

    const errors = validateAfaForm({ ...facts, fertigstellungsjahr: undefined }) as Record<string, string>;
    expect(errors.fertigstellungsjahr).toBeTruthy();
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(
      <TaxWorkspace {...FIXTURE} validationErrors={errors} afaFacts={facts} />,
    );
    expect(html).toContain(errors.fertigstellungsjahr);
    for (const field of ['kaufpreisCent', 'uebergangNutzenLastenDatum', 'aufteilungsWeg']) {
      expect(html).toContain(`name="${field}"`);
    }
  });

  it('builds real profile, mapping and readiness payloads using selected stored versions', async () => {
    const module = await taxModule();
    const buildProfile = exportedFunction(module, 'buildAdviserProfileRequest');
    const buildMapping = exportedFunction(module, 'buildTaxMappingRequest');
    const buildReadiness = exportedFunction(module, 'buildReadinessRequest');
    expect(buildProfile({
      beraternummer: '123', mandantennummer: '456', kontenrahmen: 'SKR04',
      sachkontenlaenge: 4, wirtschaftsjahresbeginn: '2025-01-01',
    }, '2025-01-02T03:04:05Z')).toMatchObject({
      profile: { beraternummer: '123', mandantennummer: '456', kontenrahmen: 'SKR04' },
    });
    const mapping = buildMapping({
      sourceCategory: 'kaltmiete', anlageVLine: 'income_rent', account: '4100',
    }, 2025, '2025-01-02T03:04:05Z') as Record<string, unknown>;
    expect(mapping).toMatchObject({ taxYear: 2025 });
    expect(mapping.mapping).not.toEqual([]);
    expect(buildReadiness({
      buildingId: 'building-2', taxYear: 2024, afaVersionId: 'afa-2',
      adviserProfileVersionId: 'profile-2', mappingVersionId: 'mapping-3',
    })).toEqual({
      buildingId: 'building-2', taxYear: 2024, afaVersionId: 'afa-2',
      adviserProfileVersionId: 'profile-2', mappingVersionId: 'mapping-3',
    });
  });

  it('renders all supported years, stored version selection and readiness errors', async () => {
    const module = await taxModule();
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(
      <TaxWorkspace {...FIXTURE} readinessError="Bereitschaft konnte nicht geprüft werden." />,
    );
    for (const year of [2024, 2025, 2026]) expect(html).toContain(`value="${year}"`);
    expect(html).toContain('value="profile-2"');
    expect(html).toContain('value="mapping-3"');
    expect(html).toContain('Bereitschaft konnte nicht geprüft werden.');

    const readyHtml = renderToStaticMarkup(
      <TaxWorkspace {...FIXTURE} readiness={{ productionBlocked: false, findings: [] }} />,
    );
    expect(readyHtml).toMatch(/<button(?![^>]*disabled)[^>]*>Export erzeugen<\/button>/);
  });

  it('maps archive evidence from the API without inventing blockers or Rechtsstand', async () => {
    const module = await taxModule();
    const mapHistory = exportedFunction(module, 'mapExportHistoryResponse');
    const mapped = mapHistory({ exports: [{
      id: 'export-1', version: 4, sha256: 'archive-sha',
      generatedAt: '2025-01-02T03:04:05Z', readinessFindings: [
        { code: 'source_gap', message: 'Quellennachweis fehlt.' },
      ], blockers: ['Kontenzuordnung ist nicht verifiziert.'],
      afaRechtsstand: '09/2031', exportRechtsstand: '10/2032',
      artifacts: [{ id: 'artifact-1', filename: 'anlage-v.pdf', sha256: 'pdf-sha', artifactKind: 'anlage_v_pdf' }],
    }] }) as Record<string, unknown>[];
    expect(mapped[0]).toMatchObject({
      blockers: ['Kontenzuordnung ist nicht verifiziert.'],
      afaRechtsstand: '09/2031', exportRechtsstand: '10/2032',
    });
    expect(JSON.stringify(mapped)).toContain('Quellennachweis fehlt.');
  });

  it('uses a visible archive link only when the archived response permits download', async () => {
    const module = await taxModule();
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const ready = renderToStaticMarkup(
      <TaxWorkspace {...FIXTURE} readiness={{ productionBlocked: false, findings: [] }} />,
    );
    expect(ready).toMatch(/<a(?![^>]*sr-only)[^>]*href="[^"]+\/artifacts\/[^"]+"[^>]*>Herunterladen<\/a>/);
    expect(ready).not.toMatch(/<button[^>]*>Herunterladen<\/button>/);
    const blocked = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} />);
    expect(blocked).not.toMatch(/<a[^>]*href="[^"]+\/artifacts\/[^"]+"/);
    expect(blocked).toMatch(/<button[^>]*disabled[^>]*>Herunterladen<\/button>/);
  });

  it('routes advisers to the editable restricted tax workspace without the placeholder', async () => {
    const landingPath = exportedFunction(PortalShellModule, 'taxAdvisorLandingPath');
    expect(landingPath('acc-1')).toBe('/a/acc-1/steuern');
    const module = await taxModule();
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} role="TAX_ADVISOR" />);
    for (const field of ['beraternummer', 'mandantennummer', 'kontenrahmen', 'anlageVLine', 'account']) {
      expect(html).toContain(`name="${field}"`);
    }
    expect(html).not.toContain('Steuerfunktionen werden vorbereitet');
  });

  it('shows plain German blocker copy without raw codes or record identifiers', async () => {
    const module = await taxModule();
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} readiness={{
      productionBlocked: true,
      findings: [{ severity: 'rot', message: 'Die Kontenzuordnung ist noch nicht verifiziert.' }],
    }} />);
    expect(html).toContain('Die Kontenzuordnung ist noch nicht verifiziert.');
    expect(html).not.toContain('mapping_unverified');
    expect(html).not.toContain('readiness-1');
  });

  it('uses only edited visible AfA facts and maps a true annual AfA field', async () => {
    const module = await taxModule();
    const buildAfaRequest = exportedFunction(module, 'buildAfaRequest');
    const mapAfaHistory = exportedFunction(module, 'mapAfaHistoryResponse');
    const editedFacts = {
      erwerbsart: 'kauf', gebaeudetyp: 'mfh', fertigstellungsjahr: 1999,
      uebergangNutzenLastenDatum: '2025-06-01', wohnflaecheGesamt: 22200,
      grundstuecksflaecheM2: 555, kaufpreisCent: 61234567,
      grunderwerbsteuerCent: 4000000, notarGrundbuchCent: 800000,
      grundschuldkostenCent: 12345, maklerprovisionCent: 2000000,
      sonstigeAnkCent: 12300, beweglicheWgCent: 45600, aufteilungsWeg: 'vertrag',
      vertragGebaeudeCent: 35000000, vertragBodenCent: 33046967,
    };
    const request = buildAfaRequest(editedFacts, {
      buildingId: 'building-1', taxYear: 2025, generatedAt: '2025-01-02T03:04:05Z',
      rules: { registerRows: [], rechtsstand: '08/2026' },
    }) as { facts: Record<string, unknown> };
    expect(request.facts).toEqual(editedFacts);
    expect(Object.values(request.facts)).not.toContain(48000000);
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} afaFacts={editedFacts} />);
    for (const field of Object.keys(editedFacts)) expect(html).toContain(`name="${field}"`);
    expect(html).toContain('value="61234567"');
    expect(html).not.toContain('value="48000000"');

    const mapped = mapAfaHistory({ records: [{
      id: 'afa-1', version: 1, buildingId: 'building-1', taxYear: 2025,
      annualAfaCents: 540103,
      result: { calculated_values: { acquisition_total_cents: 53553600 } },
    }] }, 'building-1', 2025) as { annualCents: number }[];
    expect(mapped).toEqual([{ id: 'afa-1', version: 1, annualCents: 540103 }]);
    expect(mapped[0]?.annualCents).not.toBe(53553600);
  });

  it('preserves every profile field and creates category-correct separate SKR mappings', async () => {
    const module = await taxModule();
    const buildProfile = exportedFunction(module, 'buildAdviserProfileRequest');
    const buildMapping = exportedFunction(module, 'buildTaxMappingRequest');
    const profile = buildProfile({
      beraternummer: '123', mandantennummer: '456', kontenrahmen: 'SKR03',
      sachkontenlaenge: 6, wirtschaftsjahresbeginn: '2025-04-01',
    }, '2025-01-02T03:04:05Z') as Record<string, unknown>;
    expect(profile).toMatchObject({ profile: {
      beraternummer: '123', mandantennummer: '456', kontenrahmen: 'SKR03',
      sachkontenlaenge: 6, wjBeginn: '2025-04-01',
    } });
    const income = buildMapping({ sourceCategory: 'kaltmiete', anlageVLine: 'income_rent', skr03Account: '4100', skr04Account: '4400' }, 2025, '2025-01-02T03:04:05Z') as { mapping: Record<string, unknown>[] };
    const cost = buildMapping({ sourceCategory: 'werbungskosten', anlageVLine: 'costs', skr03Account: '4200', skr04Account: '4500' }, 2025, '2025-01-02T03:04:05Z') as { mapping: Record<string, unknown>[] };
    expect(income.mapping[0]).toMatchObject({ skr03Account: '4100', skr04Account: '4400', direction: 'einnahme' });
    expect(cost.mapping[0]).toMatchObject({ skr03Account: '4200', skr04Account: '4500', direction: 'ausgabe' });
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} adviserProfileForm={{
      beraternummer: '123', mandantennummer: '456', kontenrahmen: 'SKR03',
      sachkontenlaenge: 6, wirtschaftsjahresbeginn: '2025-04-01',
    }} mappingForm={{
      sourceCategory: 'kaltmiete', anlageVLine: 'income_rent',
      skr03Account: '4100', skr04Account: '4400',
    }} />);
    for (const value of ['123', '456', 'SKR03', '6', '2025-04-01', '4100', '4400']) {
      expect(html).toContain(`value="${value}"`);
    }
    const transition = exportedFunction(module, 'savedTaxVersionTransition');
    expect(transition('profile', { id: 'profile-new' }, 'acc-1', 2025)).toEqual({
      selectedVersionId: 'profile-new', invalidateQueryKey: ['account', 'acc-1', 'tax', 'adviser-profile'],
    });
  });

  it('uses stable supported years and scopes archived evidence by object and year', async () => {
    const module = await taxModule();
    const supportedYears = exportedFunction(module, 'supportedTaxYears');
    const scopeHistory = exportedFunction(module, 'scopeExportHistory');
    expect(supportedYears()).toEqual([2024, 2025, 2026]);
    expect(supportedYears(1999)).toEqual([2024, 2025, 2026]);
    const scoped = scopeHistory([
      { id: 'selected', buildingId: 'building-1', taxYear: 2025, afaRechtsstand: '09/2031', exportRechtsstand: '10/2032' },
      { id: 'other', buildingId: 'building-2', taxYear: 2024, afaRechtsstand: '01/1999', exportRechtsstand: '02/1999' },
    ], 'building-1', 2025) as Record<string, unknown>[];
    expect(scoped.map((row) => row.id)).toEqual(['selected']);
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE}
      exportHistory={scoped}
      rechtsstandEvidence={{ afa: scoped[0]?.afaRechtsstand, export: scoped[0]?.exportRechtsstand }}
    />);
    expect(html).toContain('AfA 09/2031');
    expect(html).toContain('Export 10/2032');
    expect(html).not.toContain('01/1999');
    expect(html).not.toContain('02/1999');
  });

  it('renders the real adviser shell branch without obsolete production wording', async () => {
    const adviserHtml = renderToStaticMarkup(
      <PortalShellContent accountId="acc-1" account={ADVISOR} accounts={[ADVISOR]} pathname="/a/acc-1">
        <p>Steuerarbeitsbereich</p>
      </PortalShellContent>,
    );
    expect(adviserHtml).toContain('Steuerarbeitsbereich');
    expect(adviserHtml).not.toContain('Steuerfunktionen werden vorbereitet');

    const module = await taxModule();
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const blocked = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} />);
    expect(blocked).not.toContain('Produktionsausgabe');
    expect(blocked).not.toContain('Produktionsdownloads');
    expect(blocked).toContain('Download ist gesperrt');
  });

  it('validates allocation-route fields and renders preview and mutation errors', async () => {
    const module = await taxModule();
    const validate = exportedFunction(module, 'validateAfaForm');
    const allocationRoute = exportedFunction(module, 'allocationRouteForFacts');
    const common = {
      erwerbsart: 'kauf', gebaeudetyp: 'mfh', fertigstellungsjahr: 1978,
      uebergangNutzenLastenDatum: '2024-03-15', wohnflaecheGesamt: 19400,
      grundstuecksflaecheM2: 420, kaufpreisCent: 48000000,
      grunderwerbsteuerCent: 3120000, notarGrundbuchCent: 720000,
      grundschuldkostenCent: 45000, maklerprovisionCent: 1713600,
      sonstigeAnkCent: 0, beweglicheWgCent: 0,
    };
    const contractErrors = validate({ ...common, aufteilungsWeg: 'vertrag' }) as Record<string, string>;
    expect(contractErrors.vertragGebaeudeCent).toBeTruthy();
    expect(contractErrors.vertragBodenCent).toBeTruthy();
    for (const route of ['bmf', 'gutachten']) {
      const facts = { ...common, aufteilungsWeg: route };
      const errors = validate(facts) as Record<string, string>;
      expect(errors).not.toHaveProperty('vertragGebaeudeCent');
      expect(errors).not.toHaveProperty('vertragBodenCent');
      expect(allocationRoute(facts)).toBe(route);
    }

    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE}
      afaPreviewAnnualCents={450086}
      afaMutationError="Die AfA-Vorschau konnte nicht berechnet werden."
    />);
    expect(html).toContain('4.500,86');
    expect(html).toContain('Die AfA-Vorschau konnte nicht berechnet werden.');
  });

  it('requires an explicit editable direction for every tax mapping category', async () => {
    const module = await taxModule();
    const buildMapping = exportedFunction(module, 'buildTaxMappingRequest');
    const cases = [
      ['nk_guthaben', 'einnahme'],
      ['kaution', 'clearing'],
      ['afa', 'ausgabe'],
      ['clearing', 'clearing'],
      ['non_cash', 'sachbuchung'],
    ];
    for (const [sourceCategory, direction] of cases) {
      const result = buildMapping({
        sourceCategory, direction, anlageVLine: 'caller-selected',
        skr03Account: '1234', skr04Account: '5678',
      }, 2025, '2025-01-02T03:04:05Z') as { mapping: Record<string, unknown>[] };
      expect(result.mapping[0]).toMatchObject({ category: sourceCategory, direction });
    }
    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} mappingForm={{
      sourceCategory: 'nk_guthaben', direction: 'einnahme', anlageVLine: 'income_credit',
      skr03Account: '1234', skr04Account: '5678',
    }} />);
    expect(html).toContain('name="direction"');
    expect(html).toContain('value="einnahme"');
  });

  it('submits temporal self-use periods and labels tax-year, deductible and private AfA', async () => {
    const module = await taxModule();
    const buildAfaRequest = exportedFunction(module, 'buildAfaRequest');
    const facts = {
      erwerbsart: 'kauf', fertigstellungsjahr: 1978,
      uebergangNutzenLastenDatum: '2024-03-15', wohnflaecheGesamt: 19400,
      kaufpreisCent: 48000000, aufteilungsWeg: 'vertrag',
      vertragGebaeudeCent: 27005129, vertragBodenCent: 26548471,
      selfUsePeriods: [{
        vonDatum: '2025-01-01', bisDatum: '2025-12-31',
        selbstgenutzteFlaeche: 9700, einheitIds: [],
      }],
    };
    const request = buildAfaRequest(facts, {
      buildingId: 'building-1', taxYear: 2025,
      generatedAt: '2025-01-02T03:04:05Z',
      rules: { registerRows: [], rechtsstand: '08/2026' },
    }) as { facts: typeof facts };
    expect(request.facts.selfUsePeriods).toEqual(facts.selfUsePeriods);

    const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
    const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE}
      afaFacts={facts}
      afaPreview={{
        taxYearAfaCents: 540103,
        deductibleAfaCents: 270052,
        nonDeductibleAfaCents: 270051,
      }}
    />);
    for (const field of [
      'selfUsePeriods.0.vonDatum',
      'selfUsePeriods.0.bisDatum',
      'selfUsePeriods.0.selbstgenutzteFlaeche',
    ]) expect(html).toContain(`name="${field}"`);
    expect(html).toContain('AfA im Steuerjahr');
    expect(html).toContain('5.401,03');
    expect(html).toContain('Abziehbare AfA');
    expect(html).toContain('2.700,52');
    expect(html).toContain('Nicht abziehbare AfA (Selbstnutzung)');
    expect(html).toContain('2.700,51');
    expect(html).not.toMatch(/Abziehbare AfA[^<]*5\.401,03/);
  });

  it('selects each supported export kind and sends the selected kind to readiness and generation', async () => {
    const module = await taxModule();
    const buildExportRequest = exportedFunction(module, 'buildExportRequest');
    for (const [kind, label] of [
      ['anlage_v_pdf', 'Anlage-V PDF'],
      ['anlage_v_csv', 'Anlage-V CSV'],
      ['datev_extf', 'DATEV-Format'],
    ]) {
      expect(buildExportRequest({
        exportKind: kind, buildingId: 'building-1', taxYear: 2025,
        afaRecordVersionId: 'afa-1', adviserProfileVersionId: 'profile-1',
        mappingVersionId: 'mapping-1', generatedAt: '2025-01-02T03:04:05Z',
      })).toMatchObject({ exportKind: kind, buildingId: 'building-1', taxYear: 2025 });
      const TaxWorkspace = (module as { TaxWorkspace: React.ComponentType<Record<string, unknown>> }).TaxWorkspace;
      const html = renderToStaticMarkup(<TaxWorkspace {...FIXTURE} selectedExportKind={kind} />);
      expect(html).toContain(`value="${kind}"`);
      expect(html).toContain(label);
    }
  });
});
