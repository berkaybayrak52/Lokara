import { describe, expect, it } from 'vitest';
import { cents, period } from '@lokara/domain';
import { calculateHeatingStatement, NotImplementedError } from './index';

describe('heating-engine shell (M0)', () => {
  it('is wired but not implemented until M2', () => {
    expect(() =>
      calculateHeatingStatement({
        billingPeriod: period('2025-01-01', '2026-01-01'),
        totalHeatingCost: cents(250000),
        lawAsOf: '2025-12-31',
      }),
    ).toThrow(NotImplementedError);
  });
});
