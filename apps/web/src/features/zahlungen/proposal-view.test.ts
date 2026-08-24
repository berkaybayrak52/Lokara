import { describe, expect, it } from 'vitest';

import {
  buildRows,
  groupOf,
  isDecidable,
  signalBreakdown,
  type DecisionValue,
  type OutcomeValue,
} from './proposal-view';

// Shapes are transcribed from the pinned M6-C3c contract (server payloads are
// snake_case on the wire and the view module passes cents and ISO strings
// through untouched). They are declared here so the fixture pins the contract
// rather than whatever the implementation happens to export.

type Signals = {
  iban: number;
  amount: number;
  code_or_surname: number;
  end_to_end: number;
  period: number;
};

type Candidate = {
  proposal_id: string;
  rank: number;
  receivable_id: string | null;
  renter_id: string | null;
  signals: Signals;
  confidence: number;
};

type Confirmation = {
  outcome: OutcomeValue;
  confirmed_by: string;
  confirmed_at: string;
};

type ProposalGroup = {
  transaction_id: string;
  decision: DecisionValue;
  reason_de: string | null;
  candidates: Candidate[];
  confirmation: Confirmation | null;
  ledger_entry_id: string | null;
  created_at: string;
};

type BankTransaction = {
  id: string;
  bank_account_id: string;
  provider_transaction_id: string;
  amount_cents: number;
  bank_booking_date: string;
  counterpart_name: string | null;
  purpose: string | null;
  is_potential_duplicate: boolean;
};

type Receivable = {
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
};

// `noUncheckedIndexedAccess` is on, so index access is funnelled through a
// helper that fails the test loudly instead of yielding `undefined`.
function at<T>(list: readonly T[], index: number): T {
  const value = list[index];
  if (value === undefined) {
    throw new Error(`expected an element at index ${index}, got none`);
  }
  return value;
}

function collectKeys(value: unknown, into: Set<string>): void {
  if (Array.isArray(value)) {
    for (const item of value) {
      collectKeys(item, into);
    }
    return;
  }
  if (value !== null && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      into.add(key);
      collectKeys(child, into);
    }
  }
}

// --- transactions ----------------------------------------------------------

const txAnna: BankTransaction = {
  id: 'tx-1001',
  bank_account_id: 'ba-01',
  provider_transaction_id: 'prov-1001',
  amount_cents: 108000,
  bank_booking_date: '2026-03-12',
  counterpart_name: 'Anna Müller',
  purpose: 'Miete Maerz 2026',
  is_potential_duplicate: false,
};

const txBernd: BankTransaction = {
  id: 'tx-1002',
  bank_account_id: 'ba-01',
  provider_transaction_id: 'prov-1002',
  amount_cents: 95000,
  bank_booking_date: '2026-03-11',
  counterpart_name: 'Bernd Schuster',
  purpose: 'Ueberweisung',
  is_potential_duplicate: false,
};

const txCarla: BankTransaction = {
  id: 'tx-1003',
  bank_account_id: 'ba-01',
  provider_transaction_id: 'prov-1003',
  amount_cents: 120000,
  bank_booking_date: '2026-03-10',
  counterpart_name: 'Carla Hoffmann',
  purpose: 'Miete 03/2026 LOK-4711',
  is_potential_duplicate: false,
};

const txDuplicate: BankTransaction = {
  id: 'tx-1004',
  bank_account_id: 'ba-01',
  provider_transaction_id: 'prov-1004',
  amount_cents: 108000,
  bank_booking_date: '2026-03-12',
  counterpart_name: 'Anna Müller',
  purpose: 'Miete Maerz 2026',
  is_potential_duplicate: true,
};

const txSelfPayer: BankTransaction = {
  id: 'tx-1005',
  bank_account_id: 'ba-01',
  provider_transaction_id: 'prov-1005',
  amount_cents: 42000,
  bank_booking_date: '2026-03-09',
  counterpart_name: 'Dieter Kraus',
  purpose: 'Nachzahlung Betriebskosten 2025',
  is_potential_duplicate: false,
};

