#!/usr/bin/env python3
r"""Fail when the `.claude` and `.codex` agent trees diverge.

Three things are compared, because a parity check that covers only one of them certifies
the half that matters less:

1. **Agent definitions** — `.claude/agents/*.md` vs `.codex/agents/*.toml`. Prose.
2. **Hook scripts** — `.claude/hooks/*.sh` vs `.codex/hooks/*.sh`. The mechanism.
3. **Hook wiring** — the `hooks` object of `.claude/settings.json` vs `.codex/hooks.json`:
   which event fires which script, on which matcher, with which timeout.

Checking (1) and not (2)/(3) is how this script reported "clean" on 13.08.2026 while all
three `.codex` hooks were the pre-fix versions: `write-scope.sh` still carried the
`[^\>\<]\>[^\>]` redirect regex that does not match `>>`, so a read-only agent could
**append** to any file in the repo in silence; and `post-edit.sh`/`stop-gate.sh` still did
`cd "$CLAUDE_PROJECT_DIR"` first, grading a worktree agent against the wrong tree. The
definitions are what an agent is told; the hooks are what actually stops it.

The `.codex/` tree is a parallel set of definitions and hooks for the `codex` CLI, kept as
the fallback for when tokens run out. Nothing inside this repository reads it — only the
external tool does — so it drifts silently, and a drifted definition is worse than no
definition at all: on 13.08.2026 `.codex/agents/statement-reviewer.toml` still carried the
demo's heating pair from two re-bases earlier, and *both* `engine-implementer` definitions
still stated the retired blanket rule "rounding is largest-remainder". An agent holding
that would have reverted correct `distribute_cents_half_up` code — the drift would have
written itself back into the engine.

What is compared is the **body**, not the file format. `.claude` definitions are Markdown
with YAML front-matter; `.codex` definitions are TOML with the same prose underneath. The
prose is the part that instructs the agent, so the prose is what must match. Front-matter
and TOML key/value lines are stripped before comparison, since `model = "opus"` and
`model: opus` say the same thing in two syntaxes.

Exit 0 when every pair agrees (or when `.codex/agents/` does not exist — deleting the
tree is a legitimate way to satisfy this check). Exit 1 listing each divergence.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_AGENTS = ROOT / ".claude" / "agents"
CODEX_AGENTS = ROOT / ".codex" / "agents"
CLAUDE_HOOKS = ROOT / ".claude" / "hooks"
CODEX_HOOKS = ROOT / ".codex" / "hooks"
CLAUDE_SETTINGS = ROOT / ".claude" / "settings.json"
CODEX_WIRING = ROOT / ".codex" / "hooks.json"

# Tokens a `.codex` file is *expected* to spell differently. Everything else must match.
# Kept deliberately short: each entry is a hole in the check, so a new one needs a reason.
TREE_TOKENS = [(".claude", ".codex"), ("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR")]

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


def _normalise_tree(text: str) -> str:
    """Rewrite a `.codex` file into the spelling its `.claude` twin would use."""
    for claude_token, codex_token in TREE_TOKENS:
        text = text.replace(codex_token, claude_token)
    return text


def _hook_lines(path: Path) -> list[str]:
    """A hook script's executable content: comments and blank lines dropped.

    Comments are dropped on purpose. A `.codex` hook is allowed to explain itself
    differently, but it may not *behave* differently — and it was a behavioural
    divergence (`>>` unmatched, `cd` to the wrong tree) that this check missed while
    the prose halves agreed.
    """
    out: list[str] = []
    for raw in _normalise_tree(path.read_text()).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _check_hooks(problems: list[str]) -> int:
    if not CODEX_HOOKS.is_dir():
        return 0
    checked = 0
    for claude_hook in sorted(CLAUDE_HOOKS.glob("*.sh")):
        twin = CODEX_HOOKS / claude_hook.name
        if not twin.exists():
            problems.append(
                f"MISSING  {claude_hook.relative_to(ROOT)} has no .codex twin — the "
                f"codex tree runs without that guard entirely"
            )
            continue
        checked += 1
        claude_lines = _hook_lines(claude_hook)
        codex_lines = _hook_lines(twin)
        if claude_lines == codex_lines:
            continue
        only_claude = [line for line in claude_lines if line not in codex_lines]
        only_codex = [line for line in codex_lines if line not in claude_lines]
        detail = [f"             only in .claude: {line[:96]}" for line in only_claude[:4]]
        detail += [f"             only in .codex:  {line[:96]}" for line in only_codex[:4]]
        problems.append(
            f"DRIFT    hooks/{claude_hook.name}: the two trees do not enforce the same "
            f"thing ({len(only_claude)} line(s) only in .claude, {len(only_codex)} only "
            f"in .codex)\n" + "\n".join(detail)
        )
    for codex_hook in sorted(CODEX_HOOKS.glob("*.sh")):
        if not (CLAUDE_HOOKS / codex_hook.name).exists():
            problems.append(
                f"ORPHAN   {codex_hook.relative_to(ROOT)} has no .claude twin — a guard "
                f"only one tree runs"
            )
    return checked


def _wiring(blob: dict[str, object]) -> list[tuple[str, str, str, object]]:
    """(event, matcher, script basename, timeout) for every wired hook.

    Compares which script runs on which event, not how the path to it is spelled — the
    two tools resolve paths differently and that difference is not drift.
    """
    hooks = blob.get("hooks")
    rows: list[tuple[str, str, str, object]] = []
    if not isinstance(hooks, dict):
        return rows
    for event, entries in sorted(hooks.items()):
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            matcher = str(entry.get("matcher", ""))
            for hook in entry.get("hooks", []) or []:
                if not isinstance(hook, dict):
                    continue
                command = str(hook.get("command", "")).strip().strip("'\"")
                rows.append((event, matcher, PurePosixPath(command).name, hook.get("timeout")))
    return sorted(rows)


def _check_wiring(problems: list[str]) -> int:
    if not (CODEX_WIRING.exists() and CLAUDE_SETTINGS.exists()):
        return 0
    claude_rows = _wiring(json.loads(CLAUDE_SETTINGS.read_text()))
    codex_rows = _wiring(json.loads(CODEX_WIRING.read_text()))
    if claude_rows != codex_rows:
        for row in [r for r in claude_rows if r not in codex_rows]:
            problems.append(
                f"WIRING   .claude fires {row[2]} on {row[0]} (matcher {row[1]!r}, "
                f"timeout {row[3]}) — .codex does not"
            )
        for row in [r for r in codex_rows if r not in claude_rows]:
            problems.append(
                f"WIRING   .codex fires {row[2]} on {row[0]} (matcher {row[1]!r}, "
                f"timeout {row[3]}) — .claude does not"
            )

    # An absolute path pins the config to one machine and one checkout location.
    hardcoded = [
        line.strip()
        for line in CODEX_WIRING.read_text().splitlines()
        if "/Users/" in line or "/home/" in line
    ]
    if hardcoded:
        problems.append(
            f"ABSOLUTE {CODEX_WIRING.relative_to(ROOT)} hardcodes an absolute path on "
            f"{len(hardcoded)} line(s) — it breaks on a move or a fresh clone. Use the "
            f"project-dir variable or a path relative to the config file."
        )
    return len(claude_rows)


def main() -> int:
    if not (CODEX_AGENTS.is_dir() or CODEX_HOOKS.is_dir()):
        print("agent parity: clean — no .codex/ tree to keep in sync")
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

    hooks_checked = _check_hooks(problems)
    wired = _check_wiring(problems)

    if problems:
        print("agent parity: PROBLEMS\n")
        for problem in problems:
            print(f"  {problem}")
        print(
            "\nThe .codex/ tree is read by the external `codex` CLI, not by anything in "
            "this repo, so it\ndrifts silently — and it is the fallback that gets used "
            "when tokens run out, i.e. exactly\nwhen nobody is watching. A DRIFT on a "
            "hook means the two trees do not enforce the same\nrule: sync the pair. "
            "Definitions may differ only in the tokens each tool spells its own way."
        )
        return 1

    print(
        f"agent parity: clean — {checked} agent pair(s), {hooks_checked} hook pair(s) "
        f"and {wired} wired hook(s) agree"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
