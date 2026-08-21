#!/usr/bin/env python3
"""Keep the D3 correspondence retirement closed.

The retired filenames are historical evidence only. Their sole repository reference is
the disposition ledger in docs/03; current code, tests and documentation must use the
approved docs, original Pages/annexes or the Rechtsstand register.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = Path("docs/03-nk-heating-engines.md")
LEDGER_HEADING = "## Appendix D — correspondence-retirement disposition ledger"
RETIRED_PATHS = (
    Path("FEEDBACK-to-Berkay-01b.md"),
    Path("FRAGEN-an-Berkay-02.md"),
    Path("FRAGEN-an-Berkay-03.md"),
    Path("berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md"),
    Path("berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md"),
    Path("berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md"),
    Path("berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md"),
)
SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".venv",
    "node_modules",
    "__pycache__",
}


def _repository_files(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
        check=False,
        capture_output=True,
    )
    if completed.returncode == 0:
        return [root / name for name in completed.stdout.decode().split("\0") if name]
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not (set(path.relative_to(root).parts) & SKIP_PARTS)
    ]


def _references(text: str) -> tuple[str, ...]:
    return tuple(str(path) for path in RETIRED_PATHS if path.name in text or str(path) in text)


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for retired in RETIRED_PATHS:
        if (root / retired).exists():
            errors.append(f"retired path exists: {retired}")

    for path in _repository_files(root):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if set(relative.parts) & SKIP_PARTS or relative == Path(
            "scripts/check_correspondence_retirement.py"
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if relative == LEDGER:
            if LEDGER_HEADING not in text:
                errors.append(f"historical ledger heading missing: {LEDGER}")
                continue
            before, ledger = text.split(LEDGER_HEADING, maxsplit=1)
            following_appendix = ledger.find("\n## Appendix ")
            after = ledger[following_appendix:] if following_appendix >= 0 else ""
            for reference in _references(before + after):
                errors.append(
                    f"retired reference outside historical ledger: {relative}: {reference}"
                )
            continue

        for reference in _references(text):
            errors.append(f"retired reference: {relative}: {reference}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = check(args.root.resolve())
    if errors:
        print("Correspondence retirement check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Correspondence retirement check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
