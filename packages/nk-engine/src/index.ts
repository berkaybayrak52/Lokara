import type { AllocationKey, Cents, Period } from '@lokara/domain';

/**
 * M0 SHELL — the real engine is M1 (PLAN.md). The Definition of Done there is
 * the €1,200 garbage-cost golden fixture (docs/03-nk-heating-engines.md) passing
 * byte-for-byte. This package must stay PURE: no framework, DB, or vendor imports.
 */

export interface NkCostInput {
  readonly label: string;
  readonly amount: Cents;
  readonly allocationKey: AllocationKey;
}

export interface NkOccupancyInput {
  readonly unitId: string;
  readonly renterId: string | null; // null = vacancy → landlord
  readonly areaSqmX100: number;
  readonly persons: number;
  readonly period: Period;
}

export interface NkStatementInput {
  readonly billingPeriod: Period;
  readonly costs: readonly NkCostInput[];
  readonly occupancies: readonly NkOccupancyInput[];
}

export interface NkShare {
  readonly unitId: string;
  readonly renterId: string | null;
  readonly costLabel: string;
  readonly amount: Cents;
}

export interface NkStatementResult {
  readonly shares: readonly NkShare[];
  readonly total: Cents;
}

export class NotImplementedError extends Error {
  constructor(milestone: string) {
    super(`Not implemented — scheduled for milestone ${milestone}`);
    this.name = 'NotImplementedError';
  }
}

export function calculateNkStatement(_input: NkStatementInput): NkStatementResult {
  throw new NotImplementedError('M1');
}
