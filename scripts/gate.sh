#!/usr/bin/env bash
# The green gate. Everything CLAUDE.md calls a Definition of Done, as one command.
#
#   scripts/gate.sh fast    lint + types + unit tests, no database, no browser  (~seconds)
#   scripts/gate.sh full    fast + the whole pytest suite + both TS lanes       (~CI parity)
#   scripts/gate.sh demo    full + scripts/verify_demo_path.sh                  (milestone end)
#
# Called by the Stop hook in .claude/settings.json, so an agent cannot end its turn on
# red. Exit 2 there is what feeds the failure back and keeps it working; this script
# exits 1 and the hook wrapper translates.
#
# One exception, and only at `fast`: a `.lokara-red` sentinel declares a red window that
# CLAUDE.md § 10 itself requires. See scripts/check_red_sentinel.py.

set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.bun/bin:$PATH"

# docs/01 D9: ApiSettings requires ENVIRONMENT and deliberately has no default, so the
# eleven bare ApiSettings() sites under apps/api/tests fail without it. This is the local
# counterpart of ci.yml's `ENVIRONMENT: ci`.
#
# It is exported here rather than written into .env, and the difference is not cosmetic.
# pydantic-settings consults the .env file whenever the process env has no value, so a
# .env line survives monkeypatch.delenv -- and test_environment_guard.py's "a missing
# ENVIRONMENT is a startup failure" would then pass for the wrong reason, locally,
# forever, while still being genuinely red in CI (which has no .env). A guard whose own
# test cannot fail is an assertion. Verified, not assumed: with the line in .env, that
# test reports environment='local' instead of raising.
#
# `:-` so an explicit `ENVIRONMENT=production scripts/gate.sh` still overrides -- which is
# a useful thing to run: it should go red, and that is the guard working.
export ENVIRONMENT="${ENVIRONMENT:-local}"

LEVEL="${1:-fast}"
FAILED=()

run() {
  local label="$1"; shift
  printf '\n\033[1m==> %s\033[0m\n' "$label"
  if "$@"; then
    printf '\033[32m    ok\033[0m\n'
  else
    printf '\033[31m    FAILED\033[0m\n'
    FAILED+=("$label")
  fi
}

# --- the deliberate red window -----------------------------------------------------
# CLAUDE.md § 10 forbids one agent from writing both a test and the implementation that
# satisfies it, so every calculation slice has a window where the fixture is red on
# purpose. This gate is what the Stop hook runs, and it was rejecting turn-endings inside
# that window -- 12 of 19 subagent blocks were spec-scribe, whose deliverable IS the
# failing fixture. `.lokara-red` names the slice and the reason; see
# scripts/check_red_sentinel.py for why it is announced at `fast` and fatal at full/demo.
SENTINEL_ACTIVE=""
sentinel_out=$(uv run python scripts/check_red_sentinel.py 2>&1) || SENTINEL_ACTIVE="yes"
if [[ -n "$SENTINEL_ACTIVE" ]]; then
  printf '\n\033[1m==> red window\033[0m\n'
  printf '%s\n' "$sentinel_out"
  if [[ "$LEVEL" == "fast" ]]; then
    printf '\033[33m    declared — red is expected here and does not block\033[0m\n'
  else
    printf '\033[31m    FAILED — remove .lokara-red before closing or merging\033[0m\n'
    FAILED+=("red window")
  fi
fi

# --- always ------------------------------------------------------------------------
run "ruff"                uv run ruff check .
run "ruff format"         uv run ruff format --check .
run "mypy --strict"       uv run mypy
run "engine purity"       uv run python scripts/check_engine_purity.py
# Nothing in this repo reads .codex/, so it drifts unnoticed. It once told an agent that
# rounding is largest-remainder after CLAUDE.md had split the rule per engine -- an
# instruction to revert correct code. Cheap check; no DB, no network.
run "agent parity"        uv run python scripts/check_agent_parity.py
run "correspondence retirement" uv run python scripts/check_correspondence_retirement.py
run "retirement checker test" uv run pytest -q scripts/tests/test_correspondence_retirement.py
run "red sentinel test"  uv run pytest -q scripts/tests/test_red_sentinel.py

case "$LEVEL" in
  fast)
    # Engines and domain only: pure, no DB, no Chromium. Fast enough for a tight loop.
    run "pytest (pure packages)" uv run pytest -q \
      packages/domain/tests packages/nk-engine/tests \
      packages/heating-engine/tests packages/rules-store/tests \
      packages/matching-engine/tests
    ;;
  full|demo)
    # LOKARA_REQUIRE_DB / LOKARA_REQUIRE_PDF turn an unreachable Postgres or a missing
    # Chromium from a pytest.skip into a hard failure. Only ci.yml set them, so with
    # Docker down this gate went GREEN with 93 tests skipped -- including the entire RLS
    # isolation suite, i.e. CLAUDE.md rule 3. Eight sessions of "local green" rested on
    # that. A gate that cannot tell a skipped suite from a passing one is not a gate.
    run "pytest (all)"      env LOKARA_REQUIRE_DB=1 LOKARA_REQUIRE_PDF=1 uv run pytest -q
    run "pre-context reads" uv run python scripts/check_pre_context_reads.py
    run "eslint"            bun run lint
    run "tsc"               bun run typecheck
    run "vitest"            bun run test
    # Not in `fast`: mid-task stops legitimately predate the handoff. At full/demo you are
    # closing something, and that is when a stale LAST_OUTPUT.md starts lying to the next
    # session.
    run "handoff"           scripts/check_handoff.sh
    ;;
  *)
    echo "usage: scripts/gate.sh [fast|full|demo]" >&2; exit 2 ;;
esac

if [[ "$LEVEL" == "demo" ]]; then
  run "demo path" scripts/verify_demo_path.sh
fi

if (( ${#FAILED[@]} )); then
  printf '\n\033[31mgate (%s): %d failed — %s\033[0m\n' \
    "$LEVEL" "${#FAILED[@]}" "$(IFS=', '; echo "${FAILED[*]}")" >&2
  # A declared red window reports every failure above and still exits 0, but only at
  # `fast`. That is the whole point: the agent sees exactly what is red, and is not forced
  # to either close a window it is forbidden to close or spend another turn being told so.
  if [[ -n "$SENTINEL_ACTIVE" && "$LEVEL" == "fast" ]]; then
    printf '\033[33mred window declared by .lokara-red — not blocking. Remove it to close the slice.\033[0m\n' >&2
    exit 0
  fi
  exit 1
fi

printf '\n\033[32mgate (%s): green\033[0m\n' "$LEVEL"
