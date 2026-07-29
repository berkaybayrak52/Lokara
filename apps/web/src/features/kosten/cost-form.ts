import { z } from 'zod';

import { ALLOCATION_KEYS } from '@/lib/contracts';
import { parseEurToCents } from '@/lib/format';

import type { CostCreateInput } from './queries';

/**
 * The one cost-entry form contract.
 *
 * Shared by "Kosten erfassen" and the Beleg review step on purpose: a
 * prefilled entry has to clear exactly the same bar as a typed one, so
 * confirming an extraction can never write something the manual form would
 * have rejected. Two copies of this schema would eventually disagree.
 */
export const CostFormSchema = z
  .object({
    label: z.string().min(1, 'Pflichtfeld'),
    amount: z
      .string()
      .min(1, 'Pflichtfeld')
      .refine((v) => parseEurToCents(v) !== null, 'Betrag wie 1.200,00 angeben')
      .refine((v) => (parseEurToCents(v) ?? 0) > 0, 'Betrag muss größer als 0 sein'),
    periodFrom: z.string().min(1, 'Pflichtfeld'),
    periodTo: z.string().min(1, 'Pflichtfeld'),
    key: z.enum(ALLOCATION_KEYS),
    directUnitId: z.string(),
  })
  .refine((v) => v.periodTo > v.periodFrom, {
    path: ['periodTo'],
    message: 'Ende muss nach dem Beginn liegen',
  })
  .refine((v) => v.key !== 'DIRECT' || v.directUnitId !== '', {
    path: ['directUnitId'],
    message: 'Direktzuordnung braucht eine Einheit',
  });

export type CostForm = z.infer<typeof CostFormSchema>;

export const EMPTY_COST_FORM: CostForm = {
  label: '',
  amount: '',
  periodFrom: '2025-01-01',
  periodTo: '2026-01-01',
  key: 'AREA',
  directUnitId: '',
};

/**
 * German text → integer cents at the form edge, once. Returns null only for
 * input the schema already rejects, so callers treat it as a no-op guard.
 */
export function toCostCreateInput(values: CostForm): CostCreateInput | null {
  const amountCents = parseEurToCents(values.amount);
  if (amountCents === null) return null;
  return {
    label: values.label,
    amountCents,
    periodFrom: values.periodFrom,
    periodTo: values.periodTo,
    key: values.key,
    directUnitId: values.key === 'DIRECT' ? values.directUnitId : undefined,
  };
}
