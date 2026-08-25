import { describe, expect, it } from 'vitest';

import type { AdvancePaymentPeriodOut } from '@/lib/contracts';

import { selectAdvancePaymentAmount } from './unit-detail-page';

function period(
  validFrom: string,
  validTo: string | null,
  amountEur: string,
): AdvancePaymentPeriodOut {
  return {
    id: `advance-${validFrom}`,
    amountCents: Number(amountEur.replace(/\D/g, '')),
    amountEur,
    validFrom,
    validTo,
    predecessorId: null,
    declarationRef: 'Mietvertrag',
  };
}

describe('selectAdvancePaymentAmount', () => {
  it('selects the period that is valid today using half-open dates', () => {
    const schedule = [
      period('2024-01-01', '2025-07-01', '180,00 €'),
      period('2025-07-01', null, '220,00 €'),
    ];

    expect(selectAdvancePaymentAmount(schedule, '2025-06-30')).toBe('180,00 €');
    expect(selectAdvancePaymentAmount(schedule, '2025-07-01')).toBe('220,00 €');
  });

  it('falls back to the chronologically latest period when none is valid today', () => {
    const past = [
      period('2023-01-01', '2024-01-01', '150,00 €'),
      period('2024-01-01', '2025-01-01', '190,00 €'),
    ];
    const future = [
      period('2027-01-01', null, '240,00 €'),
      period('2026-01-01', '2027-01-01', '210,00 €'),
    ];

    expect(selectAdvancePaymentAmount(past, '2025-06-01')).toBe('190,00 €');
    expect(selectAdvancePaymentAmount(future, '2025-06-01')).toBe('240,00 €');
  });

  it('returns null for an empty schedule so the table can render an em dash', () => {
    expect(selectAdvancePaymentAmount([], '2025-06-01')).toBeNull();
  });
});
