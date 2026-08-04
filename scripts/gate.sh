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

set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.bun/bin:$PATH"

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

# --- always ------------------------------------------------------------------------
run "ruff"                uv run ruff check .
run "ruff format"         uv run ruff format --check .
run "mypy --strict"       uv run mypy
run "engine purity"       uv run python scripts/check_engine_purity.py

case "$LEVEL" in
  fast)
    # Engines and domain only: pure, no DB, no Chromium. Fast enough for a tight loop.
    run "pytest (pure packages)" uv run pytest -q \
      packages/domain/tests packages/nk-engine/tests \
      packages/heating-engine/tests packages/rules-store/tests
    ;;
  full|demo)
    run "pytest (all)"      uv run pytest -q
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
  exit 1
fi

printf '\n\033[32mgate (%s): green\033[0m\n' "$LEVEL"
