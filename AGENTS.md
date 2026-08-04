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
the two **implementers** also run `isolation: worktree`, and stray writes land in a throwaway
copy of the repo rather than in your tree.

`spec-scribe` deliberately does **not** get a worktree. It writes only `docs/**` and tests,
the hook already fences it, and anything stray shows up in `git status` immediately. The
isolation bought nothing there and cost a copy-back on every run.

### Worktrees do not sync back

A worktree agent reports success while your tree is still clean. Its edits stay in
`.claude/worktrees/agent-<id>/` on a `worktree-agent-<id>` branch, **uncommitted**, and
nothing merges them for you. After every worktree run:

```bash
W=.claude/worktrees/agent-<id>
git -C "$W" status --short        # what it actually touched — trust this, not the report
cp "$W/<path>" <path>             # copy each file across
scripts/gate.sh fast              # re-run the gates HERE
git worktree remove --force "$W"  # only once the diff is in and verified
```

Re-run the gates in the main tree rather than trusting the agent's output — a worktree can be
green on a stale base. Read the agent's factual claims the same way: counts, survey results
and "I verified X" are worth re-deriving, and both runs so far have had one number wrong.

**A worktree agent must not run `scripts/verify_demo_path.sh`, and cannot.** The script does
`docker compose up`, which derives its project name from the working directory — so from a
worktree it tries to start a *second* stack and dies on
`Conflict. The container name "/lokara-db" is already in use`, after creating a stray volume
and network you then have to remove by hand.

Generalise from that: **DB-backed gates run in the main tree only.** The Postgres container is
a single shared resource, and a worktree agent driving it is driving *your* database —
`alembic upgrade`/`downgrade`, seeds and probes from a worktree all land in the same instance
the main tree is using. That is acceptable for `check_rls_coverage.py`, `check_fk_isolation.py`
and `pytest` (read-mostly, and a migration left at head is the state you want anyway); it is not
acceptable for anything that recreates the stack. One run cost the demo seed three tables when
an agent misread a swallowed `downgrade` and ran it twice. So: let agents run the query-level
gates, and run `verify_demo_path.sh` yourself after the copy-back.

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
uv run python scripts/check_fk_isolation.py     # docs/02 isolation rule (needs a migrated DB)
```

**What each one turns from discipline into a command:**

- `check_engine_purity.py` — rule 1. AST-level: forbidden imports, no I/O, no clock, and
  engines never importing `rules-store`. Runs on every Python edit via `PostToolUse`.
- `check_rls_coverage.py` — rule 3. Queries the **live migrated database**, because the
  policies are created inside `for table in (...)` loops and any grep-based checker gives
  false answers in both directions. Checks ENABLE, **FORCE**, a policy, and that the table is
  named in the isolation test.
- `check_fk_isolation.py` — the other half of rule 3, which RLS structurally cannot cover.
  Postgres checks foreign keys with **RLS bypassed**, so a correctly stamped row can still
  point at another account's parent. Fails on any FK whose child and parent are both
  account-scoped and which is not composite on `(id, account_id)` — and on `MATCH FULL`
  over a nullable link, which would silently make an optional relationship mandatory.
- `verify_demo_path.sh` + `assert_statement_pdf.py` — `PLAN.md` hard rule 2, and the one
  documented blind spot in the test suite. `docs/03` says it outright: *"tests comparing
  integers stay green through this bug — read the rendered PDF."* So the script reads the
  rendered PDF and asserts `18.250` is present and `1.825.000` is not.
- `stop-gate.sh` — an agent cannot end its turn on red. Set `LOKARA_GATE=off` for
  exploratory sessions, `full` or `demo` when it matters.

**`gate.sh demo` is expected red until M5 — and step 2 is now two DB gates, not one.**
`verify_demo_path.sh` runs `check_rls_coverage.py` and then `check_fk_isolation.py`, and gates
on each one's **exit code**. Their status differs, so read them separately:

| Gate | Status | Why |
| --- | --- | --- |
| `check_fk_isolation.py` | **green** since the FK-Isolation slice (`0004`) | all 17 tenant-to-tenant edges are composite |
| `check_rls_coverage.py` | **red**, 2 problems | `landlord` + `self_use_period` have policies no test exercises — M5 populates those tables |

Note the ordering trap: RLS runs **first**, so `verify_demo_path.sh` aborts there and never
reaches the FK step. Run `uv run python scripts/check_fk_isolation.py` directly to see it
green — do not conclude from a red demo path that the FK work regressed. Everything
downstream (seed → statement → PDF → `assert_statement_pdf.py`) still passes when run by
hand. And do not add a tolerance to either gate to make the path green: a canary tuned until
it goes green is worse than no canary.

---

## How to run a piece of work

### Every slice gets its own branch

**Decision, 03.08, after CI went red on `main` for exactly this reason.** The spec-before-
implementation split is not optional here — `spec-scribe` writes the failing test, and only
then may an implementer satisfy it. That guarantees a **red window on every slice**, and
`main` is the wrong place to spend it: `.github/workflows/ci.yml` runs `uv run pytest` with
`LOKARA_REQUIRE_DB=1`, so a committed red fixture is a red push, indistinguishable from a
real regression by anyone reading the badge.

So:

```bash
git switch main && git pull      # ALWAYS from main — see below
git switch -c slice/<name>       # BEFORE dispatching spec-scribe
# ... red tests commit, then the implementation commit(s), on the branch
scripts/gate.sh full             # green in the main tree, on the branch
git switch main && git merge --no-ff slice/<name>
git push                         # main is only ever pushed green
git push -u origin slice/<name>  # push the slice too: ci.yml's slice/** trigger
                                 # fires on push, and on nothing else
