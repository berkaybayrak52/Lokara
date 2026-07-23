const MS_PER_DAY = 24 * 60 * 60 * 1000;

/**
 * A half-open temporal validity range [validFrom, validTo).
 * `validTo === null` means open-ended ("still valid").
 * Dates are date-only (UTC midnight); day counting is calendar-day based.
 */
export interface Period {
  readonly validFrom: Date;
  readonly validTo: Date | null;
}

export function toUtcDate(isoDate: string): Date {
  const d = new Date(`${isoDate}T00:00:00.000Z`);
  if (Number.isNaN(d.getTime())) {
    throw new Error(`Invalid ISO date: ${isoDate}`);
  }
  return d;
}

export function period(validFromIso: string, validToIso?: string | null): Period {
  const validFrom = toUtcDate(validFromIso);
  const validTo = validToIso ? toUtcDate(validToIso) : null;
  if (validTo && validTo.getTime() <= validFrom.getTime()) {
    throw new Error(`Period validTo (${validToIso}) must be after validFrom (${validFromIso})`);
  }
  return { validFrom, validTo };
}

/** Number of days in the half-open range [from, to). */
export function daysBetween(from: Date, to: Date): number {
  return Math.round((to.getTime() - from.getTime()) / MS_PER_DAY);
}

/** Days a period overlaps a billing window [windowFrom, windowTo). */
export function overlapDays(p: Period, windowFrom: Date, windowTo: Date): number {
  const start = Math.max(p.validFrom.getTime(), windowFrom.getTime());
  const end = Math.min(p.validTo?.getTime() ?? Infinity, windowTo.getTime());
  if (end <= start) return 0;
  return Math.round((end - start) / MS_PER_DAY);
}

/** True if two periods share at least one day (used to reject RENTED/SELF_USED overlaps). */
export function periodsOverlap(a: Period, b: Period): boolean {
  const aEnd = a.validTo?.getTime() ?? Infinity;
  const bEnd = b.validTo?.getTime() ?? Infinity;
  return a.validFrom.getTime() < bEnd && b.validFrom.getTime() < aEnd;
}
