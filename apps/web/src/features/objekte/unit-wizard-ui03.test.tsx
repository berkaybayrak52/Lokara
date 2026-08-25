// @vitest-environment happy-dom

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { BuildingDetailPage } from './building-detail-page';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const mocks = vi.hoisted(() => ({
  useBuildingDetail: vi.fn(),
  mutate: vi.fn(),
  clearDraft: vi.fn(),
}));

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>
      {children}
    </a>
  ),
}));
vi.mock('@/lib/form-draft', () => ({
  useFormDraft: () => ({ draftRestored: false, clearDraft: mocks.clearDraft }),
}));
vi.mock('./queries', () => ({
  useBuildingDetail: mocks.useBuildingDetail,
  useCreateUnit: () => ({
    mutate: mocks.mutate,
    isPending: false,
    isError: false,
    isSuccess: false,
  }),
}));

async function loadWizard(): Promise<
  React.ComponentType<{ accountId: string; buildingId: string; buildingName: string }>
> {
  const modulePath = './unit-wizard';
  const module = (await import(/* @vite-ignore */ modulePath)) as {
    UnitWizard: React.ComponentType<{
      accountId: string;
      buildingId: string;
      buildingName: string;
    }>;
  };
  return module.UnitWizard;
}

function button(name: string): HTMLButtonElement {
  const match = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => candidate.textContent?.trim() === name,
  );
  expect(match, `button "${name}" is missing`).toBeDefined();
  return match as HTMLButtonElement;
}

function input(label: string): HTMLInputElement {
  const match = Array.from(document.querySelectorAll<HTMLLabelElement>('label')).find(
    (candidate) => candidate.textContent?.trim() === label,
  );
  const control = match?.htmlFor ? document.getElementById(match.htmlFor) : null;
  expect(control, `input "${label}" is missing`).toBeInstanceOf(HTMLInputElement);
  return control as HTMLInputElement;
}

function setValue(control: HTMLInputElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
  setter?.call(control, value);
  control.dispatchEvent(new Event('input', { bubbles: true }));
  control.dispatchEvent(new Event('change', { bubbles: true }));
}

describe('UI-03 BuildingDetailPage and UnitWizard', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
    mocks.useBuildingDetail.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        id: 'building-1',
        name: 'Musterstraße 12',
        street: 'Musterstraße 12',
        postalCode: '60311',
        city: 'Frankfurt am Main',
        units: [],
      },
    });
    mocks.mutate.mockImplementation(
      (
        _payload: unknown,
        options: { onSuccess?: (created: { id: string; label: string }) => void },
      ) => options.onSuccess?.({ id: 'unit-new', label: 'Wohnung 4 (DG)' }),
    );
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it('links to the exact unit wizard route and removes the inline form', () => {
    act(() => root.render(<BuildingDetailPage accountId="account-1" buildingId="building-1" />));
    const link = document.querySelector<HTMLAnchorElement>(
      'a[href="/a/account-1/objekte/building-1/einheit/neu"]',
    );
    expect(link).not.toBeNull();
    expect(link?.textContent ?? '').toContain('Einheit anlegen');
    expect(document.querySelector('section[aria-label="Einheit anlegen"]')).toBeNull();
    expect(document.querySelector('label[for="unit-area"]')).toBeNull();
  });

  it('submits one unit and shows exactly the three named success actions', async () => {
    const UnitWizard = await loadWizard();
    act(() =>
      root.render(
        <UnitWizard accountId="account-1" buildingId="building-1" buildingName="Musterstraße 12" />,
      ),
    );
    expect(document.body.textContent).toContain('Einheit anlegen — Musterstraße 12');
    expect(document.body.textContent).toContain('Fotos (optional)');
    expect(document.body.textContent).toContain('Foto-Upload kommt bald');
    expect(document.querySelector('input[type="file"]')).toBeNull();

    setValue(input('Bezeichnung'), 'Wohnung 4 (DG)');
    setValue(input('Wohnfläche in m²'), '64,50');
    await act(async () => {
      button('Einheit anlegen').click();
      await Promise.resolve();
    });

    expect(mocks.mutate).toHaveBeenCalledWith(
      { label: 'Wohnung 4 (DG)', areaSqmX100: 6450 },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    const success = document.querySelector('[role="status"][aria-label="Einheit angelegt"]');
    expect(success?.textContent).toContain('Wohnung 4 (DG)');
    expect(
      Array.from(success?.querySelectorAll('a, button') ?? [], (action) =>
        action.textContent?.trim(),
      ),
    ).toEqual(['Noch eine Einheit anlegen', 'Zur Einheit', 'Fertig — zum Objekt']);
    expect(success?.querySelector('a[href="/a/account-1/einheiten/unit-new"]')).not.toBeNull();
    expect(success?.querySelector('a[href="/a/account-1/objekte/building-1"]')).not.toBeNull();
  });

  it('starts a clean form after Noch eine Einheit anlegen', async () => {
    const UnitWizard = await loadWizard();
    act(() =>
      root.render(
        <UnitWizard accountId="account-1" buildingId="building-1" buildingName="Musterstraße 12" />,
      ),
    );
    setValue(input('Bezeichnung'), 'Wohnung 4 (DG)');
    setValue(input('Wohnfläche in m²'), '64,50');
    await act(async () => {
      button('Einheit anlegen').click();
      await Promise.resolve();
    });
    act(() => button('Noch eine Einheit anlegen').click());

    expect(input('Bezeichnung').value).toBe('');
    expect(input('Wohnfläche in m²').value).toBe('');
    expect(mocks.clearDraft).toHaveBeenCalled();
  });
});
