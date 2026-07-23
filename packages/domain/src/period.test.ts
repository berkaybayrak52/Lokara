import { describe, expect, it } from 'vitest';
import { daysBetween, overlapDays, period, periodsOverlap, toUtcDate } from './period';

describe('period', () => {
  it('builds half-open periods and rejects inverted ranges', () => {
    const p = period('2025-01-01', '2025-07-01');
    expect(p.validFrom.toISOString()).toBe('2025-01-01T00:00:00.000Z');
    expect(() => period('2025-07-01', '2025-01-01')).toThrow();
    expect(() => period('not-a-date')).toThrow();
  });

  it('counts calendar days, DST-safe (UTC)', () => {
    // 2025 is not a leap year: Jan 1 → Jan 1 next year = 365 days.
    expect(daysBetween(toUtcDate('2025-01-01'), toUtcDate('2026-01-01'))).toBe(365);
    // Renter 2 from the arch example: Jan 1 → moved out end of Jun 30 = 181 days.
    expect(daysBetween(toUtcDate('2025-01-01'), toUtcDate('2025-07-01'))).toBe(181);
  });

  it('computes overlap with a billing window', () => {
    const window = [toUtcDate('2025-01-01'), toUtcDate('2026-01-01')] as const;
    expect(overlapDays(period('2025-01-01', '2025-07-01'), ...window)).toBe(181);
    expect(overlapDays(period('2025-07-01'), ...window)).toBe(184); // open-ended vacancy Jul–Dec
    expect(overlapDays(period('2024-01-01', '2024-12-31'), ...window)).toBe(0);
  });

  it('detects overlapping periods (RENTED vs SELF_USED invariant)', () => {
    expect(periodsOverlap(period('2025-01-01', '2025-07-01'), period('2025-06-30'))).toBe(true);
    expect(periodsOverlap(period('2025-01-01', '2025-07-01'), period('2025-07-01'))).toBe(false);
  });
});
