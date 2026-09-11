# Bank matching — deterministic proposals and immutable settlement

**Status:** approved Page-08 base merged 20.08.2026; Berkay's round-five decisions of 11.09.2026
are specified below but not yet implemented or fixture-covered

**Authoritative sources:**

- `berkay-work/Spec-Seiten/08 · Bank-Matching 3ac5fd42073181c3a63dd13b94ff4f57.md`
- the approved F03/E12 correction preserved in §§ 1, 4, 7–8 and the oracle

**Fixtures:** exactly thirteen executable cases, `BANKMATCH-F01`–`BANKMATCH-F13`, in
`packages/rules-store/tests/berkay_15_golden.py`

**Implementation status:** M6-C1 ships the pure matching engine and all thirteen fixtures run
through it. M6-C2 ships the normalized bank adapter, nine account-scoped bank/receivable/matching/
ledger tables and owner-scoped import/list/Page-01-handoff endpoints. M6-C3-0 closes the audited
database invariants in migration `0020`. M6-C3a's matching service, final migration `0021` and
exactly five owner APIs are technically complete, development-synchronized and locally merged into
`main`. C3b's scheduler port and three job entrypoints are technically complete and
locally merged into `main`, and so is C3c's landlord *Zahlungen* screen, which completes M6.
The shipped § 4 E2E signal is deliberately inert; see § 4 below. Berkay's round-five answer now
defines its two source fields, but the migration, engine fixture and screen change remain future
work. The C3c screen therefore still renders it as *noch nicht ausgewertet* rather than as an unmet
criterion.

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
The M6-C1/M6-C2/M6-C3-0/C3a implementation boundary is shipped on local `main`; finAPI remains
stubbed, the legal/product conventions retain their flags, and M6-A/M6-B technical
advance/finalization archives do not change this contract.

**Unresolved authority added by M6-C3b — the 180-day AIS consent window.** The authoritative
`berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv` contains **no** row for bank-account
consent, PSD2, SCA or AIS; a case-insensitive grep for `consent`, `PSD2`, `SCA`, `AIS`,
`Einwilligung` and `Zustimmung` matches exactly one row, W5 *Zustimmungs-/Wirksamkeits-/Klagefrist
Mieterhöhung*, which is unrelated. `AIS_CONSENT_MAX_DAYS = 180` in
`apps/api/src/lokara_api/jobs.py` is therefore a **Lokara `Konvention`**, flagged
`verify-before-production`, `Rechtsstand 08/2026`, citing PSD2 RTS Art. 10 (Commission Delegated
Regulation (EU) 2018/389, as amended) as an **unverified** primary source — the amending regulation
and the current wording of the renewal period were not checked against the primary text, so this
citation must not be repeated as settled law. It is not a legal deadline in this document and it
is not Berkay-confirmed.

Its use is deliberately narrow. The jobs **never default an expiry from it**: consent state is read
only from the stored `bank_account.consent_expires_at`, a `NULL` value means "no consent" rather
than "180 days from now", and no job writes that column. The constant is used solely as a ceiling
check — a stored expiry further than `AIS_CONSENT_MAX_DAYS` in the future is reported as the
`ConsentFinding` state `"exceeds_max_window"`, a report and nothing more. Nothing is refused,
shortened or deleted because of it, and no legal claim is made about how long a landlord's AIS
consent may run. Resolving this needs either a primary-source check of the applicable RTS article
or a register row; until then the flag stays visible.

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

Berkay's round-five answer supersedes the earlier per-Renter debt shape. A receivable belongs to
the **tenancy**, because multiple parties to one residential tenancy are jointly and severally
liable in the default case under §§ 421, 427 BGB: the creditor may demand the whole performance
from any one party, but only once overall. The target contract is:

