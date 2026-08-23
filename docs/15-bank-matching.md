# Bank matching — deterministic proposals and immutable settlement

**Status:** complete D2 transcription; approved and merged 20.08.2026

**Authoritative sources:**

- `berkay-work/Spec-Seiten/08 · Bank-Matching 3ac5fd42073181c3a63dd13b94ff4f57.md`
- the approved F03/E12 correction preserved in §§ 1, 4, 7–8 and the oracle

**Fixtures:** exactly thirteen executable cases, `BANKMATCH-F01`–`BANKMATCH-F13`, in
`packages/rules-store/tests/berkay_15_golden.py`

**Implementation status:** the pure matching engine is implemented in
`packages/matching-engine` (M6-C1), and all thirteen fixtures run through it as executable tests.
No receivable model, payment ledger, adapter rewrite or endpoint exists yet — that is M6-C2/C3.
The § 4 E2E signal is inert; see § 4 below.

This document owns the deterministic normalization, candidate scoring, decision and settlement
contract for incoming renter payments. Matching is a proposal mechanism. It does not create a
legal booking merely because a score is high. A payment affects a receivable only after an
Auto-Match allowed by this contract or an explicit user confirmation.

## 1. Source status, precedence and resolved gap

The complete original Page 08, the approved F03 contract preserved here, Rechtsstand-Register CSV
rows 169–181, the Page 08 section of Non-Goals V1 and the arithmetic audit were reconciled. The Page header promises exactly
`BANKMATCH-F01…F13`, but the original worked examples jumped from F02 to F04. The authoritative
correction resolves that omission: F03 is E12 and distinguishes a potential-duplicate Review from a
silent exact-ID re-import dedupe. This approved doc and its oracle control F03/E12; the original Page
controls the remaining method and cases.

The earlier prepared transcription correctly kept F03 as a missing-source sentinel while no
authority existed. That historical blocker is resolved by the approved correction: the sentinel is
replaced with its stated inputs and outcomes, without reconstructing a case from neighboring
examples. The oracle now contains exactly thirteen executable dictionaries.

The arithmetic audit confirms the arithmetic printed for the twelve original cases. The correction
supplies the thirteenth case and its own summation checks. Neither source clears any
`verify-before-production` flag. The CSV controls structured values, legal nature, source and flag;
the original Page and this approved contract supply the expanded method where the CSV row is shorthand. Emir approved
this transcription on 20.08.2026, and the slice was merged into `main` with a no-fast-forward merge.
No bank-matching, payment-ledger or finAPI M6 implementation is approved. M6-A/M6-B technical
advance/finalization archives do not change this contract.

## 2. Legal rules versus matching conventions

Matching identity is entirely a Lokara convention. The four checked BGB rows apply only after the
payment has been assigned. They must never be presented as legal support for the score or the
Auto-Match decision.

| CSV row | Rule/value | Nature and source | Flag · Rechtsstand |
| ---: | --- | --- | --- |
| 169 | no amount tolerance: exact, partial or overpayment | Konvention | `verify-before-production` · 07/2026 |
| 170 | within one debt: costs → interest → principal | Gesetz · § 367 BGB | `geprüft` · 07/2026 |
| 171 | Auto = unique IBAN; Review 40–79; Unmatched < 40 | Konvention | `verify-before-production` · 07/2026 |
| 172 | IBAN 60 / ambiguous 20; amount 30; code 15; E2E 15; surname 10; month 5 | Konvention | `verify-before-production` · 07/2026 |
| 173 | partial component split: `component × P / expected`, Largest Remainder | Konvention | `verify-before-production` · 07/2026 |
| 174 | without designation: due before not due, older first | Gesetz · § 366 Abs. 2 BGB | `geprüft` · 07/2026 |
| 175 | full payment fulfils the receivable | Gesetz · § 362 BGB | `geprüft` · 07/2026 |
| 176 | debtor's designation in purpose takes priority | Gesetz · § 366 Abs. 1 BGB | `geprüft` · 07/2026 |
| 177 | Page 01 Nachzahlung becomes an automatic receivable | Konvention | `verify-before-production` · 07/2026 |
| 178 | finAPI `isPotentialDuplicate` forces Review | Konvention · finAPI docs | `verify-before-production` · 07/2026 |
| 179 | learn IBAN only from a confirmed match | Konvention | `verify-before-production` · 07/2026 |
| 180 | provider float → cents by decimal commercial rounding | Konvention · finAPI docs | `verify-before-production` · 07/2026 |
| 181 | Auto-Match only for exactly one known IBAN owner | Konvention | `verify-before-production` · 07/2026 |

