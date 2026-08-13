"""`check_agent_parity.py` must be red on the divergences that actually happened.

A parity check that has never failed is not evidence of anything. Two of these cases are
transcribed from real drift found on 13.08.2026, when the check reported "clean" while
`.codex` carried three pre-fix hooks — because it compared agent *definitions* and not the
*mechanism*. Each case reproduces one divergence in a throwaway tree and asserts the check
refuses it.

The first case is the important one. `.codex/hooks/write-scope.sh` carried the original
redirect regex `[^\\>\\<]\\>[^\\>]`, which requires a non-`>` character on both sides of the
`>` and therefore never matches `>>`. A read-only agent (`docs-reconciler`,
`boundary-auditor`, `statement-reviewer`) could `echo … >> any/file.py` and the hook stayed
silent. Truncate and append are the same escape; only one of them was guarded.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
CHECK = ROOT / "scripts" / "check_agent_parity.py"

# The regex as it stood before H3, and as it stands after. The `>>` case is what separates
# them; both match a plain `>`, which is why the divergence survived review.
PRE_FIX_REDIRECT = r"[^\>\<]\>[^\>]"
POST_FIX_REDIRECT = r"(^|[^0-9\<\>\&])\>\>?[[:space:]]*[^\&\>[:space:]]"


def _run(tree: Path) -> subprocess.CompletedProcess[str]:
    """Run the real check against a throwaway copy of the two trees."""
    return subprocess.run(
        [sys.executable, str(tree / "scripts" / "check_agent_parity.py")],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A minimal repo whose `.claude` and `.codex` halves agree."""
    subdirs = (".claude/agents", ".claude/hooks", ".codex/agents", ".codex/hooks", "scripts")
    for sub in subdirs:
        (tmp_path / sub).mkdir(parents=True)
    shutil.copy(CHECK, tmp_path / "scripts" / "check_agent_parity.py")

    (tmp_path / ".claude/agents/demo.md").write_text("---\nname: demo\n---\n\nBody line.\n")
    (tmp_path / ".codex/agents/demo.toml").write_text(
        'name = "demo"\n\nprompt = """\nBody line.\n"""\n'
    )

    for tool, token in ((".claude", "CLAUDE"), (".codex", "CODEX")):
        (tmp_path / tool / "hooks" / "write-scope.sh").write_text(
            f'#!/usr/bin/env bash\ncd "${{{token}_PROJECT_DIR:-$PWD}}"\n'
            f'if [[ "$cmd" =~ {POST_FIX_REDIRECT} ]]; then deny; fi\n'
        )

    wiring = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "X/write-scope.sh", "timeout": 10}],
                }
            ]
        }
    }
    claude = json.loads(json.dumps(wiring).replace("X", "$CLAUDE_PROJECT_DIR/.claude/hooks"))
    codex = json.loads(json.dumps(wiring).replace("X", ".codex/hooks"))
    (tmp_path / ".claude/settings.json").write_text(json.dumps(claude))
    (tmp_path / ".codex/hooks.json").write_text(json.dumps(codex))
    return tmp_path


class TestTheCheckPassesWhenTheTreesAgree:
    def test_a_synced_tree_is_clean(self, tree: Path) -> None:
        """Guards the guard: if this ever fails, every red below is meaningless."""
        result = _run(tree)
        assert result.returncode == 0, result.stdout
        assert "clean" in result.stdout

    def test_the_tokens_each_tool_spells_differently_are_not_drift(self, tree: Path) -> None:
        """`.codex` says CODEX_PROJECT_DIR and `.codex/`; that is correct, not divergence."""
        body = (tree / ".codex/hooks/write-scope.sh").read_text()
        assert "CODEX_PROJECT_DIR" in body and "CLAUDE_PROJECT_DIR" not in body
        assert _run(tree).returncode == 0


class TestTheDivergencesThatActuallyHappened:
    def test_the_pre_fix_redirect_regex_is_caught(self, tree: Path) -> None:
        """THE case this test exists for: `>>` unguarded in one tree only.

        Both regexes match a plain `>`, so the two hooks behave identically on every
        truncating redirect — the divergence only shows on an append. The check must not
        need to understand bash to catch it; differing enforcement is enough.
        """
        hook = tree / ".codex/hooks/write-scope.sh"
        hook.write_text(hook.read_text().replace(POST_FIX_REDIRECT, PRE_FIX_REDIRECT))

        result = _run(tree)
        assert result.returncode == 1, "the >> divergence was NOT caught"
        assert "write-scope.sh" in result.stdout
        assert "DRIFT" in result.stdout

    def test_grading_the_wrong_tree_is_caught(self, tree: Path) -> None:
        """`cd "$PROJECT_DIR"` before `git rev-parse` grades a worktree agent's wrong tree."""
        hook = tree / ".codex/hooks/write-scope.sh"
        hook.write_text(
            hook.read_text().replace('cd "${CODEX_PROJECT_DIR:-$PWD}"', 'cd "$CODEX_PROJECT_DIR"')
        )
        assert _run(tree).returncode == 1

    def test_a_comment_only_difference_is_not_drift(self, tree: Path) -> None:
        """The two trees may explain themselves differently. Only behaviour must match."""
        hook = tree / ".codex/hooks/write-scope.sh"
        hook.write_text("# codex-specific note nobody executes\n" + hook.read_text())
        assert _run(tree).returncode == 0


class TestTheWiringAndTheAbsolutePaths:
    def test_a_hook_wired_in_one_tree_only_is_caught(self, tree: Path) -> None:
        wiring = json.loads((tree / ".codex/hooks.json").read_text())
        wiring["hooks"].pop("PreToolUse")
        (tree / ".codex/hooks.json").write_text(json.dumps(wiring))

        result = _run(tree)
        assert result.returncode == 1
        assert "WIRING" in result.stdout

    def test_a_changed_timeout_is_caught(self, tree: Path) -> None:
        """A 10s guard silently becoming 900s is a real difference in what gets enforced."""
        raw = (tree / ".codex/hooks.json").read_text()
        (tree / ".codex/hooks.json").write_text(raw.replace('"timeout": 10', '"timeout": 900'))
        assert _run(tree).returncode == 1

    def test_an_absolute_path_is_caught(self, tree: Path) -> None:
        """It breaks on a move or a fresh clone; it was hardcoded four times over."""
        raw = (tree / ".codex/hooks.json").read_text()
        (tree / ".codex/hooks.json").write_text(
            raw.replace(".codex/hooks", "/Users/someone/repo/.codex/hooks")
        )

        result = _run(tree)
        assert result.returncode == 1
        assert "ABSOLUTE" in result.stdout

    def test_a_missing_codex_hook_is_caught(self, tree: Path) -> None:
        """No twin at all means codex runs without that guard entirely."""
        (tree / ".codex/hooks/write-scope.sh").unlink()

        result = _run(tree)
        assert result.returncode == 1
        assert "MISSING" in result.stdout