```text
Receivable
  id, account_id, tenancy_id
  source_type, source_id?      recurring rent, Page 01 statement, or guard handoff
  period                      YYYY-MM, or the statement period for NK-Nachzahlung
  due_date
  expected_cents
  open_cents                  0 <= open <= expected plus separately open costs/interest
  status                      open | partial | settled
  category                    rent | nk_nachzahlung
  principal_components        base_rent, nk_advance, heating_advance, garage
  open_costs_cents, open_interest_cents, open_principal_cents
  e2e_reference?              only when Lokara generated the collection
```

The nominal components sum to `expected_cents`. The Page 01 handoff creates an
`nk_nachzahlung` receivable only for a positive finalized Saldo and copies that cent value exactly;
`F12` copies 24,500 cents. A purpose that names a period for which no receivable exists does not
invent one: the amount becomes renter credit after other valid allocation, as in `F08`.

Candidate identity is formed by joining every `TenancyParty` of the receivable's tenancy. In
Lokara's schema, the legal debtor party is the account-scoped `Renter`; `Person` is only the
optional global login identity. Berkay's phrase “IBAN history remains per person” therefore
normalizes to the existing `IbanHistory.renter_id`, not `person_id`, so bank matching never depends
on M10 portal activation. Payments from different joint Renter parties can settle the same debt.
One party's payment reduces the single receivable for all parties. The current schema still carries
`receivable.renter_id`; the existing 409 refusal for multi-party statement handoff remains mandatory
until a migration removes that edge. Do not add a uniqueness or check constraint that would make an
expressly agreed partial-debt model impossible later; § 427 applies only “im Zweifel”.

### 3.3 Renter matching profile and IBAN history

