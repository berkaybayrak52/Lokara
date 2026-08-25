// @vitest-environment happy-dom

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const mocks = vi.hoisted(() => ({ mutate: vi.fn(), push: vi.fn(), clearDraft: vi.fn() }));

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: mocks.push }) }));
vi.mock('@/lib/form-draft', () => ({
  useFormDraft: () => ({ draftRestored: false, clearDraft: mocks.clearDraft }),
}));
vi.mock('./queries', () => ({
  useCreateBuilding: () => ({
    mutate: mocks.mutate,
    isPending: false,
    isError: false,
    isSuccess: false,
  }),
}));

async function loadWizard(): Promise<React.ComponentType<{ accountId: string }>> {
  const modulePath = './building-wizard';
  const module = (await import(/* @vite-ignore */ modulePath)) as {
    BuildingWizard: React.ComponentType<{ accountId: string }>;
  };
  return module.BuildingWizard;
}

function button(name: string): HTMLButtonElement {
  const match = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => candidate.textContent?.trim() === name,
  );
  expect(match, `button "${name}" is missing`).toBeDefined();
  return match as HTMLButtonElement;
}

function radio(label: string): HTMLInputElement {
  const match = Array.from(document.querySelectorAll<HTMLLabelElement>('label')).find((candidate) =>
    candidate.textContent?.includes(label),
  );
  const control = match?.querySelector<HTMLInputElement>('input[type="radio"]');
  expect(control, `radio "${label}" is missing`).not.toBeNull();
  return control as HTMLInputElement;
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

describe('UI-03 BuildingWizard', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
    mocks.mutate.mockImplementation(
      (_payload: unknown, options: { onSuccess?: (created: { id: string }) => void }) =>
        options.onSuccess?.({ id: 'building-new' }),
    );
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it('renders four radio choices and requires predominant use for mixed-use buildings', async () => {
    const BuildingWizard = await loadWizard();
    act(() => root.render(<BuildingWizard accountId="account-1" />));

    expect(document.body.textContent).toContain('Schritt 1 von 2');
    expect(Array.from(document.querySelectorAll('input[type="radio"]'))).toHaveLength(4);
    for (const label of [
      'Wohn- und Geschäftshaus',
      'Wohnhaus',
      'Gewerbeimmobilie',
      'Einfamilienhaus',
    ]) {
      expect(document.body.textContent).toContain(label);
    }
    expect(button('Weiter').disabled).toBe(true);

    act(() => radio('Wohn- und Geschäftshaus').click());
    expect(document.body.textContent).toContain('Überwiegende Nutzung');
    expect(radio('Wohnen')).toBeDefined();
    expect(radio('Gewerbe')).toBeDefined();
    expect(button('Weiter').disabled).toBe(true);
  });

  it('submits mixed-commercial metadata, inactive photos and routes to the new object', async () => {
    const BuildingWizard = await loadWizard();
    act(() => root.render(<BuildingWizard accountId="account-1" />));
    act(() => radio('Wohn- und Geschäftshaus').click());
    act(() => radio('Gewerbe').click());
    act(() => button('Weiter').click());

    expect(document.body.textContent).toContain('Schritt 2 von 2');
    expect(
      Array.from(document.querySelectorAll<HTMLLabelElement>('form label'), (label) =>
        label.textContent?.trim(),
      ),
    ).toEqual(['Bezeichnung', 'Straße', 'Hausnummer', 'PLZ', 'Ort', 'Land']);
    expect(input('Land').value).toBe('Deutschland');
    expect(document.body.textContent).toContain('Fotos (optional)');
    expect(document.body.textContent).toContain('Foto-Upload kommt bald');
    expect(document.body.textContent).toContain('Foto folgt');
    expect(document.querySelector('input[type="file"]')).toBeNull();

    setValue(input('Bezeichnung'), 'Handelshof 7');
    setValue(input('Straße'), 'Handelsweg');
    setValue(input('Hausnummer'), '7');
    setValue(input('PLZ'), '60313');
    setValue(input('Ort'), 'Frankfurt am Main');

    await act(async () => {
      button('Objekt anlegen').click();
      await Promise.resolve();
    });

    expect(mocks.mutate).toHaveBeenCalledWith(
      {
        name: 'Handelshof 7',
        street: 'Handelsweg',
        houseNumber: '7',
        postalCode: '60313',
        city: 'Frankfurt am Main',
        country: 'Deutschland',
        buildingType: 'WOHN_UND_GESCHAEFTSHAUS',
        isResidential: false,
      },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(mocks.clearDraft).toHaveBeenCalledOnce();
    expect(mocks.push).toHaveBeenCalledWith('/a/account-1/objekte/building-new');
  });
});
