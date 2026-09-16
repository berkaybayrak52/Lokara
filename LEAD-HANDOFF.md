# Lead handoff — M10-I2 technically complete

## Current state — 16.09.2026

M10-I0/I1 is committed as `58f8f36` and fast-forwarded into local `main`; nothing is pushed. Branch
`slice/m10-i2-investment-persistence` is based on that commit. M10-I2 is technically complete but
uncommitted. Nothing was pushed and `.lokara-red` is absent.

The approved `docs/14` § 4.7 contract is implemented by migration `0045`, mapped metadata and
exactly three append-only investment tables. The real `0044 → 0045` application and `109` focused
tests pass. Canonical replay is byte-identical, RLS covers `80` tenant tables, all `161` tenant FKs
preserve `account_id`, and the full RLS suite passes `113`.

The required boundary audit has no finding. It confirms owner-only forced RLS, renter refusal,
immutable correction streams, database-verified hashes and no Building/statement/tax/demo coupling.
The full gate is green with `2259` Python tests and `258` web tests; Ruff, formatting, strict mypy,
purity, parity and pre-context checks pass.

M10-I3 API/entitlement and M10-I4 cockpit/Bank-PDF remain pending. All Page-07 production blockers
remain active. Preserve the five unrelated untracked `adjustment/` files.
