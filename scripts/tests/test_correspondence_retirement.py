"""The D3 retirement guard must fail when a dependency is reintroduced."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_correspondence_retirement.py"


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("retirement_checker", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(tree: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(tree)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_reintroduced_path_or_reference_fails(tmp_path: Path) -> None:
    checker = _load_checker()
    retired = checker.RETIRED_PATHS
    ledger = tmp_path / checker.LEDGER
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        "# Spec\n\n"
        f"{checker.LEDGER_HEADING}\n\n" + "\n".join(f"- `{path}`" for path in retired) + "\n",
        encoding="utf-8",
    )
    assert _run(tmp_path).returncode == 0

    dependency = tmp_path / "current-notes.md"
    dependency.write_text(f"Depends on {retired[0].name}.\n", encoding="utf-8")
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "retired reference" in result.stdout
    dependency.unlink()

    restored = tmp_path / retired[0]
    restored.write_text("restored dependency\n", encoding="utf-8")
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "retired path exists" in result.stdout
