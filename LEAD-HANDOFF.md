# LEAD-HANDOFF.md — M6-C merged through C1; M6-C2 is the open work

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting.

## Current state — 23.08.2026

- `main` is at `8306b68` "merge: complete M6-C1 bank-matching engine". Two slices merged this
  session: `slice/m6-workflow-correction` (`cc2f758`) and `slice/m6-c1-matching-engine`
  (`8306b68`). Both slice branches are fully contained in `main` and have no unmerged work.
- Local `main` is **15 commits ahead of `origin/main`** (`a748729`, the M5 merge). Nothing has been
  pushed since M5. Do not push without Emir's explicit go-ahead.
- `Antwort-an-Emir_04.md` stays untracked at repository root by Emir's decision. Keep it out of
  every commit.
- `scripts/gate.sh full` is green: 1077 Python tests, 43 web tests, `mypy --strict` clean, engine
  purity clean, handoff clean.
- `stash@{0}` ("m6c1-superseded-by-a203755") is fully superseded by the merged engine and can be
  dropped. `stash@{1}` is an older M6-A rebase checkpoint; it was left alone.

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

1. **M6-C2** — models, migration `0017`, RLS, the § 3.1 adapter rewrite and owner-scoped
   endpoints. Add the stored-reference field to the `receivable` table there and only then make
   the § 4 E2E signal live again.
2. **M6-C3** — the German landlord *Zahlungen* screen, the three job entrypoints and the
   `docs/15` implementation-status closure.

The workflow correction that `PLAN.md` § M6-C put before M6-C2 is **done and merged**:
`.lokara-red` lets a slice declare the red window `CLAUDE.md` § 10 requires, announced and
non-blocking at `gate.sh fast`, a hard failure at `full`/`demo`. `AGENTS.md` § 4 carries the
brief and turn discipline and the measured baseline it is judged against.

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
