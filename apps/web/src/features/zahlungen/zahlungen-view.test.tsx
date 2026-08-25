import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api';
import type {
  BankTransactionOut,
  MatchProposalGroup,
  PaymentLedgerEntry,
  ReceivableOut,
} from '@/lib/contracts';

/**
 * Render guard for the Zahlungen screen (docs/15).
 *
 * Every asserted value below is derived from the M6-C3c contract and from
 * docs/15, never from reading what the components happen to emit. A render test
 * written against the implementation certifies the implementation's bugs.
 *
 * `apps/web/vitest.config.ts` runs `environment: 'node'`: no jsdom, no
 * testing-library. The assertions therefore run against static SSR markup, and
 * every property here is a presence/absence property, which is exactly what a
 * safety gate ("this control must be unreachable") needs to be.
 */

const queryState = vi.hoisted(() => ({
  proposals: [] as unknown[],
  transactions: [] as unknown[],
  receivables: [] as unknown[],
  ledger: [] as unknown[],
  decide: {
    isPending: false,
    isError: false,
    error: null as unknown,
    mutate: () => undefined,
  },
}));

vi.mock('./queries', () => ({
  useMatchProposals: () => ({
    data: { transactions: queryState.proposals },
    isPending: false,
    isError: false,
  }),
  useBankTransactions: () => ({
    data: { transactions: queryState.transactions },
    isPending: false,
    isError: false,
  }),
  useReceivables: () => ({
    data: { receivables: queryState.receivables },
    isPending: false,
    isError: false,
  }),
  usePaymentLedger: () => ({
    data: { entries: queryState.ledger },
    isPending: false,
    isError: false,
  }),
  useDecideMatch: () => queryState.decide,
}));

import { ZahlungenPage } from './zahlungen-page';

// ---------------------------------------------------------------------------
// Fixtures — shapes from the M6-C3c contract transcription.
// ---------------------------------------------------------------------------

type MatchCandidate = MatchProposalGroup['candidates'][number];
type MatchSignals = MatchCandidate['signals'];

/**
 * docs/15 § 4 weights. A signal value is 0 (not met) or exactly its weight.
 * `end_to_end` is listed at 15 but is inert: the engine returns 0 for every
 * candidate, so no fixture here may set it to 15.
 */
const WEIGHT = {
  uniqueIban: 60,
  ambiguousIban: 20,
  exactAmount: 30,
  paymentCode: 15,
  surname: 10,
  period: 5,
} as const;

const NO_SIGNALS: MatchSignals = {
  iban: 0,
  amount: 0,
  code_or_surname: 0,
  end_to_end: 0,
  period: 0,
};

/**
 * A renter is never named on this screen: no route resolves `renter_id` to a
 * legal name, and a bare id printed where a name belongs reads as one. This
 * value is deliberately distinctive so its absence cannot be an accident.
 */
const RENTER_ID = 'renter-8f31c0d2-DO-NOT-PRINT';

/** The server authors this sentence on 409; the client may only reprint it. */
const CONFLICT_DETAIL =
  'Für diesen Bankumsatz existiert bereits eine abweichende Entscheidung (Pruefkennung QX7-ZAHLUNG).';

/** The approved lifecycle-wide web disclaimer. */
const DISCLAIMER =
  'Lokara unterstützt Vermieter bei der rechtskonformen Verwaltung ihrer Objekte und ersetzt keine Rechts- oder Steuerberatung.';

const RECEIVABLE: ReceivableOut = {
  id: 'rec-1',
  renter_id: RENTER_ID,
  tenancy_id: 'tenancy-1',
  source_type: 'rent_schedule',
  source_id: null,
  period: '2026-03',
  due_date: '2026-03-03',
  expected_cents: 95000,
  open_cents: 95000,
  status: 'open',
  category: 'rent',
};