Every row's affected source is Page 08. The table names the external primary source where the CSV
has one; otherwise no external source is present. `geprüft` means the primary statutory text was
checked, not that a lawyer approved the product rule.

CSV row 171 is shorthand, not a general score-only Auto threshold. Page 08's binding decision says
a unique known IBAN may Auto-Match even at confidence 60 (`F04`, `F11`), while a shared IBAN may
never Auto-Match even at 65 (`F07`). A non-auto candidate at 40 or above is Review; below 40 is
Unmatched. A shared-IBAN candidate remains Review even if a future combination exceeds 79. These
thresholds remain flagged conventions.

## 3. Normalized input contracts

All normalized money is integer cents. Provider floats end at the adapter. All matching, splitting,
settlement and reversal arithmetic after import is integer-only and performs no approximate match.

### 3.1 Bank transaction

The adapter must normalize a provider transaction into this immutable record:

```text
BankTransaction
  id
  account_id
  bank_account_id
  provider_transaction_id
  amount_cents                 signed integer after Decimal ROUND_HALF_UP import
  bank_booking_date            controls due/not-due ordering
  finapi_booking_date
  value_date
  counterpart_iban?            nullable
  counterpart_name?            nullable, max 80
  purpose?                     nullable, max 2000
  end_to_end_reference?        nullable
  counterpart_mandate_reference? nullable
  bank_transaction_code?       nullable
  provider_type?               nullable
  is_potential_duplicate
```

Exact re-import identity is `(account_id, bank_account_id, provider_transaction_id)`. It creates no
second normalized transaction or ledger entry. `is_potential_duplicate = true` is different: keep
the transaction and force Review; never silently discard it. `bank_booking_date`, not
`finapi_booking_date`, decides whether a receivable is due. A provider `amount` string is parsed as
`Decimal`, multiplied by 100 and rounded `ROUND_HALF_UP`; binary-float arithmetic is forbidden.

Page 08 treats a negative amount or a SEPA-return code as a reversal. A positive amount enters
scoring. Zero is retained for import audit but ignored by matching.

### 3.2 Receivable

The source calls its renter field `tenant_id`; Lokara normalizes that name to `renter_id` and also
retains the tenancy that produced the debt:

```text
Receivable
  id, account_id, renter_id, tenancy_id
  source_type, source_id?      recurring rent, Page 01 statement, or guard handoff
  period                      YYYY-MM, or the statement period for NK-Nachzahlung
  due_date
  expected_cents
  open_cents                  0 <= open <= expected plus separately open costs/interest
  status                      open | partial | settled
  category                    rent | nk_nachzahlung
  principal_components        base_rent, nk_advance, heating_advance, garage
  open_costs_cents, open_interest_cents, open_principal_cents
```

The nominal components sum to `expected_cents`. The Page 01 handoff creates an
`nk_nachzahlung` receivable only for a positive finalized Saldo and copies that cent value exactly;
`F12` copies 24,500 cents. A purpose that names a period for which no receivable exists does not
invent one: the amount becomes renter credit after other valid allocation, as in `F08`.

### 3.3 Renter matching profile and IBAN history

```text
RenterMatchingProfile
  account_id, renter_id
  payment_code?
  normalized_surname
  known_ibans[]               derived from active IbanHistory rows

IbanHistory
  id, account_id, renter_id, normalized_iban
  valid_from, valid_to?
  learned_from_transaction_id
  confirmed_match_id
  confirmed_at, confirmed_by
```

An IBAN is optional. A non-null IBAN is learned only after a user confirms a Review proposal.
Null is never learned (`F09`). History is versioned rather than overwritten. Auto eligibility is
computed inside the account: the IBAN must have exactly one active renter mapping. If two active
renters share it, each receives the ambiguous signal and the result is Review (`F07`).

## 4. Candidate, score and decision contract

Candidates are only open or partial receivables belonging to renters in the transaction's
`account_id`. No query, learned IBAN or confirmation may cross the account boundary.

For each `(transaction, renter, receivable)` candidate, normalize comparison text to lowercase,
remove spaces and special characters, and test codes as substrings. Then calculate:

