import { describe, expect, it, vi } from 'vitest';

import {
  MeResponseSchema,
  MeterWorkspaceResponseSchema,
  RenterActivationCodeIssueResponseSchema,
  RenterActivationResponseSchema,
  RenterOverviewResponseSchema,
  RenterPublicationListResponseSchema,
  UnitDashboardResponseSchema,
} from './contracts';
import * as DemoPreview from './demo-preview';

const { previewResponse } = DemoPreview;

function resetPreviewActivationState(): void {
  const reset = (DemoPreview as Record<string, unknown>).resetPreviewActivationStateForTests;
  if (typeof reset === 'function') reset();
}

function previewNotFound(): unknown {
  const sentinel = (DemoPreview as Record<string, unknown>).PREVIEW_NOT_FOUND;
  expect(sentinel, 'recognized preview refusals need an exported sentinel').toBeDefined();
  return sentinel;
}

describe('meter workspace preview', () => {
  it('satisfies the same response contract as the live meter workspace', () => {
    const response = previewResponse('/a/acc_demo_lokara/meter-workspace');

    expect(response).toBeDefined();
    const workspace = MeterWorkspaceResponseSchema.parse(response);
    const meters = workspace.buildings.flatMap((building) => [
      ...building.buildingMeters,
      ...building.units.flatMap((unit) => unit.meters),
    ]);
    expect(meters.length).toBeGreaterThan(0);
    for (const meter of meters) {
      if (meter.deviceType !== 'GAS_METER') {
        expect(meter.gasConversion).toBeNull();
      }
    }
  });
});