// --- receivables -----------------------------------------------------------

const recAnnaMarch: Receivable = {
  id: 'rec-501',
  renter_id: 'renter-anna',
  tenancy_id: 'ten-77',
  source_type: 'RENT_SCHEDULE',
  source_id: 'sched-301',
  period: '2026-03',
  due_date: '2026-03-03',
  expected_cents: 108000,
  open_cents: 108000,
  status: 'OPEN',
  category: 'RENT',
};

const recBerndMarch: Receivable = {
  id: 'rec-502',
  renter_id: 'renter-bernd',
  tenancy_id: 'ten-78',
  source_type: 'RENT_SCHEDULE',
  source_id: 'sched-302',
  period: '2026-03',
  due_date: '2026-03-03',
  expected_cents: 95000,
  open_cents: 95000,
  status: 'OPEN',
  category: 'RENT',
};

// rec-503 is referenced by a candidate below but is deliberately never
// returned by GET /receivables, so the join has to survive the miss.

// --- candidates ------------------------------------------------------------

const candidateAnna: Candidate = {
  proposal_id: 'prop-9001',
  rank: 1,
  receivable_id: 'rec-501',
  renter_id: 'renter-anna',
  signals: { iban: 20, amount: 30, code_or_surname: 10, end_to_end: 0, period: 5 },
  confidence: 65,
};

const candidateBernd: Candidate = {
  proposal_id: 'prop-9002',
  rank: 2,
  receivable_id: 'rec-502',
  renter_id: 'renter-bernd',
  signals: { iban: 20, amount: 30, code_or_surname: 0, end_to_end: 0, period: 0 },
  confidence: 50,
};

// Uncapped signals add up to 125; the server caps confidence at 100.
const candidateCarlaCapped: Candidate = {
  proposal_id: 'prop-9003',
  rank: 1,
  receivable_id: 'rec-503',
  renter_id: 'renter-carla',
  signals: { iban: 60, amount: 30, code_or_surname: 15, end_to_end: 15, period: 5 },
  confidence: 100,
};

// The engine's "no candidate" evidence row: rank 1, both ids NULL.
const candidateNoMatch: Candidate = {
  proposal_id: 'prop-9004',
  rank: 1,
  receivable_id: null,
  renter_id: null,
  signals: { iban: 0, amount: 30, code_or_surname: 0, end_to_end: 0, period: 0 },
  confidence: 30,
};

const candidateDeduped: Candidate = {
  proposal_id: 'prop-9005',
  rank: 1,
  receivable_id: null,
  renter_id: null,
  signals: { iban: 0, amount: 0, code_or_surname: 0, end_to_end: 0, period: 0 },
  confidence: 0,
};

const candidateDecided: Candidate = {
  proposal_id: 'prop-9006',
  rank: 1,
  receivable_id: 'rec-502',
  renter_id: 'renter-bernd',
  signals: { iban: 20, amount: 30, code_or_surname: 10, end_to_end: 0, period: 5 },
  confidence: 65,
};

// --- proposal groups -------------------------------------------------------

const openReview: ProposalGroup = {
  transaction_id: 'tx-1001',
  decision: 'needs_review',
  reason_de: 'Mehrdeutige IBAN: zwei Mieter teilen dieses Konto.',
  candidates: [candidateAnna, candidateBernd],
  confirmation: null,
  ledger_entry_id: null,
  created_at: '2026-03-12T08:14:00Z',
};

const autoMatched: ProposalGroup = {
  transaction_id: 'tx-1003',
  decision: 'auto_match',
  reason_de: 'Eindeutige IBAN und exakter Betrag.',
  candidates: [candidateCarlaCapped],
  confirmation: null,
  ledger_entry_id: 'ledger-3001',
  created_at: '2026-03-10T06:02:00Z',
};

