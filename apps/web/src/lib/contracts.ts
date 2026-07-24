import { z } from 'zod';

/**
 * Zod mirror of the FastAPI contract (apps/api schemas.py) — "never trust the
 * server either": every response is parsed at the boundary, so an API drift
 * fails loudly here instead of rendering garbage. camelCase to match the wire.
 */

export const HealthResponseSchema = z.object({
  status: z.literal('ok'),
  service: z.literal('lokara-api'),
  timestamp: z.string(),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

export const SessionResponseSchema = z.object({ ok: z.literal(true) });

export const DemoTenancySummarySchema = z.object({
  unitLabel: z.string(),
  areaSqm: z.number(),
  renterNames: z.array(z.string()),
  validFrom: z.string(),
  validTo: z.string().nullable(),
  baseRentEur: z.string(),
});

export const DemoSummaryResponseSchema = z.object({
  accountName: z.string(),
  buildingName: z.string(),
  buildingAddress: z.string(),
  unitCount: z.number().int(),
  tenancies: z.array(DemoTenancySummarySchema),
});
export type DemoSummaryResponse = z.infer<typeof DemoSummaryResponseSchema>;
