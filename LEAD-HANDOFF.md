# LEAD-HANDOFF.md — M6-C2 complete and unmerged; M6-C3 is the open work

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting.

## Current state — 23.08.2026

- `main` is at `e755b9c`. The working branch is `slice/m6-c2a-bank-schema`, which carries the
  three M6-C2 commits ahead of it: `f1731f6` (schema + migration `0017`), `a729bf9` (§ 3.1 adapter)
  and `5af7897` (endpoints + the `F12` handoff + migration `0018`). **Not merged.**
- `origin/main` is **also** at `e755b9c`: Emir pushed `main` on 23.08.2026 at 16:34, so this
  session's merged work (the workflow correction `cc2f758` and the M6-C1 merge `8306b68`) is on
  GitHub. Local `main` is zero commits ahead. Earlier drafts of this file said "16 ahead, nothing
  pushed since M5" — that was true when written and is now wrong.
- The M6-C2 slice branch is **not** on the remote. Do not push it without Emir's explicit
  go-ahead.
- `Antwort-an-Emir_04.md` stays untracked at repository root by Emir's decision.
- `scripts/gate.sh full` is green: 1105 Python tests, 43 web tests, `mypy --strict` clean, RLS
  coverage 38 tenant tables, FK isolation 62 edges, engine purity clean.
- The local database was rebuilt from empty with `verify_demo_path.sh --fresh` on Emir's
  authorization, which also proved migrations `0001`–`0018` apply on a clean database rather than
  only incrementally. Demo PDF fingerprint unchanged: `88eb8434eda65f8d7ff82826fc837a58`
  (149269 bytes).

## Before merging M6-C2 — one required review

`AGENTS.md` § 7 makes `boundary-auditor` mandatory here: the slice adds nine tenant tables, four
owner-scoped endpoints and an external adapter. It has **not** been run — this session's harness
does not spawn subagents unless asked. Either run it, or merge knowing the review was skipped and
record that choice.

## The red window is now declarable

`CLAUDE.md` § 10 forbids one agent from writing both a test and its implementation, so every
calculation slice has a mandatory red window — and the Stop hook, which runs `gate.sh fast`, used
to reject turn-endings inside it. Measured over the session transcripts: 9 main-session blocks plus
2 in subagents during M6-C1 alone, ~47 across all sessions, and 12 of the 19 subagent blocks were
`spec-scribe`, whose deliverable *is* a failing fixture.

Write one line naming the slice and the reason to `.lokara-red`. `gate.sh fast` then prints every
failure and exits 0; `full` and `demo` treat it as a hard failure, so nothing closes or merges with
its window open. The file is gitignored and an anonymous sentinel is rejected. See `AGENTS.md` § 4.

`AGENTS.md` § 4 also carries the brief and turn discipline: agent cost is turns × context, not
brief length, so a brief names its exact files, fixture IDs and acceptance command, and an agent
past ~40 turns stops and reports. The measured per-run baseline is recorded there.

