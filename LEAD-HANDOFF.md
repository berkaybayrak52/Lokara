# LEAD-HANDOFF.md — next main session

This file gets a new main agent aligned quickly. It contains the permanent lead rules and the current
continuation point. Verify current facts against Git before acting.

## 1. Read in this order

1. `CLAUDE.md` — binding rules and communication style.
2. `AGENTS.md` — agents, lanes, branches and gates.
3. `git status --short --branch` and `git log -5 --oneline` — actual repository state.
4. `PLAN.md` — current state and execution order.
5. `LAST_OUTPUT.md` — short summary of the latest completed session.
6. For remaining M5 work: `docs/02-data-model.md` and `docs/04-web-app-structure.md`.

Source order:

| Question | Source |
| --- | --- |
| Binding rules | `CLAUDE.md` |
| Current work | `PLAN.md` |
| Agent workflow | `AGENTS.md` |
| Architecture | `lokara-arch.md` |
| Calculation rules | `berkay-work/` → `docs/` → code |
| Feature contract | Matching file under `docs/` |
| Latest short summary | `LAST_OUTPUT.md` |

## 2. Current repository state — 16.08.2026

- Branch: `slice/m5-bootstrap-contexts`.
- `1c71a2d` contains the secure M5 bootstrap implementation.
- `b8a63d5` contains the Row 4 status and mandatory communication rules.
- The slice has not been merged or pushed.
- Uncommitted documentation cleanup currently affects `CLAUDE.md`, `PLAN.md`,
  `DEMO-RUNBOOK.md` and this file.
- The last implementation verification was green: full gate, non-destructive demo path and boundary
  audit. The statement PDF fingerprint did not change.
- Do not commit, merge or push until Emir asks.

## 3. Where M5 stands

### Complete — secure bootstrap foundation

- JWT auth carries only the verified Person subject.
- Expiry, issuer, exact audience and authenticated role are validated.
- Account context is loaded from the database, never trusted from the token.
- Migration `0006` adds the single bounded `app_bootstrap_contexts(text)` read.
- `GET /me` returns every live account Membership context.
- `/demo/summary` and the token-scoped account session are retired.
- The demo summary uses `/a/{accountId}/summary`.
- `scripts/check_pre_context_reads.py` enforces the function, role, policies, privileges and API call
  sites.
- No new dashboard, portal or account switcher was added.

### Remaining M5 work

1. Enforce Membership roles in the API:
   - OWNER has full account access;
   - EMPLOYEE sees only assigned buildings;
   - EMPLOYEE with no assignments sees nothing;
   - TAX_ADVISOR is read-only.
2. Validate every nested `/a/{accountId}/buildings/{buildingId}/…` route before doing work.
3. Return a deliberate 403/404 for unauthorized or foreign buildings.
4. Make the existing owner portal role-aware.
5. Add the visible account switcher when `/me` returns more than one context.
6. Add the OpenAPI guard proving no current route writes `renter.person_id`.

Do not build renter activation or the renter portal in this M5 continuation. M10 owns activation,
the `renter.person_id` write and renter-portal context. M6 owns separate finalized tenant documents.
If `PLAN.md` uses the broader phrase "renter-facing context" under M5, follow the narrower ownership
defined in `docs/02`: M5 adds only the no-write guard; M10 builds the actual renter context.

The next implementation should start with role enforcement and nested-building authorization. The
visible switcher follows after those boundaries are green.

## 4. How to work with Emir

- Answer only what he asks.
- Lead with the result. Use short, simple sentences.
- Stop at the requested stage.
- Verify claims before stating them.
- Ask only when a missing decision materially changes scope or risk.
- Do not add advice, next steps or work unless requested.

## 5. Lead responsibilities

- Emir controls scope, priorities, agents, commits, merges and pushes.
- Preserve unrelated user changes.
- Inspect staged and unstaged changes separately.
- Verify agent reports against code, Git and command output.
- Reviewers report findings; they never fix them.
- Implementers do not write their own tests.
- Worktree changes do not sync back automatically.
- Never run `scripts/verify_demo_path.sh` from an agent worktree.
- Keep `.claude` and `.codex` aligned through `scripts/check_agent_parity.py`.
- Preserve legal flags and provenance. `geprüft` does not mean lawyer-approved.

## 6. Before merge

- Confirm the slice contains only intended work.
- Run `scripts/gate.sh full`.
- Run the demo gate when the milestone or output requires it.
- Record the PDF fingerprint for any claimed document change or non-change.
- Merge only green work. Push only when Emir asks.

## 7. Close the session

- Overwrite `LAST_OUTPUT.md` using the format in `CLAUDE.md`.
- Put execution status in `PLAN.md` and durable feature rules in `docs/`.
- Keep raw logs, prompts and agent reports out of the handoff.
