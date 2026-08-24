/**
 * Pure view logic for the landlord Zahlungen screen (docs/15 § 4).
 *
 * No React, no network, no Zod: this module only shapes what the five payment
 * routes already returned. It joins by id, it never invents a row, and it never
 * touches money — cents and ISO strings pass through untouched, because the
 * de-scaling and formatting boundary is `@/lib/format`.
 *
 * Field names are snake_case on purpose. These payloads arrive snake_case from
 * `routers/payments.py` and `matching_service.py`; renaming them here would put
 * a second naming convention between the wire and the screen for no gain.
 */

export type DecisionValue = 'auto_match' | 'needs_review' | 'unmatched' | 'deduped';
export type OutcomeValue = 'confirmed' | 'rejected' | 'duplicate';

/**
 * What the landlord has to do with a transaction, which is not the same thing
 * as what the engine decided:
 * - `needs_review`  — open review work, and the only decidable state
 * - `decided`       — a review that has already been answered, now evidence
 * - `auto_booked`   — settled by the engine without a human decision
 * - `no_action`     — unmatched or deduplicated; nothing to answer
 */
export type ReviewGroup = 'needs_review' | 'decided' | 'auto_booked' | 'no_action';

export type SignalKey = 'iban' | 'amount' | 'code_or_surname' | 'end_to_end' | 'period';

export interface MatchSignals {
  iban: number;
  amount: number;
  code_or_surname: number;
  end_to_end: number;
  period: number;
}

export interface MatchCandidate {
  proposal_id: string;
  rank: number;
  /** NULL on the engine's "no candidate" evidence row. */
  receivable_id: string | null;
  renter_id: string | null;
  signals: MatchSignals;
  /** `min(100, sum(signals))` — the server already capped it. */
  confidence: number;
}

export interface MatchConfirmationValue {
  outcome: OutcomeValue;
  confirmed_by: string;
  confirmed_at: string;
}

export interface ProposalGroup {
  transaction_id: string;
  decision: DecisionValue;
  reason_de: string | null;
  candidates: readonly MatchCandidate[];
  confirmation: MatchConfirmationValue | null;
  ledger_entry_id: string | null;
  created_at: string;
}

export interface BankTransactionRow {
  id: string;
  bank_account_id: string;
  provider_transaction_id: string;
  amount_cents: number;
  bank_booking_date: string;
  counterpart_name: string | null;
  purpose: string | null;
  is_potential_duplicate: boolean;
}

export interface ReceivableRow {
  id: string;
  renter_id: string;
  tenancy_id: string;
  source_type: string;
  source_id: string | null;
  period: string;
  due_date: string;
  expected_cents: number;
  open_cents: number;
  status: string;
  category: string;
}

/**
 * A candidate joined to its receivable.
 *
 * The raw `signals` object is deliberately NOT carried over. It is replaced by
 * the derived `signalParts`, so a row can never be searched for a renter by one
 * of the signal field names, and so the screen reads the breakdown in the one
 * fixed docs/15 § 4 order instead of whatever key order the wire happened to
 * use. Derived fields are camelCase; everything passed through from the wire
 * keeps its snake_case name.
 */
export interface CandidateRow extends Omit<MatchCandidate, 'signals'> {
  /** null when `receivable_id` is null OR that receivable was not returned. */
  receivable: ReceivableRow | null;
  signalParts: SignalPart[];
}

export interface ProposalRow {
  transaction_id: string;
  /** null when the transaction list did not contain this id. */
  transaction: BankTransactionRow | null;
  decision: DecisionValue;
  reason_de: string | null;
  candidates: CandidateRow[];
  confirmation: MatchConfirmationValue | null;
  ledger_entry_id: string | null;
  created_at: string;
}

export interface SignalPart {
  key: SignalKey;
  met: boolean;
  points: number;
}

/** The docs/15 § 4 order, fixed so the breakdown reads the same on every row. */
const SIGNAL_ORDER: readonly SignalKey[] = [
  'iban',
  'amount',
  'code_or_surname',
  'end_to_end',
  'period',
];

/**
 * The two fields a bucket is decided from. Narrowed on purpose so a joined
 * `ProposalRow` answers the same question as the raw `ProposalGroup` — one
 * implementation, so the buttons and the section headings can never disagree.
 */
