import { describe, expect, it } from 'vitest';

import { AdvancePaymentPeriodOutSchema, TenancyOutSchema } from '@/lib/contracts';

describe('UI-03 tenancy response contract', () => {
  it('exports the exact advance-payment period wire schema', () => {
    const parsed = AdvancePaymentPeriodOutSchema.parse({
      id: 'advance-2025-01',
      amountCents: 22000,
      amountEur: '220,00 €',
      validFrom: '2025-01-01',
      validTo: '2025-07-01',
      predecessorId: null,
      declarationRef: 'Mietvertrag',
    });

    expect(parsed).toEqual({
      id: 'advance-2025-01',
      amountCents: 22000,
      amountEur: '220,00 €',
      validFrom: '2025-01-01',
      validTo: '2025-07-01',
      predecessorId: null,
      declarationRef: 'Mietvertrag',
    });
  });

  it('requires advancePaymentSchedule and no longer exposes the obsolete scalar fields', () => {
    const parsed = TenancyOutSchema.parse({
      id: 'tenancy-1',
      renterNames: ['Erika Musterfrau'],
      validFrom: '2025-01-01',
      validTo: null,
      baseRentCents: 90000,
      baseRentEur: '900,00 €',
      advancePaymentSchedule: [
        {
          id: 'advance-1',
          amountCents: 22000,
          amountEur: '220,00 €',
          validFrom: '2025-01-01',
          validTo: null,
          predecessorId: null,
          declarationRef: 'Mietvertrag',
        },
      ],
      activeToday: true,
      advancePaymentCents: 22000,
      advancePaymentEur: '220,00 €',
    });

    expect(parsed.advancePaymentSchedule).toHaveLength(1);
    expect(parsed).not.toHaveProperty('advancePaymentCents');
    expect(parsed).not.toHaveProperty('advancePaymentEur');

    const missingSchedule = { ...parsed } as Record<string, unknown>;
    delete missingSchedule.advancePaymentSchedule;
    expect(TenancyOutSchema.safeParse(missingSchedule).success).toBe(false);
  });
});