function transaction(id: string, over: Partial<BankTransactionOut> = {}): BankTransactionOut {
  return {
    id,
    bank_account_id: 'bank-account-1',
    provider_transaction_id: `provider-${id}`,
    amount_cents: 95000,
    bank_booking_date: '2026-03-04',
    counterpart_name: 'M. Kowalski',
    purpose: 'Miete 03/2026',
    is_potential_duplicate: false,
    ...over,
  };
}

function candidate(over: Partial<MatchCandidate> = {}): MatchCandidate {
  const signals = over.signals ?? NO_SIGNALS;
  const raw =
    signals.iban + signals.amount + signals.code_or_surname + signals.end_to_end + signals.period;
  return {
    proposal_id: `proposal-${over.rank ?? 1}`,
    rank: 1,
    receivable_id: RECEIVABLE.id,
    renter_id: RENTER_ID,
    confidence: Math.min(100, raw),
    ...over,
    signals,
  };
}

function group(over: Partial<MatchProposalGroup> = {}): MatchProposalGroup {
  return {
    transaction_id: 'txn-1',
    decision: 'needs_review',
    reason_de: 'Betrag und Zeitraum passen, die IBAN ist mehreren Mietern bekannt.',
    candidates: [
      candidate({
        signals: {
          iban: WEIGHT.ambiguousIban,
          amount: WEIGHT.exactAmount,
          code_or_surname: WEIGHT.surname,
          end_to_end: 0,
          period: WEIGHT.period,
        },
      }),
    ],
    confirmation: null,
    ledger_entry_id: null,
    created_at: '2026-03-04T08:00:00Z',
    ...over,
  };
}

const PAYMENT_ENTRY: PaymentLedgerEntry = {
  id: 'ledger-1',
  bank_transaction_id: 'txn-auto',
  match_proposal_id: 'proposal-auto',
  kind: 'payment',
  amount_cents: 95000,
  credit_cents: 0,
  ordering_version: 1,
  reverses_entry_id: null,
  created_at: '2026-03-05T09:00:00Z',
  allocations: [
    {
      id: 'allocation-1',
      receivable_id: RECEIVABLE.id,
      costs_cents: 0,
      interest_cents: 0,
      principal_cents: 95000,
      components: {
        base_rent_cents: 70000,
        nk_advance_cents: 18000,
        heating_advance_cents: 7000,
        garage_cents: 0,
      },
      resulting_status: 'settled',
      before: {
        open_costs_cents: 0,
        open_interest_cents: 0,
        open_principal_cents: 95000,
        open_cents: 95000,
        status: 'open',
      },
      after: {
        open_costs_cents: 0,
        open_interest_cents: 0,
        open_principal_cents: 0,
        open_cents: 0,
        status: 'settled',
      },
    },
  ],
};

