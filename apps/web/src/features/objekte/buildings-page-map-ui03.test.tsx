// @vitest-environment happy-dom

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { BuildingSummary } from '@/lib/contracts';

import { BuildingsPage } from './buildings-page';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const mocks = vi.hoisted(() => ({ useBuildings: vi.fn(), useMe: vi.fn() }));

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>
      {children}
    </a>
  ),
}));
vi.mock('./queries', () => ({
  useBuildings: mocks.useBuildings,
  useCreateBuilding: () => ({
    isPending: false,
    isError: false,
    isSuccess: false,
    mutate: vi.fn(),
  }),
}));
vi.mock('../portal/queries', () => ({ useMe: mocks.useMe }));
vi.mock('@/lib/form-draft', () => ({
  useFormDraft: () => ({ draftRestored: false, clearDraft: vi.fn() }),
}));

const BUILDING: BuildingSummary = {
  id: 'building-1',
  name: 'Musterstraße 12',
  street: 'Musterstraße 12',
  postalCode: '60311',
  city: 'Frankfurt am Main',
  unitCount: 3,
  buildingType: 'WOHNHAUS',
  latitude: 50.1109,
  longitude: 8.6821,
};
const BUILDINGS: BuildingSummary[] = [BUILDING];

async function loadMapModule(): Promise<{
  BuildingMap: React.ComponentType<{ accountId: string; buildings: BuildingSummary[] }>;
  buildingTypeLabel: (value: string) => string;
  buildMapEntries: (
    accountId: string,
    buildings: BuildingSummary[],
  ) => Array<{
    id: string;
    href: string;
    address: string;
    typeLabel: string;
    latitude: number;
    longitude: number;
  }>;
}> {
  const modulePath = './building-map';
  return import(/* @vite-ignore */ modulePath) as ReturnType<typeof loadMapModule>;
}

function button(name: string): HTMLButtonElement {
  const match = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => candidate.textContent?.trim() === name,
  );
  expect(match, `button "${name}" is missing`).toBeDefined();
  return match as HTMLButtonElement;
}

describe('UI-03 BuildingsPage', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
    mocks.useMe.mockReturnValue({
      data: { accounts: [{ id: 'account-1', role: 'OWNER', name: 'Konto', shape: 'SOLO' }] },
    });
    mocks.useBuildings.mockReturnValue({
      isPending: false,
      isError: false,
      data: { buildings: BUILDINGS },
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it('renders owner action, final German copy and no inline creation form', () => {
    act(() => root.render(<BuildingsPage accountId="account-1" />));

    const createLink = document.querySelector<HTMLAnchorElement>(
      'a[href="/a/account-1/objekte/neu"]',
    );
    expect(createLink).not.toBeNull();
    expect(createLink?.textContent ?? '').toContain('Objekt anlegen');
    expect(document.body.textContent).toContain(
      'Alle Objekte dieses Kontos. Ein Klick auf ein Objekt öffnet seine Einheiten.',
    );
    expect(document.querySelector('section[aria-label="Objekt anlegen"]')).toBeNull();
    expect(document.querySelector('label[for="building-street"]')).toBeNull();

    mocks.useMe.mockReturnValue({
      data: { accounts: [{ id: 'account-1', role: 'EMPLOYEE', name: 'Konto', shape: 'SOLO' }] },
    });
    act(() => root.render(<BuildingsPage accountId="account-1" />));
    expect(document.querySelector('a[href="/a/account-1/objekte/neu"]')).toBeNull();
  });

  it('toggles list and map with aria-pressed while preserving the loaded object', () => {
    act(() => root.render(<BuildingsPage accountId="account-1" />));
    expect(button('Liste').getAttribute('aria-pressed')).toBe('true');
    expect(button('Karte').getAttribute('aria-pressed')).toBe('false');
    expect(document.querySelector('a[href="/a/account-1/objekte/building-1"]')).not.toBeNull();

    act(() => button('Karte').click());
    expect(button('Liste').getAttribute('aria-pressed')).toBe('false');
    expect(button('Karte').getAttribute('aria-pressed')).toBe('true');
    const map = document.querySelector('[role="region"][aria-label="Objektkarte"]');
    expect(map).not.toBeNull();
    expect(map?.textContent).toContain('Musterstraße 12');
  });

  it('keeps map rendering behind shared loading and error gates', () => {
    mocks.useBuildings.mockReturnValue({ isPending: true, isError: false, data: undefined });
    act(() => root.render(<BuildingsPage accountId="account-1" />));
    expect(document.querySelector('[role="region"][aria-label="Objektkarte"]')).toBeNull();

    mocks.useBuildings.mockReturnValue({ isPending: false, isError: true, data: undefined });
    act(() => root.render(<BuildingsPage accountId="account-1" />));
    expect(document.body.textContent).toContain('Objekte konnten nicht geladen werden.');
    expect(document.querySelector('[role="region"][aria-label="Objektkarte"]')).toBeNull();
  });

  it('shows an honest map state when the loaded collection is empty', () => {
    mocks.useBuildings.mockReturnValue({
      isPending: false,
      isError: false,
      data: { buildings: [] },
    });
    act(() => root.render(<BuildingsPage accountId="account-1" />));
    act(() => button('Karte').click());
    expect(document.body.textContent).toContain(
      'Für diese Objekte liegen noch keine Koordinaten vor.',
    );
  });
});

describe('UI-03 BuildingMap seam', () => {
  it('provides readable labels for all four building types', async () => {
    const { buildingTypeLabel } = await loadMapModule();
    expect([
      buildingTypeLabel('WOHN_UND_GESCHAEFTSHAUS'),
      buildingTypeLabel('WOHNHAUS'),
      buildingTypeLabel('GEWERBEIMMOBILIE'),
      buildingTypeLabel('EINFAMILIENHAUS'),
    ]).toEqual(['Wohn- und Geschäftshaus', 'Wohnhaus', 'Gewerbeimmobilie', 'Einfamilienhaus']);
  });

  it('creates markers only from complete coordinate pairs', async () => {
    const { buildMapEntries } = await loadMapModule();
    const entries = buildMapEntries('account-1', [
      ...BUILDINGS,
      { ...BUILDING, id: 'missing-lat', latitude: null },
      { ...BUILDING, id: 'missing-lon', longitude: null },
    ]);

    expect(entries).toEqual([
      expect.objectContaining({
        id: 'building-1',
        href: '/a/account-1/objekte/building-1',
        address: 'Musterstraße 12, 60311 Frankfurt am Main',
        typeLabel: 'Wohnhaus',
        latitude: 50.1109,
        longitude: 8.6821,
      }),
    ]);
  });

  it('renders the no-coordinate state without loading tiles', async () => {
    const { BuildingMap } = await loadMapModule();
    const container = document.createElement('div');
    document.body.append(container);
    const root = createRoot(container);
    act(() =>
      root.render(
        <BuildingMap
          accountId="account-1"
          buildings={[{ ...BUILDING, latitude: null, longitude: null }]}
        />,
      ),
    );
    expect(document.body.textContent).toContain(
      'Für diese Objekte liegen noch keine Koordinaten vor.',
    );
    act(() => root.unmount());
    container.remove();
  });
});
