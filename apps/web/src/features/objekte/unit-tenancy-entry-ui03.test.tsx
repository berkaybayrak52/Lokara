// @vitest-environment happy-dom

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { UnitDetailPage } from './unit-detail-page';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const mocks = vi.hoisted(() => ({ useUnitDetail: vi.fn() }));

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
vi.mock('./queries', () => ({
  useUnitDetail: mocks.useUnitDetail,
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

describe('UI-03 tenancy entry on UnitDetailPage', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
    mocks.useUnitDetail.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        id: 'unit-1',
        label: 'Wohnung 1 (EG links)',
        areaSqm: 64.5,
        buildingId: 'building-1',
        buildingName: 'Musterstraße 12',
        tenancies: [],
        selfUsePeriods: [],
      },
    });
  });

  afterEach(() => {
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
});
