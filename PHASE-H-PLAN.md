# Phase H — cutover & cleanup (the concrete version)

> `MIGRATION-PLAN.md` §Phase H states the goal in four lines. This file is the executable
> version: exact inventory, exact edits, exact gates, exact rollback.
>
> **Goal:** no NestJS, no Prisma, no TypeScript engine mirrors. One Python backend, one TS
> frontend, one CI lane each, and docs that no longer say "pending migration".

---

## Why this comes before anything else

Not tidiness — **agent reliability**. A fresh Claude Code session that opens `apps/api/src`
today sees `app.module.ts`, `main.ts` and `prisma.service.ts` sitting next to `main.py`, and
has to work out which backend is real before it can do anything. Every subagent starts cold,
so it pays that tax every single time. `packages/nk-engine` currently ships two
implementations of the crown-jewel calculation in two languages; nothing in the tree says
which one the statement uses.

Deleting ~1,200 LOC and one CI lane makes every agent after it cheaper and less likely to
edit the dead copy.

---

## 0. Preconditions

```bash
git status                       # must be clean
git tag phase-h-start            # rollback anchor, in addition to demo-green-1
scripts/gate.sh full             # must be green BEFORE you start, or you can't attribute a break
```

If `gate.sh` is red before you begin, stop and fix that first. You cannot tell a Phase H
regression from a pre-existing failure otherwise.

---

## 1. Inventory — what is dead

Verified: **`apps/web` imports exactly one workspace package, `@lokara/ui`.** Nothing else on
the TS side is consumed by the frontend. Every reference to the packages below lives either
inside a file that is being deleted, or in `package.json` / `ci.yml`, both edited in §2.

### 1a. NestJS backend — `apps/api` (TS only; leave every `.py` alone)

```
apps/api/package.json
apps/api/tsconfig.json
apps/api/vitest.config.ts
apps/api/src/app.module.ts
apps/api/src/main.ts
apps/api/src/contract.ts
apps/api/src/env.ts
apps/api/src/auth/auth.types.ts
apps/api/src/auth/dev-token.controller.ts
apps/api/src/auth/public.decorator.ts
apps/api/src/auth/supabase-jwt.guard.ts
apps/api/src/auth/supabase-jwt.guard.test.ts
apps/api/src/demo/demo.controller.ts
apps/api/src/health/health.controller.ts
apps/api/src/prisma/prisma.service.ts
```

### 1b. TypeScript engine mirrors — `packages/*`

For each of `domain`, `nk-engine`, `heating-engine`, `rules-store`, `adapters`, `pdf`:
delete `package.json`, `tsconfig.json`, `vitest.config.ts`, and **every `.ts` file under
`src/`**. The `src/lokara_*/` Python trees, `tests/`, and `pyproject.toml` all stay.

Named explicitly, so nothing is missed:

```
packages/domain/src/{index,money,money.test,period,period.test,allocation-key}.ts
packages/nk-engine/src/{index,index.test}.ts
packages/heating-engine/src/{index,index.test}.ts
packages/rules-store/src/{index,store,store.test}.ts
packages/rules-store/src/rules/heating-split.ts
packages/adapters/src/{index,adapters.test}.ts
packages/adapters/src/bank/{bank-gateway,stub-bank-gateway}.ts
packages/adapters/src/email/{email-gateway,stub-email-gateway}.ts
packages/adapters/src/vision/{vision-gateway,stub-vision-gateway}.ts
packages/pdf/src/{index,render,render.test,demo,placeholder-statement}.ts
```

### 1c. Prisma — `packages/db`

```
packages/db/package.json
packages/db/tsconfig.json
packages/db/prisma/                 # schema.prisma, migrations/, seed.ts
packages/db/generated/              # gitignored, but delete the working copy too
packages/db/.env                    # Prisma-only; the Python side reads the root .env
```

Keep: `alembic.ini`, `alembic/`, `src/lokara_db/`, `tests/`, `pyproject.toml`,
`scripts/init-app-role.sql` (docker-compose mounts it).

