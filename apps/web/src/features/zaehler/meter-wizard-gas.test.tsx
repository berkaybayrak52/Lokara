// @vitest-environment happy-dom

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DEVICE_TYPE_UNIT, METER_DEVICE_TYPES, METER_DEVICE_TYPE_LABELS } from '@/lib/contracts';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

const mocks = vi.hoisted(() => ({
  mutate: vi.fn(),
  clearDraft: vi.fn(),
  workspace: {
    permissions: { canWrite: true },
    expiredMeterIds: [] as string[],
    periodLabel: '2026',
    buildings: [
      {
        id: 'building-1',
        name: 'Musterstraße 12',
        address: 'Musterstraße 12, 10115 Berlin',
        activeMeterCount: 0,
        expiredCount: 0,
        missingDataCount: 0,
        units: [],
        buildingMeters: [],
      },
    ],
  },
}));

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>
      {children}
    </a>
  ),
}));
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams({ objektId: 'building-1' }),
}));
vi.mock('@/lib/form-draft', () => ({
  useFormDraft: () => ({ draftRestored: false, clearDraft: mocks.clearDraft }),
}));
vi.mock('./heating-cost-section', () => ({
  HeatingCostSection: () => <div>Heizkosten-Abrechnungsgrundlagen</div>,
}));
vi.mock('./queries', () => ({
  useMeterWorkspace: () => ({
    isPending: false,
    isError: false,
    data: mocks.workspace,
  }),
  useCreateMeter: () => ({
    mutate: mocks.mutate,
    isPending: false,
    isError: false,
    isSuccess: false,
  }),
}));

async function loadWizard(): Promise<React.ComponentType<{ accountId: string }>> {
  const modulePath = './meter-wizard';
  const module = (await import(/* @vite-ignore */ modulePath)) as {
    MeterWizard: React.ComponentType<{ accountId: string }>;
  };
  return module.MeterWizard;
}

async function loadMetersPage(): Promise<React.ComponentType<{ accountId: string }>> {
  const modulePath = './meters-page';
  const module = (await import(/* @vite-ignore */ modulePath)) as {
    MetersPage: React.ComponentType<{ accountId: string }>;
  };
  return module.MetersPage;
}

function radio(label: string): HTMLInputElement {
  const match = Array.from(document.querySelectorAll<HTMLLabelElement>('label')).find((candidate) =>
    candidate.textContent?.includes(label),
  );
  const control = match?.querySelector<HTMLInputElement>('input[type="radio"]');
  expect(control, `radio "${label}" is missing`).toBeDefined();
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

function optionalInput(label: string): HTMLInputElement | null {
  const match = Array.from(document.querySelectorAll<HTMLLabelElement>('label')).find(
    (candidate) => candidate.textContent?.trim() === label,
  );
  return match?.htmlFor
    ? (document.getElementById(match.htmlFor) as HTMLInputElement | null)
    : null;
}

function button(name: string): HTMLButtonElement {
  const match = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => candidate.textContent?.trim() === name,
  );
  expect(match, `button "${name}" is missing`).toBeDefined();
  return match as HTMLButtonElement;
}

function setValue(control: HTMLInputElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
  setter?.call(control, value);
  control.dispatchEvent(new Event('input', { bubbles: true }));
  control.dispatchEvent(new Event('change', { bubbles: true }));
}

describe('UI-08 gas meter wizard', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.append(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it('exposes the fifth label with its fixed cubic-metre unit', () => {
    expect(METER_DEVICE_TYPES).toContain('GAS_METER');
    expect((METER_DEVICE_TYPE_LABELS as Record<string, string>).GAS_METER).toBe('Gaszähler');
    expect((DEVICE_TYPE_UNIT as Record<string, string>).GAS_METER).toBe('CUBIC_METRE');
  });

  it('renders meter navigation as one interactive control per destination', async () => {
    const [MetersPage, MeterWizard] = await Promise.all([loadMetersPage(), loadWizard()]);
    act(() =>
      root.render(
        <>
          <MetersPage accountId="account-1" />
          <MeterWizard accountId="account-1" />
        </>,
      ),
    );

    expect(document.querySelector('a button, button a')).toBeNull();
  });

  it('shows gas-only supplier fields and sends the exact nested payload', async () => {
    const MeterWizard = await loadWizard();
    act(() => root.render(<MeterWizard accountId="account-1" />));

    expect(optionalInput('Brennwert (kWh/m³)')).toBeNull();
    expect(optionalInput('Zustandszahl')).toBeNull();
    act(() => radio('Gaszähler').click());

    for (const label of [
      'Brennwert (kWh/m³)',
      'Zustandszahl',
      'Gültig ab',
      'Gültig bis (optional)',
      'Versorgerrechnung / Belegreferenz',
    ]) {
      expect(input(label)).toBeDefined();
    }
    expect(radio('Gaszähler').parentElement?.textContent).toContain('Kubikmeter (m³)');

    setValue(input('Zählernummer'), 'GAS-2027-001');
    setValue(input('Brennwert (kWh/m³)'), '10,2500');
    setValue(input('Zustandszahl'), '0,9500');
    setValue(input('Gültig ab'), '2027-01-01');
    setValue(input('Gültig bis (optional)'), '2027-12-31');
    setValue(input('Versorgerrechnung / Belegreferenz'), 'gas-invoice-2027-001');

    await act(async () => {
      button('Zähler anlegen').click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(mocks.mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        deviceType: 'GAS_METER',
        gasConversion: {
          calorificFactorKwhPerM3: '10.2500',
          conditionNumber: '0.9500',
          validFrom: '2027-01-01',
          validTo: '2027-12-31',
          supplierInvoiceReference: 'gas-invoice-2027-001',
        },
      }),
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );

    act(() => radio('Wärmemengenzähler').click());
    expect(optionalInput('Brennwert (kWh/m³)')).toBeNull();
    expect(optionalInput('Zustandszahl')).toBeNull();
  });
});
