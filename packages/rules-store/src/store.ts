/**
 * Versioned legal rules/config store.
 *
 * Never hardcode a legal rule (CLAUDE.md): AfA rates, HKVO ratios, the CO₂ 10-step
 * table, Anlage-V line numbers etc. are DATA with an "as-of law date". Engines ask
 * for a rule as of a date and stamp `Rechtsstand MM/JJJJ` into every legal output.
 */

export interface RuleVersion<T> {
  /** The date this version of the rule became law ("Rechtsstand"). ISO date. */
  readonly validFrom: string;
  /** Optional end of validity (exclusive). Open-ended if absent. */
  readonly validTo?: string;
  /** Citation, e.g. "§ 7 Abs. 1 HeizkostenV". */
  readonly source: string;
  readonly value: T;
}

export interface RuleSet<T> {
  readonly key: string;
  readonly versions: readonly RuleVersion<T>[];
}

export interface ResolvedRule<T> {
  readonly key: string;
  readonly value: T;
  readonly source: string;
  /** e.g. "Rechtsstand 12/2023" — must be shown in every legal output. */
  readonly rechtsstand: string;
}

export class RuleNotFoundError extends Error {
  constructor(key: string, asOf: string) {
    super(`No version of rule "${key}" is valid as of ${asOf}`);
    this.name = 'RuleNotFoundError';
  }
}

export function formatRechtsstand(isoDate: string): string {
  const [year, month] = isoDate.split('-');
  if (!year || !month) {
    throw new Error(`Invalid ISO date for Rechtsstand: ${isoDate}`);
  }
  return `Rechtsstand ${month}/${year}`;
}

/**
 * Resolves the version of a rule valid as of `asOf` (ISO date): the latest
 * `validFrom <= asOf` whose `validTo` (if any) is still open at `asOf`.
 */
export function getRule<T>(ruleSet: RuleSet<T>, asOf: string): ResolvedRule<T> {
  const applicable = [...ruleSet.versions]
    .filter((v) => v.validFrom <= asOf && (!v.validTo || asOf < v.validTo))
    .sort((a, b) => (a.validFrom < b.validFrom ? 1 : -1));

  const match = applicable[0];
  if (!match) {
    throw new RuleNotFoundError(ruleSet.key, asOf);
  }
  return {
    key: ruleSet.key,
    value: match.value,
    source: match.source,
    rechtsstand: formatRechtsstand(match.validFrom),
  };
}
