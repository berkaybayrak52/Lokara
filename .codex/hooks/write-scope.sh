#!/usr/bin/env bash
# PreToolUse guard: each agent may only write inside its own lane.
#
# Why this exists. The most common failure in a producer/critic agent setup is the
# critic "fixing" a failure by weakening the assertion, or the producer deleting a
# refusal it read as a bug. This repo already documents the second one:
#
#   docs/03: "If the energy/cost total or a denominator is absent, the API refuses and
#             explains, in German. Don't 'fix' the refusal by adding a fallback estimate."
#
# An agent that can edit both the engine and its test can make any red thing green.
# Partitioning writes so no two agents share a file is what makes a critic's report
# worth reading.
#
# Claude Code sends this hook the tool call as JSON on stdin. Subagent calls carry
# `agent_type`; the main conversation does not, so it defaults to "main" and stays
# unrestricted -- you are the lead, not a worker.
#
# HONEST LIMIT: this guards Edit/Write/NotebookEdit and obvious Bash redirection. It is
# a guardrail, not a sandbox: an agent determined to write out of lane via a python
# heredoc will succeed. That is why every write-capable agent also runs with
# `isolation: worktree`, so a stray write lands in a throwaway copy of the repo and
# shows up in the diff you review.

set -uo pipefail

input=$(cat)
jqr() { printf '%s' "$input" | jq -r "$1" 2>/dev/null || true; }

agent=$(jqr '.agent_type // "main"')
tool=$(jqr '.tool_name // empty')
path=$(jqr '.tool_input.file_path // empty')
cmd=$(jqr '.tool_input.command // empty')

root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
rel="${path#"$root"/}"
rel="${rel#./}"

deny() {
  {
    echo "write-scope: agent '$agent' may not write $1"
    echo
    echo "$2"
    echo
    echo "If this file genuinely belongs to this agent, change .claude/hooks/write-scope.sh"
    echo "and say why in the commit. Do not work around it by shelling out."
  } >&2
  exit 2
}

# --- Bash: catch the obvious escapes, then get out of the way ----------------------
if [[ "$tool" == "Bash" ]]; then
  case "$agent" in
    main) exit 0 ;;
    boundary-auditor|statement-reviewer|docs-reconciler)
      if [[ "$cmd" =~ [^\>\<]\>[^\>]|[[:space:]]tee[[:space:]]|sed[[:space:]]+-i|(^|[[:space:]])rm[[:space:]] ]]; then
        deny "via Bash redirection" "This agent is read-only: it reports, it does not fix."
      fi
      ;;
  esac
  exit 0
fi

case "$tool" in
  Edit|Write|NotebookEdit|MultiEdit) ;;
  *) exit 0 ;;
esac
[[ -z "$rel" ]] && exit 0

case "$agent" in

  main) exit 0 ;;

  # Owns the specs and the fixtures derived from them. Never source: a fixture written
  # by whoever is about to satisfy it proves nothing (PLAN.md hard rule 1).
  spec-scribe)
    case "$rel" in
      docs/*|PLAN.md|MIGRATION-PLAN.md|lokara-arch.md|DEMO-RUNBOOK.md|AGENTS.md) exit 0 ;;
      */tests/*|*_test.py|test_*.py|*.test.ts|*.test.tsx) exit 0 ;;
      *) deny "$rel" "spec-scribe owns docs/ and tests/ only. It writes the spec and the golden
fixture; an implementer then makes the fixture pass." ;;
    esac ;;

  # Owns the pure/backend packages. Cannot touch tests, so it cannot move the goalposts.
  engine-implementer)
    case "$rel" in
      */tests/*|*_test.py|test_*.py|*.test.ts)
        deny "$rel" "The implementer does not write its own tests. Ask spec-scribe for the fixture
first (PLAN.md hard rule 1: no calculation without its golden fixture)." ;;
      packages/*/src/*|packages/db/alembic/*) exit 0 ;;
      *) deny "$rel" "engine-implementer writes packages/*/src and packages/db/alembic only." ;;
    esac ;;

  # Owns the framework side: API routers, web pages, UI components, the PDF template.
  app-implementer)
    case "$rel" in
      */tests/*|*_test.py|test_*.py|*.test.ts|*.test.tsx)
        deny "$rel" "The implementer does not write its own tests. Ask spec-scribe." ;;
      apps/api/src/*|apps/web/src/*|packages/ui/src/*|packages/pdf/src/*) exit 0 ;;
      apps/web/*.ts|apps/web/*.mjs|apps/web/*.json) exit 0 ;;
      *) deny "$rel" "app-implementer writes apps/*/src and packages/{ui,pdf}/src only. Engine and
domain packages belong to engine-implementer; docs belong to spec-scribe." ;;
    esac ;;

  # Read-only by design. Their whole value is having no way to make red green.
  boundary-auditor|statement-reviewer|docs-reconciler)
    deny "$rel" "This agent is read-only: it reports findings to you, and you decide. An auditor
that can edit is an auditor you cannot trust." ;;

  *)
    deny "$rel" "Unknown agent type '$agent' -- add its lane to .claude/hooks/write-scope.sh." ;;
esac
