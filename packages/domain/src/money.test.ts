import { describe, expect, it } from 'vitest';
import { addCents, cents, distributeCents, formatEur, NonIntegerCentsError } from './money';

describe('cents', () => {
  it('accepts integers and rejects floats', () => {
    expect(cents(120000)).toBe(120000);
    expect(() => cents(1200.5)).toThrow(NonIntegerCentsError);
    expect(() => cents(Number.NaN)).toThrow(NonIntegerCentsError);
  });

  it('adds without float drift', () => {
    expect(addCents(cents(1), cents(2), cents(3))).toBe(6);
  });
});

describe('formatEur', () => {
  it('formats German currency', () => {
    // Intl emits a non-breaking space before the € sign; normalize for comparison.
    expect(formatEur(cents(120000)).replace(/[\u00A0\u202F]/g, ' ')).toBe('1.200,00 €');
  });
});

describe('distributeCents (largest remainder)', () => {
  it('reconciles the €1,200 garbage-cost example from lokara-arch.md §10 to the cent', () => {
    // Weights are m²·days: Unit A (50m²·365d), Unit B renter (30m²·181d),
    // Unit B vacancy (30m²·184d), Unit C (20m²·365d).
    const shares = distributeCents(cents(120000), [18250, 5430, 5520, 7300]);
    expect(shares).toEqual([60000, 17852, 18148, 24000]);
    expect(shares.reduce((s, v) => s + v, 0)).toBe(120000);
  });

  it('always reconciles to the total', () => {
    const shares = distributeCents(cents(100), [1, 1, 1]);
    expect(shares.reduce((s, v) => s + v, 0)).toBe(100);
    expect(shares).toEqual([34, 33, 33]);
  });

  it('is deterministic on ties (lowest index wins the extra cent)', () => {
    expect(distributeCents(cents(101), [1, 1])).toEqual([51, 50]);
  });

  it('handles zero weights (that party gets nothing)', () => {
    expect(distributeCents(cents(100), [0, 1])).toEqual([0, 100]);
  });

  it('rejects empty, negative, and all-zero weights', () => {
    expect(() => distributeCents(cents(100), [])).toThrow();
    expect(() => distributeCents(cents(100), [-1, 2])).toThrow();
    expect(() => distributeCents(cents(100), [0, 0])).toThrow();
  });
});
