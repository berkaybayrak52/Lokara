#!/usr/bin/env python3
r"""Report whether a slice has declared a deliberate red window.

`CLAUDE.md` § 10: *"No agent may write both a test and the implementation that satisfies
it."* That rule creates a window, on every calculation slice, where the fixture exists and
the code does not — the suite is red, on purpose, and the agent holding it is not allowed
to close it.

The Stop hook runs `scripts/gate.sh fast` and refuses to let an agent end its turn on red.
So the gate was fighting the rule that produces the window. Measured over the session
transcripts: 9 main-session blocks plus 2 in subagents during M6-C1 alone, ~47 across all
sessions, and **12 of the 19 subagent blocks were `spec-scribe`** — the one role whose
entire deliverable is a failing fixture. Each block costs a full extra turn, and a turn is
a whole context re-read.

`.lokara-red` is how a slice says "this red is intended". It is untracked and gitignored,
so it cannot ride along in a commit, and it must name the slice and the reason — an
anonymous sentinel is an off switch, which is exactly what this must not become.

The levels differ on purpose:

- `gate.sh fast` — the tight loop and the Stop hook. The sentinel is announced loudly and
  the gate does not block, so the red window can be worked in.
- `gate.sh full` / `demo` — the levels you run to close or merge something. The sentinel is
  a hard failure there, because a slice does not ship with its window still open.

Exit 0 when no sentinel exists. Exit 1, printing its contents, when one does. This script
only reports; `gate.sh` decides what the level makes of it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SENTINEL = ".lokara-red"
MIN_REASON_CHARS = 10


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="tree to check (default: repo root)")
    args = parser.parse_args()

    root = Path(args.root) if args.root else Path(__file__).resolve().parents[1]
    sentinel = root / SENTINEL

    if not sentinel.is_file():
        print(f"red sentinel: none ({SENTINEL} absent)")
        return 0

    reason = sentinel.read_text(encoding="utf-8").strip()
    if len(reason) < MIN_REASON_CHARS:
        print(f"red sentinel: {SENTINEL} exists but names no slice or reason.")
        print("  Write one line naming the slice and why the suite is red, e.g.")
        print("    slice/m6-c1-matching-engine · BANKMATCH fixtures land before the engine")
        return 1

    print(f"red sentinel: {SENTINEL} declares a deliberate red window.")
    for line in reason.splitlines():
        print(f"  {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
