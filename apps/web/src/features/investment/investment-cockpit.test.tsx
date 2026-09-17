// @vitest-environment happy-dom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { existsSync } from 'node:fs';
import { URL as NodeURL } from 'node:url';
import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

type Role = 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR';

const mocks = vi.hoisted(() => ({
  role: 'OWNER' as Role,
  search: 'caseKey=case-frozen-1',
  replace: vi.fn(),
  fetch: vi.fn<typeof fetch>(),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => '/a/account-1/investment',
  useSearchParams: () => new URLSearchParams(mocks.search),
  useRouter: () => ({ replace: mocks.replace }),
}));
vi.mock('@/features/portal/queries', () => ({
  useMe: () => ({
    isPending: false,
    isError: false,
    data: { accounts: [{ id: 'account-1', name: 'Eigentümer', role: mocks.role }] },
  }),
}));

const kpiSlots = {
  factor: { status: 'available', value: 1321 },
  gross_yield: { status: 'available', value: 757 },
  net_yield: { status: 'available', value: 542 },
  dscr: { status: 'available', value: 122, color: 'green' },
  equity_return: { status: 'available', before_tax: 1006, after_tax: 811 },
  cashflow: { status: 'available', before_tax: 37533, after_tax: 19127, color: 'green' },
  break_even: { status: 'available', before_tax: 227467, after_tax: 232023 },
};
const schedule = Array.from({ length: 12 }, (_, index) => [
  34_000_000 - index * 56_667,
  110_500 - index * 184,
  56_667 + index * 184,
  33_943_333 - index * 56_851,
]);
const interestSensitivity = [290, 340, 390, 440, 490].map((interestBp, index) => ({
  interest_bp: interestBp,
  is_base: interestBp === 390,
  dscr_hundredths: [147, 134, 122, 113, 105][index],
  cashflow_after_month_cents: [35672, 27400, 19127, 10855, 2582][index],
  equity_return_after_bp: [983, 897, 811, 725, 639][index],
  break_even_after_month_cents: [203496, 217759, 232023, 246284, 260548][index],
  dscr_color: index < 3 ? 'green' : 'amber',
  cashflow_color: index < 4 ? 'green' : 'amber',
}));
const repaymentSensitivity = [100, 200, 300, 400].map((initialRepaymentBp, index) => ({
  initial_repayment_bp: initialRepaymentBp,
  dscr_hundredths: [147, 122, 105, 91][index],
  cashflow_after_month_cents: [47676, 19127, -9421, -37969][index],
  closing_balance_cents: [33653861, 33307709, 32961570, 32615428][index],
  equity_return_after_bp: [808, 811, 815, 818][index],
  dscr_color: ['green', 'green', 'amber', 'red'][index],
  cashflow_color: ['green', 'green', 'red', 'red'][index],
}));
const caseResponse = {
  caseKey: 'case-frozen-1',
  version: 1,
  resultId: 'result-frozen-1',
  outcome: 'calculated',
  calculatedValues: { schedule },
  kpiSlots,
  rechtsstand: '07/2026',
  productionBlocked: true,
  findings: [],
  warnings: [],
};

async function loadCockpit(): Promise<React.ComponentType<{ accountId: string }>> {
  expect(
    existsSync(new NodeURL('./investment-cockpit.tsx', import.meta.url)),
    'RED M10-I4: owner investment cockpit is missing',
  ).toBe(true);
  expect(
    existsSync(new NodeURL('../../app/a/[accountId]/investment/page.tsx', import.meta.url)),
    'RED M10-I4: /a/{accountId}/investment route is missing',
  ).toBe(true);
  const modulePath = './investment-cockpit';
  const module = (await import(/* @vite-ignore */ modulePath)) as {
    InvestmentCockpit: React.ComponentType<{ accountId: string }>;
  };
  expect(module.InvestmentCockpit).toBeDefined();
  return module.InvestmentCockpit;
}