### 1d. Stale artefact

```
packages/pdf/output/placeholder-statement.pdf    # produced by the deleted TS demo
```

**Do not delete:** `packages/ui/**`, `apps/web/**`, `bun.lock`, `turbo.json`,
`eslint.config.mjs`, `.prettierrc.json`, `tsconfig.base.json`, any `.py`, any
`pyproject.toml`, `uv.lock`.

---

## 2. Config edits

### `package.json` (root)

- `workspaces` → `["apps/web", "packages/ui"]`. **Must become an explicit list** — the
  current `apps/*` / `packages/*` globs will match directories that no longer contain a
  `package.json` and Bun will complain.
- Delete the `db:migrate` and `db:seed` scripts (Prisma-only; Alembic replaced them).
- `trustedDependencies` → drop `@nestjs/core`, `@prisma/client`, `@prisma/engines`,
  `prisma`, `playwright`. Keep `esbuild`, `sharp`, `unrs-resolver`.

### `turbo.json`

- Remove `"generated/**"` from the `build` outputs — that was the Prisma client.

### `.github/workflows/ci.yml` — the `ts` job

Delete from that job: the whole `services: postgres:` block, the `env:` block
(`DATABASE_URL`, `DIRECT_URL`, `SUPABASE_JWT_SECRET`), the
`bun run --filter @lokara/db migrate:deploy` step, and the
`bun run --filter @lokara/pdf install-browser` step. What remains:

```yaml
  ts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
        with:
          bun-version: 1.3.14
      - run: bun install --frozen-lockfile
      - run: bun run lint
      - run: bun run typecheck
      - run: bun run test
      - run: bun run build
```

The `python` job is untouched — it already carries Postgres, `LOKARA_REQUIRE_DB=1` and
`LOKARA_REQUIRE_PDF=1`. Consider adding one step at the end while you're in the file:

```yaml
      - run: uv run python scripts/check_engine_purity.py
```

### `.gitignore`

- Remove `packages/db/generated/` (nothing generates there any more). Leave the rest.

### `bun.lock`

- Run `bun install` after the workspace change and commit the regenerated lockfile.
  `bun.lockb` is already gitignored; delete the stray working copy if present.

---

## 3. Documentation de-bannering

The migration warnings are correct today and become actively misleading the moment the code
is gone — a fresh agent reads *"the scaffold may still be the older TS/NestJS/Prisma build"*
and goes looking for it.

| File | What to change |
| --- | --- |
| `CLAUDE.md` | Delete the `⚠️ Stack migration in progress (v4)` block. Change "The current `apps/api` + `packages/*-engine` scaffold is still the older TypeScript code" to a plain statement of the current stack. **Add a line pointing at `AGENTS.md`.** |
| `README.md` | Replace the "Works today (Phase A…)" run instructions with the real flow: `uv sync`, `bun install`, `docker compose up -d`, `uv run alembic -c packages/db/alembic.ini upgrade head`, `uv run playwright install chromium`, `uv run lokara-seed-demo`, then the two servers. Drop `bun run db:migrate` / `db:seed`. |
| `lokara-arch.md` | Keep the v4 stack revision note; delete the trailing "The scaffold code may still be the older TS/NestJS/Prisma build" clause. |
| `PLAN.md` | M0's "✅ built (interim TS stack)" block: the interim stack no longer exists. Rewrite as built-on-Python. Update the status line at the top: Phase H done, only Phase G (Expo) outstanding. |
| `MIGRATION-PLAN.md` | Mark Phase H ✅ with the date and the commit. Leave the rest as history — it explains why the tree looks the way it does. |
| `docs/04-web-app-structure.md` | Confirm the tree diagram matches reality after deletion. |

---

## 4. Verification — in this order

```bash
bun install                                  # regenerate the lockfile
scripts/gate.sh full                         # ruff, mypy, purity, pytest, eslint, tsc, vitest
scripts/verify_demo_path.sh --fresh          # empty DB -> migrate -> seed -> statement -> read the PDF
```

