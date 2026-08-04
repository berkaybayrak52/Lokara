#!/usr/bin/env bash
# PostToolUse: the cheap checks, on the file that just changed.
#
# Deliberately fast (< ~2s). The full gate runs at Stop; this is the tight loop, so it
# only runs things that answer instantly and unambiguously:
#   - ruff on the edited Python file
#   - engine purity on the edited file, if it lives in a purity zone
#
# Exit 2 feeds stderr back to the agent as an error it must address.

set -uo pipefail
# Grade the tree the agent is actually working in, not the one the session started in.
# $CLAUDE_PROJECT_DIR points at the main checkout, so inside a worktree this graded the
# wrong files -- an agent that had done everything right ended on a red gate for work that
# was not in the directory under test. Cost two sessions. The cwd toplevel is the tree
# whose changes are being graded; CLAUDE_PROJECT_DIR is only the fallback.
cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || cd "${CLAUDE_PROJECT_DIR:-$PWD}"

input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[[ -z "$path" || ! -f "$path" ]] && exit 0

out=""
rc=0

if [[ "$path" == *.py ]]; then
  if ! ruff_out=$(uv run ruff check "$path" 2>&1); then
    out+="$ruff_out"$'\n'; rc=2
  fi
  if ! purity_out=$(uv run python scripts/check_engine_purity.py "$path" 2>&1); then
    out+="$purity_out"$'\n'; rc=2
  fi
fi

if (( rc != 0 )); then
  printf '%s' "$out" >&2
  exit 2
fi
exit 0
