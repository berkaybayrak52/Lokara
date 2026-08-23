# Last output — M6-C2 complete after a boundary audit found six HIGH defects

HEAD `56b4c61` on `slice/m6-c2a-bank-schema` · `23.08.2026`
Status: Complete

## Wanted
Clear the two items `PLAN.md` put before M6-C2, build M6-C2, and review it before merging.

## Done
The workflow correction (`cc2f758`) and the M6-C1 merge gate (`8306b68`) are on `main`. M6-C2 adds
nine account-scoped tables (`0017`), the `docs/15` § 3.1 adapter rewrite with `BANKMATCH-F10` at
the import boundary, and owner-scoped endpoints carrying the `F12` handoff. `0018` narrows the
component check to rent; `0019` carries the boundary audit's fixes. The audit found **six HIGH
defects in code and fixtures written by one session** — an allocation could settle another
renter's debt or exceed its entry, a reversal could be positive or filed twice, `iban_history` was
rewritable and needed no confirmation, and two tables documented immutable were not. All fixed,
with fifteen new tests. `check_rls_coverage` now requires `WITH CHECK` and a real cross-account
write assertion, which immediately found three more tables predating this slice. `gate.sh full`
green: 1119 Python tests, 43 web, `mypy --strict` clean, RLS 38 tables, FK isolation 63 edges;
`gate.sh demo` green, fingerprint `88eb8434eda65f8d7ff82826fc837a58`.

## Not done
M6-C3 is untouched. The § 4 stored-reference signal stays inert pending Berkay's answer. LOW
findings are recorded in `PLAN.md` § M6-C, not fixed. No second audit pass after `0019`.

## Optional next step
Start M6-C3, and consider re-running `boundary-auditor` over `0019` since it changed a great deal.
