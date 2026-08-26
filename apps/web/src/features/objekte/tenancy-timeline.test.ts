import { describe, expect, it } from 'vitest';

import type { SelfUsePeriodOut, TenancyOut } from '@/lib/contracts';

import { buildSegments } from './tenancy-timeline';

const WINDOW_FROM = Date.UTC(2025, 0, 1);
const WINDOW_TO = Date.UTC(2026, 0, 1);

function tenancy(validFrom: string, validTo: string | null, name: string): TenancyOut {
  return {
    id: `${name}-${validFrom}`,
    renterNames: [name],
    validFrom,
    validTo,
    baseRentCents: 0,
    baseRentEur: '',
    advancePaymentSchedule: [],
    activeToday: false,
  };
}

function selfUse(validFrom: string, validTo: string | null): SelfUsePeriodOut {
  return { kind: 'OWNER_OCCUPIED', validFrom, validTo };
}

const kinds = (tenancies: TenancyOut[], periods: SelfUsePeriodOut[] = []) =>
  buildSegments(tenancies, periods, WINDOW_FROM, WINDOW_TO).map((s) => s.kind);

describe('buildSegments', () => {
  it('derives the vacancy gap that explains the landlord share', () => {
    // The canonical fixture: unit B rented until 30 Jun (validTo exclusive
    // 1 Jul), vacant for the rest of the year → €181,48 to the landlord.
    const segments = buildSegments(
      [tenancy('2024-08-01', '2025-07-01', 'Bernd Muster')],
      [],
      WINDOW_FROM,
      WINDOW_TO,
    );
    expect(segments.map((s) => s.kind)).toEqual(['TENANCY', 'VACANCY']);
    expect(segments[1]?.label).toContain('Leerstand');
    expect(segments[1]?.fromMs).toBe(Date.UTC(2025, 6, 1)); // gap starts 1 Jul
    expect(segments[1]?.toMs).toBe(WINDOW_TO);
  });

  it('leaves no gap for a full-year tenancy', () => {
    expect(kinds([tenancy('2024-01-01', null, 'Anna Beispiel')])).toEqual(['TENANCY']);
  });

  it('marks a leading gap before the first tenancy', () => {
    expect(kinds([tenancy('2025-04-01', null, 'Neu')])).toEqual(['VACANCY', 'TENANCY']);
  });

  it('renders self-use as its own segment, not as vacancy', () => {
    expect(kinds([], [selfUse('2025-01-01', '2026-01-01')])).toEqual(['SELF_USE']);
    expect(kinds([tenancy('2025-07-01', null, 'Mieter')], [selfUse('2025-01-01', '2025-07-01')])).toEqual(
      ['SELF_USE', 'TENANCY'],
    );
  });

  it('fills the gap between two tenancies', () => {
    expect(
      kinds([tenancy('2025-01-01', '2025-04-01', 'Erste'), tenancy('2025-06-01', null, 'Zweite')]),
    ).toEqual(['TENANCY', 'VACANCY', 'TENANCY']);
  });

  it('clips periods to the window', () => {
    const segments = buildSegments(
      [tenancy('2020-01-01', '2030-01-01', 'Lang')],
      [],
      WINDOW_FROM,
      WINDOW_TO,
    );
    expect(segments).toHaveLength(1);
    expect(segments[0]?.fromMs).toBe(WINDOW_FROM);
    expect(segments[0]?.toMs).toBe(WINDOW_TO);
  });
});
