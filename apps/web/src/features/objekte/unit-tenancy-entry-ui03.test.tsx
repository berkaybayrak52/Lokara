// @vitest-environment happy-dom

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { UnitDetailPage } from './unit-detail-page';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const mocks = vi.hoisted(() => ({
  useUnitDashboard: vi.fn(),
  useCreateRenterActivationCode: vi.fn(),
}));

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>
      {children}
    </a>
  ),
}));
vi.mock('@/lib/form-draft', () => ({
  useFormDraft: () => ({ draftRestored: false, clearDraft: vi.fn() }),
}));
vi.mock('next/navigation', () => ({ useSearchParams: () => new URLSearchParams() }));
vi.mock('./queries', () => ({
  useUnitDashboard: mocks.useUnitDashboard,
  useCreateRenterActivationCode: mocks.useCreateRenterActivationCode,
  useCreateUnitProfileVersion: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateTenancy: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
  }),
}));

function button(name: string): HTMLButtonElement {
  const match = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => candidate.textContent?.trim() === name,
  );
  expect(match, `button "${name}" is missing`).toBeDefined();
  return match as HTMLButtonElement;
}

function buttonWithAccessibleName(name: string): HTMLButtonElement {
  const match = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => (candidate.getAttribute('aria-label') ?? candidate.textContent?.trim()) === name,
  );
  expect(match, `button with accessible name "${name}" is missing`).toBeDefined();
  return match as HTMLButtonElement;
}

function activationButtons(): HTMLButtonElement[] {
  return Array.from(document.querySelectorAll<HTMLButtonElement>('button')).filter((candidate) =>
    (candidate.getAttribute('aria-label') ?? candidate.textContent?.trim())?.startsWith(
      'Aktivierungscode für ',
    ),
  );
}

function rentedDashboard(portalAvailable = true, hasCurrentTenancy = true) {
  return {
    asOf: '2026-09-12',
    id: 'unit-1',
    label: 'Wohnung 1 (EG links)',
    areaSqmX100: 6450,
    areaSqmDisplay: '64,50',
    buildingId: 'building-1',
    buildingName: 'Musterstraße 12',
    buildingAddress: 'Musterstraße 12, 60311 Frankfurt am Main',
    state: hasCurrentTenancy ? 'RENTED' : 'VACANT',
    stateLabel: hasCurrentTenancy ? 'Vermietet' : 'Leerstand',
    profile: {
      version: null,
      usageType: null,
      usageLabel: 'Nicht dokumentiert',
      roomsX100: null,
      roomsDisplay: null,
      amenities: [],
      amenityLabels: [],
      amenityNote: null,
      evidenceRef: null,
    },
    currentTenancy: hasCurrentTenancy
      ? {
          id: 'tenancy-1',
          parties: [
            { id: 'renter-1', name: 'Anna Beispiel', email: 'anna@example.test' },
            { id: 'renter-2', name: 'Berta Beispiel', email: null },
          ],
          validFrom: '2025-01-01',
          validTo: null,
          contractType: null,
          contractTypeLabel: 'Nicht dokumentiert',
          contractEvidenceRef: null,
          coldRentCents: 95000,
          coldRentEur: '950,00 €',
          coldRentPerSqmEur: '14,73',
          advancePaymentCents: 22000,
          advancePaymentEur: '220,00 €',
          totalMonthlyCents: 117000,
          totalMonthlyEur: '1.170,00 €',
          positions: [],
          lastRentChange: null,
        }
      : null,
    history: [],
    historyTotal: 0,
    historyHasMore: false,
    documents: [],
    modules: [
      { key: 'PAYMENTS', available: true, unavailableReason: null },
      {
        key: 'PORTAL',
        available: portalAvailable,
        unavailableReason: portalAvailable ? null : 'Mieterportal ist nicht verfügbar.',
      },
      { key: 'MESSAGES', available: false, unavailableReason: 'Nicht verfügbar.' },
      { key: 'DOCUMENTS', available: true, unavailableReason: null },
    ],
    primaryAction: null,
    permissions: {
      canEditProfile: true,
      canCreateTenancy: true,
      canRecordContractFacts: true,
    },
  };
}