const REVERSAL_ENTRY: PaymentLedgerEntry = {
  id: 'ledger-2',
  bank_transaction_id: 'txn-auto',
  match_proposal_id: 'proposal-auto',
  kind: 'reversal',
  amount_cents: -95000,
  credit_cents: 0,
  ordering_version: 2,
  reverses_entry_id: PAYMENT_ENTRY.id,
  created_at: '2026-03-07T09:00:00Z',
  allocations: [],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage(): string {
  return renderToStaticMarkup(
    <QueryClientProvider client={new QueryClient()}>
      <ZahlungenPage accountId="acc-1" />
    </QueryClientProvider>,
  );
}

function textOfAll(html: string, tag: 'button' | 'a'): string[] {
  const pattern = new RegExp(`<${tag}\\b[^>]*>([\\s\\S]*?)</${tag}>`, 'g');
  return [...html.matchAll(pattern)].map((match) =>
    (match[1] ?? '')
      .replace(/<[^>]*>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim(),
  );
}

/** The whole list entry carrying the End-to-End signal, however it is ordered. */
function endToEndEntry(html: string): string {
  const at = html.indexOf('End-to-End');
  expect(at, 'the signal breakdown must name the End-to-End signal').toBeGreaterThan(-1);
  const start = html.lastIndexOf('<li', at);
  const end = html.indexOf('</li>', at);
  return html.slice(start === -1 ? at : start, end === -1 ? html.length : end + '</li>'.length);
}

const DECISION_CONTROLS = ['Bestätigen', 'Ablehnen', 'Als Dublette markieren'] as const;

function populate(): void {
  queryState.proposals = [group()];
  queryState.transactions = [transaction('txn-1')];
  queryState.receivables = [RECEIVABLE];
  queryState.ledger = [REVERSAL_ENTRY, PAYMENT_ENTRY];
}

beforeEach(() => {
  queryState.proposals = [];
  queryState.transactions = [];
  queryState.receivables = [];
  queryState.ledger = [];
  queryState.decide = { isPending: false, isError: false, error: null, mutate: () => undefined };
});

// ---------------------------------------------------------------------------
// 1. A decision is final: the controls exist only for an open review.
// ---------------------------------------------------------------------------

describe('Zahlungen — decision controls', () => {
  it('offers all three decisions for an open Needs-Review proposal', () => {
    queryState.proposals = [group({ transaction_id: 'txn-1', confirmation: null })];
    queryState.transactions = [transaction('txn-1')];
    queryState.receivables = [RECEIVABLE];

    const labels = textOfAll(renderPage(), 'button');

    for (const control of DECISION_CONTROLS) {
      expect(labels).toContain(control);
    }
  });

  const UNDECIDABLE: { name: string; proposal: MatchProposalGroup }[] = [
    {
      name: 'an auto-matched proposal (the engine already booked it)',
      proposal: group({ decision: 'auto_match', ledger_entry_id: 'ledger-1' }),
    },
    {
      name: 'an unmatched proposal (nothing reached the review floor)',
      proposal: group({
        decision: 'unmatched',
        candidates: [candidate({ receivable_id: null, renter_id: null, signals: NO_SIGNALS })],
      }),
    },
    {
      name: 'a deduped proposal (the transaction is a duplicate)',
      proposal: group({ decision: 'deduped' }),
    },
    {
      name: 'a Needs-Review proposal that already carries a confirmation',
      proposal: group({
        confirmation: {
          outcome: 'confirmed',
          confirmed_by: 'membership-1',
          confirmed_at: '2026-03-06T10:00:00Z',
        },
        ledger_entry_id: 'ledger-1',
      }),
    },
  ];

  it.each(UNDECIDABLE)('offers no decision for $name', ({ proposal }) => {
    queryState.proposals = [proposal];
    queryState.transactions = [transaction(proposal.transaction_id)];
    queryState.receivables = [RECEIVABLE];

    const html = renderPage();
    const labels = textOfAll(html, 'button');

    for (const control of DECISION_CONTROLS) {
      // A second decision must be unreachable, not merely rejected later: the
      // first one is immutable and already wrote (or refused to write) a ledger
      // entry.
      expect(labels.some((label) => label.includes(control))).toBe(false);
      expect(html).not.toContain(control);
    }
  });
});

// ---------------------------------------------------------------------------
// 3. + 4. What the landlord is allowed to read.
// ---------------------------------------------------------------------------

describe('Zahlungen — footer and internal references', () => {
  it('carries the one approved disclaimer and no attestation wording', () => {
    populate();

    const html = renderPage();

    expect(html).toContain(DISCLAIMER);
    // "arbeitet rechtskonform" is a retired attestation: it claims the work on
    // this page was carried out in conformity with the law. The approved
    // sentence claimed what Lokara IS. It must not come back.
    expect(html).not.toContain('arbeitet rechtskonform');
  });

  it('leaks no internal reference into the landlord-facing page', () => {
    populate();

    const html = renderPage();

    expect(html).not.toContain('docs/');
    expect(html).not.toContain('verify-before-production');
    // Statutory text is not an internal reference — the § 4 check must not be
    // written so broadly that it would also reject this.
    expect(html).toContain('§§ 366, 367 BGB');
    expect(html).not.toContain('§ 4');
  });
});

// ---------------------------------------------------------------------------
// 5. The inert End-to-End signal.
// ---------------------------------------------------------------------------

describe('Zahlungen — signal breakdown', () => {
  it('shows the End-to-End signal as not yet evaluated, never as a missed criterion', () => {
    queryState.proposals = [
      group({
        candidates: [
          candidate({
            signals: {
              iban: WEIGHT.uniqueIban,
              amount: WEIGHT.exactAmount,
              code_or_surname: WEIGHT.paymentCode,
              end_to_end: 0,
              period: WEIGHT.period,
            },
          }),
        ],
      }),
    ];
    queryState.transactions = [transaction('txn-1')];
    queryState.receivables = [RECEIVABLE];

    const entry = endToEndEntry(renderPage());

    // docs/15 § 4 marks the signal inert and `matching-engine/scoring.py`
    // returns 0 for it unconditionally — it was never evaluated. Printing that
    // 0 as a score would assert a false negative about the payment.
    expect(entry).toContain('noch nicht ausgewertet');
    expect(entry).not.toMatch(/Punkte/);
  });
});

// ---------------------------------------------------------------------------
// 6. An empty state that does not imply everything is settled.
// ---------------------------------------------------------------------------

describe('Zahlungen — empty state', () => {
  it('says no matching run has happened and denies the "all assigned" reading', () => {
    queryState.proposals = [];
    queryState.transactions = [transaction('txn-1')];
    queryState.receivables = [RECEIVABLE];

    const html = renderPage();

    expect(html).toMatch(/noch kein[^<]{0,30}Abgleich/);
    // The failure mode is an empty list read as "everything is assigned". The
    // disclaiming clause is the property, not the surrounding wording.
    expect(html).toMatch(/bedeutet nicht, dass alle Zahlungen bereits zugeordnet/);
  });
});

// ---------------------------------------------------------------------------
// 7. A conflict is the server's sentence, verbatim.
// ---------------------------------------------------------------------------

describe('Zahlungen — decision conflict', () => {
  it('prints the 409 detail exactly as the server authored it', () => {
    queryState.proposals = [group()];
    queryState.transactions = [transaction('txn-1')];
    queryState.receivables = [RECEIVABLE];
    queryState.decide = {
      isPending: false,
      isError: true,
      error: new ApiError(409, '/a/acc-1/bank-transactions/txn-1/decision', CONFLICT_DETAIL),
      mutate: () => undefined,
    };

    const html = renderPage();

    expect(html).toContain(CONFLICT_DETAIL);
  });
});

// ---------------------------------------------------------------------------
// 8. The Zahlungsjournal is append-only (§ 147 AO).
// ---------------------------------------------------------------------------

describe('Zahlungen — journal', () => {
  it('renders booked entries without any edit, delete or reversal control', () => {
    populate();

    const html = renderPage();

    // Non-vacuity: the journal really rendered, including a reversal, which is
    // a record written by the server and not an action offered here.
    expect(html).toContain('Zahlungsjournal');
    expect(html).toContain('-950,00 €');

    const MUTATING = /bearbeiten|löschen|stornieren|ändern|entfernen|korrigieren|rückgängig/i;
    const controls = [...textOfAll(html, 'button'), ...textOfAll(html, 'a')];
    expect(controls.length).toBeGreaterThan(0);
    for (const label of controls) {
      expect(label).not.toMatch(MUTATING);
    }
  });
});

// ---------------------------------------------------------------------------
// 9. No renter identity.
// ---------------------------------------------------------------------------

describe('Zahlungen — renter identity', () => {
  it('identifies the payer by the bank counterpart and never by renter id', () => {
    populate();

    const html = renderPage();

    expect(html).toContain('M. Kowalski');
    // This slice resolves no renter name, so a bare id must not stand in for
    // one anywhere on the page.
    expect(html).not.toContain(RENTER_ID);
  });
});