```text
RenterMatchingProfile
  account_id, renter_id
  payment_code?
  sepa_mandate_reference?     unique within the account; stable for the tenancy
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
Null is never learned (`F09`). History is versioned rather than overwritten and belongs to the
paying Renter party. Auto eligibility is computed inside the account: the IBAN must have exactly
one active Renter mapping. If two active parties share it, each receives the ambiguous signal and
the result is Review (`F07`). This deliberately preserves the current account-scoped Renter foreign
key while `Receivable` moves from one Renter to the tenancy.

The mandate reference is set by the creditor through Lokara and proves identity. The receivable
E2E reference proves identity plus debt only when Lokara generated the debit. A payer-supplied E2E
value such as `NOTPROVIDED` is not stored as trusted receivable evidence.

## 4. Candidate, score and decision contract

Candidates are only open or partial receivables whose tenancy and all joined parties belong to the
transaction's `account_id`. No query, learned IBAN or confirmation may cross the account boundary.

For each `(transaction, renter, receivable)` candidate, normalize comparison text to lowercase,
remove spaces and special characters, and test codes as substrings. Then calculate:

| Signal | Points |
| --- | ---: |
| known IBAN unique to one renter | 60 |
| known IBAN shared by more than one renter | 20 |
| `amount_cents == open_cents` | 30 |
| purpose contains payment code | 15 |
| otherwise purpose contains surname | 10 |
| E2E matches `Receivable.e2e_reference`, or mandate reference matches `RenterMatchingProfile.sepa_mandate_reference` | 15 |
| purpose contains the receivable period token | 5 |

Code and surname are mutually exclusive; take 15 or 10, not both. Confidence is
`min(100, sum(signals))`. There is no amount tolerance.

The two structured-reference checks are mutually exclusive: together they contribute at most 15,
never 30, because they prove the same identity fact. A mandate match alone earns 15. The structured
reference signal is additive to a payment code found in the purpose because those are independent
pieces of evidence. Code and surname remain mutually exclusive. Missing reference fields contribute
zero and are the normal legacy state.

This is a Lokara `Konvention`, Rechtsstand 09/2026, `verify-before-production`, like the other
matching weights. The thresholds 40/79 and all other weights remain unchanged. The shipped engine
still returns zero for this signal until one new fixture per reference field and the two persistence
fields exist. This does not affect the § 5.3 reversal lookup, which resolves an original match by
E2E/mandate reference and is already source-backed and fixture-covered.

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
cent redistribution. Berkay's round-five answer fixes this versioned convention for equal
remainders:

```text
TIE_BREAK_ORDER = [base_rent, nk_advance, heating_advance, garage]
```

Assign each remaining cent to the earliest tied component in this order; if more than one cent
remains, traverse again from the start. `TieBreakUnspecifiedError` remains only for an unknown
component absent from the list. The shipped engine still refuses an ordinary equal-remainder tie;
a new fixture with two equal nominal components and an odd partial payment must reach this branch
before implementation changes.

This order is a `geprüft` Lokara `Konvention`, Rechtsstand 09/2026. `base_rent` comes first because
an avoidable residual there is the least renter-friendly direction in arrears handling; § 543 Abs.
2 BGB supports only that direction, not the cent order itself. `nk_advance` precedes
`heating_advance` because it feeds the Page-01 annual total, and `garage` is last because it has no
follow-on annual calculation. Table or contract-column order never decides a tie.

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

### 5.3a Round-five credit, rejection and identity decisions — specified, not implemented

An overpayment remainder is an unused credit of the same tenancy. It remains immutable ledger
evidence until the owner either pays it outside V1 or expressly offsets it. Lokara never offsets it
automatically: §§ 387, 388 BGB require an eligible counterclaim and an offset declaration. When a
new receivable becomes due, the *Zahlungen* screen offers exactly this owner action:

```text
Guthaben verrechnen (<Betrag>)
```

The action is never preselected or automatic. One click is the owner's declaration and appends a
separate ledger entry with actor and time. It never rewrites the original payment or credit.

The reminder path must account for unused credit even before that action. A receivable fully
covered by unused credit of the same tenancy produces no reminder and instead shows:

```text
offenes Guthaben deckt diese Forderung — bitte verrechnen oder auszahlen
```

For partial coverage, only the uncovered remainder may enter reminder output and the available
credit is stated in the reminder text. This reminder suppression is a Lokara `Konvention`,
Rechtsstand 09/2026, `verify-before-production`; the declaration requirement is law and `geprüft`.
Payout remains outside V1; credit neither expires nor is written off.

A final rejection stays append-only, settles nothing and leaves the receivable unchanged. It may be
evaluated again only after one actual input event: a receivable is created or becomes due, an IBAN
is learned through another confirmed assignment, a matching profile changes, or a tenancy is
created or changes. Each re-evaluation is a new proposal run with its own ranks; the rejected run is
never overwritten or deleted. There is no user-triggered rerun on unchanged inputs.

The owner never chooses a receivable. Under § 366 Abs. 1 BGB, the debtor makes a payment
designation; without one the statutory § 366 Abs. 2 order applies, followed by § 367. The decision
endpoint may instead accept these two optional input corrections:

```text
identity_correction: { tenancy_id, reason }
  A factual correction identifying the tenancy that made the payment. The tenancy must belong to
  the URL account. Append as MANUAL_IDENTITY with actor, time and mandatory reason.

debtor_designation: { text, quelle, datum }
  Evidence of a designation the debtor communicated outside the purpose, for example by telephone,
  e-mail or letter. All three fields are mandatory. Append with visible provenance as a debtor
  designation under § 366 Abs. 1 BGB.
