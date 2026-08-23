"""The red-window sentinel must be detected, and must refuse to be anonymous.

`AGENTS.md` § 2: a new gate needs a test that proves it can fail. The failure that matters
here is the inverse of the usual one — this check exits 1 when the sentinel is *present* —
so the test pins both directions plus the anonymity guard, which is what keeps `.lokara-red`
from degrading into a general-purpose off switch for the gate.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_red_sentinel.py"
SENTINEL = ".lokara-red"


def _run(tree: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(tree)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_absent_sentinel_passes(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "none" in result.stdout


def test_declared_sentinel_fails_and_reports_its_reason(tmp_path: Path) -> None:
    reason = "slice/m6-c1-matching-engine · BANKMATCH fixtures land before the engine"
    (tmp_path / SENTINEL).write_text(f"{reason}\n", encoding="utf-8")

    result = _run(tmp_path)
    assert result.returncode == 1
    assert "deliberate red window" in result.stdout
    assert reason in result.stdout


def test_anonymous_sentinel_is_rejected(tmp_path: Path) -> None:
    """An empty sentinel is an off switch. It fails, and says what is missing."""
    (tmp_path / SENTINEL).write_text("\n", encoding="utf-8")

    result = _run(tmp_path)
    assert result.returncode == 1
    assert "names no slice or reason" in result.stdout