const unmatched: ProposalGroup = {
  transaction_id: 'tx-1002',
  decision: 'unmatched',
  reason_de: 'Keine Forderung erreicht die Pruefschwelle.',
  candidates: [candidateNoMatch],
  confirmation: null,
  ledger_entry_id: null,
  created_at: '2026-03-11T07:41:00Z',
};

const deduped: ProposalGroup = {
  transaction_id: 'tx-1004',
  decision: 'deduped',
  reason_de: 'Dublette zur Transaktion tx-1001.',
  candidates: [candidateDeduped],
  confirmation: null,
  ledger_entry_id: null,
  created_at: '2026-03-12T08:14:30Z',
};

const decidedReview: ProposalGroup = {
  transaction_id: 'tx-1005',
  decision: 'needs_review',
  reason_de: 'Betrag weicht von der offenen Forderung ab.',
  candidates: [candidateDecided],
  confirmation: {
    outcome: 'confirmed',
    confirmed_by: 'membership-emir',
    confirmed_at: '2026-03-13T09:30:00Z',
  },
  ledger_entry_id: 'ledger-3002',
  created_at: '2026-03-09T05:55:00Z',
};

// The transaction list never returns tx-9999 (e.g. it fell outside the page).
const orphanGroup: ProposalGroup = {
  transaction_id: 'tx-9999',
  decision: 'needs_review',
  reason_de: null,
  candidates: [],
  confirmation: null,
  ledger_entry_id: null,
  created_at: '2026-03-08T04:20:00Z',
};

const allTransactions: BankTransaction[] = [
  txAnna,
  txBernd,
  txCarla,
  txDuplicate,
  txSelfPayer,
];

const allReceivables: Receivable[] = [recAnnaMarch, recBerndMarch];

describe('groupOf', () => {
  it('puts an undecided needs_review group into the review bucket', () => {
    expect(groupOf(openReview)).toBe('needs_review');
  });

  it('moves a needs_review group to decided once a confirmation exists', () => {
    expect(groupOf(decidedReview)).toBe('decided');
    expect(
      groupOf({
        ...decidedReview,
        confirmation: {
          outcome: 'rejected',
          confirmed_by: 'membership-emir',
          confirmed_at: '2026-03-13T09:31:00Z',
        },
      }),
    ).toBe('decided');
    expect(
      groupOf({
        ...decidedReview,
        confirmation: {
          outcome: 'duplicate',
          confirmed_by: 'membership-emir',
          confirmed_at: '2026-03-13T09:32:00Z',
        },
      }),
    ).toBe('decided');
  });

  it('reports an auto_match group as auto_booked', () => {
    expect(groupOf(autoMatched)).toBe('auto_booked');
  });

  it('reports unmatched and deduped groups as no_action', () => {
    expect(groupOf(unmatched)).toBe('no_action');
    expect(groupOf(deduped)).toBe('no_action');
  });

  it('lets the decision win when an auto_match group carries a confirmation', () => {
    // The API cannot produce this today. If it ever does, the decision decides:
    // an already booked transaction must not reappear as review work.
    const contradictory: ProposalGroup = {
      ...autoMatched,
      confirmation: {
        outcome: 'confirmed',
        confirmed_by: 'membership-emir',
        confirmed_at: '2026-03-10T06:03:00Z',
      },
    };
    expect(groupOf(contradictory)).toBe('auto_booked');
  });
});

describe('isDecidable', () => {
  it('is true for an undecided needs_review group', () => {
    expect(isDecidable(openReview)).toBe(true);
  });

  it('is false once the needs_review group has been decided', () => {
    expect(isDecidable(decidedReview)).toBe(false);
  });

  it('is false for auto_match, unmatched and deduped groups', () => {
    expect(isDecidable(autoMatched)).toBe(false);
    expect(isDecidable(unmatched)).toBe(false);
    expect(isDecidable(deduped)).toBe(false);
  });

  it('agrees with groupOf on every group', () => {
    // The buttons read this single gate; it must never diverge from the bucket.
    for (const group of [openReview, autoMatched, unmatched, deduped, decidedReview, orphanGroup]) {
      expect(isDecidable(group)).toBe(groupOf(group) === 'needs_review');
    }
  });
});