```

After either input, the unchanged § 366/§ 367 engine chooses the debt and component allocation. A
free-form owner assignment to a selected receivable is forbidden. The statutory restriction is
`geprüft`; the identity-correction and external-designation evidence shapes are Lokara
`Konvention`, Rechtsstand 09/2026.

### 5.4 M6-C3a persistence and service boundary

**Status:** technically complete, development-synchronized and locally merged into `main`. The
final amended `0021` is verified from the disposable `lokara_c3a_check` database, and development
matches its exact catalog after one validated transactional hand-delta. Evidence counts and all 68
legacy Auto confirmations remain unchanged.
This section does not change
the Page-08 calculation rules or their `Rechtsstand 07/2026`. It defines how C3a persists and
exposes the already-approved engine result.

One bank transaction has one immutable proposal run. The service locks the transaction before
processing; a repeated or concurrent call returns the stored run and may create at most one ledger
result. Every engine candidate is stored as one `MatchProposal` with a deterministic rank unique
inside the transaction. An Unmatched result with no candidate is still auditable: it receives one
ranked evidence row whose receivable and renter are null. Existing proposal rows are backfilled
deterministically when migration `0021` adds the rank. Before future-only triggers are installed,
the migration validates every backfilled transaction group and fails rather than rewriting evidence
if ranks are not contiguous from 1 or decision, German reason or convention version differs.

That paragraph describes the shipped C3a model. The round-five target permits multiple immutable
runs for one transaction only after an input event listed in § 5.3a. The migration must give each
run its own identity and rank scope while preserving the complete old run; it must not loosen
idempotency for unchanged inputs.

Candidate selection joins only `open` or `partial` receivables to a matching profile in the same
account. Active IBAN ownership comes only from `IbanHistory.valid_to IS NULL`. The database keeps
its uppercase decisions; the engine and API keep their approved lowercase values. The service
translates between them and does not widen the database CHECK.

A positive `AUTO_MATCH` settles immediately. A `NEEDS_REVIEW` or `UNMATCHED` proposal moves zero
cents. A final `CONFIRMED` review settles only the engine's rank-1 candidate; a caller cannot name
another receivable. Final `REJECTED` and `DUPLICATE` decisions preserve evidence and settle
nothing. Repeating the same final decision is idempotent; attempting a different later outcome is
a conflict. A non-null IBAN is learned only after explicit confirmation, with the confirmation
timestamp as `valid_from`, and an already-active mapping is not duplicated.

Every new `PAYMENT` ledger row must cite either an `AUTO_MATCH` proposal or a
`NEEDS_REVIEW` proposal whose decision row is `CONFIRMED`. A rejection, duplicate, unmatched or
unconfirmed review can never book money. This evidence check runs after the row operation so a
foreign-account insert reaches its RLS `WITH CHECK` policy before a parent lookup can mask it.

For every payment, at deferred constraint time:

```text
assigned_cents = sum(costs_cents + interest_cents + principal_cents)
credit_cents = amount_cents - assigned_cents
```

A reversal has zero credit. Each new allocation stores nullable before/after receivable projection
snapshots sufficient to reconstruct the engine result: open costs, interest and principal, total
open cents, and status. New service writes always populate a complete pair. Existing legacy rows
remain nullable for migration compatibility, but an incomplete legacy snapshot cannot be reversed
automatically.

A negative movement uses the engine reversal path and appends one compensating ledger entry. It
restores the recorded projections and emits `payment_returned`. The complete operation is refused
and rolled back for an ambiguous original, a partial return, missing or incomplete legacy
snapshots, or a later allocation that makes the stored after-snapshot no longer equal the current
projection. The currently shipped Largest-Remainder tie likewise raises a conflict and rolls back
the whole operation; the round-five `TIE_BREAK_ORDER` is specified but not yet implemented.
Zero-value movements stay as imported evidence and create neither a proposal nor a ledger row.

### 5.5 M6-C3a owner API

C3a adds exactly five owner-scoped capabilities under `/a/{account_id}`:

1. `PUT /renters/{renter_id}/matching-profile` normalizes and upserts surname plus an optional
   payment code.
2. `POST /bank-transactions/{transaction_id}/match` runs or returns the immutable proposal run.
3. `GET /match-proposals` returns transaction-grouped German reasons, lowercase decisions, ranked
   candidates, signals, confidence, confirmation and ledger reference.
4. `POST /bank-transactions/{transaction_id}/decision` records the final `confirmed`, `rejected`
   or `duplicate` outcome. The round-five target request also permits `identity_correction` and
   `debtor_designation` exactly as specified in § 5.3a; it never accepts a receivable choice.
5. `GET /payment-ledger` returns immutable payments, reversals, credit and before/after allocation
   snapshots newest first.

Every endpoint requires `OWNER` membership in the URL account. An employee and an owner of a
different account cannot read, decide or book these rows. Missing resources and conflicts use
German 404/409 messages. C3a intentionally adds no pagination and does not change the existing
generic owner-denial copy.

### 5.6 M6-C3b scheduled jobs and the scheduler boundary

**Status:** technically complete and locally merged into `main`, 24.08.2026. It changes no
Page-08 calculation rule and no `Rechtsstand 07/2026` value. Every decision, score and cent still
comes from §§ 3–5.

C3b adds three job entrypoints in `apps/api/src/lokara_api/jobs.py` and one scheduler port in
`packages/adapters/src/lokara_adapters/scheduler.py`. It adds no endpoint, no engine rule and no
convention.

**The three jobs.**

1. `sync_bank_transactions(session, *, account_id, window_from, window_to, gateway, now) ->
   SyncResult`. Per connected bank account it pulls the § 3.1 window through the `BankGateway`
   port, stores what is new, then runs § 4 matching over what it stored. `SyncResult` carries
   `account_id` and a `bank_accounts` tuple of `BankAccountSyncResult`, sorted by
   `bank_account_id`. Each result carries `skipped_reason` (`None`, `"consent_missing"` or
   `"consent_expired"`), `imported`, `skipped_as_duplicate`, `auto_matched`, `needs_review`,
   `unmatched`, `deduped`, `reversed_payments`, `settled` and a `refused` tuple of `JobRefusal`
   (`bank_transaction_id`, `reason`).
2. `expire_bank_consents(session, *, account_id, now) -> tuple[ConsentFinding, ...]`. It reports
   only. A `ConsentFinding` carries `bank_account_id`, `display_name`, `state` (`"missing"`,
   `"expired"` or `"exceeds_max_window"`) and `expires_at`.
3. `watch_deadlines(session, *, account_id, today, now) -> DeadlineWatchResult`. It reports only.
   The result carries `overdue_receivables` — `OverdueReceivable` rows of `receivable_id`,
   `renter_id`, `period`, `due_date`, `days_overdue` and `open_cents`, sorted by
   `(due_date, receivable_id)` — and the same `consent_findings` tuple.

`run_for_accounts(engine, account_ids, job) -> tuple[T, ...]` runs one job per id and returns one
result per id, in the order given.

**Time is an input, never the clock.** `today` and `now` are parameters on every job. No job calls
`datetime.now()` or `date.today()`. A job whose result depends on the wall clock is not a golden
fixture, and a § 11 EStG payment date that shifts with the runner's timezone is a defect that
reaches a statement. Naive (timezone-unaware) datetimes are refused rather than assumed to be UTC.

**One account per run.** Every job takes an explicit `account_id` and reads through one
account-scoped session; `run_for_accounts` opens one per id, through `deps.job_account_session`,
and never shares a transaction across accounts. The session boundary stays in `deps.py` because
`scripts/check_pre_context_reads.py` requires it — a job is not an exception to that rule, and the
first implementation of `run_for_accounts` failed that gate for calling `account_scoped_session`
directly. `job_account_session` additionally refuses a role that bypasses RLS: the engine is a
parameter, the owner `DIRECT_URL` engine bypasses FORCEd RLS, and `run_match` resolves its scope
from the row it found — so a job wired to that engine would settle across accounts with no error
anywhere. C3b adds **no** pre-context read: `app_bootstrap_contexts(text)` remains the only one
(`CLAUDE.md` § 3.3), and `scripts/check_pre_context_reads.py` is unchanged and green.
A scheduled job has no HTTP request and no membership behind it, so the account context is carried
by the caller, not discovered by the job.

**Import moves out of the router.** The transaction-import loop currently inlined in
`apps/api/src/lokara_api/routers/payments.py` becomes `bank_sync.import_transactions(...) ->
ImportOutcome` (`imported`, `skipped_as_duplicate`, `imported_transaction_ids`), so the endpoint
and the job share one import path rather than two drifting copies. The § 3.1 distinction is
unchanged: an exact `provider_transaction_id` re-import is skipped silently and creates no second
row, while `is_potential_duplicate` keeps its transaction and forces Review.

**Matching runs inside sync, and § 5.4 still decides.** Sync is two phases: it imports from every
connected bank account first, then matches the merged result in
`(bank_booking_date, provider_transaction_id)` order, so a run is reproducible and § 5.1's due
before not-due ordering sees payments in the order the bank booked them. The phases are separate
for a reason — § 5.1 settles a renter's receivables across *all* of their payments, and a renter's
rent and garage may arrive on two different accounts, so matching one bank account to completion
before opening the next would order settlement by `bank_account_id` first and only then by date.
`apps/api/tests/test_m6c3b_jobs.py` pins that with a fixture rather than a comment: one renter is
paid twice, the earlier booking sits on the bank account whose id sorts later, and the asserted
allocations differ between the two orders. A positive `AUTO_MATCH`
therefore settles on a schedule instead of on a click — the decision, the § 367 order and the
split are exactly the ones § 5 already approved. A `NEEDS_REVIEW` or `UNMATCHED` result still
moves zero cents; nothing in C3b confirms a proposal, and no schedule may stand in for the user
decision § 5.4 requires. Each `run_match` runs inside a `session.begin_nested()` SAVEPOINT: one
transaction whose match refuses (an ambiguous reversal, a Largest-Remainder tie, an incomplete
legacy snapshot) is recorded in `refused` and rolled back alone, without discarding the imports
and settlements of the rest of the run.

The SAVEPOINT alone does not achieve that, and the first implementation did not. Migration `0021`
declares `match_proposal_run_consistency`, `payment_ledger_reconciliation` and
`payment_allocation_reconciliation` `DEFERRABLE INITIALLY DEFERRED`, because a settlement inserts
its ledger entry before its allocations and is consistent only once both are in. Under C3a one
request was one `run_match` was one transaction, so the deferred check ran at the same COMMIT. A
job matches many transactions in one transaction, so a violation would have surfaced at the outer
COMMIT — discarding every import and settlement of the whole run, the exact opposite of what this
paragraph promises, and reported as `settled` before it was checked. Each savepoint therefore
issues `SET CONSTRAINTS ALL IMMEDIATE` after its `run_match` and restores `ALL DEFERRED`, and an
`IntegrityError` is refused like any other refusal. Exactly those three constraints are deferrable
in this schema, so `ALL` names them and nothing else.

**Consent is a precondition of the pull, not of the data.** `import_transactions` refuses to call
the gateway when the bank account's `consent_expires_at` is `NULL` or `<= now`, raising
`ConsentExpiredError("consent_missing")` or `ConsentExpiredError("consent_expired")`; sync records
that as the bank account's `skipped_reason` and imports nothing for it. Reading a landlord's
account without live consent is the one thing an AIS integration must not do, and a stub is not an
excuse to build the habit.

**"Cleanup" never deletes a bank transaction.** `expire_bank_consents` stops future pulls. It does
not delete, redact or rewrite a `bank_transaction`, a proposal, a confirmation or a ledger row:
§ 6 and § 147 AO make those append-only, and an expired consent changes what may be fetched next,
never what was already booked. There is no consent-driven deletion path in Lokara.

**The watcher reports facts and applies no guard rule.** `watch_deadlines` reads overdue
receivables and consent state and returns them. It applies no `docs/12` guard rule, no threshold,
no warning copy, no severity and no escalation ladder, and it writes nothing — no guard row, no
reminder, no notification, no email. `days_overdue` is `today - due_date` in whole days and
`open_cents` is the stored open amount; both are facts already in the database. § 9 keeps late
interest and reminder fees out of V1, and the `docs/12` guard conventions are not settled here.
Wiring these facts into the `docs/12` Guard/Wächter mechanism is a later slice with its own
transcription.

**Open gap: account enumeration.** `run_for_accounts` is given its account ids. Nothing in C3b
discovers them, because the only way to list accounts before account context exists is a second
pre-context read, and `CLAUDE.md` § 3.3 permits exactly one. A real scheduler must therefore learn
its account ids from its caller — an operator-supplied list, a per-account trigger, or a
deliberately designed and least-privileged enumeration function. Closing this needs a boundary
decision recorded in `docs/02` and `scripts/check_pre_context_reads.py`, not a convenience query.
Until it is made, C3b's jobs are callable but not self-scheduling.

**No runner is installed.** Redis, Arq and Celery stay uninstalled (`docs/01` D7). `SchedulerPort`
is a Protocol with `register(job)` and `due_jobs(now)`; `ScheduledJob` is a frozen
`(name, account_id, interval_days, last_run_at)` record; `StubScheduler` is the only
implementation. It refuses `interval_days < 1` and naive datetimes with `ValueError`, replaces an
entry registered again under the same `(name, account_id)`, returns due jobs sorted by
`(name, account_id)`, treats `last_run_at is None` as due, and **executes nothing** — `due_jobs`
is a query with no side effect. The port exists so the process boundary is designed before a queue
is chosen, not so a queue can be smuggled in.

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
- A match never moves money between tenancies. One confirmed transaction belongs to exactly one
  tenancy; multiple parties may supply identity evidence for that one tenancy debt.

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

Round five requires additional executable coverage without rewriting `BANKMATCH-F01…F13`: one
equal-remainder case that proves `TIE_BREAK_ORDER`, one mandate-reference case, one Lokara-issued
E2E-reference case, tenancy-wide joint-debtor settlement, explicit credit offset, full/partial
reminder suppression, event-triggered re-evaluation, identity correction and documented debtor
designation. Those fixtures do not exist yet, so none of these target rules is claimed as shipped.

## 8. Source coverage ledger

| Source | Destination | Disposition |
| --- | --- | --- |
| Page 08 metadata and § 1 | §§ 0–1 | current; optional M6 sub-scope preserved |
| Page 08 § 2 | §§ 2, 5 | matching convention separated from §§ 362/366/367 settlement law |
| Page 08 § 3 transaction fields | § 3.1 | complete provider-to-normalized field mapping |
| Page 08 § 3 receivable/profile fields | §§ 3.2–3.3 | original per-Renter shape preserved historically; round five supersedes the target with `Receivable.tenancy_id` and adds mandate/E2E fields |
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
| Berkay round-five answer, 11.09.2026, §§ 4–5 | §§ 2–7 and § 11 | tie-break, stored references, tenancy debt, credit handling, event-triggered re-evaluation and identity/designation evidence specified; implementation and new fixtures pending |

## 9. Explicit non-goals

V1 does not pay out renter credit through PIS, execute SEPA direct debits, calculate late interest
or reminder fees, create a receivable for a nonexistent named period, net balances between
tenancies, let an owner freely choose a debt, categorize outgoing bank transactions/invoices,
decide tax treatment or infer object identity without recorded evidence. Page 05 creates
costs/interest that this contract may consume. Object context comes from the confirmed tenancy
relationship. V1 is AIS-only; the renter pushes the payment.

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

Migration `0019` carries the invariants a boundary audit of 23.08.2026 found `0017` had left to
the application: § 6's "a match never moves money between renters" is now four parent-scope
triggers rather than a convention; an allocation cannot exceed the cents its ledger entry carried
and its components cannot be negative; a `REVERSAL` must be negative, must name what it reverses
and may be filed once, so `F06` can only net to zero; § 3.3's confirmation requirement for a
learned IBAN is a constraint and the row is versioned rather than rewritable; and
`bank_transaction`, `match_proposal` and `match_confirmation` are append-only, as § 4 and § 147 AO
already said they were.

Migration `0020` repairs `0019`. A second boundary audit on 23.08.2026 found that the fourth
parent-scope trigger `docs/02` § 6 documents had never been written — an allocation could still
settle another renter's debt, which is the one rule § 6 states outright — and that three of
`0019`'s constraints contradicted this document or the engine: the blanket non-negative check
rejected `reversal.py`'s compensating rows, `abs(amount_cents)` gave a negative reversal a positive
budget and failed open when the entry was missing, and `uq_iban_history_active` made the `F07`
shared-IBAN state unrepresentable. `0020` adds the fourth trigger, makes the cap signed and
kind-aware under `FOR UPDATE`, ties a learned IBAN to a `CONFIRMED` proposal for that renter,
re-keys the active-IBAN index per renter, constrains a reversal to negate a `PAYMENT` exactly, and
adds one `nk_nachzahlung` per tenancy period. `docs/02` § 6 holds the full table.

**A third audit, 24.08.2026, reopened `0020`.** The pass over `0020` itself — which the previous
handoff recorded as never having run — found two HIGH and five MEDIUM defects in the repair. The
fourth trigger resolved the wrong renter when a reversal carried its own proposal, which § 5.3
permits. No trigger function pinned `search_path`; a learned IBAN could cite no transaction; and
two isolation tests passed on the wrong refusal. The amended `0020` is now proved on a fresh
database and the complete hand-delta is applied to development. R13–R18, the focused RLS checks,
the full gate and the non-fresh demo gate pass; the PDF is unchanged. `docs/02` § 6 "Closed on
`0020`" carries the per-finding table and fixture ids.

The same audit found `scripts/check_rls_coverage.py`'s write-assertion matcher vacuous: it split
the isolation suite only at method indentation, so a module-level fixture's body was glued onto an
unrelated test and all nine tables inherited its markers. Repaired, it immediately named four more
tables predating this slice, whose assertions were added rather than grandfathered. That repair was
itself incomplete — splitting at the next `def` still glued a following class header onto the last
test body, and never matched `async def`. Test bodies now come from `ast`, so a chunk ends where the
test ends; all 38 tenant tables stayed covered, so none had been resting on glue.

M6-C3a is technically complete, development-synchronized and locally merged, and C3b's three job
entrypoints are technically complete and locally merged, and so is C3c's landlord *Zahlungen*
screen, which closes M6-C3. It also inherits the gaps in `PLAN.md` § M6-C —
`ordering_version` and `convention_version` are free text where `CLAUDE.md` § 6 wants a rules-store
reference, and `receivable.source_id` is polymorphic and therefore carries no composite FK.

## 11. Approval and implementation boundary

All thirteen cases, register rows, model boundaries and correspondence coverage are fully
transcribed. Emir approved the transcription on 20.08.2026. M6-C1/M6-C2/M6-C3-0/C3a technically
verify the engine, persistence, normalized stub adapter, service and owner endpoints on local
`main`; they do not approve production bank-matching behavior or any legal/product convention.
C3b technically verifies the scheduler port, the three job entrypoints and the PSD2 consent
precondition on local `main`; that is a technical result, not approval of the 180-day
convention or of production bank matching. C3c technically completes the landlord *Zahlungen* screen on local `main`; that too is a
technical result, and the § 4 weights it displays stay `Konvention`, `verify-before-production`,
presented as a decision aid and never as legal support for a match. finAPI and renter delivery
remain unshipped. Round five resolves the former source gaps but does not implement them: the
tenancy-bound receivable migration, both reference fields/signals, tie-break fixture, explicit
credit offset and reminder suppression, event-triggered re-evaluation, identity correction and
documented debtor designation are all pending. Free owner selection of a receivable remains
forbidden. The separate `docs/16` D2 transcription is approved and merged.
