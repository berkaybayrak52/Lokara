#!/usr/bin/env python3
"""Mechanize CLAUDE.md rule 1: engines stay pure, framework-free and deterministic.

Rule 1 says the money/legal math lives in pure Python packages that import no web
framework, no vendor SDK and no database. Until now that was enforced by discipline.
This script enforces it by AST, so a violation fails a hook or CI instead of a review.

What it checks, per package (see LAYERS below):

1. **Forbidden imports.** A deny-list, not an allow-list: `pydantic` is fine (docs/03
   allows "plain dataclasses / Pydantic models"), `fastapi` and `sqlalchemy` are not.
2. **No I/O.** `open`, `pathlib`, `os`, `requests` — an engine that reads a file is no
   longer a pure function of its inputs and its golden fixture stops proving anything.
3. **No ambient time.** `datetime.now()`, `date.today()`, `time.time()`, `random`. An
   as-of law date is a *parameter* (docs/03: "passed in as a parameter with an as-of
   law date"), never something the engine reads from the clock.
4. **Engines never import `rules-store`** (docs/03: "the caller resolves the values and
   passes them in"). `domain` holds the value *shapes*; `rules-store` holds the values.

Usage:
    uv run python scripts/check_engine_purity.py            # whole repo
    uv run python scripts/check_engine_purity.py FILE...    # only these files (hook mode)

Exit 0 = clean, exit 1 = violations printed to stderr.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The repo pins 3.13 (.python-version) and uses PEP 695 generics (`class RuleVersion[T]`).
# A 3.10/3.11 interpreter cannot parse that and would report every such file as a
# violation, which is worse than not running at all. Always invoke via `uv run python`.
if sys.version_info < (3, 12):  # noqa: UP036 — guards the interpreter, not the source
    print(
        f"check_engine_purity: needs Python >= 3.12 to parse this codebase "
        f"(running {sys.version_info.major}.{sys.version_info.minor}).\n"
        f"  Use: uv run python scripts/check_engine_purity.py",
        file=sys.stderr,
    )
    raise SystemExit(2)

# Modules no pure package may import, whatever the layer.
VENDOR_AND_FRAMEWORK = {
    "fastapi",
    "starlette",
    "uvicorn",
    "flask",
    "django",
    "sqlalchemy",
    "alembic",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "prisma",
    "supabase",
    "redis",
    "celery",
    "arq",
    "boto3",
    "stripe",
    "playwright",
    "httpx",
    "requests",
    "aiohttp",
    "urllib",
    "urllib3",
    "socket",
}

# Modules that break determinism or purity of a golden-tested engine.
IO_AND_AMBIENT = {"os", "sys", "pathlib", "shutil", "subprocess", "tempfile", "random", "secrets"}

# Callables that read ambient state. Matched on the dotted call name.
AMBIENT_CALLS = {
    "datetime.now",
    "datetime.utcnow",
    "date.today",
    "datetime.today",
    "time.time",
    "time.monotonic",
    "random.random",
    "random.choice",
    "uuid.uuid4",
    "open",
}


@dataclass(frozen=True)
class Layer:
    """One purity zone: a source root plus the extra modules it may not import."""

    root: str
    forbidden_internal: frozenset[str] = field(default_factory=frozenset)
    allow_io: bool = False


LAYERS: tuple[Layer, ...] = (
    # domain holds value objects only — it sits below everything.
    Layer(
        "packages/domain/src",
        forbidden_internal=frozenset(
            {
                "lokara_nk_engine",
                "lokara_heating_engine",
                "lokara_rules_store",
                "lokara_adapters",
                "lokara_db",
                "lokara_api",
                "lokara_pdf",
            }
        ),
    ),
    # The two crown-jewel engines: domain only. Never rules-store (docs/03).
    Layer(
        "packages/nk-engine/src",
        forbidden_internal=frozenset(
            {
                "lokara_rules_store",
                "lokara_adapters",
                "lokara_db",
                "lokara_api",
                "lokara_pdf",
                "lokara_heating_engine",
            }
        ),
    ),
    Layer(
        "packages/heating-engine/src",
        forbidden_internal=frozenset(
            {
                "lokara_rules_store",
                "lokara_adapters",
                "lokara_db",
                "lokara_api",
                "lokara_pdf",
                "lokara_nk_engine",
            }
        ),
    ),
    # rules-store is data + resolution. It may know domain shapes, nothing above.
    Layer(
        "packages/rules-store/src",
        forbidden_internal=frozenset(
            {
                "lokara_nk_engine",
                "lokara_heating_engine",
                "lokara_adapters",
                "lokara_db",
                "lokara_api",
                "lokara_pdf",
            }
        ),
    ),
    # adapters own the vendor edge, so vendor SDKs are legal here — but they must not
    # reach up into the API or down into the DB layer, and they normalize to domain.
    Layer(
        "packages/adapters/src",
        forbidden_internal=frozenset({"lokara_db", "lokara_api"}),
        allow_io=True,
    ),
)


def _dotted(node: ast.AST) -> str:
    """Best-effort dotted name for a call target, e.g. `datetime.now`."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _layer_for(path: Path) -> Layer | None:
    # The PostToolUse hook feeds this every .py file an agent touches, including scratch
    # files outside the repo. `relative_to` raises there, and a traceback reads like a
    # purity violation. Outside the repo is simply "no layer" — nothing to check.
    try:
        rel = path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return None
    for layer in LAYERS:
        if rel.startswith(layer.root + "/"):
            return layer
    return None


def check_file(path: Path, layer: Layer) -> list[str]:
    rel = path.resolve().relative_to(REPO).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:  # let ruff/mypy report the real error
        return [f"{rel}:{exc.lineno}: could not parse ({exc.msg})"]

    banned_modules = set(VENDOR_AND_FRAMEWORK) | set(layer.forbidden_internal)
    if not layer.allow_io:
        banned_modules |= IO_AND_AMBIENT

    problems: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in banned_modules:
                    problems.append(
                        f"{rel}:{node.lineno}: forbidden import `{alias.name}` "
                        f"in {layer.root} (CLAUDE.md rule 1)"
                    )
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if node.level == 0 and top in banned_modules:
                problems.append(
                    f"{rel}:{node.lineno}: forbidden import `from {node.module}` "
                    f"in {layer.root} (CLAUDE.md rule 1)"
                )
        elif isinstance(node, ast.Call) and not layer.allow_io:
            name = _dotted(node.func)
            if name in AMBIENT_CALLS:
                problems.append(
                    f"{rel}:{node.lineno}: `{name}()` reads ambient state — an engine must be "
                    f"a pure function of its inputs (docs/03: as-of date is a parameter)"
                )

    return problems


def main(argv: list[str]) -> int:
    if argv:
        candidates = [Path(a).resolve() for a in argv]
    else:
        candidates = [p for layer in LAYERS for p in (REPO / layer.root).rglob("*.py")]

    problems: list[str] = []
    checked = 0
    for path in candidates:
        if path.suffix != ".py" or not path.is_file():
            continue
        layer = _layer_for(path)
        if layer is None:
            continue  # not a purity zone — nothing to say
        checked += 1
        problems.extend(check_file(path, layer))

    if problems:
        print(f"engine purity: {len(problems)} violation(s)\n", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(
            "\nVendor code belongs in packages/adapters. Legal values belong in "
            "packages/rules-store and are passed in, never imported.",
            file=sys.stderr,
        )
        return 1

    print(f"engine purity: clean ({checked} file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