| Signal | Points |
| --- | ---: |
| known IBAN unique to one renter | 60 |
| known IBAN shared by more than one renter | 20 |
| `amount_cents == open_cents` | 30 |
| purpose contains payment code | 15 |
| otherwise purpose contains surname | 10 |
| E2E or mandate reference matches stored reference | 15 — **inert, see below** |
| purpose contains the receivable period token | 5 |

Code and surname are mutually exclusive; take 15 or 10, not both. Confidence is
`min(100, sum(signals))`. There is no amount tolerance.

The "stored reference" this table scores against is **named here and defined nowhere in § 3**:
neither `Receivable` (§ 3.2) nor `RenterMatchingProfile` (§ 3.3) carries such a field. No fixture
exercises the signal — index 3 is 0 in all thirteen cases — so the oracle cannot settle it either.
Binding it to any existing field would be an invented matching convention, and +15 is not
cosmetic: it lifts a candidate from 25 to 40, which is Unmatched to Review. The implemented engine
therefore returns 0 for this signal. The question is open in `FRAGEN-an-Berkay-05.md`; M6-C2 adds
the real field with the `receivable` table and makes the signal live. This does not affect the
§ 5.3 reversal lookup, which resolves an original match by E2E/mandate reference and is
source-backed and fixture-covered.

Decision order:

1. An exact provider-ID re-import is deduplicated.
2. A potential duplicate forces `Needs Review`, even with a unique known IBAN.
3. Exactly one renter with the unique-IBAN signal produces `Auto-Match`; amount affects allocation,
   not identity.
4. A shared IBAN never Auto-Matches.
5. Without Auto eligibility, confidence at least 40 produces `Needs Review`; below 40 is
   `Unmatched`.
6. Review ranking uses amount, then code, surname and E2E evidence. No amount is settled before
   confirmation.

The stored proposal contains the normalized transaction ID, candidate receivable and renter IDs,
all component signals, confidence, decision, applicable convention version and the reason an Auto
decision was allowed or demoted. Confirmation records the actor and time; it does not rewrite the
original proposal.

## 5. Settlement and payment-ledger contract

Scoring and settlement are separate. After Auto-Match or confirmation, allocate the signed cent
amount in this order.

### 5.1 Choose receivables

1. A purpose designation naming a period or receivable has priority under § 366 Abs. 1 BGB.
2. Without designation, use Page 08 FIFO: receivables due at `bank_booking_date` before not-due
   receivables, then older `due_date` before newer.
3. Within a selected debt, apply cents to open costs, then interest, then principal under § 367 BGB.
4. Exact payment settles the selected open amount. A partial payment reduces it and leaves
   `partial`. Overpayment repeats the order across further receivables; any final remainder becomes
   renter credit. It is not paid out by Lokara.

The statutory order in this section is independent from the scoring conventions in § 4. A high
confidence never changes § 366/§ 367 ordering.

### 5.2 Principal-component split

A full principal payment copies nominal components. For a partial principal payment `P`:

```text
raw_component = nominal_component * P / expected_cents
component_paid = whole-cent proportional share
reconcile the cent remainder by Largest Remainder
```

The reconciled components must sum exactly to `P`; the paid NK-advance component feeds the annual
actual-advance total used by Page 01. `F11` yields 78,704 / 13,889 / 7,407 cents and needs no final
cent redistribution. Page 08 does not specify the tie-break between equal fractional remainders;
that missing deterministic convention must be added to the authoritative source before a future
implementation claims the unexercised tie branch.

### 5.3 Immutable events and reversal

The payment ledger is append-only. It records the transaction, confirmation/Auto evidence,
allocations to debts and components, resulting credit, legal ordering version and timestamps.
`open_cents` and status may be projected for fast reads, but past allocation entries are never
edited or deleted.

A negative amount or return code enters the reversal path. Resolve the original match by E2E or
mandate reference; only then use the Page fallback `(IBAN, amount, date)`, within the same account.
Append compensating entries that reverse the original allocations exactly, restore the receivable
projection and emit `payment_returned` for the Page 05 guard. Do not rescore or create a replacement
positive payment. `F06` restores 108,000 cents and nets the payment ledger to zero.

## 6. Account-isolation and immutability requirements

