# Last output — M6 merged through C2, documents reconciled

HEAD `92e1318` on `main` · `23.08.2026`
Status: Complete

## Wanted
Finish the M6-C1 handoff, clear the two items `PLAN.md` put before M6-C2, build M6-C2, review it,
and reconcile every document with the result.

## Done
Three slices merged into local `main`: the workflow correction (`cc2f758`, the `.lokara-red` red
window plus brief discipline), M6-C1 (`8306b68`, the pure matching engine with the § 4 signal made
inert), and M6-C2 (`92e1318`, nine account-scoped tables across migrations `0017`/`0018`/`0019`,
the `docs/15` § 3.1 adapter rewrite, and four owner-only endpoints carrying the `F12` handoff). A
`boundary-auditor` pass found **six HIGH defects** in M6-C2 — an allocation could settle another
renter's debt or exceed its entry, a reversal could be positive or filed twice, `iban_history` was
rewritable without confirmation, and two tables documented immutable were not. All fixed in `0019`
with fifteen new tests. `check_rls_coverage` now requires `WITH CHECK` and a real cross-account
write assertion instead of the table merely being named, which immediately surfaced three more
tables predating the slice. `gate.sh full` and `demo` green: 1119 Python tests, 43 web,
`mypy --strict` clean, RLS 38 tables, FK isolation 63 edges, fingerprint
`88eb8434eda65f8d7ff82826fc837a58`. Eleven documents reconciled with the result.

## Not done
M6-C3 — the Zahlungen screen, the three job entrypoints and the `docs/15` status closure. The § 4
stored-reference signal stays inert pending Berkay. LOW audit findings are recorded in `PLAN.md`
§ M6-C, not fixed. No second audit ran after `0019`. Nothing pushed; `main` is 9 ahead of
`origin/main`.

## Optional next step
Start M6-C3, and consider re-running `boundary-auditor` over `0019` before it lands.
