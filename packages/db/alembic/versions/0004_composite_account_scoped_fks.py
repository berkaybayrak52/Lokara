"""Composite FKs on (id, account_id) — a cross-account edge becomes unrepresentable.

docs/02-data-model.md → "Isolation rule". Postgres enforces referential integrity
with **RLS bypassed**: the check runs as a system operation, not as the querying
role, so it never consults a policy. A session in account B can stamp
`account_id = B` on a row (satisfying `WITH CHECK`) and still point that row's
parent link at a row owned by account A. The row is isolated; the edge it draws
is not. No policy formulation fixes this, because no policy runs.

The fix is structural, in three parts:

1. `building_assignment` gains its own `account_id` (decision, docs/02 + PLAN.md).
   It was the one tenant table scoped transitively, through `membership`. The
   denormalisation is self-enforcing — the composite FK below makes a
   `building_assignment` whose `account_id` disagrees with its membership's
   non-existent — and its RLS policy collapses to the same local-column
   comparison every other table uses.
2. Every referenced parent gains `UNIQUE (id, account_id)`. `id` is already the
   primary key, so the constraint is redundant as a uniqueness statement; it
   exists solely to be a referenceable target for the composite FK below. That
   redundancy is the point, not an oversight.
3. Every foreign key between two account-scoped tables is dropped and recreated as
   `FOREIGN KEY (parent_id, account_id) REFERENCES parent (id, account_id)`,
   `MATCH SIMPLE`. **Never MATCH FULL**: `account_id` is NOT NULL, so FULL would
   demand all-or-nothing across both columns and silently turn every optional link
   (`meter.unit_id`, `building.landlord_id`, the `direct_*` columns) into a
   mandatory one. MATCH SIMPLE skips the check whenever any referencing column is
   NULL, which keeps "unset" legal and every set value checked.

Completeness is enforced by `scripts/check_fk_isolation.py`, not by counting the
edges here; the behavioural proof lives in
`packages/db/tests/test_rls_isolation.py::TestCrossAccountForeignKeys`.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Parents referenced by an account-scoped child. Each gains UNIQUE (id, account_id)
# purely so the pair can be the target of a composite FK (see the module docstring).
_PARENTS: tuple[str, ...] = (
    "membership",
    "landlord",
    "renter",
    "building",
    "unit",
    "tenancy",
    "cost_entry",
    "meter",
)

# Every tenant-to-tenant edge: (child, link column, parent, ondelete).
# The constraint keeps its original `{child}_{column}_fkey` name — same edge, wider
# reference — so the schema reads the same after the migration as before it.
_EDGES: tuple[tuple[str, str, str, str | None], ...] = (
    ("building", "landlord_id", "landlord", None),  # nullable link
    ("building_assignment", "membership_id", "membership", "CASCADE"),
    ("building_assignment", "building_id", "building", None),
    ("unit", "building_id", "building", None),
    ("tenancy", "unit_id", "unit", None),
    ("tenancy_party", "tenancy_id", "tenancy", None),
    ("tenancy_party", "renter_id", "renter", None),
    ("self_use_period", "unit_id", "unit", None),
    ("statement", "building_id", "building", None),
    ("cost_entry", "building_id", "building", None),
    ("allocation_key_assignment", "cost_entry_id", "cost_entry", None),
    ("allocation_key_assignment", "direct_unit_id", "unit", None),  # nullable link
    ("allocation_key_assignment", "direct_tenancy_id", "tenancy", None),  # nullable link
    ("meter", "building_id", "building", None),
    ("meter", "unit_id", "unit", None),  # nullable link (building-level Hauptzähler)
    ("meter_reading", "meter_id", "meter", None),
    ("heating_cost_entry", "building_id", "building", None),
)


def _unique_name(parent: str) -> str:
    return f"uq_{parent}_id_account"


def _fk_name(child: str, column: str) -> str:
    return f"{child}_{column}_fkey"


def upgrade() -> None:
    # ── 1. building_assignment gains its own account_id ────────────────────────
    op.add_column(
        "building_assignment",
        sa.Column("account_id", sa.String(), nullable=True),  # NOT NULL after the backfill
    )
    # The backfill reads `membership` and writes `building_assignment`, both of which
    # are FORCEd under RLS — and FORCE binds the table owner too, so on a
    # non-superuser owner (Supabase) the UPDATE would silently match zero rows and
    # the SET NOT NULL below would fail. Lifting FORCE for the length of this
    # transaction makes the migration behave the same on every deployment.
    #
    # NO FORCE, not DISABLE: this migration runs as the table owner, and NO FORCE is
    # exactly the switch that exempts the owner while leaving RLS enabled — every
    # non-owner role (`lokara_app`) stays bound by its policies throughout. DISABLE
    # would turn the policies off for *everyone* for the length of the transaction,
    # which is a far larger blast radius for the same backfill. FORCE is restored
    # below; a NO FORCE that is never restored is a silent isolation hole.
    #
    # What actually guarantees the restoration on the FAILURE path is **transactional
    # DDL**, not the explicit FORCE statements below: `packages/db/alembic/env.py`
    # wraps the whole run in `context.begin_transaction()`, and Postgres rolls back
    # `ALTER TABLE … NO FORCE` with everything else. If any statement after this point
    # raises, `membership` and `building_assignment` come back FORCEd because the
    # transaction never committed — the two `FORCE` calls below are what covers the
    # *success* path only.
    #
    # Therefore: do not introduce `op.get_context().autocommit_block()` anywhere in
    # this migration. It commits the surrounding transaction and runs outside it, so a
    # later failure would leave the NO FORCE committed — `membership` un-FORCEd, its
    # owner exempt from RLS, with nothing in the schema recording that it happened.
    # The same applies to changing `env.py` to autocommit. If a future statement here
    # genuinely needs autocommit (e.g. CREATE INDEX CONCURRENTLY), it belongs in its
    # own migration, not inside this NO FORCE window.
    op.execute("ALTER TABLE membership NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE building_assignment NO FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        UPDATE building_assignment ba
        SET account_id = m.account_id
        FROM membership m
        WHERE m.id = ba.membership_id
        """
    )
    # Restore FORCE. RLS itself was never switched off, so there is nothing to
    # re-ENABLE — only the owner exemption is taken back.
    op.execute("ALTER TABLE membership FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE building_assignment FORCE ROW LEVEL SECURITY")

    op.alter_column("building_assignment", "account_id", nullable=False)
    op.create_foreign_key(
        "building_assignment_account_id_fkey",
        "building_assignment",
        "account",
        ["account_id"],
        ["id"],
    )
    op.create_index("ix_building_assignment_account", "building_assignment", ["account_id"])

    # Its scope is now local, so the policy is the same one every other tenant table
    # has — no more EXISTS (SELECT 1 FROM membership …) subquery to keep in step.
    op.execute("DROP POLICY building_assignment_isolation ON building_assignment")
    op.execute(
        """
        CREATE POLICY building_assignment_isolation ON building_assignment
        USING (account_id = current_setting('app.account_id', true))
        WITH CHECK (account_id = current_setting('app.account_id', true))
        """
    )

    # ── 2. UNIQUE (id, account_id) on every referenced parent ─────────────────
    # Redundant against the primary key by design: a composite FK can only target a
    # unique constraint, and this is the one that makes the *pair* referenceable.
    for parent in _PARENTS:
        op.create_unique_constraint(_unique_name(parent), parent, ["id", "account_id"])

    # ── 3. Bare FK → composite FK, MATCH SIMPLE ───────────────────────────────
    for child, column, parent, ondelete in _EDGES:
        name = _fk_name(child, column)
        op.drop_constraint(name, child, type_="foreignkey")
        op.create_foreign_key(
            name,
            child,
            parent,
            [column, "account_id"],
            ["id", "account_id"],
            ondelete=ondelete,
            # Explicit, because the alternative is a silent data-model change:
            # MATCH FULL on a nullable link would make that link mandatory.
            match="SIMPLE",
        )


