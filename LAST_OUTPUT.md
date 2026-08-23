# Last output — M6-C1 merged, red window declarable

HEAD `8306b68` on `main` · `23.08.2026`
Status: Complete

## Wanted
Clear the two items `PLAN.md` § M6-C puts before M6-C2, in that order.

## Done
Both are merged into local `main`. The **workflow correction** (`cc2f758`) adds `.lokara-red`: a
slice declares the red window `CLAUDE.md` § 10 requires, `gate.sh fast` reports every failure and
exits 0 while it exists, `full`/`demo` treat it as a hard failure, and
`scripts/tests/test_red_sentinel.py` proves the check can fail. `AGENTS.md` § 4 adds brief and turn
discipline with the measured baseline. The **M6-C1 merge gate** (`8306b68`) is closed: the § 4
stored-reference signal returns 0, since §§ 3.2–3.3 define no such field, with the gap recorded in
the docstring, `docs/15` § 4 and `FRAGEN-an-Berkay-05.md`; the § 5.3 reversal lookup was not
touched and `F06` stays green. `docs/15`'s status lines now describe `main`. `gate.sh full` is
green: 1077 Python tests, 43 web tests, `mypy --strict` clean.

The agent system was measured against the session transcripts rather than estimated: subagents are
~39 % of spend, 95 % of that is context re-read, and 12 of 19 subagent gate blocks were
`spec-scribe`. Two candidate fixes were rejected on that evidence and recorded in `PLAN.md`.

## Not done
Nothing requested. M6-C2 (models, migration `0017`, RLS, the § 3.1 adapter rewrite, owner-scoped
endpoints) is untouched. Nothing was pushed; `main` is 15 commits ahead of `origin/main`.

## Optional next step
Start M6-C2, adding the § 4 stored-reference field with the `receivable` table.
