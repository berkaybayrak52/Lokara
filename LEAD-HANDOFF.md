# Lead handoff — M7 is merged; M7-F reviews are what remain

M7-0 through M7-E are technically complete and locally merged into `main` from
`slice/m7-afa-tax-export` on 25.08.2026. Nothing was pushed. `.lokara-red` is gone: the declared
RED window closed when its focused suite went green, and the file is never committed.

Technical closure is not production or legal approval. Every authority flag below still blocks real
output.

## What closed the RED window

The window was declared for the verified-export adapter, where the server still accepted
caller-supplied artifact bytes and keyed archive streams on the readiness attempt. All four causes
are resolved:

- `generate_verified_test_export(account_id, readiness_attempt_id, generated_at, session)` resolves
  the rule bundle itself and builds the bytes from domain inputs. It takes no `bundle` and no
  `content_bytes`. A client payload can never supply a verified-test bundle.
- `archive_verified_test_artifacts` is the internal exact-byte boundary. It freezes the readiness
  findings, blockers and both `Rechtsstand` values it loaded, and refuses a readiness snapshot with
  no `blockers` key rather than defaulting one.
- Archive versions and supersession run per logical export stream — account, building, tax year and
  export kind — never per readiness attempt, so a second attempt for the same stream supersedes the
  first.
- The readiness projection handed to the export engine carries no tenant identity: cash-basis facts
  plus the stored provenance snapshot, and nothing naming an account, a building or a unit.
- A tax-event correction is its own model. It supersedes one stored row and reads building,
  allocation, component and receipt reference from that row, so a correction can never re-parent an
  event or move it to another stream.

## Evidence

| Gate | Result |
| --- | --- |
| `scripts/gate.sh fast` | green |
| `scripts/gate.sh full` | green — `1709` pytest, `106` vitest |
| `mypy --strict` | clean over `234` source files |
| `scripts/verify_demo_path.sh` (non-fresh) | green |
| `scripts/pdf_fingerprint.sh` | `88eb8434eda65f8d7ff82826fc837a58` / `149269` bytes — unchanged |
| RLS coverage | `55` tenant tables ENABLEd + FORCEd + policied WITH CHECK + cross-account-write tested |
| FK isolation | `97` tenant-to-tenant foreign keys, all carrying `account_id` |
| Pre-context reads | one bounded SECURITY DEFINER function, one bootstrap caller |

The unchanged statement fingerprint is the specific claim that M7 altered nothing a landlord already
reads.

## Development database

The development database had been synchronized to an earlier draft of `0024`, which is why its
`tax_event` lacked `receipt_reference`, `source`, `unit_id` and `version` and its
`tax_export_archive` lacked `building_id`, `tax_year` and `export_kind`. With Emir's authorization
the M7 objects from that draft were dropped, the revision was stamped back to `0023` and `0024` was
re-applied. The seven M7 tables now match the models column for column. Supabase was never touched.

Two test fixtures had been written against the draft schema and were repaired by `spec-scribe`, not
by the implementer:

- the fake session in `test_verified_archive_versions_and_supersession_are_per_logical_export_stream`
  matched candidate archives by readiness id, which the stream query it mandates can never bind, so
  its three assertions were unreachable;
- the M7 RLS probe row omitted three NOT NULL columns, so the isolation test died on an insert
  before RLS was ever exercised.

## What remains — M7-F

1. Run a fresh `boundary-auditor` over the merged M7 schema, endpoints and roles.
2. Run a fresh `statement-reviewer` over the tax workspace and the Anlage-V PDF.
3. Run a fresh `docs-reconciler` over `docs/09`–`docs/11` against the merged code.

Earlier clean reviews predate the normalized M7-A/M7-B work and are not closure evidence. Nothing in
M7 may be described as production-ready until these run and their findings are resolved.

## Authority limits that still stand

- K09's month-granular use-change convention, although `10-F11` technically selects 453,798 ct.
- Weg-B placeholders and the missing Gutachten share.
- All Anlage-V line numbers, SKR03/SKR04 accounts, DATEV EXTF parameters and Soll/Haben orientation.
- Successful archive behaviour uses the explicitly verified test-only rule bundle. Runtime mappings
  remain blocked, and the API refuses a real export with
  `Export gesperrt: Die Quellen müssen zuerst geprüft werden.`

## Preserve unrelated work

`Antwort-an-Emir_04.md`, `berkay-specs.md` and `berkay-work/UI-specs/` remain untracked by Emir's
decision and were not staged. Do not use `git add -A`. Push requires separate authorization.
