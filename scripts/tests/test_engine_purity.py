"""The guard engine must remain below rules-store and ambient time."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check_engine_purity.py"


def _load_checker() -> ModuleType:
    module_name = "engine_purity_checker"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_guard_layer_rejects_rules_store_and_ambient_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checker = _load_checker()
    monkeypatch.setattr(checker, "REPO", tmp_path)
    source = tmp_path / "packages/guard-engine/src/lokara_guard_engine/bad.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "from datetime import date\n"
        "from lokara_rules_store import resolve\n\n"
        "TODAY = date.today()\n",
        encoding="utf-8",
    )

    layer = checker._layer_for(source)
    assert layer is not None
    problems = checker.check_file(source, layer)

    assert any("forbidden import `from lokara_rules_store`" in problem for problem in problems)
    assert any("`date.today()` reads ambient state" in problem for problem in problems)
