#!/usr/bin/env bash
# Mechanize PLAN.md hard rule 2: "The demo path is sacred."
#
#   clean DB -> migrate -> seed -> statement -> PDF -> the numbers a human reads
#
# Until now that was a rule people followed. This makes it a command that fails.
#
# What this covers:   the data-and-numbers path, end to end, through the real engines,
#                     the real rules-store and the real renderer.
# What it does NOT:   the six-screen browser walkthrough in DEMO-RUNBOOK.md. Hydration,
#                     nav, autosave and the WCAG surface still need a human (or the
#                     statement-reviewer agent). Green here means the numbers are right,
#                     not that the demo is rehearsed.
#
# Usage:
#   scripts/verify_demo_path.sh            # against the running dev database
#   scripts/verify_demo_path.sh --fresh    # destroy the pg volume and start from empty
#
# --fresh is the honest version of the check (PLAN.md M3 DoD says "from a clean login")
# and it DELETES the local Postgres volume. It never touches Supabase.

set -euo pipefail

cd "$(dirname "$0")/.."

FRESH=0
[[ "${1:-}" == "--fresh" ]] && FRESH=1

PDF="packages/pdf/output/nk-heating-statement-demo.pdf"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[31mFAILED: %s\033[0m\n' "$1" >&2; exit 1; }

# --- 0. toolchain ------------------------------------------------------------------
command -v uv >/dev/null     || fail "uv is not on PATH"
command -v docker >/dev/null || fail "docker is not on PATH"

# DEMO-RUNBOOK Trap 1: Homebrew's bun shadows ~/.bun/bin. Harmless if already correct.
export PATH="$HOME/.bun/bin:$PATH"

# --- 1. database -------------------------------------------------------------------
if [[ $FRESH -eq 1 ]]; then
  step "Destroying the local Postgres volume (--fresh)"
  docker compose down -v
fi

step "Starting Postgres"
docker compose up -d

printf 'waiting for pg_isready'
for _ in $(seq 1 40); do
  if docker compose exec -T db pg_isready -U lokara -d lokara >/dev/null 2>&1; then
    printf ' ok\n'; break
  fi
  printf '.'; sleep 1
done
docker compose exec -T db pg_isready -U lokara -d lokara >/dev/null 2>&1 \
  || fail "Postgres did not become ready"

# --- 2. schema ---------------------------------------------------------------------
step "alembic upgrade head"
uv run alembic -c packages/db/alembic.ini upgrade head || fail "migrations did not apply"

# Both isolation gates run, and BOTH report, before either aborts the path. Short-circuiting
# on the first one hid the second: while check_rls_coverage.py is red on landlord +
# self_use_period, an FK regression could not surface here at all. A gate you cannot reach
# is not a gate.
ISOLATION_FAILED=()

step "RLS coverage (CLAUDE.md rule 3 — isolation enforced twice)"
uv run python scripts/check_rls_coverage.py || ISOLATION_FAILED+=("RLS coverage")

step "FK isolation (docs/02 — RLS does not cover referential integrity)"
uv run python scripts/check_fk_isolation.py || ISOLATION_FAILED+=("FK isolation")

if (( ${#ISOLATION_FAILED[@]} )); then
  fail "isolation gate(s) red: $(IFS=', '; echo "${ISOLATION_FAILED[*]}") — see above"
fi

# --- 3. seed -----------------------------------------------------------------------
step "Seeding the demo scenario (docs/06)"
uv run lokara-seed-demo || fail "demo seed failed"

# --- 4. statement + PDF ------------------------------------------------------------
step "Rendering the statement through the real engines"
rm -f "$PDF"
uv run lokara-pdf-demo || fail "statement render failed"
[[ -s "$PDF" ]] || fail "no PDF at $PDF"

# --- 5. read what a human would read ------------------------------------------------
step "Asserting the rendered numbers (docs/03 goldens + de-scaling canaries)"
uv run --with pypdf python scripts/assert_statement_pdf.py "$PDF" \
  || fail "the PDF does not read correctly — see above"

# --- 6. purity ----------------------------------------------------------------------
step "Engine purity (CLAUDE.md rule 1)"
uv run python scripts/check_engine_purity.py || fail "an engine imports something it must not"

printf '\n\033[32mdemo path green.\033[0m  PDF: %s\n' "$PDF"
printf 'Tag it if this is a milestone end:  git tag demo-green-<n>\n'
