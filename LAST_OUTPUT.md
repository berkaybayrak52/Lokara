# Last output — M6-C2 complete, unmerged and awaiting its boundary review

HEAD `5af7897` on `slice/m6-c2a-bank-schema` · `23.08.2026`
Status: Complete

## Wanted
Clear the two items `PLAN.md` put before M6-C2, then build M6-C2 itself.

## Done
The workflow correction (`cc2f758`) and the M6-C1 merge gate (`8306b68`) are merged into local
`main`. M6-C2 follows in three commits: nine account-scoped tables with migration `0017`, FORCEd
RLS and composite FKs; the `docs/15` § 3.1 adapter rewrite with `BANKMATCH-F10` executed at the
import boundary; and owner-scoped endpoints carrying the `F12` Page-01 handoff, which copies a
finalized settlement at exact cents and refuses to run twice. Migration `0018` narrows the
receivable component check to rent, because an `nk_nachzahlung` parked in `nk_advance_cents` would
double-count as an advance Page 01 never received. The Zahlungsfrist is asked for rather than
defaulted, since the register records no statutory deadline and the 30 days is a flagged
`Konvention`. `gate.sh full` green: 1105 Python tests, 43 web tests, `mypy --strict` clean, RLS 38
tables, FK isolation 62 edges. The local database was rebuilt from empty on Emir's authorization,
which also proved `0001`–`0018` apply on a clean database; demo fingerprint unchanged at
`88eb8434eda65f8d7ff82826fc837a58`.

## Not done
M6-C2 is **unmerged** and `boundary-auditor` has not been run, though `AGENTS.md` § 7 requires it
for nine new tenant tables, four endpoints and an adapter. M6-C3 is untouched. Nothing pushed;
`main` is 16 commits ahead of `origin/main`.

## Optional next step
Run `boundary-auditor` over the slice, then merge it and start M6-C3.
