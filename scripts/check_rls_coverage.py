#!/usr/bin/env python3
"""Mechanize CLAUDE.md rule 3: multi-tenant isolation is enforced twice.

MIGRATION-PLAN.md §8 says it plainly: *"Every new tenant table needs an RLS policy +
a line in the isolation test. A table without a policy is a silent leak."* That rule
was enforced by review. This enforces it against the **live migrated database**, which
is the only ground truth — the policies in `packages/db/alembic/versions/` are created
inside `for table in (...)` loops, so any grep-based checker gives false answers in
both directions.

Checks, for every table that carries an `account_id` column:

1. `relrowsecurity`  — RLS is ENABLEd.
2. `relforcerowsecurity` — RLS is FORCEd. Without FORCE the table owner bypasses every
   policy, which is exactly the connection a migration or a careless script uses.
3. At least one policy exists on the table.
4. The table is named in `packages/db/tests/test_rls_isolation.py`, so the policy is
   not merely present but actually exercised.

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


def _model_name(table: str) -> str:
    """`allocation_key_assignment` -> `AllocationKeyAssignment`.

    The isolation test selects mapped classes, not table names, so a literal search for
    the snake_case name reports covered tables as uncovered.
    """
    return "".join(part.capitalize() for part in table.split("_"))


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
           (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies
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

    for name, enabled, forced, policies in tenant_rows:
        if not enabled:
            problems.append(f"{name}: has account_id but RLS is NOT ENABLEd — silent leak")
        if not forced:
            problems.append(f"{name}: RLS not FORCEd — the table owner bypasses every policy")
        if policies == 0:
            problems.append(
                f"{name}: RLS enabled but no policy exists — denies everything or nothing"
            )
        if test_src and not _is_named(name, test_src):
            problems.append(
                f"{name}: not named in packages/db/tests/test_rls_isolation.py — "
                f"the policy is untested"
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
        f"policied + named in the isolation test; {len(EXEMPT)} exempt"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
