import { describe, expect, it } from 'vitest';

import { CostFormSchema, EMPTY_COST_FORM, toCostCreateInput } from './cost-form';

const valid = {
  ...EMPTY_COST_FORM,
  catalogueId: 'muellabfuhr',
  label: 'Müllabfuhr',
  amount: '1.200,00',
  key: 'AREA' as const,
};

describe('CostFormSchema', () => {
  it('accepts a German amount and turns it into integer cents', () => {
    expect(CostFormSchema.safeParse(valid).success).toBe(true);
    expect(toCostCreateInput(valid)?.amountCents).toBe(120000);
  });

  it('rejects an amount that is not German-formatted', () => {
    // "1,200.00" is the English grouping — parsing it as German would silently
    // book € 1,20 instead of € 1.200,00.
    expect(CostFormSchema.safeParse({ ...valid, amount: '1,200.00' }).success).toBe(false);
  });

  it('rejects a zero or empty amount', () => {
    expect(CostFormSchema.safeParse({ ...valid, amount: '0' }).success).toBe(false);
    expect(CostFormSchema.safeParse({ ...valid, amount: '' }).success).toBe(false);
  });

  it('accepts an empty optional label', () => {
    expect(CostFormSchema.safeParse({ ...valid, label: '' }).success).toBe(true);
  });

  it('rejects a period that ends before it starts', () => {
    const result = CostFormSchema.safeParse({ ...valid, periodTo: '2024-01-01' });
    expect(result.success).toBe(false);
  });

  it('requires a target for DIRECT and none otherwise', () => {
    expect(CostFormSchema.safeParse({ ...valid, key: 'DIRECT' }).success).toBe(false);
    expect(
      CostFormSchema.safeParse({ ...valid, key: 'DIRECT', directUnitId: 'unit-a' }).success,
    ).toBe(true);
  });

  it('drops the direct target for every other key', () => {
    // The API rejects a target on a non-DIRECT key; sending one because the
    // select still held a stale value would 422 a valid entry.
    const input = toCostCreateInput({ ...valid, key: 'AREA', directUnitId: 'unit-a' });
    expect(input?.directUnitId).toBeUndefined();
  });
});

describe('the Beleg review step and Kosten erfassen share one contract', () => {
  it('validates a prefilled entry exactly like a typed one', () => {
    // The review step builds this shape from ExtractionPrefill (cents →
    // German text). If the two screens ever diverge, a confirmed extraction
    // could write something the manual form would have refused.
    const fromExtraction = {
      ...EMPTY_COST_FORM,
      catalogueId: 'muellabfuhr',
      label: 'Müllabfuhr',
      amount: '1200,00',
      periodFrom: '2025-01-01',
      periodTo: '2026-01-01',
      key: 'AREA' as const,
    };
    expect(CostFormSchema.safeParse(fromExtraction).success).toBe(true);
    expect(toCostCreateInput(fromExtraction)).toEqual({
      catalogueId: 'muellabfuhr',
      label: 'Müllabfuhr',
      amountCents: 120000,
      periodFrom: '2025-01-01',
      periodTo: '2026-01-01',
      keyOverride: undefined,
      directUnitId: undefined,
    });
  });
});