describe('buildRows', () => {
  it('joins each group to its bank transaction and each candidate to its receivable', () => {
    const rows = buildRows({
      proposals: [openReview],
      transactions: allTransactions,
      receivables: allReceivables,
    });

    expect(rows).toHaveLength(1);
    const row = at(rows, 0);
    expect(row.transaction_id).toBe('tx-1001');
    expect(row.transaction).toEqual(txAnna);
    expect(row.decision).toBe('needs_review');
    expect(row.reason_de).toBe('Mehrdeutige IBAN: zwei Mieter teilen dieses Konto.');
    expect(row.candidates).toHaveLength(2);
    expect(at(row.candidates, 0).proposal_id).toBe('prop-9001');
    expect(at(row.candidates, 0).receivable).toEqual(recAnnaMarch);
    expect(at(row.candidates, 1).proposal_id).toBe('prop-9002');
    expect(at(row.candidates, 1).receivable).toEqual(recBerndMarch);
  });

  it('preserves group order and candidate rank order', () => {
    const rows = buildRows({
      proposals: [deduped, openReview, autoMatched, unmatched, decidedReview],
      transactions: allTransactions,
      receivables: allReceivables,
    });

    expect(rows.map((row) => row.transaction_id)).toEqual([
      'tx-1004',
      'tx-1001',
      'tx-1003',
      'tx-1002',
      'tx-1005',
    ]);
    expect(at(rows, 1).candidates.map((candidate) => candidate.rank)).toEqual([1, 2]);
    expect(at(rows, 1).candidates.map((candidate) => candidate.proposal_id)).toEqual([
      'prop-9001',
      'prop-9002',
    ]);
  });

  it('yields a null transaction when the group references an unknown transaction', () => {
    const rows = buildRows({
      proposals: [orphanGroup],
      transactions: allTransactions,
      receivables: allReceivables,
    });

    expect(rows).toHaveLength(1);
    expect(at(rows, 0).transaction).toBeNull();
    expect(at(rows, 0).transaction_id).toBe('tx-9999');
    expect(at(rows, 0).candidates).toEqual([]);
  });

  it('keeps the rank-1 evidence row that carries no receivable and no renter', () => {
    const rows = buildRows({
      proposals: [unmatched],
      transactions: allTransactions,
      receivables: allReceivables,
    });

    expect(rows).toHaveLength(1);
    const candidates = at(rows, 0).candidates;
    expect(candidates).toHaveLength(1);
    expect(at(candidates, 0).rank).toBe(1);
    expect(at(candidates, 0).receivable_id).toBeNull();
    expect(at(candidates, 0).renter_id).toBeNull();
    expect(at(candidates, 0).receivable).toBeNull();
  });

  it('yields a null receivable when the referenced receivable was not returned', () => {
    // rec-503 exists on the server but is not in this page of /receivables.
    const rows = buildRows({
      proposals: [autoMatched],
      transactions: allTransactions,
      receivables: allReceivables,
    });

    const candidates = at(rows, 0).candidates;
    expect(candidates).toHaveLength(1);
    expect(at(candidates, 0).receivable_id).toBe('rec-503');
    expect(at(candidates, 0).receivable).toBeNull();
  });

  it('does not throw when every lookup list is empty', () => {
    const rows = buildRows({
      proposals: [openReview, orphanGroup],
      transactions: [],
      receivables: [],
    });

    expect(rows).toHaveLength(2);
    expect(at(rows, 0).transaction).toBeNull();
    expect(at(rows, 0).candidates.map((candidate) => candidate.receivable)).toEqual([null, null]);
  });

  it('returns an empty list for an empty proposal list', () => {
    expect(buildRows({ proposals: [], transactions: allTransactions, receivables: [] })).toEqual([]);
  });

  it('never produces a renter name anywhere in the output', () => {
    // There is no route that resolves renter_id to a legal_name in this slice.
    // The only human-readable name in a row is the bank counterpart.
    const rows = buildRows({
      proposals: [openReview, autoMatched, unmatched, deduped, decidedReview, orphanGroup],
      transactions: allTransactions,
      receivables: allReceivables,
    });

    const keys = new Set<string>();
    collectKeys(rows, keys);
    expect([...keys].filter((key) => key.toLowerCase().includes('name')).sort()).toEqual([
      'counterpart_name',
    ]);
    expect(JSON.stringify(rows)).not.toContain('renter_name');
    expect(JSON.stringify(rows)).not.toContain('legal_name');
  });

  it('passes cents and ISO strings through untouched', () => {
    const rows = buildRows({
      proposals: [openReview],
      transactions: allTransactions,
      receivables: allReceivables,
    });

    const row = at(rows, 0);
    const transaction = row.transaction;
    expect(transaction).not.toBeNull();
    expect(transaction?.amount_cents).toBe(108000);
    expect(Number.isInteger(transaction?.amount_cents)).toBe(true);
    expect(transaction?.bank_booking_date).toBe('2026-03-12');
    expect(row.created_at).toBe('2026-03-12T08:14:00Z');

    const receivable = at(row.candidates, 0).receivable;
    expect(receivable?.expected_cents).toBe(108000);
    expect(receivable?.open_cents).toBe(108000);
    expect(Number.isInteger(receivable?.open_cents)).toBe(true);
    expect(receivable?.due_date).toBe('2026-03-03');
  });
});

