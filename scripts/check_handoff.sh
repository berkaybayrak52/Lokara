#!/usr/bin/env bash
# The last rule in CLAUDE.md that was enforced by nothing.
#
#   "Write your end-of-task summary to LAST_OUTPUT.md at the repo root, overwriting it
#    each time — it's the handoff other tools read."
#
# Every other rule in the contract has been mechanized: purity is a script, RLS coverage
# is a script, the demo path is a script, tests-before-code is the write-scope hook,
# docs-before-calculation is spec-scribe's lane. This one stayed discipline, and on the
# heating-disclosure spec it was silently skipped — two commits landed while LAST_OUTPUT.md
# still read "Nothing started". A stale handoff is worse than no handoff: the next session
# trusts it and redoes the work, or starts something that conflicts.
#
# The check is content-based, not mtime-based, because a checkout or a rebase touches
# mtimes without changing anything. LAST_OUTPUT.md must name the current HEAD — which is
# the convention already in use ("`main` at `bdd15a6`"). So this fails in exactly one
# situation: HEAD has moved past what the handoff records.
#
# A session that committed nothing passes, correctly: HEAD is unchanged, so the sha
# already in the file is still the right one.

set -uo pipefail
cd "$(dirname "$0")/.."

HANDOFF="LAST_OUTPUT.md"

if ! head_sha=$(git rev-parse --short HEAD 2>/dev/null); then
  echo "check_handoff: not a git repo — skipping"
  exit 0
fi

if [[ ! -f "$HANDOFF" ]]; then
  {
    echo "check_handoff: $HANDOFF does not exist."
    echo "CLAUDE.md: write the end-of-task summary there — what was built, decisions worth"
    echo "knowing, gates, what's next. It is the file the next session reads first."
  } >&2
  exit 1
fi

if ! grep -qF "$head_sha" "$HANDOFF"; then
  recorded=$(grep -oE '\b[0-9a-f]{7,40}\b' "$HANDOFF" | head -1)
  {
    echo "check_handoff: $HANDOFF does not name HEAD ($head_sha)."
    [[ -n "$recorded" ]] && echo "  It records ${recorded} — $(git log --oneline -1 "$recorded" 2>/dev/null || echo 'an unknown commit')."
    echo
    echo "  HEAD is: $(git log --oneline -1)"
    echo
    echo "CLAUDE.md requires the handoff to be rewritten each task. A summary that predates"
    echo "the commits it is supposed to describe is worse than none — the next session"
    echo "believes it."
  } >&2
  exit 1
fi

echo "check_handoff: $HANDOFF names HEAD ($head_sha)"
