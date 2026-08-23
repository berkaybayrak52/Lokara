#!/usr/bin/env python3
"""Mechanize CLAUDE.md rule 3: multi-tenant isolation is enforced twice.

AGENTS.md says it plainly (moved there from MIGRATION-PLAN.md §8 when that file was
retired): *"Every new tenant table needs an RLS policy and a line in the isolation
test — a table without a policy is a silent leak."* That rule was enforced by
review. This enforces it against the **live migrated database**, which
is the only ground truth — the policies in `packages/db/alembic/versions/` are created
inside `for table in (...)` loops, so any grep-based checker gives false answers in
both directions.

Checks, for every table that carries an `account_id` column:

1. `relrowsecurity`  — RLS is ENABLEd.
2. `relforcerowsecurity` — RLS is FORCEd. Without FORCE the table owner bypasses every
   policy, which is exactly the connection a migration or a careless script uses.
3. At least one policy exists on the table, **with a WITH CHECK clause**. USING alone
   filters reads; without WITH CHECK a scoped session can still INSERT a row stamped
   with someone else's account_id.
4. The table is named in `packages/db/tests/test_rls_isolation.py`, so the policy is
   not merely present but actually exercised.
5. That mention is inside a test that actually attempts a **cross-account write**.
   Checks 3 and 4 both passed for all nine M6-C2 tables while not one of them had a
   write assertion — two of the four tests ran on the owner engine, which bypasses
   RLS entirely, and an `import` line satisfied "named". The boundary audit of
   23.08.2026 found six defects behind that gap. "Named" is weaker than "tested",
   and this is the difference.

Tables without `account_id` are out of scope **of this script**, not of isolation. `person`
is the case that makes the distinction matter: it is global by design — one human, many
accounts, Supabase Auth maps onto it — so it has no `account_id` and stays in EXEMPT, but
it does carry RLS (a policy over `membership`, M5a). EXEMPT means "not scoped by a local
account_id column", never "unprotected". Add any other intentional exception below, with a
reason — and if it holds identities or money, say where its protection lives instead.

Usage:
    docker compose up -d
    uv run alembic -c packages/db/alembic.ini upgrade head
    uv run python scripts/check_rls_coverage.py

Exit 0 = every tenant table is covered, exit 1 = a leak, exit 2 = could not reach the DB.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parent.parent
ISOLATION_TEST = REPO / "packages/db/tests/test_rls_isolation.py"

# Tables that legitimately have no account_id column. Note that "no account_id" is NOT
# the same as "no policy": account is ENABLEd, FORCEd and policied — it just derives the
# account from something other than a local column.
# Keep this list short and always give the reason.
#
# `building_assignment` used to be here, scoped transitively through membership. Migration
# 0004 gave it a real account_id (docs/02 → "Isolation rule"), so it is now an ordinary
# tenant table and this script checks it like any other.
EXEMPT: dict[str, str] = {
    "alembic_version": "migration bookkeeping, not tenant data",
    "person": "global identity — one human, many accounts (migration 0001)",
    "account": "IS the isolation boundary — its own id is the account id; policy compares id",
}

# M6-B's public ORM names deliberately distinguish the two archive audiences
# from their SQL table names.  The isolation suite selects these classes by
# their public names, so the coverage checker must use the same vocabulary.
MODEL_NAME_OVERRIDES = {
    "tenancy_delivery_address": "DeliveryAddress",
    "owner_payment_credit_instruction": "PaymentInstruction",
    "statement_document_archive": "StatementArchive",
}


def _model_name(table: str) -> str:
    """`allocation_key_assignment` -> `AllocationKeyAssignment`.

    The isolation test selects mapped classes, not table names, so a literal search for
    the snake_case name reports covered tables as uncovered.
    """
    return MODEL_NAME_OVERRIDES.get(table, "".join(part.capitalize() for part in table.split("_")))


def _is_named(table: str, test_src: str) -> bool:
    r"""Is this table actually mentioned in the isolation test?

    Word-boundary, not substring. A plain `name in test_src` reports a table as covered
    whenever its name happens to sit inside a longer identifier, which is the direction
    of error that hides an untested policy:

        unit    matched  measurement_unit=MeasurementUnit.KWH
        tenancy matched  tenancy_party / tenancy_id
        meter   matches  meter_reading

    `\b` does not fire between `_` and a letter, nor between two letters, so none of
    those longer identifiers counts as a mention of the shorter table any more.
    """
    return any(
        re.search(rf"\b{re.escape(token)}\b", test_src) for token in (table, _model_name(table))
    )


# The shapes a cross-account write assertion takes in the isolation suite: a scoped
# session for another account, and an expectation that the write is refused. Both must
# appear in the same test body as the table's model name.
_WRITE_ASSERTION = re.compile(r"pytest\.raises\(")
_SCOPED_SESSION = re.compile(r"account_scoped_session\(\s*app")

# Test bodies are taken from the parse tree, not by splitting on `def`. Every regex
# boundary tried here has leaked: `\n    def ` did not break at a module-level fixture,
# and `\n(?:    )?def ` broke at the next `def` rather than at the end of the test — so a
# following class header, its docstring or a module-level constant stayed glued onto the
# last test body and inherited its markers. A `def` is where the *next* thing starts, not
# where this one ends; only the parser knows the difference.

# Both account names in one body. A same-account immutability test also holds a scoped
# session and a `pytest.raises`; only the pair proves the write crossed a boundary.
_ACCOUNT_A = re.compile(r"\baccount_a\b")
_ACCOUNT_B = re.compile(r"\baccount_b\b")


def _test_bodies(test_src: str) -> list[str]:
    """The source of every `test_…` function, each ending where that function ends.

    `ast.walk` reaches methods inside classes, which is where the isolation suite keeps
    almost all of them, and `AsyncFunctionDef` is included because an `async def test_…`
    is a test. Decorators are excluded by `get_source_segment`, which is correct here:
    the four markers this gate looks for all live in the body.

    A file that does not parse is a hard failure, not a silent zero. Returning `[]` would
    report every table as uncovered, and the pressure that creates is exactly how a gate
    gets weakened — the M6-C2 audit's six HIGH defects shipped behind this check.
    """
    try:
        tree = ast.parse(test_src)
    except SyntaxError as exc:  # pragma: no cover - a broken suite fails louder elsewhere
        raise SystemExit(f"check_rls_coverage: cannot parse the isolation suite: {exc}") from exc

    bodies: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("test_"):
            continue
        segment = ast.get_source_segment(test_src, node)
        if segment is not None:
            bodies.append(segment)
    return bodies


def _write_tested(table: str, test_src: str) -> bool:
    """Is this table named inside a test that attempts a refused cross-account write?

    Three things have to line up in **one** `test_` body: the table's name, a scoped
    session, and a refusal — across two different accounts.

    The M6-C2 boundary audit is why each clause is here. `\n    def ` split only at
    method indentation, so the module-level `m6c2_bank_rows` fixture — which names all
    nine matching tables and writes them on the *owner* engine, asserting nothing — was
    glued onto the end of an unrelated statement test that did carry both markers. All
    nine tables were reported write-tested while not one had a cross-account write
    assertion, and the six HIGH defects that audit found shipped behind a green gate.

    Splitting on `def` was tried twice and leaked twice — see the note above `_TEST_DEF`.
    The bodies now come from `ast`, so a chunk ends where the test ends. That also picks
    up `async def test_…`, which the regex never matched: no isolation test is async
    today, and the moment one is, its table would have silently lost coverage.

    Both account names are still required, which is what separates a cross-account write
    from a same-account immutability test.

    `scripts/tests/test_rls_coverage_matcher.py` holds all four directions — the glued
    fixture and the glued class docstring must not vouch, and a genuine assertion must,
    whether it is `def` or `async def`.
    """
    tokens = (table, _model_name(table))
    for body in _test_bodies(test_src):
        if not any(re.search(rf"\b{re.escape(t)}\b", body) for t in tokens):
            continue
        if not (_WRITE_ASSERTION.search(body) and _SCOPED_SESSION.search(body)):
            continue
        if _ACCOUNT_A.search(body) and _ACCOUNT_B.search(body):
            return True
    return False


def _url() -> str:
    # The rest of the stack loads the root .env itself (alembic's env.py, ApiSettings via
    # pydantic-settings), so an operator who never exports DIRECT_URL still has a working
    # repo. This script has to do the same or it fails on a correctly configured machine.
    load_dotenv(REPO / ".env")
    url = os.environ.get("DIRECT_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print(
            "check_rls_coverage: set DIRECT_URL (or DATABASE_URL) to the migrated database.\n"
            "  docker compose up -d && uv run alembic -c packages/db/alembic.ini upgrade head",
            file=sys.stderr,
        )
        raise SystemExit(2)
    # SQLAlchemy 2.0 wants an explicit driver.
    return (
        url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://")
        else url
    )


TENANT_TABLES = text(
    """
    SELECT c.relname AS table_name,
           c.relrowsecurity AS enabled,
           c.relforcerowsecurity AS forced,
           (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies,
           (SELECT count(*) FROM pg_policy p
             WHERE p.polrelid = c.oid AND p.polwithcheck IS NOT NULL) AS with_check_policies
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
      AND EXISTS (
          SELECT 1 FROM information_schema.columns col
          WHERE col.table_schema = 'public'
            AND col.table_name = c.relname
            AND col.column_name = 'account_id'
      )
    ORDER BY c.relname
    """
)

ALL_TABLES = text(
    """
    SELECT c.relname
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r'
    ORDER BY c.relname
    """
)


def main() -> int:
    engine = create_engine(_url())
    try:
        with engine.connect() as conn:
            tenant_rows = conn.execute(TENANT_TABLES).all()
            all_tables = [r[0] for r in conn.execute(ALL_TABLES).all()]
    except Exception as exc:  # any connection failure is the same answer: cannot verify
        print(f"check_rls_coverage: cannot reach the database: {exc}", file=sys.stderr)
        return 2

    if not all_tables:
        print(
            "check_rls_coverage: database has no tables — run alembic upgrade head first.",
            file=sys.stderr,
        )
        return 2

    test_src = ISOLATION_TEST.read_text(encoding="utf-8") if ISOLATION_TEST.exists() else ""

    problems: list[str] = []

    for name, enabled, forced, policies, with_check_policies in tenant_rows:
        if not enabled:
            problems.append(f"{name}: has account_id but RLS is NOT ENABLEd — silent leak")
        if not forced:
            problems.append(f"{name}: RLS not FORCEd — the table owner bypasses every policy")
        if policies == 0:
            problems.append(
                f"{name}: RLS enabled but no policy exists — denies everything or nothing"
            )
        if policies and not with_check_policies:
            problems.append(
                f"{name}: policy has USING but no WITH CHECK — reads are filtered while a "
                f"scoped session can still write a row stamped with another account"
            )
        if test_src and not _is_named(name, test_src):
            problems.append(
                f"{name}: not named in packages/db/tests/test_rls_isolation.py — "
                f"the policy is untested"
            )
        elif test_src and not _write_tested(name, test_src):
            problems.append(
                f"{name}: named in the isolation test but never in a test that attempts a "
                f"cross-account write — add one using account_scoped_session(app, other) "
                f"plus pytest.raises, or the WITH CHECK side of the policy is unproven"
            )

    # A table with neither account_id nor an exemption is the more dangerous case:
    # somebody added tenant data and forgot the column entirely.
    covered = {r[0] for r in tenant_rows}
    for name in all_tables:
        if name not in covered and name not in EXEMPT:
            problems.append(
                f"{name}: no account_id column and not in EXEMPT — either scope it to an "
                f"account or add it to EXEMPT in this script with a reason"
            )

    if problems:
        print(f"RLS coverage: {len(problems)} problem(s)\n", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1

    print(
        f"RLS coverage: clean — {len(tenant_rows)} tenant table(s) ENABLEd + FORCEd + "
        f"policied WITH CHECK + cross-account-write tested; {len(EXEMPT)} exempt"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