Then prove the dead code is actually gone:

```bash
# each of these must print nothing
grep -rn "nestjs\|@nestjs\|PrismaClient\|prisma" --include='*.ts' --include='*.tsx' \
  --include='*.json' --include='*.yml' . | grep -v node_modules | grep -v MIGRATION-PLAN
find apps/api packages/domain packages/nk-engine packages/heating-engine \
     packages/rules-store packages/adapters packages/pdf packages/db -name '*.ts'
```

And confirm nothing shrank by accident:

```bash
uv run pytest -q            # expect 196 passing (or more) — NOT fewer
bun run test                # vitest count drops: the deleted TS tests are gone. Expect the
                            # apps/web + packages/ui tests only. Record the new number.
```

> The vitest count **should** fall — that is the point. Note the before/after in the commit
> message so a future reader doesn't read it as a regression.

---

## 5. Commit & rollback

One commit, one concern:

```
chore(phase-h): remove the NestJS/Prisma scaffold and the TS engine mirrors

Deletes ~1,200 LOC of pre-migration TypeScript: the NestJS API, the Prisma
schema/client/seed, and the TS mirrors of domain/nk/heating/rules-store/
adapters/pdf. The TS workspace is now apps/web + packages/ui only.

CI: the ts lane drops Postgres, Prisma migrate and the Chromium install —
it is a pure frontend lane now. The python lane is unchanged.

Docs: migration banners removed from CLAUDE.md, README.md, lokara-arch.md,
PLAN.md. MIGRATION-PLAN Phase H marked done.

pytest 196 unchanged. vitest <before> -> <after> (deleted TS suites).
Demo path re-verified from an empty database.
```

Rollback: `git reset --hard phase-h-start`. Everything is on `feat/py-migration`; `main`
still holds the TS M0 as the historical fallback.

---

## 6. Prompts to hand to Claude Code