```

**A slice is cut from `main`, never from another slice branch.** Branching
`slice/b` off `slice/a` because `b` "needs the spec from `a`" couples them
permanently: merging `b` drags every commit of `a` along with it, whether or not
`a` was ready, and the two red windows become one. If `b` genuinely needs `a`,
merge `a` to `main` first and cut `b` from the new tip — that is a two-command
fix before the fact and a rebase after it. (Cost 03.08: `slice/heating-typography`
was cut from `slice/heating-disclosure` and had to be re-cut with
`git rebase --onto main <old-base> slice/heating-typography`.)

⚠️ **`git reset --hard origin/<branch>` when local is ahead silently discards
those commits.** No prompt, no summary, and the branch afterwards looks
plausible — it just quietly lost work. Whether that work is still recoverable
depends on something git never mentions at the prompt: another ref pointing at
the same objects, or the reflog. On 03.08 the discarded commits stayed reachable
the whole time, because `slice/heating-typography` had already been cut from them
— a property of the branch layout that happened to hold, not a safety net you can
count on. Reach for `git status` and `git log origin/<branch>..HEAD` first; if
that list is non-empty, `reset --hard` is not the command you want. `git pull
--ff-only` fails loudly instead, which is the point.

The red tests and the implementation land on the **same** branch. Merge to `main` only once
the gates are green. This does not relax the lane rules — `spec-scribe` still cannot satisfy
its own test, it just does so on a branch instead of on the trunk.

The worktree note above still applies and is a different thing: worktrees isolate an *agent's
writes*, slice branches isolate a *red window*. An implementer in a worktree branches from
`HEAD`, so create the slice branch first and let the worktree fork from it.

### The loop

The normal loop, for anything with a calculation in it:

1. **Spec** — `> Use spec-scribe to transcribe <spec> into docs/ and write the failing fixture.`
   It reports a docs path and a red test. If the spec contradicts `docs/`, it stops and asks —
   that is correct behaviour, not a failure.
2. **Implement** — `> Use engine-implementer to make packages/nk-engine/tests/test_x.py pass.`
   The `Stop` gate won't let it finish red.
3. **Audit** — `> Use boundary-auditor to review the diff` for anything touching tables,
   endpoints or roles. `> Use statement-reviewer` for anything touching output.
4. **You** read the findings and decide. Fixes go back through an implementer.
5. **Close** — `scripts/gate.sh demo`, **merge the slice branch to `main`**, then
   `git tag demo-green-<n>`, then write `LAST_OUTPUT.md`.

**When a slice claims to change the document — or claims not to — record
`scripts/pdf_fingerprint.sh` before and after in `LAST_OUTPUT.md`.** Both directions are claims, and
both are cheap to check and easy to assert instead. An engine refactor that swears it is invisible
and a typography slice that swears it is visible are the same bet, and the fingerprint settles it in
one line. It is deliberately **not** in `gate.sh`: most slices are supposed to move the page, so a
standing assertion would be red by default and ignored within a week. Nothing else prompts you —
that is why it is written here, in the step where you are already writing the handoff.

For work with no calculation in it (a screen, a refactor), skip step 1 and go straight to
`app-implementer` — but the reviewer step is not optional for anything a landlord will read.

**A handoff that accuses — "unauthorized change", "the agent did this unprompted", "fabricated" —
is verified against git before anyone acts on it.** `git log`, `git show`, `md5` the file against
what you actually wrote. A session that compacts mid-task reconstructs its own history from a
summary and writes the reconstruction fluently and confidently; fluency is not evidence. On 04.08
such a claim came within one command of a history rewrite over a commit that was correct in every
particular — the attribution it called fabricated was byte-accurate, and the "unprompted" actions
were all in the prompt. The cost of checking is one `git show`. The cost of not checking is
reverting good work and distrusting a lane that was behaving.

**A tool the lead hands you is unverified until it has run on *your* machine.** The same standard
this file applies to agent claims applies to the lead's. `scripts/pdf_fingerprint.sh` arrived
described as verified — and it was, on Linux. It piped to `md5sum`, which darwin does not ship, and
`set -uo pipefail` without `-e` let the failure through: it printed an **empty hash and exited 0**.
Before and after would have compared equal, which is precisely the failure the script exists to
catch — a verification tool that passes by producing nothing. "It works on the machine it was
written on" is a claim about that machine. Run it, look at the output, and check it against a value
you already know before you trust it with a question that matters.

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