describe('owner renter-activation preview', () => {
  it('exposes the renter portal only for a rented preview unit with the exact party ids', () => {
    const response = previewResponse('/a/acc_demo_lokara/units/u_muster_a/dashboard');
    const dashboard = UnitDashboardResponseSchema.parse(response);
    const portal = dashboard.modules.find((module) => module.key === 'PORTAL');

    expect(portal).toEqual({ key: 'PORTAL', available: true, unavailableReason: null });
    expect(dashboard.currentTenancy?.id).toBe('t_anna');
    expect(dashboard.currentTenancy?.parties).toEqual([
      { id: 'r_anna', name: 'Anna Beispiel', email: null },
    ]);
  });

  it('keeps the renter portal unavailable for a vacant preview unit', () => {
    const response = previewResponse('/a/acc_demo_lokara/units/u_linden_3/dashboard');
    const dashboard = UnitDashboardResponseSchema.parse(response);
    const portal = dashboard.modules.find((module) => module.key === 'PORTAL');

    expect(dashboard.currentTenancy).toBeNull();
    expect(portal?.available).toBe(false);
    expect(portal?.unavailableReason).toBeTruthy();
  });

  it('refuses a preview unit dashboard carried under another account', () => {
    expect(previewResponse('/a/acc_other/units/u_muster_a/dashboard')).toBe(previewNotFound());
  });

  it('issues a strict one-time preview code only for the matched tenancy party', () => {
    const response = previewResponse(
      '/a/acc_demo_lokara/tenancies/t_anna/renters/r_anna/activation-codes',
      { method: 'POST' },
    );
    const issued = RenterActivationCodeIssueResponseSchema.parse(response);

    expect(issued.activationCodeId).not.toBe('');
    expect(issued.activationCode).not.toBe('');
    expect(issued.activationCode).toMatch(/^acc_demo_lokara\.[^.]+$/);
    expect(Number.isNaN(Date.parse(issued.expiresAt))).toBe(false);
    expect(issued.expiresAt).toMatch(/(?:Z|[+-]\d{2}:\d{2})$/);
  });

  it.each([
    '/a/acc_demo_lokara/tenancies/t_unknown/renters/r_anna/activation-codes',
    '/a/acc_demo_lokara/tenancies/t_anna/renters/r_unknown/activation-codes',
    '/a/acc_demo_lokara/tenancies/t_fatma/renters/r_anna/activation-codes',
    '/a/acc_other/tenancies/t_anna/renters/r_anna/activation-codes',
  ])('refuses unmatched activation path %s', (path) => {
    expect(previewResponse(path, { method: 'POST' })).toBe(previewNotFound());
  });

  it('keeps unrelated unknown reads eligible for normal fallback', () => {
    expect(previewResponse('/unrelated-preview-unknown')).toBeUndefined();
  });

  it('issues, expires and spends preview codes before exposing only the activated renter portal', () => {
    const now = new Date('2026-09-12T10:00:00.000Z');
    const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
    resetPreviewActivationState();
    vi.useFakeTimers();
    vi.setSystemTime(now);

    try {
      const before = MeResponseSchema.parse(previewResponse('/me'));
      expect(before.renterContexts).toEqual([]);
      expect(previewResponse('/renter/t_anna')).toBe(previewNotFound());
      expect(previewResponse('/renter/t_anna/documents')).toBe(previewNotFound());
      expect(previewResponse('/renter/t_unknown')).toBe(previewNotFound());
      expect(previewResponse('/renter/t_unknown/documents')).toBe(previewNotFound());

      const issuePath = '/a/acc_demo_lokara/tenancies/t_anna/renters/r_anna/activation-codes';
      const first = RenterActivationCodeIssueResponseSchema.parse(
        previewResponse(issuePath, { method: 'POST' }),
      );
      const second = RenterActivationCodeIssueResponseSchema.parse(
        previewResponse(issuePath, { method: 'POST' }),
      );

      expect(second.activationCodeId).not.toBe(first.activationCodeId);
      expect(second.activationCode).not.toBe(first.activationCode);
      expect(Date.parse(first.expiresAt)).toBe(now.getTime() + sevenDaysMs);
      expect(Date.parse(second.expiresAt)).toBe(now.getTime() + sevenDaysMs);
      expect(first.expiresAt).toMatch(/(?:Z|[+-]\d{2}:\d{2})$/);

      const activationInit = (activationCode: string): RequestInit => ({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ activationCode }),
      });
      expect(
        previewResponse('/renter/t_anna/activation', activationInit('wrong.preview.code')),
      ).toBe(previewNotFound());
      expect(
        previewResponse('/renter/t_fatma/activation', activationInit(first.activationCode)),
      ).toBe(previewNotFound());

      vi.setSystemTime(new Date(now.getTime() + sevenDaysMs));
      expect(
        previewResponse('/renter/t_anna/activation', activationInit(second.activationCode)),
      ).toBe(previewNotFound());
      vi.setSystemTime(new Date(now.getTime() + 1_000));

      const activated = RenterActivationResponseSchema.parse(
        previewResponse('/renter/t_anna/activation', activationInit(first.activationCode)),
      );
      expect(activated).toEqual({ ok: true, tenancyId: 't_anna', renterId: 'r_anna' });
      expect(
        previewResponse('/renter/t_anna/activation', activationInit(first.activationCode)),
      ).toBe(previewNotFound());

      const after = MeResponseSchema.parse(previewResponse('/me'));
      expect(after.renterContexts).toEqual([{ tenancyId: 't_anna' }]);

      const overview = RenterOverviewResponseSchema.parse(previewResponse('/renter/t_anna'));
      expect(overview).toMatchObject({
        tenancyId: 't_anna',
        unitLabel: 'Wohnung A · EG links',
        buildingName: 'Musterstraße 12',
        street: 'Musterstraße 12',
        postalCode: '60311',
        city: 'Frankfurt am Main',
      });
      expect(
        RenterPublicationListResponseSchema.parse(previewResponse('/renter/t_anna/documents')),
      ).toEqual({ documents: [] });
      expect(previewResponse('/renter/t_fatma')).toBe(previewNotFound());
      expect(previewResponse('/renter/t_fatma/documents')).toBe(previewNotFound());
    } finally {
      vi.useRealTimers();
      resetPreviewActivationState();
    }
  });
});