describe('UI-03 tenancy entry on UnitDetailPage', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    localStorage.removeItem('lokara:preview');
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        asOf: '2026-08-28',
        id: 'unit-1',
        label: 'Wohnung 1 (EG links)',
        areaSqmX100: 6450,
        areaSqmDisplay: '64,50',
        buildingId: 'building-1',
        buildingName: 'Musterstraße 12',
        buildingAddress: 'Musterstraße 12, 60311 Frankfurt am Main',
        state: 'VACANT',
        stateLabel: 'Leerstand',
        profile: {
          version: null,
          usageType: null,
          usageLabel: 'Nicht dokumentiert',
          roomsX100: null,
          roomsDisplay: null,
          amenities: [],
          amenityLabels: [],
          amenityNote: null,
          evidenceRef: null,
        },
        currentTenancy: null,
        history: [],
        historyTotal: 0,
        historyHasMore: false,
        documents: [],
        modules: [],
        primaryAction: {
          key: 'CREATE_TENANCY',
          label: 'Jetzt Mietverhältnis erstellen',
          href: '#aktuelles-mietverhaeltnis',
        },
        permissions: {
          canEditProfile: false,
          canCreateTenancy: true,
          canRecordContractFacts: false,
        },
      },
    });
    mocks.useCreateRenterActivationCode.mockReturnValue({
      mutate: vi.fn(),
      data: undefined,
      variables: undefined,
      isPending: false,
      isError: false,
      error: null,
    });
  });

  afterEach(() => {
    localStorage.removeItem('lokara:preview');
    act(() => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it('starts with one primary tenancy action instead of the manual form', () => {
    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));
    expect(button('Jetzt Mietverhältnis erstellen')).toBeDefined();
    expect(document.querySelector('form')).toBeNull();
  });

  it('reveals two choices, the exact generator link and the corrected manual form', () => {
    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));
    act(() => button('Jetzt Mietverhältnis erstellen').click());

    expect(document.body.textContent).toContain('Mit Vertragsgenerator');
    expect(document.body.textContent).toContain('Vertragsdaten selbst einpflegen');
    expect(
      document.querySelector('a[href="/a/account-1/vertraege/neu?unitId=unit-1"]'),
    ).not.toBeNull();
    act(() => button('Vertragsdaten selbst einpflegen').click());

    const declarationLabel = Array.from(document.querySelectorAll('label')).find(
      (label) => label.textContent?.trim() === 'Grundlage der NK-Vorauszahlung',
    );
    const declaration = declarationLabel?.htmlFor
      ? document.getElementById(declarationLabel.htmlFor)
      : null;
    expect(declaration).toBeInstanceOf(HTMLInputElement);
    expect((declaration as HTMLInputElement).value).toBe('Mietvertrag');
  });

  it('offers one activation-code action per current renter and passes the selected renter id', () => {
    const mutate = vi.fn();
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: rentedDashboard(),
    });
    mocks.useCreateRenterActivationCode.mockReturnValue({
      mutate,
      data: undefined,
      variables: undefined,
      isPending: false,
      isError: false,
      error: null,
    });

    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));

    expect(document.body.textContent).toContain('Weitere Bereiche');
    const actions = activationButtons();
    expect(actions).toHaveLength(2);
    expect(buttonWithAccessibleName('Aktivierungscode für Anna Beispiel erstellen')).toBeDefined();
    const bertaAction = buttonWithAccessibleName('Aktivierungscode für Berta Beispiel erstellen');
    expect(mocks.useCreateRenterActivationCode).toHaveBeenCalledWith('account-1', 'tenancy-1');

    act(() => bertaAction.click());
    expect(mutate).toHaveBeenCalledWith('renter-2');
  });

  it('disambiguates duplicate renter names visibly and in each activation action', () => {
    const mutate = vi.fn();
    const duplicateNames = rentedDashboard();
    if (duplicateNames.currentTenancy) {
      duplicateNames.currentTenancy.parties = [
        { id: 'renter-1', name: 'Anna Beispiel', email: 'anna.one@example.test' },
        { id: 'renter-2', name: 'Anna Beispiel', email: 'anna.two@example.test' },
      ];
    }
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: duplicateNames,
    });
    mocks.useCreateRenterActivationCode.mockReturnValue({
      mutate,
      data: undefined,
      variables: undefined,
      isPending: false,
      isError: false,
      error: null,
    });

    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));

    expect(document.body.textContent).toContain('Vertragspartei 1');
    expect(document.body.textContent).toContain('Vertragspartei 2');
    const actions = activationButtons();
    expect(actions).toHaveLength(2);
    const accessibleNames = actions.map(
      (action) => action.getAttribute('aria-label') ?? action.textContent?.trim() ?? '',
    );
    expect(new Set(accessibleNames).size).toBe(2);
    expect(accessibleNames[0]).toContain('Vertragspartei 1');
    expect(accessibleNames[1]).toContain('Vertragspartei 2');

    act(() => actions[1]?.click());
    expect(mutate).toHaveBeenCalledWith('renter-2');
  });

  it('blocks overlapping issuance and exposes which renter request is pending', () => {
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: rentedDashboard(),
    });
    mocks.useCreateRenterActivationCode.mockReturnValue({
      mutate: vi.fn(),
      data: undefined,
      variables: 'renter-1',
      isPending: true,
      isError: false,
      error: null,
    });

    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));

    const actions = activationButtons();
    expect(actions).toHaveLength(2);
    expect(actions.every((action) => action.disabled)).toBe(true);
    const pendingAction = buttonWithAccessibleName(
      'Aktivierungscode für Anna Beispiel wird erstellt',
    );
    expect(pendingAction.getAttribute('aria-busy')).toBe('true');
  });

  it('shows the one-time code, renter and expiry together without client persistence', () => {
    const rawCode = 'account-locator.one-time-secret';
    localStorage.clear();
    localStorage.setItem('lokara:preview', '1');
    sessionStorage.clear();
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: rentedDashboard(),
    });
    mocks.useCreateRenterActivationCode.mockReturnValue({
      mutate: vi.fn(),
      data: {
        activationCodeId: 'activation-code-1',
        activationCode: rawCode,
        expiresAt: '2026-09-13T12:00:00Z',
      },
      variables: 'renter-1',
      isPending: false,
      isError: false,
      error: null,
    });

    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));

    const portalHeading = Array.from(document.querySelectorAll('p')).find(
      (node) => node.textContent?.trim() === 'Mieterportal',
    );
    const portalSection = portalHeading?.parentElement;
    const successResult = Array.from(
      portalSection?.querySelectorAll<HTMLElement>('[role="status"]') ?? [],
    ).find((node) => node.textContent?.includes(rawCode));
    expect(successResult, 'the raw code must be inside its success status').toBeDefined();
    expect(successResult?.textContent).toContain('Anna Beispiel');
    expect(successResult?.textContent).toContain('Vertragspartei 1');
    expect(successResult?.textContent).toContain(rawCode);
    expect(successResult?.textContent).toContain('13.09.2026');
    expect(successResult?.textContent).toContain('14:00');
    expect(successResult?.textContent).toContain('MESZ');
    const portalLink = Array.from(
      successResult?.querySelectorAll<HTMLAnchorElement>('a') ?? [],
    ).find((link) => link.textContent?.trim() === 'Mieterportal öffnen');
    expect(portalLink, 'the success status must link to the activated renter portal').toBeDefined();
    expect(portalLink?.getAttribute('href')).toBe('/renter/tenancy-1');
    expect(portalLink?.getAttribute('target')).toBeNull();
    expect(document.body.textContent?.split(rawCode)).toHaveLength(2);
    expect(localStorage.getItem('lokara:preview')).toBe('1');
    expect([...Array(localStorage.length)].map((_, index) => localStorage.key(index))).toEqual([
      'lokara:preview',
    ]);
    expect(
      [...Array(localStorage.length)].map((_, index) =>
        localStorage.getItem(localStorage.key(index)!),
      ),
    ).not.toContain(rawCode);
    expect([...Array(sessionStorage.length)].map((_, index) => sessionStorage.key(index))).toEqual(
      [],
    );
  });

  it('does not offer the synthetic renter-portal link after a live issuance', () => {
    const rawCode = 'account-locator.live-one-time-secret';
    localStorage.removeItem('lokara:preview');
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: rentedDashboard(),
    });
    mocks.useCreateRenterActivationCode.mockReturnValue({
      mutate: vi.fn(),
      data: {
        activationCodeId: 'activation-code-live',
        activationCode: rawCode,
        expiresAt: '2026-09-13T12:00:00Z',
      },
      variables: 'renter-1',
      isPending: false,
      isError: false,
      error: null,
    });

    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));

    const successResult = Array.from(
      document.querySelectorAll<HTMLElement>('[role="status"]'),
    ).find((node) => node.textContent?.includes(rawCode));
    expect(successResult).toBeDefined();
    expect(successResult?.textContent).toContain(rawCode);
    expect(
      Array.from(successResult?.querySelectorAll('a') ?? []).some(
        (link) => link.textContent?.trim() === 'Mieterportal öffnen',
      ),
    ).toBe(false);
    expect([...Array(localStorage.length)].map((_, index) => localStorage.key(index))).toEqual([]);
  });

  it('shows a German refusal and leaves the selected renter action retryable', () => {
    const mutate = vi.fn();
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: rentedDashboard(),
    });
    mocks.useCreateRenterActivationCode.mockReturnValue({
      mutate,
      data: undefined,
      variables: 'renter-1',
      isPending: false,
      isError: true,
      error: new Error('server refused'),
    });

    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));

    expect(document.body.textContent).toContain('Aktivierungscode konnte nicht erstellt werden.');
    const action = buttonWithAccessibleName('Aktivierungscode für Anna Beispiel erstellen');
    expect(action.disabled).toBe(false);
    act(() => action.click());
    expect(mutate).toHaveBeenCalledWith('renter-1');
  });

  it('explains an unavailable portal without an activation action', () => {
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: rentedDashboard(false),
    });
    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));
    expect(activationButtons()).toHaveLength(0);
    expect(document.body.textContent).toContain('Mieterportal ist nicht verfügbar.');
  });

  it('explains an available portal without a current tenancy', () => {
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: rentedDashboard(true, false),
    });
    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));
    expect(activationButtons()).toHaveLength(0);
    expect(document.body.textContent).toContain(
      'Für diese Einheit besteht kein aktuelles Mietverhältnis.',
    );
  });

  it('explains an available portal whose current tenancy has no party', () => {
    const noParties = rentedDashboard();
    if (noParties.currentTenancy) noParties.currentTenancy.parties = [];
    mocks.useUnitDashboard.mockReturnValue({
      isPending: false,
      isError: false,
      data: noParties,
    });
    act(() => root.render(<UnitDetailPage accountId="account-1" unitId="unit-1" />));
    expect(activationButtons()).toHaveLength(0);
    expect(document.body.textContent).toContain(
      'Für das aktuelle Mietverhältnis ist keine Vertragspartei hinterlegt.',
    );
  });
});
