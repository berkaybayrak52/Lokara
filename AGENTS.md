# AGENTS.md — how Lokara is built with agents

> Read `CLAUDE.md` first: it is the contract. This file is the **operating manual** for the
> agent system that enforces it. Whatever this file says, the three rules in `CLAUDE.md` win.

---

## The idea in one paragraph

Correctness here is not a matter of taste — it is a set of named invariants that already
exist in writing (`CLAUDE.md`'s three rules, `PLAN.md`'s five hard rules, the two Definitions
of Done). So the agent system is organised **one role per invariant**, not one role per
activity. Each agent owns a lane, writes only inside it, and is judged by whether its
invariant still holds. Nothing that can be checked by a script is left to an agent, and
nothing an agent asserts is trusted without a script.

Three layers, in order of trust:

| Layer | What | Can it be wrong? |
| --- | --- | --- |
| **0 — Gates** | `scripts/*` + `.claude/hooks/*`, run by hooks and CI | No. Deterministic. |
| **1 — Agents** | `.claude/agents/*.md`, judgement inside one lane | Yes — which is why layer 0 exists |
| **2 — You** | The main session. Reads reports, decides, merges | You are the lead |

There is deliberately **no manager agent**. `PLAN.md`, `CLAUDE.md`, `LAST_OUTPUT.md` and the
`demo-green-<n>` tags already are the coordination layer, and unlike an LLM they cannot drift,
get optimistic, or declare a milestone done because the summary sounded finished. Status is
derived from gates going green, never from an agent's opinion of its own work.

---

## The roster

| Agent | Owns the invariant | Writes | Reads |
| --- | --- | --- | --- |
| `spec-scribe` | *No calculation without a transcribed spec + golden fixture* | `docs/**`, `PLAN.md`, `*/tests/**` | everything |
| `engine-implementer` | *Engines are pure, deterministic, cent-exact* | `packages/*/src/**`, `packages/db/alembic/**` | everything |
| `app-implementer` | *The framework layer never trusts the client, and the UI is AA* | `apps/*/src/**`, `packages/{ui,pdf}/src/**` | everything |
| `boundary-auditor` | *Isolation enforced twice; data immutable + versioned* | **nothing** | everything |
| `statement-reviewer` | *The rendered document is right* | **nothing** | everything |
| `docs-reconciler` | *Docs and code agree* | **nothing** | everything |

**No two agents can write the same file.** That is the property that makes the whole thing
worth having. Concretely:

- The implementer **cannot write tests**, so it cannot move the goalposts. If the fixture
  doesn't exist, it must stop and ask for `spec-scribe` — which is exactly `PLAN.md` hard
  rule 1, enforced mechanically instead of remembered.
- The auditors **cannot write anything**, so a green report is information rather than a
  self-assessment. An auditor that can edit is an auditor you cannot trust.

Enforced by `.claude/hooks/write-scope.sh` (a `PreToolUse` hook that reads `agent_type` and
the target path). It is a guardrail, not a sandbox — a determined agent could shell out — so
every write-capable agent also runs `isolation: worktree`, and stray writes land in a
throwaway copy of the repo that shows up in your diff.

---

## The gates

Run them directly, or let the hooks run them.

```bash
scripts/gate.sh fast          # ruff + mypy + purity + pure-package pytest   (seconds)
scripts/gate.sh full          # + all pytest, eslint, tsc, vitest           (CI parity)
scripts/gate.sh demo          # + the whole demo path                        (milestone end)

scripts/verify_demo_path.sh           # clean DB -> migrate -> seed -> statement -> PDF -> read it
scripts/verify_demo_path.sh --fresh   # ...starting from an empty volume (destroys local pg data)

uv run python scripts/check_engine_purity.py    # CLAUDE.md rule 1
uv run python scripts/check_rls_coverage.py     # CLAUDE.md rule 3 (needs a migrated DB)
```

**What each one turns from discipline into a command:**

