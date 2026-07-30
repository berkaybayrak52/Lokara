#!/usr/bin/env bash
# Stop / SubagentStop: an agent cannot end its turn on red.
#
# PLAN.md hard rule 2 -- "the demo path is sacred" -- and the per-milestone DoDs in
# CLAUDE.md were both enforced by discipline. This makes them mechanical: exit 2 sends
# the failure text back to the agent, which then keeps working instead of handing you
# a summary that says "done" over a broken suite. That is the single most valuable
# thing in this setup, because "task status can lag" is the known weak point of every
# LLM-managed workflow.
#
# Level is controlled by LOKARA_GATE (fast | full | demo | off), default "fast".
# Set LOKARA_GATE=off for exploratory sessions where you want no gate at all.

set -uo pipefail
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

level="${LOKARA_GATE:-fast}"
[[ "$level" == "off" ]] && exit 0

# Don't loop forever: if the gate already ran and reported, let the turn end so the
# human can look. Claude Code sets stop_hook_active when it re-entered after a block.
input=$(cat)
active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null || echo false)
[[ "$active" == "true" ]] && exit 0

if ! out=$(scripts/gate.sh "$level" 2>&1); then
  {
    echo "The green gate failed. Do not end the turn here."
    echo
    printf '%s\n' "$out" | tail -60
    echo
    echo "Fix it, or revert. PLAN.md hard rule 2: a working demo beats a broader broken one."
  } >&2
  exit 2
fi
exit 0