describe('signalBreakdown', () => {
  it('returns the five signals in the fixed contract order', () => {
    expect(signalBreakdown(candidateAnna).map((part) => part.key)).toEqual([
      'iban',
      'amount',
      'code_or_surname',
      'end_to_end',
      'period',
    ]);
  });

  it('marks each signal as met with its weight in points', () => {
    expect(signalBreakdown(candidateAnna)).toEqual([
      { key: 'iban', met: true, points: 20 },
      { key: 'amount', met: true, points: 30 },
      { key: 'code_or_surname', met: true, points: 10 },
      { key: 'end_to_end', met: false, points: 0 },
      { key: 'period', met: true, points: 5 },
    ]);
  });

  it('reports every signal as unmet for a zero-confidence candidate', () => {
    const parts = signalBreakdown(candidateDeduped);
    expect(parts.every((part) => part.met === false)).toBe(true);
    expect(parts.every((part) => part.points === 0)).toBe(true);
  });

  it('sums to the candidate confidence below the cap', () => {
    const total = signalBreakdown(candidateAnna).reduce((sum, part) => sum + part.points, 0);
    expect(total).toBe(65);
    expect(total).toBe(candidateAnna.confidence);

    const berndTotal = signalBreakdown(candidateBernd).reduce((sum, part) => sum + part.points, 0);
    expect(berndTotal).toBe(50);
    expect(berndTotal).toBe(candidateBernd.confidence);
  });

  it('reports the uncapped points when the confidence is capped at 100', () => {
    const parts = signalBreakdown(candidateCarlaCapped);
    expect(parts).toEqual([
      { key: 'iban', met: true, points: 60 },
      { key: 'amount', met: true, points: 30 },
      { key: 'code_or_surname', met: true, points: 15 },
      { key: 'end_to_end', met: true, points: 15 },
      { key: 'period', met: true, points: 5 },
    ]);

    const total = parts.reduce((sum, part) => sum + part.points, 0);
    expect(total).toBe(125);
    expect(total).toBeGreaterThan(candidateCarlaCapped.confidence);
    expect(Math.min(100, total)).toBe(candidateCarlaCapped.confidence);
  });
});
