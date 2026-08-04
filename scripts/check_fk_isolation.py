#!/usr/bin/env python3
"""Every foreign key between two account-scoped tables must carry `account_id`.

The rule and its reasoning live in `docs/02-data-model.md` → "Isolation rule". In short:

    Postgres enforces referential integrity with **RLS bypassed** — the check runs as a
    system operation, not as the querying role. So a session in account B can stamp
    `account_id = B` on a row (passing WITH CHECK) and still point its foreign key at a
    parent owned by account A. The row is isolated; the edge it draws is not. No policy
    formulation fixes this, because no policy runs.

The fix is structural: `FOREIGN KEY (parent_id, account_id) REFERENCES parent (id, account_id)`,
backed by `UNIQUE (id, account_id)` on the parent. A cross-account edge then has no
representable form.

`packages/db/tests/test_rls_isolation.py` proves the **mechanism** on a few representative
edges. This script proves **completeness** — that no edge was missed, and that edge 16 has
to satisfy the same rule. Fifteen copies of one behavioural assertion prove neither better
than three, and rot faster.

Scope: a foreign key is in scope when the child table *and* the parent table both carry an
`account_id` column. FKs to `account` and to the global `person` are out of scope
automatically, because neither carries `account_id` — the boundary itself is not scoped by
it, and `person` is global by design (migration 0001).

Usage:
    docker compose up -d
    uv run alembic -c packages/db/alembic.ini upgrade head
    uv run python scripts/check_fk_isolation.py

Exit 0 = every in-scope FK is composite, 1 = at least one bare edge, 2 = no database.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Connection, create_engine, text

REPO = Path(__file__).resolve().parent.parent

# Deliberate exceptions. Keep empty if you can; every entry is an edge the database will
# happily point at another account. Key is "child_table.constraint_name".
ALLOW: dict[str, str] = {}

# 'f' = MATCH FULL, 'p' = MATCH PARTIAL, 's' = MATCH SIMPLE
MATCH_NAMES = {"f": "FULL", "p": "PARTIAL", "s": "SIMPLE"}


def _url() -> str:
    load_dotenv(REPO / ".env")
    url = os.environ.get("DIRECT_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print(
            "check_fk_isolation: set DIRECT_URL (or DATABASE_URL) to the migrated database.\n"
            "  docker compose up -d && uv run alembic -c packages/db/alembic.ini upgrade head",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return (
        url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://")
        else url
    )


ACCOUNT_SCOPED = text(
    """
    SELECT table_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND column_name = 'account_id'
    """
)

# Nullability of every column, so a MATCH FULL constraint on an optional link can be
# distinguished from a correct one. MATCH FULL would forbid the null entirely, because
# account_id is never null and FULL demands all-or-nothing.
NULLABILITY = text(
    """
    SELECT table_name, column_name, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    """
)

FOREIGN_KEYS = text(
    """
    SELECT con.conname                AS name,
           child.relname              AS child_table,
           parent.relname             AS parent_table,
           con.confmatchtype::text    AS match_type,
           (SELECT array_agg(a.attname ORDER BY u.ord)
              FROM unnest(con.conkey) WITH ORDINALITY AS u(attnum, ord)
              JOIN pg_attribute a
                ON a.attrelid = con.conrelid AND a.attnum = u.attnum) AS child_cols,
           (SELECT array_agg(a.attname ORDER BY u.ord)
              FROM unnest(con.confkey) WITH ORDINALITY AS u(attnum, ord)
              JOIN pg_attribute a
                ON a.attrelid = con.confrelid AND a.attnum = u.attnum) AS parent_cols
    FROM pg_constraint con
    JOIN pg_class     child  ON child.oid  = con.conrelid
    JOIN pg_class     parent ON parent.oid = con.confrelid
    JOIN pg_namespace n      ON n.oid      = child.relnamespace
    WHERE con.contype = 'f'
      AND n.nspname = 'public'
    ORDER BY child.relname, con.conname
    """
)


def _survey_rows(conn: Connection, edges: list[tuple[str, str, str]]) -> list[str]:
    """`--rows`: find data that already crosses accounts, before the migration runs.

    Migration 0004 adds the composite constraints. On a database that has been writable
    under 0001-0003 — which every one of them has, since bare FKs are the whole defect —
    `ALTER TABLE ... ADD CONSTRAINT` fails on the first offending row and says nothing
    about the other sixteen edges. The operator then re-runs, fixes one, re-runs, and
    learns the extent of the damage seventeen deploys later.

    This enumerates every violating row across every in-scope edge in one pass, so the
    deploy decision is made with the whole picture. Run it as the table **owner** on the
    target database *before* upgrading — under RLS you would only see your own rows,
    which is precisely the blind spot being probed.
    """
    findings: list[str] = []
    for child, parent, link in edges:
        sql = text(
            # Table/column names are interpolated because they come from pg_constraint,
            # not from user input — there is no parameter form for an identifier.
            f"SELECT c.id, c.account_id AS child_account, p.account_id AS parent_account "
            f'FROM "{child}" c JOIN "{parent}" p ON c."{link}" = p.id '
            f"WHERE c.account_id IS DISTINCT FROM p.account_id "
            f"LIMIT 20"
        )
        try:
            rows = conn.execute(sql).all()
        except Exception as exc:  # a shape we cannot probe is still news
            findings.append(f"{child}.{link} -> {parent}: could not probe ({exc})")
            continue
        for row_id, child_acct, parent_acct in rows:
            findings.append(
                f"{child}.{link} -> {parent}: row {row_id!r} is in account "
                f"{child_acct!r} but its parent belongs to {parent_acct!r}"
            )
    return findings


def main() -> int:
    rows_mode = "--rows" in sys.argv
    engine = create_engine(_url())
    try:
        with engine.connect() as conn:
            scoped = {r[0] for r in conn.execute(ACCOUNT_SCOPED).all()}
            nullable = {(r[0], r[1]): (r[2] == "YES") for r in conn.execute(NULLABILITY).all()}
            fks = conn.execute(FOREIGN_KEYS).all()

            if rows_mode:
                edges = [
                    (
                        child,
                        parent,
                        next(c for c in (child_cols or []) if c != "account_id"),
                    )
                    for _n, child, parent, _m, child_cols, _p in fks
                    if child in scoped
                    and parent in scoped
                    and any(c != "account_id" for c in (child_cols or []))
                ]
                violations = _survey_rows(conn, edges)
    except Exception as exc:  # any connection failure is the same answer: cannot verify
        print(f"check_fk_isolation: cannot reach the database: {exc}", file=sys.stderr)
        return 2

    if not fks:
        print(
            "check_fk_isolation: no foreign keys found — run alembic upgrade head first.",
            file=sys.stderr,
        )
        return 2

    if rows_mode:
        if violations:
            print(
                f"FK isolation (--rows): {len(violations)} row(s) already cross accounts. "
                f"Migration 0004 WILL FAIL on this database.\n",
                file=sys.stderr,
            )
            for v in violations:
                print(f"  {v}", file=sys.stderr)
            print(
                "\nQuarantine or repair these rows before upgrading. Each one is a "
                "reference that should never have been representable.",
                file=sys.stderr,
            )
            return 1
        print(f"FK isolation (--rows): clean — no cross-account rows across {len(edges)} edge(s)")
        return 0

    problems: list[str] = []
    in_scope = 0
    composite = 0

    # A composite FK on a nullable account_id is decorative: MATCH SIMPLE skips the check
    # entirely when any referencing column is NULL, so the pair stops constraining anything.
    for table in sorted(scoped):
        if nullable.get((table, "account_id"), False):
            problems.append(
                f"{table}: account_id is NULLABLE — every composite FK on this table is a "
                f"no-op for rows where it is NULL (MATCH SIMPLE skips them). Make it NOT NULL."
            )

    for name, child, parent, match_type, child_cols, parent_cols in fks:
        # Out of scope unless both ends are account-scoped tables.
        if child not in scoped or parent not in scoped:
            continue
        in_scope += 1

        key = f"{child}.{name}"
        if key in ALLOW:
            print(f"  allowed: {key} — {ALLOW[key]}", file=sys.stderr)
            continue

        child_cols = list(child_cols or [])
        parent_cols = list(parent_cols or [])

        if "account_id" not in child_cols or "account_id" not in parent_cols:
            link = ", ".join(c for c in child_cols if c != "account_id") or "?"
            problems.append(
                f"{child}.{name}: bare FK ({', '.join(child_cols)}) -> "
                f"{parent}({', '.join(parent_cols)}). Postgres checks this with RLS "
                f"bypassed, so account B can point {link} at account A's {parent}. "
                f"Make it composite on (id, account_id)."
            )
            continue

        composite += 1

        # A composite FK on an optional link must be MATCH SIMPLE. account_id is never
        # null, so MATCH FULL would require the link column to be non-null too — turning
        # an optional relationship into a mandatory one, silently, at migration time.
        link_cols = [c for c in child_cols if c != "account_id"]
        if match_type == "f" and any(nullable.get((child, c), False) for c in link_cols):
            problems.append(
                f"{child}.{name}: MATCH FULL on a nullable link ({', '.join(link_cols)}). "
                f"account_id is NOT NULL, so FULL makes the link mandatory. Use MATCH SIMPLE."
            )

    if problems:
        print(f"FK isolation: {len(problems)} problem(s)\n", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(
            f"\n{composite}/{in_scope} in-scope edges are composite. "
            f"See docs/02-data-model.md -> 'Isolation rule'.",
            file=sys.stderr,
        )
        return 1

    print(
        f"FK isolation: clean — all {in_scope} tenant-to-tenant foreign key(s) carry "
        f"account_id; {len(ALLOW)} allowed exception(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
