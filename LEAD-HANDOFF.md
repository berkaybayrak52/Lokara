# Lead handoff — U5 closed locally

`main` contains U5 feature `36d62b2`, merged locally as `a54350f` on 24.08.2026. Nothing is pushed.

## What is complete

U1–U5 are technically complete and reviewed:

- U1/U1b provide the pure UVI calculation, structured rule evidence/conflicts and labelled
  suppression.
- U2 provides versioned Heizspiegel rules and resolved row evidence.
- U3 provides annual and monthly DWD normalization plus deterministic persisted station assignment.
- U4 adds migration `0022`: monthly readings, station assignments, climate factors, immutable
  `uvi_run` archives and delivery events with account-scoped foreign keys, RLS and append-only
  guards.
- U4b adds migration `0023`: monthly degree days, effective-dated building configuration,
  building-month evidence and immutable raw-reading source links. Configuration and building
  evidence persist the full `source_type` plus `source_id` identity.
- U5 adds owner-side generation and archived PDF retrieval. It resolves heat-only compatible meter
  rows and each represented month's effective configuration, evaluates normalized Block A and
  Blocks B/C/D-or-D2, hashes complete source snapshots, writes a new immutable run on retry, and
  renders one separate German renter document.

U5 does not publish to a renter portal and does not send email. Publication remains M10; scheduled
delivery and its retry ledger remain M9.

## Review and verification

- Focused U5 suite: 202 passed.
- Closing boundary audit: no findings.
- Closing renter-document review: no findings.
- Demo gate: green with 1,542 Python tests and 84 web tests.
- RLS coverage: 48 tenant tables; FK isolation: 82 tenant foreign keys.
- PDF fingerprint remained `88eb8434eda65f8d7ff82826fc837a58`, 149269 bytes.
- `.lokara-red` is absent.

The development database remains at Alembic `0023`. Because it had already been stamped before the
uncommitted migration gained `source_type`, an exact additive parity delta added the two non-null
columns and matching checks without resetting or deleting data. Existing immutable RLS fixture rows
were preserved with the explicit legacy source type `LEGACY_RLS_FIXTURE`; no lasting default remains.

## Production blockers remain open

Technical closure is not legal or production approval:

- Emir still must choose the PLZ geodataset.
- Berkay still must supply the three missing UVI register rows; the CSV remains at 180 rows.
- The exact monthly § 6a/EED content list needs a versioned authoritative source.
- The Wärmepumpe deduction, W4 heating-season scope and BAnz/GEG authority questions remain
  `verify-before-production` as recorded in `docs/16-uvi.md` and `FRAGEN-an-Berkay-05.md`.
- Lokara never applies the 3% or 15% reductions automatically.

## Next execution boundary

`PLAN.md` places M7 next: tax export and AfA from approved `docs/09`–`docs/11`. Do not pull M9 UVI
scheduling or M10 renter publication forward.

Before the next slice, check `main`, local changes and the current handoff. Preserve the unrelated
untracked `Antwort-an-Emir_04.md`, `berkay-specs.md` and `berkay-work/UI-specs/`; never use
`git add -A`. Do not run `scripts/verify_demo_path.sh --fresh` without Emir's explicit permission.
