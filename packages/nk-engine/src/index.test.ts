import { describe, expect, it } from 'vitest';
import { period } from '@lokara/domain';
import { calculateNkStatement, NotImplementedError } from './index';

describe('nk-engine shell (M0)', () => {
  it('is wired but not implemented until M1', () => {
    expect(() =>
      calculateNkStatement({
        billingPeriod: period('2025-01-01', '2026-01-01'),
        costs: [],
        occupancies: [],
      }),
    ).toThrow(NotImplementedError);
  });
});
