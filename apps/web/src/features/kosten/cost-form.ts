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
    catalogueId: z.string().min(1, 'Bitte eine Kostenart wählen'),
    label: z.string().max(200, 'Maximal 200 Zeichen'),
    amount: z
      .string()
      .min(1, 'Pflichtfeld')
      .refine((v) => parseEurToCents(v) !== null, 'Betrag wie 1.200,00 angeben')
      .refine((v) => (parseEurToCents(v) ?? 0) > 0, 'Betrag muss größer als 0 sein'),
    periodFrom: z.string().min(1, 'Pflichtfeld'),
    periodTo: z.string().min(1, 'Pflichtfeld'),
    key: z.enum(ALLOCATION_KEYS).or(z.literal('')),
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

const CURRENT_YEAR = new Date().getFullYear();

export const EMPTY_COST_FORM: CostForm = {
  catalogueId: '',
  label: '',
  amount: '',
  periodFrom: `${CURRENT_YEAR}-01-01`,
  periodTo: `${CURRENT_YEAR + 1}-01-01`,
  key: '',
  directUnitId: '',
};

/**
 * German text → integer cents at the form edge, once. Returns null only for
 * input the schema already rejects, so callers treat it as a no-op guard.
 */
export function toCostCreateInput(
  values: CostForm,
  fallbackLabel: string = values.label,
  defaultKey: (typeof ALLOCATION_KEYS)[number] | null = values.key || null,
): CostCreateInput | null {
  const amountCents = parseEurToCents(values.amount);
  const label = values.label.trim() || fallbackLabel;
  if (amountCents === null || values.catalogueId === '' || label === '') return null;
  const keyOverride = values.key !== '' && values.key !== defaultKey ? values.key : undefined;
  return {
    catalogueId: values.catalogueId,
    label,
    amountCents,
    periodFrom: values.periodFrom,
    periodTo: values.periodTo,
    keyOverride,
    directUnitId: values.key === 'DIRECT' ? values.directUnitId : undefined,
  };
}
