#!/usr/bin/env python3
"""Fail when a `.claude` agent definition and its `.codex` twin disagree.

The `.codex/` tree is a parallel set of agent definitions for the `codex` CLI. Nothing
inside this repository reads it — only the external tool does — so it drifts silently,
and a drifted definition is worse than no definition at all: on 13.08.2026
`.codex/agents/statement-reviewer.toml` still carried the demo's heating pair from two
re-bases earlier, and *both* `engine-implementer` definitions still stated the retired
blanket rule "rounding is largest-remainder". An agent holding that would have reverted
correct `distribute_cents_half_up` code — the drift would have written itself back into
the engine.

What is compared is the **body**, not the file format. `.claude` definitions are Markdown
with YAML front-matter; `.codex` definitions are TOML with the same prose underneath. The
prose is the part that instructs the agent, so the prose is what must match. Front-matter
and TOML key/value lines are stripped before comparison, since `model = "opus"` and
`model: opus` say the same thing in two syntaxes.

Exit 0 when every pair agrees (or when `.codex/agents/` does not exist — deleting the
tree is a legitimate way to satisfy this check). Exit 1 listing each divergence.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_AGENTS = ROOT / ".claude" / "agents"
CODEX_AGENTS = ROOT / ".codex" / "agents"

# A TOML scalar assignment at the top level: `model = "opus"`, `name = "spec-scribe"`.
TOML_ASSIGNMENT = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_-]*\s*=\s*(".*"|\[.*\]|\S+)\s*$')
# The opening of a multi-line assignment — `description = '''`, `prompt = """`, or a
# single-quoted string that wraps onto the next line.
TOML_BLOCK_OPEN = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_-]*\s*=\s*[\"']")

# The one substitution that is NOT drift. Claude Code auto-reads `CLAUDE.md`; the `codex`
# CLI auto-reads `AGENTS.md`. Each tree naming the file its own tool loads is correct, so
# comparing them literally would report a permanent, unfixable difference — and a check
# that is permanently red teaches people to ignore it.
EQUIVALENT = [("CLAUDE.md", "AGENTS.md")]


def _body(text: str, *, toml: bool) -> list[str]:
    """The instructing prose, with syntax and formatting noise removed."""
    lines = text.splitlines()

    if not toml:
        # Strip YAML front-matter delimited by a leading `---` … `---`.
        if lines and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    lines = lines[i + 1 :]
                    break
    else:
        # Drop top-level TOML assignments and section headers; keep the prose. A
        # triple-quoted block is the usual container for it, so drop the fence too.
        kept: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                continue
            if TOML_ASSIGNMENT.match(line) or TOML_BLOCK_OPEN.match(line):
                continue
            if stripped in ('"""', "'''"):
                continue
            # A closing fence usually rides on the last prose line (`… worthless."""`).
            for fence in ('"""', "'''"):
                if stripped.endswith(fence):
                    stripped = stripped[: -len(fence)].rstrip()
            kept.append(stripped)
        lines = kept

    # Compare on content, not whitespace: a reflowed paragraph is not a semantic change,
    # but a changed word is.
    out = [s for s in (line.strip() for line in lines) if s]
    for claude_name, codex_name in EQUIVALENT:
        out = [s.replace(codex_name, claude_name) for s in out]
    return out


def main() -> int:
    if not CODEX_AGENTS.is_dir():
        print("agent parity: clean — no .codex/agents/ tree to keep in sync")
        return 0

    problems: list[str] = []
    checked = 0

    for codex_file in sorted(CODEX_AGENTS.glob("*.toml")):
        twin = CLAUDE_AGENTS / f"{codex_file.stem}.md"
        if not twin.exists():
            problems.append(
                f"ORPHAN   {codex_file.relative_to(ROOT)} has no .claude twin at "
                f"{twin.relative_to(ROOT)} — an agent definition nothing maintains"
            )
            continue

        checked += 1
        codex_body = _body(codex_file.read_text(), toml=True)
        claude_body = _body(twin.read_text(), toml=False)
        if codex_body == claude_body:
            continue

        only_claude = [line for line in claude_body if line not in codex_body]
        only_codex = [line for line in codex_body if line not in claude_body]
        detail = []
        for line in only_claude[:3]:
            detail.append(f"             only in .claude: {line[:90]}")
        for line in only_codex[:3]:
            detail.append(f"             only in .codex:  {line[:90]}")
        problems.append(
            f"DRIFT    {codex_file.stem}: .claude and .codex definitions disagree "
            f"({len(only_claude)} line(s) only in .claude, {len(only_codex)} only in "
            f".codex)\n" + "\n".join(detail)
        )

    for claude_file in sorted(CLAUDE_AGENTS.glob("*.md")):
        if not (CODEX_AGENTS / f"{claude_file.stem}.toml").exists():
            problems.append(
                f"MISSING  {claude_file.relative_to(ROOT)} has no .codex twin — either "
                f"add one or delete the .codex/agents/ tree"
            )

    if problems:
        print("agent parity: PROBLEMS\n")
        for problem in problems:
            print(f"  {problem}")
        print(
            "\nThe .codex/ tree is read by the external `codex` CLI, not by anything in "
            "this repo,\nso it drifts silently. Either sync the pair, or delete "
            ".codex/agents/ — an unmaintained\nparallel agent definition is worse than "
            "none: it can instruct an agent to revert correct code."
        )
        return 1

    print(f"agent parity: clean — {checked} .claude/.codex agent pair(s) agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
