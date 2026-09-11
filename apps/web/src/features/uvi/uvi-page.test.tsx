// @vitest-environment happy-dom

import React, { act } from 'react';
import { existsSync } from 'node:fs';
import { URL as NodeURL } from 'node:url';
import { createRoot, type Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { MeterWorkspaceResponse } from '@/lib/contracts';
import type * as DemoPreview from '@/lib/demo-preview';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const mocks = vi.hoisted(() => ({
  role: 'OWNER' as 'OWNER' | 'EMPLOYEE' | 'TAX_ADVISOR',
  preview: false,
  fetch: vi.fn<typeof fetch>(),
}));

const workspace: MeterWorkspaceResponse = {
  asOf: '2026-09-11T12:34:18.314263Z',
  periodLabel: '2026',
  permissions: { canWrite: true },
  expiredMeterIds: [],
  buildings: ['building-1', 'building-2'].map((id) => ({
    id,
    name: id === 'building-1' ? 'Musterstraße 12' : 'Waldstraße 8',
    address: '10115 Berlin',
    activeMeterCount: 0,
    expiredCount: 0,
    missingDataCount: 0,
    buildingMeters: [],
    units: ['unit-1', 'unit-2'].map((suffix) => ({
      id: `${id}-${suffix}`,
      label: suffix === 'unit-1' ? 'Erdgeschoss' : 'Obergeschoss',
      activeMeterCount: 0,
      warningCount: 0,
      meters: [],
      tenancies: ['tenancy-1', 'tenancy-2'].map((tenancy) => ({
        id: `${id}-${suffix}-${tenancy}`,
        label: tenancy === 'tenancy-1' ? 'Mietverhältnis Müller' : 'Mietverhältnis Kaya',
        validFrom: tenancy === 'tenancy-1' ? '2025-01-01' : '2026-01-01',
        validTo: tenancy === 'tenancy-1' ? '2025-12-31' : null,
      })),
    })),
  })),
};

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>{children}</a>
  ),
}));
vi.mock('next/navigation', () => ({
  usePathname: () => '/a/account-1/uvi',
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock('@/features/portal/queries', () => ({
  useMe: () => ({
    isPending: false,
    isLoading: false,
    isError: false,
    data: { accounts: [{ id: 'account-1', name: 'Eigentümer', role: mocks.role }] },
  }),
}));
vi.mock('@/features/zaehler/queries', () => ({
  useMeterWorkspace: () => ({ isPending: false, isLoading: false, isError: false, data: workspace }),
}));
vi.mock('@/lib/demo-preview', async (importOriginal) => ({
  ...(await importOriginal<typeof DemoPreview>()),
  isDemoPreview: () => mocks.preview,
}));

const result = {
  runId: 'run-1',
  documentUrl: '/a/account-1/buildings/building-1/uvi-runs/run-1/document',
  productionBlocked: true,
  unresolvedConflicts: ['UVI-REGISTER-OPEN', 'MONTHLY-CONTENT-OPEN'],
};

async function loadPage(): Promise<React.ComponentType<{ accountId: string }>> {
  // Deliberate behavior-contract failure before the UI exists, not an import-resolution error.
  expect(
    existsSync(new NodeURL('./uvi-page.tsx', import.meta.url)),
    'Owner UVI generation/download page is not implemented',
  ).toBe(true);
  const modulePath = './uvi-page';
  const module = (await import(/* @vite-ignore */ modulePath)) as {
    UviPage: React.ComponentType<{ accountId: string }>;
  };
  return module.UviPage;
}

function control(label: string): HTMLSelectElement | HTMLInputElement {
  const match = Array.from(document.querySelectorAll('label')).find(
    (candidate) => candidate.textContent?.trim() === label,
  );
  const element = match?.htmlFor
    ? document.getElementById(match.htmlFor)
    : match?.querySelector('input, select');
  expect(element, `labelled control ${label} is missing`).toBeTruthy();
  return element as HTMLSelectElement | HTMLInputElement;
}

function select(label: string, value: string): void {
  const element = control(label);
  const prototype = element instanceof HTMLSelectElement
    ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  act(() => {
    Object.getOwnPropertyDescriptor(prototype, 'value')?.set?.call(element, value);
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

function generateButton(): HTMLButtonElement {
  const button = Array.from(document.querySelectorAll('button')).find(
    (candidate) => /UVI erstellen|UVI wird|Wird erstellt/.test(candidate.textContent ?? ''),
  );
  expect(button, 'explicit UVI generation action is missing').toBeDefined();
  return button as HTMLButtonElement;
}

function pdfLink(): HTMLAnchorElement | undefined {
  return Array.from(document.querySelectorAll('a')).find(
    (candidate) => candidate.textContent?.trim() === 'PDF herunterladen',
  );
}

async function settle(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 20));
  });
}

describe('owner UVI generation and archived PDF access', () => {
  let container: HTMLDivElement;
  let root: Root;
  let client: QueryClient;

  async function renderPage(): Promise<void> {
    const UviPage = await loadPage();
    await act(async () => {
      root.render(
        <QueryClientProvider client={client}><UviPage accountId="account-1" /></QueryClientProvider>,
      );
    });
  }

  function fillSelection(): void {
    select('Objekt', 'building-1');
    select('Einheit', 'building-1-unit-1');
    select('Mietverhältnis', 'building-1-unit-1-tenancy-1');
    select('Monat', '2025-04');
  }

  async function generate(): Promise<void> {
    act(() => generateButton().click());
    await settle();
  }

  beforeEach(() => {
    mocks.role = 'OWNER';
    mocks.preview = false;
    mocks.fetch.mockReset();
    mocks.fetch.mockResolvedValue(new Response(JSON.stringify(result), { status: 201 }));
    vi.stubGlobal('fetch', mocks.fetch);
    vi.stubEnv('NEXT_PUBLIC_API_URL', '/api/backend');
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
    client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  });

  afterEach(() => {
    act(() => root.unmount());
    client.clear();
    container.remove();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('waits for explicit submit and posts only tenancy and first-of-month to the selected object', async () => {
    await renderPage();
    expect(document.querySelector('h1')?.textContent).toBe('Verbrauchsinformation (UVI)');
    fillSelection();
    expect(mocks.fetch).not.toHaveBeenCalled();
    await generate();

    expect(mocks.fetch).toHaveBeenCalledTimes(1);
    const request = mocks.fetch.mock.calls[0];
    expect(request).toBeDefined();
    if (!request) throw new Error('UVI request was not sent');
    const [url, init] = request;
    expect(url).toBe('/api/backend/a/account-1/buildings/building-1/uvi-runs');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({
      tenancyId: 'building-1-unit-1-tenancy-1', targetMonth: '2025-04-01',
    });
  });

  it('defaults to the previous month using the live workspace timestamp', async () => {
    await renderPage();
    expect(control('Monat').value).toBe('2026-08');
    expect(mocks.fetch).not.toHaveBeenCalled();
  });

  it('does not attach an in-flight result to a newly selected month', async () => {
    let resolveResponse!: (value: Response) => void;
    mocks.fetch.mockReturnValue(new Promise<Response>((resolve) => { resolveResponse = resolve; }));
    await renderPage();
    fillSelection();
    act(() => generateButton().click());
    await settle();
    select('Monat', '2025-05');
    resolveResponse(new Response(JSON.stringify(result), { status: 201 }));
    await settle();
    expect(pdfLink()).toBeUndefined();
    expect(generateButton().disabled).toBe(false);
  });

  it('refuses a document URL belonging to a different account', async () => {
    mocks.fetch.mockResolvedValue(new Response(JSON.stringify({
      ...result, documentUrl: '/a/account-2/buildings/building-1/uvi-runs/run-1/document',
    }), { status: 201 }));
    await renderPage();
    fillSelection();
    await generate();
    expect(pdfLink()).toBeUndefined();
    expect(document.querySelector('[role="alert"]')?.textContent).toContain('UVI konnte nicht geöffnet werden.');
  });

  it.each([200, 201])('shows archived PDF with production conflicts after HTTP %s', async (status) => {
    mocks.fetch.mockResolvedValue(new Response(JSON.stringify(result), { status }));
    await renderPage();
    fillSelection();
    await generate();

    expect(pdfLink()?.getAttribute('href')).toBe(`/api/backend${result.documentUrl}`);
    expect(container.textContent).toContain('Nicht für den produktiven Versand freigegeben');
    expect(container.textContent).toContain('Es wird keine E-Mail versendet.');
    for (const conflict of result.unresolvedConflicts) expect(container.textContent).toContain(conflict);
    expect(document.querySelector('a button, button a')).toBeNull();
  });

  it('keeps a missing-data 422 visible without fabricating a PDF success', async () => {
    mocks.fetch.mockResolvedValue(new Response(JSON.stringify({
      detail: 'Monatliche Zählerdaten fehlen für den gewählten Monat.',
    }), { status: 422 }));
    await renderPage();
    fillSelection();
    await generate();

    expect(document.querySelector('[role="alert"]')?.textContent).toContain('Monatliche Zählerdaten fehlen');
    expect(pdfLink()).toBeUndefined();
    expect(generateButton().disabled).toBe(false);
  });

  it('clears dependent selections and hides stale PDFs on object or unit changes', async () => {
    await renderPage();
    fillSelection();
    await generate();
    expect(pdfLink()).toBeDefined();
    select('Einheit', 'building-1-unit-2');
    expect(control('Mietverhältnis').value).toBe('');
    expect(pdfLink()).toBeUndefined();
    expect(generateButton().disabled).toBe(true);

    select('Objekt', 'building-2');
    expect(control('Einheit').value).toBe('');
    expect(control('Mietverhältnis').value).toBe('');
    expect(mocks.fetch).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['Monat', '2025-05'],
    ['Mietverhältnis', 'building-1-unit-1-tenancy-2'],
  ])('hides the prior PDF after changing %s', async (label, value) => {
    await renderPage();
    fillSelection();
    await generate();
    expect(pdfLink()).toBeDefined();
    select(label, value);
    expect(pdfLink()).toBeUndefined();
    expect(mocks.fetch).toHaveBeenCalledTimes(1);
  });

  it('blocks duplicate submission while the request is pending', async () => {
    let resolveResponse!: (value: Response) => void;
    mocks.fetch.mockReturnValue(new Promise<Response>((resolve) => { resolveResponse = resolve; }));
    await renderPage();
    fillSelection();
    act(() => generateButton().click());
    await settle();
    expect(generateButton().disabled).toBe(true);
    act(() => generateButton().click());
    expect(mocks.fetch).toHaveBeenCalledTimes(1);
    resolveResponse(new Response(JSON.stringify(result), { status: 201 }));
    await settle();
  });

  it('never generates or invents a PDF in preview and offers full live navigation', async () => {
    mocks.preview = true;
    await renderPage();
    expect(container.textContent).toContain('Vorschau');
    const live = container.querySelector('a[href="/a/account-1/uvi?preview=0"]');
    expect(live?.textContent).toContain('Live-Daten öffnen');
    for (const button of container.querySelectorAll('button')) act(() => button.click());
    expect(mocks.fetch).not.toHaveBeenCalled();
    expect(pdfLink()).toBeUndefined();
  });

  it.each(['EMPLOYEE', 'TAX_ADVISOR'] as const)('does not offer generation to %s', async (role) => {
    mocks.role = role;
    await renderPage();
    expect(Array.from(container.querySelectorAll('button')).some(
      (button) => /UVI erstellen/.test(button.textContent ?? ''),
    )).toBe(false);
    expect(mocks.fetch).not.toHaveBeenCalled();
    expect(pdfLink()).toBeUndefined();
  });
});