- `BankTransaction`, `Receivable`, `RenterMatchingProfile`, `IbanHistory`, `MatchProposal`,
  confirmation and every payment-ledger row carry `account_id`.
- Every reference between account-scoped rows is a composite
  `(parent_id, account_id) → (id, account_id)` foreign key with RLS coverage.
- Candidate selection, IBAN uniqueness, duplicate detection, reversal lookup and confirmation are
  restricted to one account before any score is calculated.
- A provider transaction ID is unique only together with its account and bank-account identity.
- Legal/money events are immutable. Corrections and reversals append new linked entries; learned
  IBAN facts use `valid_from`/`valid_to` history.
- A match never moves money between renters. One confirmed transaction belongs to exactly one
  renter; no cross-renter current account exists.

## 7. Edge cases and exact fixture coverage

The oracle is data-only and imports no production module. Green checks prove transcription, not
current implementation.

| Fixture | Source case and required result |
| --- | --- |
| `BANKMATCH-F01` | unique IBAN; 95 points; Auto; designated July debt settled; 85,000 / 15,000 / 8,000 |
| `BANKMATCH-F02` | no known IBAN; exact amount + surname = 40; Review; zero assigned before confirmation |
| `BANKMATCH-F03` | unique IBAN, purpose “Miete Juli” and 108,000 open/paid; `isPotentialDuplicate` forces Review and zero assignment until decision; “Doublette” assigns zero, “echte Zahlung” delegates to F04 FIFO/credit; identical-ID re-import dedupes before scoring and leaves one 108,000 settlement |
| `BANKMATCH-F04` | unique IBAN at 60; Auto; FIFO settles 108,000 + 108,000 and creates 4,000 credit |
| `BANKMATCH-F05` | two candidates at 30; Unmatched; zero assigned |
| `BANKMATCH-F06` | −108,000 return reverses original E2E match; net zero; debt reopens at 108,000 |
| `BANKMATCH-F07` | shared IBAN candidates 65 / 50; Review ranks C then D; zero assigned |
| `BANKMATCH-F08` | designated August debt before due date; 95; Auto; 108,000 settled in advance |
| `BANKMATCH-F09` | null IBAN + exact amount + code = 45; Review; null is not learned |
| `BANKMATCH-F10` | decimal 1080.00 → 108,000; decimal 1080.005 → 108,001 cents |
| `BANKMATCH-F11` | 100,000 partial payment; 60; Auto; split 78,704 / 13,889 / 7,407; 8,000 open |
| `BANKMATCH-F12` | Page 01 24,500 Nachzahlung copied to receivable; designated and settled at 24,500 |
| `BANKMATCH-F13` | first payment 40 and Review; confirmed non-null IBAN learned; following month Auto |

Page 08 edge cases E1–E12 map to the named fixtures above. The approved F03 correction assigns E12 to
`BANKMATCH-F03` and keeps its two mechanisms separate: `isPotentialDuplicate` is a distinct
transaction that requires Review, while the same provider transaction `id` is the already processed
movement and is silently deduplicated before channel selection or scoring.

## 8. Source coverage ledger

| Source | Destination | Disposition |
| --- | --- | --- |
| Page 08 metadata and § 1 | §§ 0–1 | current; optional M6 sub-scope preserved |
| Page 08 § 2 | §§ 2, 5 | matching convention separated from §§ 362/366/367 settlement law |
| Page 08 § 3 transaction fields | § 3.1 | complete provider-to-normalized field mapping |
| Page 08 § 3 receivable/profile fields | §§ 3.2–3.3 | complete; `tenant_id` normalized to Lokara `renter_id` |
| Page 08 § 4 steps 1–5 | § 4 | channel, candidates, signals, confidence and decision |
| Page 08 § 4 step 6 | § 5 | designation, FIFO, § 367 order, status, overpayment and split |
| Page 08 reversal paragraph | § 5.3 | immutable compensating-event form |
| Page 08 § 5 E1–E12 | §§ 3–7 | all mapped; the approved correction assigns E12 to F03 |
| Page 08 § 6 | § 7 + oracle | twelve original examples transcribed exactly |
| Approved F03/E12 correction | §§ 1, 4, 7 + oracle | potential duplicate Review and same-ID dedupe remain separate |
| Page 08 § 7 | § 9 | complete out-of-scope transcription |
| CSV rows 169–181 | § 2 | all values, sources, natures, flags and Rechtsstand preserved |
| Non-Goals V1, Page 08 | § 9 | all six Page 08 exclusions preserved |
| `Anlagen/README-for-Emir.md` | §§ 1, 7 | arithmetic evidence for the twelve original cases retained; approved correction closes F03 |
| Historical correspondence | `docs/03` Appendix D | single retirement ledger; exact F03 correction disposition preserved |