export type GroupState = Pick<ProposalGroup, 'decision' | 'confirmation'>;

/**
 * A confirmation only ever exists for a `needs_review` proposal, so the
 * decision is checked first: were the API ever to attach one to an already
 * booked transaction, that transaction must not reappear as review work.
 */
export function groupOf(group: GroupState): ReviewGroup {
  switch (group.decision) {
    case 'auto_match':
      return 'auto_booked';
    case 'unmatched':
    case 'deduped':
      return 'no_action';
    case 'needs_review':
      return group.confirmation === null ? 'needs_review' : 'decided';
  }
}

/**
 * The single gate the Bestätigen / Ablehnen / Dublette buttons read.
 *
 * A decision is final and immutable, so everything else on the screen is
 * read-only evidence: auto-booked, unmatched and deduplicated transactions have
 * nothing to answer, and an answered review would be a second decision.
 */
export function isDecidable(group: GroupState): boolean {
  return groupOf(group) === 'needs_review';
}

export function buildRows(input: {
  proposals: readonly ProposalGroup[];
  transactions: readonly BankTransactionRow[];
  receivables: readonly ReceivableRow[];
}): ProposalRow[] {
  const transactionById = new Map(input.transactions.map((row) => [row.id, row]));
  const receivableById = new Map(input.receivables.map((row) => [row.id, row]));

  // Order is the server's (newest first) and candidate order is rank order —
  // both are preserved rather than re-sorted, so the screen shows the ranking
  // the engine produced and not one the client invented.
  return input.proposals.map((group) => ({
    transaction_id: group.transaction_id,
    transaction: transactionById.get(group.transaction_id) ?? null,
    decision: group.decision,
    reason_de: group.reason_de,
    confirmation: group.confirmation,
    ledger_entry_id: group.ledger_entry_id,
    created_at: group.created_at,
    candidates: group.candidates.map((candidate) => ({
      proposal_id: candidate.proposal_id,
      rank: candidate.rank,
      receivable_id: candidate.receivable_id,
      renter_id: candidate.renter_id,
      confidence: candidate.confidence,
      signalParts: signalBreakdown(candidate),
      // A miss is null, never a fabricated placeholder. There is deliberately
      // no renter lookup: no route resolves renter_id to a legal name, and a
      // bare id printed where a name belongs would read as one.
      receivable:
        candidate.receivable_id === null
          ? null
          : (receivableById.get(candidate.receivable_id) ?? null),
    })),
  }));
}

const GERMAN_MONTHS = [
  'Januar',
  'Februar',
  'März',
  'April',
  'Mai',
  'Juni',
  'Juli',
  'August',
  'September',
  'Oktober',
  'November',
  'Dezember',
] as const;

/**
 * `period` for display: "2026-03" → "März 2026".
 *
 * `Receivable.period` is `YYYY-MM` for rent (docs/15 § 3.2) but explicitly
 * opaque — an NK-Nachzahlung may carry a free statement label instead. So the
 * field is never parsed for meaning and never throws: anything that is not a
 * `YYYY-MM` with a real month number is passed through unchanged rather than
 * guessed at, because a wrong month on a Forderung is worse than an ISO string.
 */
export function periodToGerman(period: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (match === null) return period;
  const [, year, month] = match;
  if (year === undefined || month === undefined) return period;
  const name = GERMAN_MONTHS[Number.parseInt(month, 10) - 1];
  return name === undefined ? period : `${name} ${year}`;
}

/**
 * The five docs/15 § 4 signals with the points each contributed.
 *
 * The points are the raw weights: their sum equals `confidence` only while it
 * stays below the cap. Above it the server reports 100 and the breakdown still
 * shows what was actually scored, because a breakdown silently scaled to match
 * a capped total would explain nothing.
 *
 * These weights are a Lokara convention (`verify-before-production`), not a
 * legal rule. The screen must present them as a decision aid only.
 */
export function signalBreakdown(candidate: MatchCandidate): SignalPart[] {
  return SIGNAL_ORDER.map((key) => {
    const points = candidate.signals[key];
    return { key, met: points > 0, points };
  });
}