Run these **in order, one session each**, per `MIGRATION-PLAN.md` §8 ("one phase per
session"). Each ends with an explicit stop.

---

### Prompt H1 — delete

```
Read CLAUDE.md, PHASE-H-PLAN.md and MIGRATION-PLAN.md (Phase H) first.

Execute PHASE-H-PLAN.md sections 1 and 2 only: delete the dead TypeScript inventory
and apply the config edits. Do not touch documentation yet — that is H2.

Before you start: `git tag phase-h-start` and confirm `scripts/gate.sh full` is green.
If it is red, stop and report; I need a clean baseline to attribute a break.

Rules for this task:
- Delete ONLY what section 1 lists. Every `.py`, every `pyproject.toml`, `uv.lock`,
  `packages/ui/**` and `apps/web/**` stay. If you think something else is dead, tell me
  rather than deleting it.
- `packages/db/alembic/`, `alembic.ini`, `src/lokara_db/`, `tests/` and
  `scripts/init-app-role.sql` all stay — only the Prisma side goes.
- After the workspace change in package.json, run `bun install` and commit the
  regenerated `bun.lock`.
- Then run, in this order: `scripts/gate.sh full`, then
  `scripts/verify_demo_path.sh --fresh`, then the two grep/find checks in section 4.
  Paste me the actual output of all of them, including the pytest and vitest counts.

Do not commit until every check in section 4 has passed. Then commit with the message
in section 5, filling in the real vitest before/after numbers.

Stop after committing. Do not start H2, and do not start M5.
```

---

### Prompt H2 — de-banner the docs

```
Phase H section 3. The dead TypeScript is gone, so the migration banners in the docs are
now wrong and will actively mislead a fresh agent into looking for a NestJS backend.

Work through the table in PHASE-H-PLAN.md section 3, file by file. For each one, show me
the diff and say in one line why the old text is now false.

Constraints:
- Do not restructure or "improve" these documents. Remove what is untrue and adjust the
  status lines. Nothing else.
- CLAUDE.md gets one addition: a pointer to AGENTS.md, in the "How to work" section.
- Leave MIGRATION-PLAN.md's body intact — it is the record of why the tree looks like
  this. Only mark Phase H done, with the date and the H1 commit hash.
- If a doc says something you cannot verify from the code, do not delete it and do not
  soften it — list it for me. That is docs-reconciler's job, not a cleanup pass.

Commit as `docs: retire the v4 migration banners (Phase H)`.
Then stop.
```

---

### Prompt H3 — adopt the agent system

```
Read AGENTS.md. The agent system is already committed under .claude/ and scripts/.
Your job is to verify it actually works in this repo, not to redesign it.

1. Confirm Claude Code sees all six agents (/agents) and that the hooks in
   .claude/settings.json are loading.
2. Prove the write-scope hook. Spawn `boundary-auditor` and ask it to fix something
   trivial — it must be blocked by .claude/hooks/write-scope.sh. Then spawn
   `engine-implementer` and ask it to edit a test file — it must also be blocked.
   Paste me both refusals. If either succeeds, the hook is broken and that is the
   finding.
3. Run each gate once and paste the output:
   `uv run python scripts/check_engine_purity.py`
   `uv run python scripts/check_rls_coverage.py` (after docker compose up -d and
    alembic upgrade head)
   `scripts/gate.sh fast`
   `scripts/verify_demo_path.sh`
4. `scripts/assert_statement_pdf.py` asserts goldens I derived from docs/03, docs/06 and
   DEMO-RUNBOOK.md. Verify each MUST_APPEAR string is actually in the rendered PDF and
   each MUST_NOT_APPEAR is actually absent. If a golden is wrong, tell me which and why —
   do NOT relax the assertion to make it pass. A canary that was tuned until it went
   green is worse than no canary.

Report what works, what doesn't, and what you had to change. Fix only mechanical
breakage (a wrong path, a missing chmod, a jq that isn't installed). Anything that looks
like a design problem, bring to me.

Then stop.
```

---

### Prompt H4 — the first real run (M5, through the system)

```
M5 per PLAN.md: identity, accounts, roles, RLS, portals. Run it through the agent
system rather than as one session.

Sequence:
1. Use `spec-scribe` to check docs/02 against what M5 actually needs — Person/Account/
   Membership, Landlord, Renter, SelfUsePeriod, the three roles, AccountShape — and to
   write the failing tests first, including the RLS isolation cases for every new table.
   It must not write source.
2. Then `engine-implementer` for the models and the Alembic migration. Every new tenant
   table needs account_id + ENABLE + FORCE + a policy + a line in test_rls_isolation.py.
   `scripts/check_rls_coverage.py` must go green before anything else happens.
3. Then `app-implementer` for the endpoints and the portal switcher.
4. Then `boundary-auditor` on the whole diff, read-only. This is the milestone it exists
   for: an EMPLOYEE with no building assignments must see nothing, and a renter context
   must expose zero landlord data — verified in app logic AND in RLS, per the M5 DoD.

Do not let any agent both write a test and satisfy it. Do not mark M5 done because the
summary sounds finished — it is done when `scripts/gate.sh demo` is green and the
auditor's report is clean.

Stop after step 1 and show me the failing tests before you go on.
```

---

## 7. Risks

| Risk | Why it's plausible | Mitigation |
| --- | --- | --- |
| Deleting a `.py` alongside a `.ts` | The packages are polyglot and the filenames rhyme (`index.ts` next to `__init__.py`) | Section 1 lists files explicitly; the `find … -name '*.ts'` check in §4 catches over-deletion by leaving pytest red |
| Bun refuses to install | `workspaces` globs matching directories with no `package.json` | Explicit two-entry list in §2 |
| A doc edit removes something still true | Migration notes and architectural notes sit in the same paragraphs | H2 forbids restructuring and requires a per-file justification |
| CI TS lane still expects Postgres | The service block and the migrate step are in different parts of the job | §2 names both; CI will fail loudly, not silently |
| Losing the escape hatch | `main` is the TS fallback | `main` is untouched; `phase-h-start` and `demo-green-1` tags stay |

**Highest-leverage next action:** run Prompt H1.