function json(value: object, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function installEnabledCaseResponses(): void {
  mocks.fetch.mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith('/investment/entitlement')) return json({ enabled: true });
    if (url.endsWith('/investment/cases/case-frozen-1/sensitivity')) {
      return json({
        interestSensitivity,
        repaymentSensitivity,
        repaymentAxisMeaning: 'structure_not_stress',
      });
    }
    if (url.endsWith('/investment/cases/case-frozen-1/bank-view')) {
      return json({
        bankView: {
          renderable: true,
          recalculated: false,
          seven_kpis: kpiSlots,
          twelve_month_schedule: schedule,
        },
      });
    }
    if (url.endsWith('/investment/cases/case-frozen-1') && init?.method !== 'POST') {
      return json(caseResponse);
    }
    throw new Error(`Unexpected request: ${init?.method ?? 'GET'} ${url}`);
  });
}

function installAllEquityCaseResponses(): void {
  const allEquitySlots = {
    ...kpiSlots,
    dscr: { status: 'not_applicable', value: 'n/a (kein Fremdkapital)' },
  };
  mocks.fetch.mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith('/investment/entitlement')) return json({ enabled: true });
    if (url.endsWith('/investment/cases/case-frozen-1/sensitivity')) {
      return json({
        interestSensitivity: [],
        repaymentSensitivity: [],
        repaymentAxisMeaning: 'structure_not_stress',
      });
    }
    if (url.endsWith('/investment/cases/case-frozen-1/bank-view')) {
      return json({
        bankView: {
          renderable: true,
          recalculated: false,
          header: {},
          investment: {
            purchase_price_cents: 42_000_000,
            total_investment_cents: 45_360_000,
          },
          financing_ltv: { loan_cents: 0 },
          seven_kpis: allEquitySlots,
          twelve_month_schedule: [],
        },
      });
    }
    if (url.endsWith('/investment/cases/case-frozen-1')) {
      return json({
        ...caseResponse,
        calculatedValues: { schedule: [] },
        kpiSlots: allEquitySlots,
      });
    }
    throw new Error(`Unexpected request: GET ${url}`);
  });
}

async function settle(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 30));
  });
}

