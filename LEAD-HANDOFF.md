# Lead handoff — M9 boundary clean; final UI review red

**Resume only when Emir asks. Read `CLAUDE.md`, then `PLAN.md` § M9, then
`docs/12-guards-deadlines.md`. Nothing may be committed, merged or pushed without Emir's explicit
authorization.**

## Where the work is parked

| | |
| --- | --- |
| Worktree | `/private/tmp/lokara-m9-worktree` |
| Branch | `slice/m9-guards-delivery` |
| HEAD/base | `3d69013` |
| State | uncommitted and unmerged; `.lokara-red` absent |

Work only in this worktree. Preserve every existing M9 change and the untracked dependency folders.
Do not switch, clean, remove the worktree, commit, merge or push without Emir's instruction.

## Current result

M9 implements W1–W8, migration `0025`, account-scoped jobs/API, immutable reminder/delivery/checklist
evidence, default-off email delivery and `/a/{accountId}/waechter`.

The original M9-R endpoint and database-boundary defects are repaired:

- both renter-delivery write paths now run against migrated Postgres tests;
- delivery confirmation records the bound artifact and accepted owner membership;
- checklist and W1 evidence triggers enforce accepted memberships and consistent annual-statement
  artifact bindings;
- consumers use the bound artifact column, not forgeable snapshot JSON;
- statement delivery blockers are derived from the published Page-01 inventory rather than trusted
  from the writer.

A fresh `boundary-auditor` review is clean. Its focused verification passed `112` tests.
`scripts/gate.sh demo` is green: `1844` pytest, `130` vitest, `mypy --strict` over `243` source files,
65 forced-RLS tenant tables and 130 account-scoped foreign keys. The ordinary statement fingerprint
is unchanged at `88eb8434eda65f8d7ff82826fc837a58` / `149269` bytes.

**M9 is still not complete.** The fresh `statement-reviewer` run is red with one HIGH
landlord-facing presentation defect:

- actual lower-case internal blocker keys still leak on `/waechter`, including
  `missing_warning_copy:last_day`, `missing_post_retrofit_rule`, `missing_uvi_cadence_start` and
  `basis_year_mismatch`;
- the generic internal-code regex also hides the useful `SHA-256` part of an approved German
  integrity message;
- the generic fallback can falsely describe technical blockers as a missing legal/rule basis and
  can duplicate identical bullets.

The explicit German W1–W8 titles, known blocker labels, reminder-channel labels,
suppression-reason labels and corrected Unit-B heating figures are already in place. Do not undo
them.

## Exact resume point

1. Have `spec-scribe` add failing web tests for the real lower-case blocker keys, preservation of
   the approved German `SHA-256` message, accurate technical fallback wording and deduplication.
   Declare the red window in `.lokara-red`.
2. Have `app-implementer` replace the broad regex heuristic with explicit mappings/allowlisting and
   safe differentiated fallbacks. Unknown internal keys must not leak; useful German text must not
   be hidden.
3. Remove `.lokara-red`, run the focused web tests and `scripts/gate.sh demo`, confirm the fingerprint
   is unchanged, then obtain a fresh `statement-reviewer` result.
4. Reconcile current M9 documentation only after that review is clean. Present the slice without
   committing or merging it.

## Production blockers that remain out of scope

Green gates do not authorize production use. Client-supplied clocks, discovery-token expansion,
`StubEmailGateway` semantics/storage, hard-coded or exact-equality legal timing, source/legal flags,
missing immutable UVI PDF bytes, absent real email/worker/scheduler/push/Destatis providers and the
empty production checklist catalogue remain blocking. Delivery schedules remain default-off.

M7-F and M8 remain parked and are not part of this work.
