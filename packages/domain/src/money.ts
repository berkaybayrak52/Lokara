import Decimal from 'decimal.js';

/**
 * All money in Lokara is integer cents. Floats never touch money.
 * `Cents` is a branded integer so plain numbers cannot be passed accidentally.
 */
export type Cents = number & { readonly __brand: 'Cents' };

export class NonIntegerCentsError extends Error {
  constructor(value: number) {
    super(`Money must be integer cents, got: ${value}`);
    this.name = 'NonIntegerCentsError';
  }
}

export function cents(value: number): Cents {
  if (!Number.isSafeInteger(value)) {
    throw new NonIntegerCentsError(value);
  }
  return value as Cents;
}

export function addCents(...values: Cents[]): Cents {
  return cents(values.reduce((sum, v) => sum + v, 0));
}

/** Formats integer cents as a German amount string, e.g. 120000 → "1.200,00 €". */
export function formatEur(value: Cents): string {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(value / 100);
}

/**
 * Largest-remainder allocation: splits `total` cents proportionally to `weights`
 * so the parts always reconcile to `total` exactly.
 *
 * Deterministic: quotas are computed with Decimal (no float drift); leftover cents
 * go to the largest fractional remainders, ties broken by lowest index.
 */
export function distributeCents(total: Cents, weights: readonly number[]): Cents[] {
  if (weights.length === 0) {
    throw new Error('distributeCents requires at least one weight');
  }
  if (weights.some((w) => !Number.isFinite(w) || w < 0)) {
    throw new Error('distributeCents weights must be finite and >= 0');
  }
  const weightSum = weights.reduce((s, w) => new Decimal(w).plus(s), new Decimal(0));
  if (weightSum.isZero()) {
    throw new Error('distributeCents requires a positive weight sum');
  }

  const quotas = weights.map((w) => new Decimal(w).times(total).dividedBy(weightSum));
  const floors = quotas.map((q) => q.floor());
  const flooredSum = floors.reduce((s, f) => s.plus(f), new Decimal(0));
  let remainder = new Decimal(total).minus(flooredSum).toNumber();

  const byRemainder = quotas
    .map((q, index) => ({ index, frac: q.minus(q.floor()) }))
    .sort((a, b) => {
      const cmp = b.frac.comparedTo(a.frac);
      return cmp !== 0 ? cmp : a.index - b.index;
    });

  const result = floors.map((f) => f.toNumber());
  for (const { index } of byRemainder) {
    if (remainder <= 0) break;
    result[index] = (result[index] ?? 0) + 1;
    remainder -= 1;
  }
  return result.map((v) => cents(v));
}
