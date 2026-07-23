import type { Cents, Period } from '@lokara/domain';

/**
 * M0 SHELL — the real engine is M2 (PLAN.md): §§7/8 HKVO 30/70–50/50 split,
 * §9 warm-water separation, §9a estimation, degree-day apportionment, and the
 * CO₂ 10-step model (CO2KostAufG). HKVO ratios and the CO₂ table come from
 * @lokara/rules-store as data — never hardcoded here. This package must stay
 * PURE: no framework, DB, or vendor imports.
 */

export interface HeatingStatementInput {
  readonly billingPeriod: Period;
  readonly totalHeatingCost: Cents;
  /** As-of law date for rules-store lookups (drives the Rechtsstand stamp). */
  readonly lawAsOf: string;
}

export interface HeatingStatementResult {
  readonly landlordCo2Share: Cents;
  readonly renterCo2Share: Cents;
  readonly rechtsstand: string;
}

export class NotImplementedError extends Error {
  constructor(milestone: string) {
    super(`Not implemented — scheduled for milestone ${milestone}`);
    this.name = 'NotImplementedError';
  }
}

export function calculateHeatingStatement(_input: HeatingStatementInput): HeatingStatementResult {
  throw new NotImplementedError('M2');
}
