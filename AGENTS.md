# AGENTS.md — how Lokara is built with agents

> Read `CLAUDE.md` first. It is the contract. This file explains how the agent system
> follows that contract. If they disagree, `CLAUDE.md` wins.

## 1. Purpose and control

Lokara uses agents with separate roles. Each role protects one project invariant and has a
limited write lane. Implementers build. Reviewers report. The main session verifies the work and
decides what to present to Emir.

Emir controls:

- scope and priorities;
- whether agents are used;
- whether work is merged;
- whether work is pushed.

Every session must also follow `CLAUDE.md`'s mandatory communication and scope rules:

- answer only the question asked and perform only the authorized work;
- lead with the result, using short and simple language;
- do not continue from explanation to plan, or from plan to implementation, without authorization;
- verify factual claims against the repository or command output;
- ask only when a missing decision materially changes the result or risk;
- keep progress updates and final answers brief; do not add unsolicited advice or process narration.

The main session must enforce this style when presenting subagent work. A long agent report is input
for verification, not text to forward to Emir.

There is no manager agent. Coordination comes from the tracked sources of truth:

| Question | Source |
| --- | --- |
| What rules override everything? | `CLAUDE.md` |
| What is built and what comes next? | `PLAN.md` |
| How do agents and gates work? | `AGENTS.md` |
| How does the main session review and close work? | `LEAD-HANDOFF.md` |
| What happened in the latest session? | `LAST_OUTPUT.md` |

`LAST_OUTPUT.md` is only Emir's short session summary. It does not coordinate work or define
project status.

For legal and calculation work, original Pages/annexes and the authoritative register feed the
approved `docs/00`–`docs/16`; approved docs then control code. Retired correspondence is Git history,
not a precedence layer. Its sole historical disposition ledger is `docs/03` Appendix D.

## 2. Trust model

| Layer | Role |
| --- | --- |
| **Gates** | Run deterministic checks against the repository and database. |
| **Agents** | Apply judgement inside one limited role. |
| **Main session** | Verifies evidence, resolves findings and follows Emir's decisions. |

Gates are stronger than an agent's claim, but they can still have blind spots. A new gate must be
run locally and should have a test that proves it can fail. Claims such as counts, survey results
and “verified” findings must be checked against the repository or command output.

The `.claude/` and `.codex/` systems are mirrors. Their agent definitions, hook scripts and hook
wiring must stay aligned. `scripts/check_agent_parity.py` enforces this.

## 3. Agent roles and write lanes

| Agent | Responsibility | Write lane |
| --- | --- | --- |
| `spec-scribe` | Transcribe specs and create golden fixtures before implementation. | `docs/**`, tests, `PLAN.md`, `lokara-arch.md`, `DEMO-RUNBOOK.md`, `AGENTS.md` |
| `engine-implementer` | Implement pure engines, domain code, rules, adapters, models and migrations. | `packages/*/src/**`, `packages/db/alembic/**` |
| `app-implementer` | Implement API, web, UI and PDF framework code. | `apps/api/src/**`, `apps/web/src/**`, selected `apps/web` config files, `packages/{ui,pdf}/src/**` |
| `boundary-auditor` | Audit isolation, immutability and adapter boundaries. | Read-only |
| `statement-reviewer` | Review rendered statements and landlord-facing UI. | Read-only |
| `docs-reconciler` | Report drift between documentation and code. | Read-only |

The exact paths are enforced by `.claude/hooks/write-scope.sh` and its `.codex` mirror.

The lane rules are strict:

- Implementers do not write tests. A missing fixture goes to `spec-scribe` first.
- Reviewers never fix their own findings.
- Do not widen a lane only to let an agent finish.
- The main session is not restricted to an agent lane, but it must preserve unrelated user changes.

The hooks are guardrails, not a full sandbox. Always inspect the resulting diff.

## 4. Working on a slice

Every slice starts from `main`, never from another slice branch. Check the current branch and local
changes before creating it. Do not pull, merge or push unless Emir asks.

```bash
git status --short
git switch main
git switch -c slice/<name>
```

The normal flow is:

1. **Spec** — for legal or calculation work, `spec-scribe` transcribes the source and creates the
   failing fixture.
2. **Implement** — the correct implementer satisfies the existing fixture.
3. **Review** — use the matching read-only reviewer for the affected invariant.
4. **Verify** — copy back any worktree changes and run the gates in the main tree.
5. **Close** — show Emir the result. Merge or push only when he asks.