def downgrade() -> None:
    # 3. composite FK → bare FK on the link column alone.
    for child, column, parent, ondelete in _EDGES:
        name = _fk_name(child, column)
        op.drop_constraint(name, child, type_="foreignkey")
        op.create_foreign_key(name, child, parent, [column], ["id"], ondelete=ondelete)

    # 2. the pair is no longer referenced, so the redundant constraint can go.
    for parent in _PARENTS:
        op.drop_constraint(_unique_name(parent), parent, type_="unique")

    # 1. building_assignment goes back to being scoped through its membership.
    op.execute("DROP POLICY building_assignment_isolation ON building_assignment")
    op.execute(
        """
        CREATE POLICY building_assignment_isolation ON building_assignment
        USING (EXISTS (SELECT 1 FROM membership m
                       WHERE m.id = building_assignment.membership_id
                         AND m.account_id = current_setting('app.account_id', true)))
        WITH CHECK (EXISTS (SELECT 1 FROM membership m
                            WHERE m.id = building_assignment.membership_id
                              AND m.account_id = current_setting('app.account_id', true)))
        """
    )
    op.drop_index("ix_building_assignment_account", table_name="building_assignment")
    op.drop_constraint("building_assignment_account_id_fkey", "building_assignment",
                       type_="foreignkey")
    op.drop_column("building_assignment", "account_id")