Two further fixes were measured and rejected — skipping the gate for read-only agents (they were
blocked zero times in 16 runs) and downgrading the reviewers to a cheaper model (~3 % of spend,
against `statement-reviewer`'s ability to see the de-scaling defect class the suite cannot).
`PLAN.md` § M6-C records both so they are not rediscovered.

## M6-C2 — what shipped, and its two deliberate limits

Nine account-scoped tables with migration `0017`, FORCEd RLS and composite `(id, account_id)`
edges; the § 3.1 adapter rewrite with `BANKMATCH-F10` executed at the import boundary; and
owner-scoped endpoints carrying the `F12` Page-01 handoff, which copies a finalized `RECEIVABLE`
settlement into an `nk_nachzahlung` receivable at exact cents and refuses to run twice for one
statement.

1. **The Zahlungsfrist is asked for, never defaulted.** `docs/08` flags *Zahlungsfrist bei
   Nachzahlung* `verify-before-production`, and the register is explicit: no statutory deadline
   exists, the claim falls due on receipt of a proper statement, and the customary 30 days is a
   `Konvention` anchored only in § 286 Abs. 3 BGB. The handoff therefore requires an explicit due
   date and refuses without one. Do not add a default — it would make a flagged convention
   Lokara's answer on every statement.
2. **The § 4 stored-reference signal stays inert.** `receivable.stored_reference` exists so the
   field has a home. Nothing writes it. Turning the signal on without Berkay's answer restores the
   invented convention M6-C1 removed.

Migration `0018` narrows the receivable component-sum check to `category = 'rent'`. `0017` applied
it to every receivable, which is wrong for an `nk_nachzahlung`: it has no rent, garage or advance
component, and § 5.2 says the paid NK-advance component feeds the annual actual-advance total Page
01 consumes — so parking a Nachzahlung in `nk_advance_cents` to satisfy the arithmetic would
double-count it as an advance that was never paid. Page 08 gives no split for `nk_nachzahlung`, so
none was invented.

## M6-C1 — complete and merged

`packages/matching-engine` implements approved `docs/15`: signal scoring, the six-step decision
order, § 366/§ 367 settlement, Largest-Remainder principal split and reversal. All thirteen
`BANKMATCH-F01`–`F13` cases run through real code as 30 tests. The package imports the standard
library only — not even `lokara_domain` was needed. Money is integer cents and `Decimal`; `float`
is refused at the single import boundary.

**The merge gate is closed.** `scoring.py::_end_to_end_signal` now returns 0. It had bound
`docs/15` § 4's "stored reference" to `profile.payment_code`, and §§ 3.2–3.3 define no such field —
an invented matching convention with no source, exercised by zero fixtures, where +15 lifts a
candidate from 25 to 40, i.e. Unmatched to Review. The gap is recorded in the docstring, in
`docs/15` § 4 and in `FRAGEN-an-Berkay-05.md`; M6-C2 adds the real field with the `receivable`
table and makes the signal live. The § 5.3 reversal lookup resolves an original match by
E2E/mandate reference — a different, source-backed mechanism covered by `F06` — and was not
touched.

`docs/15`'s status lines were updated in the same change, so they now describe `main`.

## Judgment calls already made — do not rediscover these

The implementer flagged eight readings where `docs/15` is silent. All except the first are
conservative (they score less or demand more) and none invents a value:

1. **E2E "stored reference" → `profile.payment_code`** — the invented one; see the merge gate above.
2. **"Known IBAN" read literally** — the IBAN must be in `profile.known_ibans` as well as carrying
   `IbanOwnership.UNIQUE`, so a unique claim for an unknown IBAN scores 0 and cannot Auto-Match.
3. **Period token** — only the normalized `YYYY-MM` token counts; German month names do not, so
   F03's "Miete Juli" scores no period signal.
4. **Designation naming a nonexistent period** — FIFO still runs over remaining debts and only the
   final remainder becomes credit. F08 passes an empty list, so this is unpinned by any fixture.
5. **Reversal `(IBAN, amount, date)` fallback** — requires `bank_booking_date` and `value_date` to
   agree, because § 5.3 does not say which date it means.
6. **Restored status after reversal** — taken from the status recorded on the `Allocation` rather
   than re-derived, which would have to guess whether an earlier partial payment existed.
7. **Review ranking key** — `(-amount, -code_or_surname, -e2e, -confidence, receivable_id)`;
   confidence and id close the key for a total order. F07 is the only ranking fixture.
8. **Reason strings are German**, following the `incomplete_reason_de` precedent in
   `packages/heating-engine/src/lokara_heating_engine/page01b.py`.

## Disclosure — the main session edited the acceptance fixture

`packages/matching-engine/tests/test_berkay_15_engine.py` was edited by the main session, not by
the implementer: a two-line assertion reorder at roughly lines 727 and 789. Asserting
`decision is Decision.NEEDS_REVIEW` narrows the type, which made the following
`is not Decision.DEDUPED` provably true and `mypy --strict` rejected it as non-overlapping. All
assertions survive in both tests and only their order changed, so nothing was weakened — but this
is exactly the kind of edit `CLAUDE.md` § 10 exists to keep visible.

The implementer detected it independently by md5 and file mtime and refused to absorb it silently.
That is the separation working, and it is recorded here rather than buried.

## Next work, in order

1. **Review and merge M6-C2** — run `boundary-auditor` first (see above), then merge
   `slice/m6-c2a-bank-schema` into local `main`.
2. **M6-C3** — the German landlord *Zahlungen* screen where a Review proposal is confirmed, the
   three job entrypoints (bank sync, 180-day reconsent cleanup, deadline watchers, as service
   functions behind a scheduler port), and the `docs/15` implementation-status closure. That
   completes M6.

The workflow correction and the M6-C1 merge gate that `PLAN.md` § M6-C put before M6-C2 are both
done and merged (`cc2f758`, `8306b68`).

## A correction worth keeping

An earlier draft of this handoff claimed the agent worktree copy-back had silently reverted an edit
to `scripts/gate.sh`. **That was wrong.** The main session had run `cd` into an agent worktree and
never returned, so subsequent commands — including the first M6-C1 commit — ran against the
worktree instead of the main tree. The edit was never lost. The branch was repaired by
fast-forwarding `slice/m6-c1-matching-engine` to `a203755`; all agent worktrees and their branches
have since been removed. Worktree copy-back is not known to have failed. Judge the worktree
question on real evidence, not on that claim.

## Unresolved authority

- Every `docs/15` matching value stays `verify-before-production` `Konvention` at Rechtsstand
  07/2026: CSV rows 169, 171–173, 177–181. The 60/20/30/15/15/10/5 weights and the 40/79 thresholds
  are conventions, never legal support for a match.
- `docs/15` § 5.2's Largest-Remainder tie-break is **missing from the authoritative source**. The
  engine raises `TieBreakUnspecifiedError` on an exact tie and invents no ordering. Open question in
  `FRAGEN-an-Berkay-05.md`.
- `docs/15` § 4's "stored reference" is named by § 4 but defined nowhere in § 3. Open question in
  `FRAGEN-an-Berkay-05.md`.
- V1 is AIS-only: no PIS payouts, no SEPA direct debit, no late interest or reminder fees. Renter
  credit is recorded, never paid out. No renter delivery, portal publication or email — that is M10.