- `check_engine_purity.py` — rule 1. AST-level: forbidden imports, no I/O, no clock, and
  engines never importing `rules-store`. Runs on every Python edit via `PostToolUse`.
- `check_rls_coverage.py` — rule 3. Queries the **live migrated database**, because the
  policies are created inside `for table in (...)` loops and any grep-based checker gives
  false answers in both directions. Checks ENABLE, **FORCE**, a policy, and that the table is
  named in the isolation test.
- `verify_demo_path.sh` + `assert_statement_pdf.py` — `PLAN.md` hard rule 2, and the one
  documented blind spot in the test suite. `docs/03` says it outright: *"tests comparing
  integers stay green through this bug — read the rendered PDF."* So the script reads the
  rendered PDF and asserts `18.250` is present and `1.825.000` is not.
- `stop-gate.sh` — an agent cannot end its turn on red. Set `LOKARA_GATE=off` for
  exploratory sessions, `full` or `demo` when it matters.

---

## How to run a piece of work

The normal loop, for anything with a calculation in it:

1. **Spec** — `> Use spec-scribe to transcribe <spec> into docs/ and write the failing fixture.`
   It reports a docs path and a red test. If the spec contradicts `docs/`, it stops and asks —
   that is correct behaviour, not a failure.
2. **Implement** — `> Use engine-implementer to make packages/nk-engine/tests/test_x.py pass.`
   The `Stop` gate won't let it finish red.
3. **Audit** — `> Use boundary-auditor to review the diff` for anything touching tables,
   endpoints or roles. `> Use statement-reviewer` for anything touching output.
4. **You** read the findings and decide. Fixes go back through an implementer.
5. **Close** — `scripts/gate.sh demo`, then `git tag demo-green-<n>`, then write
   `LAST_OUTPUT.md`.

For work with no calculation in it (a screen, a refactor), skip step 1 and go straight to
`app-implementer` — but the reviewer step is not optional for anything a landlord will read.

### Parallelism — where it pays and where it doesn't

Subagents run one at a time by default and that is usually right. Implementer and tester on
the same code are inherently sequential; forcing them to run together only spends tokens.

Parallel review, on the other hand, is genuinely better than sequential review, because a
single reviewer anchors on the first problem it finds. At the end of a milestone, on a frozen
build, run the three read-only agents at once:

```
Review the M5 diff with three agents in parallel: boundary-auditor on isolation,
statement-reviewer on the rendered output, docs-reconciler on doc drift.
Do not let them fix anything — I want three separate reports.
```

**Agent teams** (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) are worth it for exactly one thing
here: competing-hypothesis debugging, where teammates argue each other out of a wrong theory.
They are the wrong tool for building a milestone — M-sized work is sequential, touches shared
files, and the known limitations (no session resumption, task status lag, the lead declaring
victory early) all bite hardest there.

---

## Things this system deliberately does not do

- **No agent decides what to build next.** That is `PLAN.md`'s execution order and the cut list.
- **No agent marks a milestone done.** Gates do, or you do.
- **No agent invents a legal number.** `spec-scribe` is instructed to report a gap instead of
  filling it, and `PLAN.md` hard rule 1 says an unbuilt milestone beats a guessed AfA rate.
- **No auto-merge, no auto-push.** `git push` is in the `ask` list in `.claude/settings.json`.

---

## Maintenance

The system is only as good as the invariants it encodes, so when a rule changes:

- New invariant that a script can check → add it to `scripts/`, wire it into `gate.sh`.
- New invariant that needs judgement → give it to an existing agent, or add one and give it a
  lane in `write-scope.sh`. Two agents sharing a lane is the failure mode to avoid.
- New golden figure on the statement → `docs/` first, then `assert_statement_pdf.py`. Never
  the other way round.
- An agent keeps making the same mistake → that is a missing line in its definition or a
  missing gate, not a reason to supervise it more closely.

Related: `CLAUDE.md` (contract) · `PLAN.md` (what and in what order) · `docs/` (specs) ·
`DEMO-RUNBOOK.md` (the human rehearsal the scripts can't replace).