function setControl(name: string, value: string): void {
  const element = document.querySelector<HTMLInputElement | HTMLSelectElement>(`[name="${name}"]`);
  expect(element, `user-facing control ${name} is missing`).toBeTruthy();
  if (!element) throw new Error(`user-facing control ${name} is missing`);
  const prototype =
    element instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  act(() => {
    Object.getOwnPropertyDescriptor(prototype, 'value')?.set?.call(element, value);
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

describe('M10-I4 owner investment cockpit', () => {
  let container: HTMLDivElement;
  let root: Root;
  let client: QueryClient;

  async function renderCockpit(): Promise<void> {
    const InvestmentCockpit = await loadCockpit();
    await act(async () => {
      root.render(
        <QueryClientProvider client={client}>
          <InvestmentCockpit accountId="account-1" />
        </QueryClientProvider>,
      );
    });
    await settle();
  }

  beforeEach(() => {
    mocks.role = 'OWNER';
    mocks.search = 'caseKey=case-frozen-1';
    mocks.replace.mockReset();
    mocks.fetch.mockReset();
    vi.stubGlobal('fetch', mocks.fetch);
    vi.stubEnv('NEXT_PUBLIC_API_URL', '/api/backend');
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  });

  afterEach(() => {
    act(() => root.unmount());
    client.clear();
    container.remove();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('M10-I4-F09 renders seven KPIs, both axes, twelve rows and exact PDF download', async () => {
    installEnabledCaseResponses();
    await renderCockpit();

    expect(
      container.querySelectorAll('section[aria-labelledby="investment-kpis"] [data-kpi-key]'),
    ).toHaveLength(7);
    expect(container.querySelectorAll('[data-sensitivity-axis="interest"] tbody tr')).toHaveLength(
      5,
    );
    expect(container.querySelectorAll('[data-sensitivity-axis="repayment"] tbody tr')).toHaveLength(
      4,
    );
    expect(
      container.querySelectorAll('table[aria-label="Annuitätenplan Jahr 1"] tbody tr'),
    ).toHaveLength(12);
    expect(container.textContent).toContain('Kaufpreisfaktor');
    expect(container.textContent).toContain('Bruttomietrendite');
    expect(container.textContent).toContain('Nettomietrendite');
    expect(container.textContent).toContain('DSCR');
    expect(container.textContent).toContain('Eigenkapitalrendite');
    expect(container.textContent).toContain('Cashflow');
    expect(container.textContent).toContain('Break-Even-Miete');
    const link = Array.from(container.querySelectorAll('a')).find(
      (candidate) => candidate.textContent?.trim() === 'Bank-PDF herunterladen',
    );
    expect(link?.getAttribute('href')).toBe(
      '/api/backend/a/account-1/investment/cases/case-frozen-1/bank-pdf',
    );

    const simulate = Array.from(container.querySelectorAll('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Finanzierung simulieren',
    );
    act(() => simulate?.click());
    const interestSlider = container.querySelector<HTMLInputElement>(
      'input[aria-label="Sollzins-Szenario"]',
    );
    expect(interestSlider).toBeTruthy();
    act(() => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set?.call(
        interestSlider,
        '4',
      );
      interestSlider?.dispatchEvent(new Event('input', { bubbles: true }));
      interestSlider?.dispatchEvent(new Event('change', { bubbles: true }));
    });
    expect(container.querySelector('output')?.textContent).toBe('4,90 %');
  });

  it('M10-I4-F10 uses colours only for liquidity and prints the required guardrail', async () => {
    installEnabledCaseResponses();
    await renderCockpit();

    const coloured = Array.from(container.querySelectorAll<HTMLElement>('[data-liquidity-color]'));
    expect(coloured.length).toBeGreaterThan(0);
    expect(new Set(coloured.map((node) => node.dataset.liquidityColor))).toEqual(
      new Set(['red', 'amber', 'green']),
    );
    const visibleToneClass = {
      green: /(?:border-green|bg-mint|text-green|text-forest)/,
      amber: /(?:border-warning|bg-warning-tint|text-warning)/,
      red: /(?:border-danger|bg-danger-tint|text-danger)/,
    } as const;
    for (const node of coloured) {
      const key = node.dataset.kpiKey;
      const tone = node.dataset.liquidityColor as keyof typeof visibleToneClass;
      expect(['dscr', 'cashflow']).toContain(key);
      expect(node.className).toMatch(visibleToneClass[tone]);
      expect(node.dataset.taxBasis).toBe(key === 'cashflow' ? 'after' : 'before');
    }
    for (const node of container.querySelectorAll<HTMLElement>(
      '[data-kpi-key="factor"], [data-kpi-key="gross_yield"], [data-kpi-key="net_yield"], ' +
        '[data-kpi-key="equity_return"], [data-kpi-key="break_even"]',
    )) {
      expect(node.hasAttribute('data-liquidity-color')).toBe(false);
      expect(node.className).not.toMatch(
        /(?:border-green|bg-mint|text-green|text-forest|border-warning|bg-warning-tint|text-warning|border-danger|bg-danger-tint|text-danger)/,
      );
    }
    expect(container.textContent).toContain(
      'Liquiditätsindikator unter Ihren Annahmen – keine Risikobewertung und keine Bankzusage.',
    );
    expect(container.textContent).toContain('Struktur-Trade-off');
    expect(container.textContent).toContain('Restschuld');
    for (const forbidden of [
      'Gesamtscore',
      'Ranking',
      'Sieger',
      'Kaufempfehlung',
      'Anlageempfehlung',
      'Zielrendite',
    ] as const) {
      expect(container.textContent).not.toContain(forbidden);
    }
  });

  it('M10-I4-F10 renders partial values as em dash with honest copy', async () => {
    installEnabledCaseResponses();
    const partial = {
      ...caseResponse,
      // Real no-financing snapshots have no calculated schedule key.
      calculatedValues: {},
      kpiSlots: {
        factor: kpiSlots.factor,
        gross_yield: kpiSlots.gross_yield,
        net_yield: { status: 'unavailable', value: '—' },
        dscr: { status: 'unavailable', value: '—' },
        equity_return: { status: 'unavailable', value: '—' },
        cashflow: { status: 'unavailable', value: '—' },
        break_even: { status: 'unavailable', value: '—' },
      },
    };
    mocks.fetch.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/investment/entitlement')) return json({ enabled: true });
      if (url.endsWith('/sensitivity')) {
        return json({
          interestSensitivity: [],
          repaymentSensitivity: [],
          repaymentAxisMeaning: 'structure_not_stress',
        });
      }
      if (url.endsWith('/bank-view')) return json({ bankView: { renderable: true } });
      return json(partial);
    });
    await renderCockpit();
    expect(container.textContent).toContain('Daten unvollständig');
    expect((container.textContent?.match(/—/g) ?? []).length).toBeGreaterThanOrEqual(5);
  });

  it('M10-I4-F10 describes all-equity DSCR as not applicable without incomplete copy', async () => {
    installAllEquityCaseResponses();
    await renderCockpit();

    const dscr = container.querySelector<HTMLElement>('[data-kpi-key="dscr"]');
    expect(dscr?.textContent).toContain('n/a (kein Fremdkapital)');
    expect(dscr?.textContent).toContain('Kein Fremdkapital');
    expect(dscr?.textContent).not.toContain('Daten unvollständig');
  });

  it('M10-I4-F10 describes empty all-equity sensitivity as no debt', async () => {
    installAllEquityCaseResponses();
    await renderCockpit();

    const section = container.querySelector<HTMLElement>(
      'section[aria-labelledby="investment-sensitivity"]',
    );
    act(() => section?.querySelector('button')?.click());
    expect(section?.textContent).toContain('Kein Fremdkapital');
    expect(section?.textContent).not.toContain('Daten unvollständig');
  });

  it('M10-I4-F10 describes an empty all-equity plan as no debt', async () => {
    installAllEquityCaseResponses();
    await renderCockpit();

    const section = container.querySelector<HTMLElement>(
      'section[aria-labelledby="investment-schedule"]',
    );
    act(() => section?.querySelector('button')?.click());
    expect(section?.textContent).toContain('Kein Fremdkapital');
    expect(section?.textContent).not.toContain('Daten unvollständig');
  });

  it('M10-I4-F09 requires an explicit loan and normalizes that exact amount', async () => {
    mocks.search = '';
    mocks.fetch.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/investment/entitlement')) return json({ enabled: true });
      if (url.endsWith('/investment/cases') && init?.method === 'POST') {
        return json(caseResponse, 201);
      }
      throw new Error(`Unexpected request: ${init?.method ?? 'GET'} ${url}`);
    });
    await renderCockpit();
    const openWizard = Array.from(container.querySelectorAll('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Neues Prüfobjekt',
    );
    act(() => openWizard?.click());

    setControl('purchasePriceEuros', '420000.00');
    setControl('acquisitionCostsEuros', '33600.00');
    setControl('equityEuros', '113600.00');
    await settle();
    const loan = container.querySelector<HTMLInputElement>('[name="loanEuros"]');
    expect(loan?.value).toBe('');

    setControl('loanEuros', '123456.78');
    setControl('monthlyActualRentEuros', '2650.00');
    const reviewStep = container.querySelector<HTMLButtonElement>(
      'button[aria-label="Schritt 6: Angaben prüfen"]',
    );
    act(() => reviewStep?.click());
    const create = Array.from(container.querySelectorAll('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Prüfobjekt berechnen',
    );
    act(() => create?.click());
    await settle();

    const post = mocks.fetch.mock.calls.find(([, init]) => init?.method === 'POST');
    expect(post).toBeDefined();
    const body = JSON.parse(String(post?.[1]?.body)) as {
      facts: Record<string, unknown>;
    };
    expect(body.facts.purchasePriceCents).toBe(42_000_000);
    expect(body.facts.acquisitionCostsCents).toBe(3_360_000);
    expect(body.facts.equityCents).toBe(11_360_000);
    expect(body.facts.loanCents).toBe(12_345_678);
  });

  it('M10-F lets wizard footer actions stack and wrap without horizontal overflow', async () => {
    mocks.search = '';
    mocks.fetch.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/investment/entitlement')) return json({ enabled: true });
      throw new Error(`Unexpected request: GET ${url}`);
    });
    await renderCockpit();
    const openWizard = Array.from(container.querySelectorAll('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Neues Prüfobjekt',
    );
    act(() => openWizard?.click());
    const reviewStep = container.querySelector<HTMLButtonElement>(
      'button[aria-label="Schritt 6: Angaben prüfen"]',
    );
    act(() => reviewStep?.click());

    const back = Array.from(container.querySelectorAll('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Zurück',
    );
    const submit = Array.from(container.querySelectorAll('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Prüfobjekt berechnen',
    );
    const footer = submit?.parentElement;

    expect(back, 'the wizard footer must expose the back action').toBeDefined();
    expect(submit, 'the wizard footer must expose the submit action').toBeDefined();
    expect(back?.parentElement).toBe(footer);
    expect(footer?.className).toMatch(/(?:\bflex-wrap\b|\bflex-col\b|\bgrid\b)/);
    for (const action of [back, submit]) {
      expect(action?.className).toMatch(/(?:\bw-full\b|\bmax-w-full\b|\bmin-w-0\b)/);
      expect(action?.className).toMatch(/(?:\bwhitespace-normal\b|\bbreak-words\b)/);
    }
  });

  it('M10-I4-F09 creates without a layout id and hands the returned case through the URL', async () => {
    mocks.search = '';
    mocks.fetch.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/investment/entitlement')) return json({ enabled: true });
      if (url.endsWith('/investment/cases') && init?.method === 'POST') {
        return json(caseResponse, 201);
      }
      throw new Error(`Unexpected request: ${init?.method ?? 'GET'} ${url}`);
    });
    await renderCockpit();
    expect(container.textContent).toContain('Investment-Dashboard');
    expect(container.querySelector('form')).toBeNull();
    const openWizard = Array.from(container.querySelectorAll('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Neues Prüfobjekt',
    );
    expect(openWizard).toBeDefined();
    act(() => openWizard?.click());
    const form = container.querySelector('form');
    expect(form).toBeTruthy();
    expect(container.querySelectorAll('button[aria-label^="Schritt "]')).toHaveLength(6);
    expect(form?.textContent).not.toMatch(/\bCent\b|Basispunkt/);
    for (const label of [
      'Kaufpreis (€)',
      'Erwerbsnebenkosten (€)',
      'Ist-Kaltmiete monatlich (€)',
      'Leerstand (%)',
      'Verwaltung pro Jahr (€)',
      'Instandhaltung pro Jahr (€)',
      'Rücklage pro Jahr (€)',
      'Mietausfallwagnis pro Jahr (€)',
      'Eigenkapital (€)',
      'Darlehen (€)',
      'Sollzins (%)',
      'Anfängliche Tilgung (%)',
      'Grenzsteuersatz (%)',
      'Gebäudeanteil (%)',
      'AfA-Satz (%)',
      'Finanzierungsquelle',
      'Objektadresse',
      'Objektart',
      'Baujahr',
      'Wohnfläche (m²)',
      'Einheiten',
      'Erstellt von',
      'Exportdatum',
    ]) {
      expect(form?.textContent).toContain(label);
    }
    for (const [name, value] of Object.entries({
      purchasePriceEuros: '420000.00',
      acquisitionCostsEuros: '33600.00',
      monthlyActualRentEuros: '2650.00',
      vacancyPercent: '0.00',
      administrationEuros: '3600.00',
      maintenanceEuros: '3000.00',
      reserveEuros: '0.00',
      vacancyRiskEuros: '636.00',
      equityEuros: '113600.00',
      loanEuros: '340000.00',
      interestPercent: '3.90',
      initialRepaymentPercent: '2.00',
      marginalTaxPercent: '42.00',
      buildingSharePercent: '75.00',
      afaRatePercent: '2.00',
      financingProvenance: 'annahme',
      bankAddress: 'Musterstraße 1, 10115 Berlin',
      bankPropertyType: 'Mehrfamilienhaus',
      bankYearBuilt: '1995',
      bankAreaSqm: '194.00',
      bankUnitCount: '4',
      bankCreator: 'Eigentümer',
      bankExportDate: '2026-09-16',
    })) {
      setControl(name, value);
    }
    const reviewStep = container.querySelector<HTMLButtonElement>(
      'button[aria-label="Schritt 6: Angaben prüfen"]',
    );
    expect(reviewStep).toBeTruthy();
    act(() => reviewStep?.click());
    const create = Array.from(container.querySelectorAll('button')).find(
      (candidate) => candidate.textContent?.trim() === 'Prüfobjekt berechnen',
    );
    expect(create).toBeDefined();
    act(() => create?.click());
    await settle();

    const post = mocks.fetch.mock.calls.find(([, init]) => init?.method === 'POST');
    expect(post).toBeDefined();
    const body = JSON.parse(String(post?.[1]?.body)) as Record<string, unknown>;
    expect(body).toEqual({
      facts: {
        purchasePriceCents: 42_000_000,
        acquisitionCostsCents: 3_360_000,
        monthlyActualRentCents: 265_000,
        vacancyBp: 0,
        administrationCents: 360_000,
        maintenanceCents: 300_000,
        reserveCents: 0,
        vacancyRiskCents: 63_600,
        equityCents: 11_360_000,
        loanCents: 34_000_000,
        interestBp: 390,
        initialRepaymentBp: 200,
        marginalTaxBp: 4_200,
        buildingShareBp: 7_500,
        afaRateBp: 200,
        analysisPeriodMonths: 12,
        financingProvenance: 'annahme',
        bankHeader: {
          address: 'Musterstraße 1, 10115 Berlin',
          propertyType: 'Mehrfamilienhaus',
          yearBuilt: 1995,
          areaSqmX100: 19_400,
          unitCount: 4,
          creator: 'Eigentümer',
          exportDate: '2026-09-16',
        },
      },
    });
    expect(body).not.toHaveProperty('layoutVersionId');
    expect(mocks.replace).toHaveBeenCalledWith('/a/account-1/investment?caseKey=case-frozen-1');
  });

  it.each(['EMPLOYEE', 'TAX_ADVISOR'] as const)(
    'M10-I4-F10 exposes no cockpit action to %s',
    async (role) => {
      mocks.role = role;
      await renderCockpit();
      expect(container.textContent).toContain('Nur für Inhaber:innen verfügbar.');
      expect(mocks.fetch).not.toHaveBeenCalled();
      expect(container.querySelector('a[href*="bank-pdf"]')).toBeNull();
      expect(container.querySelector('button[type="submit"]')).toBeNull();
    },
  );

  it('M10-I4-F10 hides case data and actions when entitlement is disabled', async () => {
    mocks.fetch.mockResolvedValue(json({ enabled: false }));
    await renderCockpit();
    expect(container.textContent).toContain(
      'Investitionsmodul ist für dieses Konto nicht aktiviert.',
    );
    expect(mocks.fetch).toHaveBeenCalledTimes(1);
    expect(container.querySelector('a[href*="bank-pdf"]')).toBeNull();
    expect(container.querySelector('button[type="submit"]')).toBeNull();
  });
});