The red fixture and its implementation stay on the same slice branch. `main` receives only green
work.

For work without a legal or calculation rule, such as a screen or a framework refactor, the spec
step may be skipped. Review is still required for anything a landlord will read.

Use one agent at a time unless Emir explicitly asks for parallel agent work. Parallel work is most
useful for independent read-only reviews of a frozen diff. Implementation and its fixture remain
sequential.

## 5. Worktrees and shared resources

Some implementers run in isolated worktrees. Their changes do not automatically appear in the main
tree. After a worktree run:

1. Inspect the worktree with `git status --short`.
2. Confirm every changed path belongs to the agent's lane.
3. Copy the intended files into the main tree.
4. Run the relevant gates in the main tree.
5. Remove the worktree only after the copy is verified.

A worktree may be based on stale code, so its green result is not enough.

Postgres and the Docker stack are shared resources. An isolated agent must not recreate the stack,
run destructive database commands or run `scripts/verify_demo_path.sh`. Run DB-backed verification
in the main tree after the work has been copied back.

## 6. Gates

```bash
scripts/gate.sh fast    # lint, types, purity, parity and pure-package tests
scripts/gate.sh full    # fast checks plus all tests and both application lanes
scripts/gate.sh demo    # full checks plus the complete demo path
```

Use `fast` during implementation. Use `full` before merging a normal slice. Use `demo` when a
milestone or output change requires the complete statement path.

Important focused checks:

```bash
uv run python scripts/check_engine_purity.py
uv run python scripts/check_agent_parity.py
uv run python scripts/check_rls_coverage.py
uv run python scripts/check_fk_isolation.py
uv run python scripts/check_pre_context_reads.py
```

- `check_engine_purity.py` protects pure, deterministic engine packages.
- `check_agent_parity.py` protects the `.claude` and `.codex` mirror.
- `check_rls_coverage.py` requires every tenant table to have RLS and isolation-test coverage.
- `check_fk_isolation.py` rejects unsafe cross-account foreign keys.
- `check_pre_context_reads.py` enforces the sole bounded pre-account identity read, including its
  function, role, policies, privileges and API call sites.
- `verify_demo_path.sh` validates migration, seed, statement, PDF and rendered figures.

`scripts/verify_demo_path.sh --fresh` destroys local Postgres data. Run it only with Emir's explicit
permission.

The stop hook prevents an agent from ending on a red configured gate. `LOKARA_GATE=off` is only for
explicit exploratory work. It is never evidence that a slice is complete.

## 7. Review requirements

Use `boundary-auditor` after changes to tables, endpoints, roles, tenant isolation, immutable data
or external adapters.

Use `statement-reviewer` after changes to the PDF, statement data, calculation engines or any
landlord-facing screen.

Use `docs-reconciler` at milestone close or when code and documentation may have drifted.

For any slice that claims the rendered document changed or stayed unchanged, record the output of
`scripts/pdf_fingerprint.sh` before and after. Put only the short result in `LAST_OUTPUT.md`; Git and
the slice evidence hold the details.

Review reports are findings, not fixes or completion decisions. The main session verifies them and
returns required changes to the correct implementer.

## 8. Merge and session close

Before proposing a merge:

- inspect staged and unstaged changes separately;
- confirm the slice contains only its intended work;
- preserve unrelated local edits;
- run `scripts/gate.sh full`;
- use the demo gate when the milestone or rendered output requires it;
- confirm required review findings are resolved.

Do not merge, tag or push automatically. Emir decides when each action happens.

At the end of the main session, overwrite `LAST_OUTPUT.md` with the short format in `CLAUDE.md`.
Only the main session writes it. Put durable execution status in `PLAN.md`, specifications in
`docs/`, legal questions in the relevant `FRAGEN-an-Berkay-*.md`, and history in Git.

## 9. Maintenance

Keep this file limited to permanent operating rules. Do not add completed threads, dated incidents,
old branch names, commit histories or temporary status.

When a rule changes:

- add a scriptable invariant to `scripts/` and wire it into the gates;
- add a judgement-based invariant to one existing role and its write lane;
- update both `.claude` and `.codex` copies;
- update golden statement figures in `docs/` before changing the PDF assertion;
- turn repeated agent mistakes into a clearer instruction or a stronger gate.

Related: `CLAUDE.md` · `PLAN.md` · `LEAD-HANDOFF.md` · `docs/` · `DEMO-RUNBOOK.md`
