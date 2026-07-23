import type { RuleSet } from '../store';

/**
 * PLACEHOLDER SAMPLE — demonstrates the rule-set shape only.
 *
 * The real HKVO consumption/base-cost split bounds (§ 7 HeizkostenV: 50–70 %
 * consumption-based) are entered and verified at M2, together with the CO₂
 * 10-step table (CO2KostAufG). Do not treat these values as legally verified.
 */
export interface HeatingSplitBounds {
  readonly minConsumptionShare: number;
  readonly maxConsumptionShare: number;
}

export const HEATING_SPLIT_BOUNDS: RuleSet<HeatingSplitBounds> = {
  key: 'hkvo.heating-split-bounds',
  versions: [
    {
      validFrom: '1989-03-01',
      source: '§ 7 Abs. 1 HeizkostenV (PLACEHOLDER — verify at M2)',
      value: { minConsumptionShare: 0.5, maxConsumptionShare: 0.7 },
    },
  ],
};
