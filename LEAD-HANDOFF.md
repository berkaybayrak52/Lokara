# LEAD-HANDOFF.md — M6-C1 committed, unmerged; workflow correction is next

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting.

## Current state — 23.08.2026

- `main` is at `4c9b9ac` (document correction), whose parent `f578f2f` is the M6-B merge. The
  working branch is `slice/m6-c1-matching-engine` at `a203755`, which carries exactly one commit
  ahead of `main`: `a203755`, the pure bank-matching engine. `git branch --contains a203755` lists
  the slice branch only.
- Local `main` is 9 commits ahead of `origin/main` (`a748729`, the M5 merge). Nothing has been
  pushed since M5. Do not push without Emir's explicit go-ahead.
- `Antwort-an-Emir_04.md` stays untracked at repository root by Emir's decision. Keep it out of
  every commit.
- `scripts/gate.sh full` is green: 1077 Python tests, 43 web tests, `mypy --strict` clean, engine
  purity clean, handoff clean.
- `stash@{0}` ("m6c1-superseded-by-a203755") is a recovery point from the branch repair described
  below. It is fully superseded by `a203755` and can be dropped once that is confirmed.

## M6-C1 — done, and deliberately NOT merged

`packages/matching-engine` implements approved `docs/15`: signal scoring, the six-step decision
order, § 366/§ 367 settlement, Largest-Remainder principal split and reversal. All thirteen
`BANKMATCH-F01`–`F13` cases run through real code as 30 tests. The package imports the standard
library only — not even `lokara_domain` was needed. Money is integer cents and `Decimal`; `float`
is refused at the single import boundary.

**The merge to `main` is blocked on one thing.**
`packages/matching-engine/src/lokara_matching_engine/scoring.py:112` (`_end_to_end_signal`) binds
`docs/15` § 4's "stored reference" to `profile.payment_code` and awards +15 on a substring match.
§§ 3.2–3.3 never define a stored-reference field, so this is an **invented matching convention with
no source**, exercised by zero fixtures — index 3 is `0` in all thirteen cases. It is not inert:
+15 can lift a candidate from 25 to 40, i.e. Unmatched to Review, changing the decision.

Before merging, make that signal return 0 with the source gap documented in the docstring. Emir
decided to defer the stored-reference question to M6-C2, and shipping a guess is deciding it rather
than deferring it. The receivable table built in M6-C2 is where the real field belongs.

Because the slice is unmerged, `docs/15` line 13 ("specification only") and § 11 ("implementation
remain paused") are still true of `main` and must **not** be edited yet. Update them in the same
change that merges.

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

1. **Workflow correction** — see `PLAN.md` § M6-C. Two real items: the stop gate cannot express
   "RED on purpose" during the red window `CLAUDE.md` § 10 itself requires, and agent briefs are
   too long (~300k tokens and ~40 minutes for one pure engine).
2. **Make `_end_to_end_signal` inert**, then merge M6-C1 into local `main` and update the `docs/15`
   status lines in the same change.
3. **M6-C2** — models, migration `0017`, RLS, the § 3.1 adapter rewrite and owner-scoped endpoints.
   Add the stored-reference field to the `receivable` table there.

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