## 9. Explicit non-goals

V1 does not pay out renter credit through PIS, execute SEPA direct debits, calculate late interest
or reminder fees, create a receivable for a nonexistent named period, net balances between renters,
categorize outgoing bank transactions/invoices, decide tax treatment or infer object identity from
the movement. Page 05 creates costs/interest that this contract may consume. Object context comes
from the confirmed renter/tenancy relationship. V1 is AIS-only; the renter pushes the payment.

## 10. Adapter and model status

`packages/adapters/src/lokara_adapters/bank.py` implements this contract as of M6-C2. It carries
the § 3.1 record in full — signed `amount_cents`, the three separate dates, the nullable
counterpart/reference/provider fields and `is_potential_duplicate` — and
`cents_from_provider_amount` does the Decimal ×100 `ROUND_HALF_UP` conversion, refusing `float` at
the boundary. `BANKMATCH-F10` is executed there rather than in the engine, because the conversion
is an import rule. `StubBankGateway` now honours its `bank_account_id`, so provider-ID uniqueness
and account isolation are provable rather than asserted. finAPI itself stays stubbed (`docs/01` D7).

`packages/db/src/lokara_db/models.py` carries the nine account-scoped tables of § 6 with migration
`0017`: `bank_account`, `bank_transaction`, `receivable`, `renter_matching_profile`,
`iban_history`, `match_proposal`, `match_confirmation`, `payment_ledger_entry` and
`payment_allocation`. RLS is ENABLEd and FORCEd on each with an isolation policy, every reference
is a composite `(id, account_id)` edge, and the payment-ledger tables are append-only by trigger.
`docs/02` § 6 holds the persisted shape.

M6-C2 is complete. `apps/api/src/lokara_api/routers/payments.py` carries the owner-scoped
endpoints — transaction import, the receivable and transaction lists, and the Page-01 handoff of
`F12`, which copies a finalized `RECEIVABLE` `StatementSettlement` into an `nk_nachzahlung`
receivable at exact cents and refuses to run twice for the same statement.

Two limits ship with it, both deliberate:

- **The Zahlungsfrist is asked for, never defaulted.** § 3.2 requires a `due_date`, but
  `docs/08` marks *Zahlungsfrist bei Nachzahlung* `verify-before-production` and the register is
  explicit — no statutory deadline exists, the claim falls due on receipt of a proper statement,
  and the customary 30 days is a `Konvention`. The handoff therefore takes the date from the
  caller and refuses without it rather than making that convention Lokara's answer.
- **The § 4 stored-reference signal remains inert.** `receivable.stored_reference` exists as a
  column so the field has a home; nothing writes it, and it stays that way until the source
  question in `FRAGEN-an-Berkay-05.md` is answered.

Migration `0018` limits the receivable component-sum check to `category = 'rent'`. An
`nk_nachzahlung` has no rent, garage or advance component, and § 5.2 makes the reason concrete:
the paid NK-advance component feeds the annual actual-advance total Page 01 consumes, so parking a
Nachzahlung in `nk_advance_cents` to satisfy an arithmetic check would double-count it as an
advance that was never paid as one. Page 08 gives no component split for `nk_nachzahlung`, so none
is invented.

M6-C3 remains open: the landlord *Zahlungen* screen, the three job entrypoints and this document's
implementation-status closure.

## 11. Approval and implementation boundary

All thirteen cases, register rows, model boundaries and correspondence coverage are fully
transcribed. Emir approved the transcription on 20.08.2026. The focused data-only checks may verify
source coverage and arithmetic, but they do not prove production bank-matching behavior or approve
any legal or product convention. The specification is merged and the pure matching engine (M6-C1) is
implemented against it; the payment ledger, persistence, finAPI adapter rewrite and endpoints
remain paused for M6-C2/C3, and the § 4 stored-reference signal stays inert until its source gap is
answered. The separate `docs/16` D2 transcription is approved and merged.
