"""M6-A temporal advance schedule and owner-confirmed actual advances.

The former tenancy scalar is copied into one open schedule row before it is
dropped.  Every later correction is an INSERT; the app role is deliberately
given no UPDATE or DELETE policy on any M6-A evidence table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "advance_payment_period",
    "advance_payment",
    "advance_allocation",
    "advance_reconciliation",
    "advance_reconciliation_allocation",
)


def _scoped_fk(table: str, column: str, parent: str, *, ondelete: str | None = None) -> None:
    op.create_foreign_key(
        f"{table}_{column}_fkey",
        table,
        parent,
        [column, "account_id"],
        ["id", "account_id"],
        ondelete=ondelete,
    )


def _scoped_tenancy_fk(table: str, column: str, parent: str) -> None:
    """Require an advance edge to retain the parent's tenancy and account."""
    op.create_foreign_key(
        f"{table}_{column}_fkey",
        table,
        parent,
        [column, "tenancy_id", "account_id"],
        ["id", "tenancy_id", "account_id"],
    )


def _scoped_account_pair_fk(table: str, column: str, parent: str) -> None:
    """Keep the usual account-pair edge alongside the stricter tenancy edge."""
    op.create_foreign_key(
        f"{table}_{column}_account_fkey",
        table,
        parent,
        [column, "account_id"],
        ["id", "account_id"],
    )


def upgrade() -> None:
    op.create_table(
        "advance_payment_period",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("predecessor_id", sa.String(), nullable=True),
        sa.Column("declaration_ref", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_cents >= 0", name="ck_advance_payment_period_non_negative"),
        sa.UniqueConstraint("id", "account_id", name="uq_advance_payment_period_id_account"),
        sa.UniqueConstraint(
            "id", "tenancy_id", "account_id", name="uq_advance_payment_period_id_tenancy_account"
        ),
        sa.UniqueConstraint(
            "tenancy_id", "valid_from", name="uq_advance_payment_period_tenancy_start"
        ),
    )
    _scoped_fk("advance_payment_period", "tenancy_id", "tenancy", ondelete="CASCADE")
    _scoped_tenancy_fk("advance_payment_period", "predecessor_id", "advance_payment_period")
    _scoped_account_pair_fk("advance_payment_period", "predecessor_id", "advance_payment_period")
    op.create_index("ix_advance_payment_period_account", "advance_payment_period", ["account_id"])
    op.create_index("ix_advance_payment_period_tenancy", "advance_payment_period", ["tenancy_id"])

    # IDs are deterministic only within this one migration; they are evidence IDs,
    # not user-visible identifiers. The declaration makes the migration's provenance explicit.
    op.execute(
        """
        INSERT INTO advance_payment_period
          (id, account_id, tenancy_id, amount_cents, valid_from, predecessor_id, declaration_ref)
        SELECT 'app_backfill_' || id, account_id, id, advance_payment_cents, valid_from,
               NULL, 'M6-A migration backfill from tenancy.advance_payment_cents'
        FROM tenancy
        """
    )
    op.drop_column("tenancy", "advance_payment_cents")

    op.create_table(
        "advance_payment",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("evidence_ref", sa.String(), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reversal_of_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_advance_payment_positive"),
        sa.UniqueConstraint("id", "account_id", name="uq_advance_payment_id_account"),
        sa.UniqueConstraint(
            "id", "tenancy_id", "account_id", name="uq_advance_payment_id_tenancy_account"
        ),
    )
    _scoped_fk("advance_payment", "tenancy_id", "tenancy")
    _scoped_tenancy_fk("advance_payment", "reversal_of_id", "advance_payment")
    _scoped_account_pair_fk("advance_payment", "reversal_of_id", "advance_payment")
    op.create_index("ix_advance_payment_account", "advance_payment", ["account_id"])
    op.create_index("ix_advance_payment_tenancy", "advance_payment", ["tenancy_id"])
    op.create_index(
        "uq_advance_payment_one_reversal",
        "advance_payment",
        ["reversal_of_id"],
        unique=True,
        postgresql_where=sa.text("reversal_of_id IS NOT NULL"),
    )

    op.create_table(
        "advance_allocation",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("payment_id", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_advance_allocation_positive"),
        sa.CheckConstraint(
            "period_end >= period_start", name="ck_advance_allocation_period_ordered"
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_advance_allocation_id_account"),
    )
    _scoped_tenancy_fk("advance_allocation", "payment_id", "advance_payment")
    _scoped_account_pair_fk("advance_allocation", "payment_id", "advance_payment")
    _scoped_fk("advance_allocation", "tenancy_id", "tenancy")
    op.create_index("ix_advance_allocation_account", "advance_allocation", ["account_id"])
    op.create_index(
        "ix_advance_allocation_tenancy_period",
        "advance_allocation",
        ["tenancy_id", "period_start", "period_end"],
    )

    op.create_table(
        "advance_reconciliation",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("supersedes_id", sa.String(), nullable=True),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "period_end >= period_start", name="ck_advance_reconciliation_period_ordered"
        ),
        sa.UniqueConstraint("id", "account_id", name="uq_advance_reconciliation_id_account"),
        sa.UniqueConstraint(
            "id", "tenancy_id", "account_id", name="uq_advance_reconciliation_id_tenancy_account"
        ),
        sa.UniqueConstraint(
            "tenancy_id",
            "period_start",
            "period_end",
            "version",
            name="uq_advance_reconciliation_version",
        ),
    )
    _scoped_fk("advance_reconciliation", "tenancy_id", "tenancy")
    _scoped_tenancy_fk("advance_reconciliation", "supersedes_id", "advance_reconciliation")
    _scoped_account_pair_fk("advance_reconciliation", "supersedes_id", "advance_reconciliation")
    op.create_index("ix_advance_reconciliation_account", "advance_reconciliation", ["account_id"])
    op.create_index(
        "ix_advance_reconciliation_tenancy_period",
        "advance_reconciliation",
        ["tenancy_id", "period_start", "period_end"],
    )

    op.create_table(
        "advance_reconciliation_allocation",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("reconciliation_id", sa.String(), nullable=False),
        sa.Column("allocation_id", sa.String(), nullable=False),
        sa.UniqueConstraint(
            "id", "account_id", name="uq_advance_reconciliation_allocation_id_account"
        ),
        sa.UniqueConstraint(
            "reconciliation_id", "allocation_id", name="uq_advance_reconciliation_allocation"
        ),
    )
    _scoped_fk("advance_reconciliation_allocation", "reconciliation_id", "advance_reconciliation")
    _scoped_fk("advance_reconciliation_allocation", "allocation_id", "advance_allocation")
    op.create_index(
        "ix_advance_reconciliation_allocation_account",
        "advance_reconciliation_allocation",
        ["account_id"],
    )

    op.execute(
        """
        CREATE FUNCTION enforce_advance_payment_period_successor()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE predecessor_start date;
        BEGIN
            IF NEW.predecessor_id IS NULL THEN
                RETURN NEW;
            END IF;
            SELECT valid_from INTO predecessor_start
            FROM advance_payment_period
            WHERE id = NEW.predecessor_id
              AND tenancy_id = NEW.tenancy_id
              AND account_id = NEW.account_id;
            IF predecessor_start IS NOT NULL AND NEW.valid_from <= predecessor_start THEN
                RAISE EXCEPTION 'advance payment period successor must start after predecessor'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$
        """
    )
    op.execute(
        "CREATE TRIGGER advance_payment_period_successor_order "
        "BEFORE INSERT ON advance_payment_period FOR EACH ROW "
        "EXECUTE FUNCTION enforce_advance_payment_period_successor()"
    )
    op.execute(
        """
        CREATE FUNCTION enforce_advance_payment_single_reversal()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.reversal_of_id IS NULL THEN
                RETURN NEW;
            END IF;
            PERFORM 1 FROM advance_payment
            WHERE id = NEW.reversal_of_id
              AND tenancy_id = NEW.tenancy_id
              AND account_id = NEW.account_id
            FOR UPDATE;
            IF EXISTS (
                SELECT 1 FROM advance_payment
                WHERE reversal_of_id = NEW.reversal_of_id
            ) THEN
                RAISE EXCEPTION 'advance payment already reversed'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$
        """
    )
    op.execute(
        "CREATE TRIGGER advance_payment_single_reversal "
        "BEFORE INSERT ON advance_payment FOR EACH ROW "
        "EXECUTE FUNCTION enforce_advance_payment_single_reversal()"
    )
    op.execute(
        """
        CREATE FUNCTION enforce_advance_allocation_cap()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE payment_amount integer;
        DECLARE allocated_amount integer;
        BEGIN
            SELECT amount_cents INTO payment_amount
            FROM advance_payment
            WHERE id = NEW.payment_id
              AND tenancy_id = NEW.tenancy_id
              AND account_id = NEW.account_id
            FOR UPDATE;
            IF NOT FOUND THEN
                RETURN NEW;
            END IF;
            SELECT COALESCE(sum(amount_cents), 0) INTO allocated_amount
            FROM advance_allocation
            WHERE payment_id = NEW.payment_id
              AND tenancy_id = NEW.tenancy_id
              AND account_id = NEW.account_id;
            IF allocated_amount + NEW.amount_cents > payment_amount THEN
                RAISE EXCEPTION 'advance allocation exceeds payment'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$
        """
    )
    op.execute(
        "CREATE TRIGGER advance_allocation_cap "
        "BEFORE INSERT ON advance_allocation FOR EACH ROW "
        "EXECUTE FUNCTION enforce_advance_allocation_cap()"
    )
    op.execute(
        """
        CREATE FUNCTION enforce_advance_reconciliation_allocation_tenancy()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE reconciliation_tenancy text;
        DECLARE allocation_tenancy text;
        BEGIN
            SELECT tenancy_id INTO reconciliation_tenancy
            FROM advance_reconciliation
            WHERE id = NEW.reconciliation_id AND account_id = NEW.account_id;
            SELECT tenancy_id INTO allocation_tenancy
            FROM advance_allocation
            WHERE id = NEW.allocation_id AND account_id = NEW.account_id;
            IF reconciliation_tenancy IS NOT NULL
               AND allocation_tenancy IS NOT NULL
               AND reconciliation_tenancy <> allocation_tenancy THEN
                RAISE EXCEPTION 'advance reconciliation allocation tenancy mismatch'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$
        """
    )
    op.execute(
        "CREATE TRIGGER advance_reconciliation_allocation_tenancy "
        "BEFORE INSERT ON advance_reconciliation_allocation FOR EACH ROW "
        "EXECUTE FUNCTION enforce_advance_reconciliation_allocation_tenancy()"
    )
    op.execute(
        """
        CREATE FUNCTION prevent_advance_rewrite()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user = 'lokara_app' THEN
                -- Demo reset may remove only a disposable schedule under its
                -- own non-canonical tenancy graph.  The app role still cannot
                -- rewrite evidence or touch canonical/demo schedule rows.
                IF TG_TABLE_NAME = 'advance_payment_period' AND TG_OP = 'DELETE' THEN
                    IF OLD.account_id = 'acc_demo_lokara'
                       AND EXISTS (
                           SELECT 1 FROM tenancy t
                           JOIN unit u ON u.id = t.unit_id
                           WHERE t.id = OLD.tenancy_id
                             AND u.building_id <> 'bld_demo_muster12'
                       ) THEN
                        RETURN OLD;
                    END IF;
                END IF;
                RAISE EXCEPTION 'advance evidence is append-only' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END; $$
        """
    )
    for table in _TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_advance_rewrite()"
        )

    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_select ON {table} FOR SELECT "
            "USING (account_id = current_setting('app.account_id', true))"
        )
        op.execute(
            f"CREATE POLICY {table}_append_only ON {table} FOR ALL "
            "USING (account_id = current_setting('app.account_id', true)) "
            "WITH CHECK (account_id = current_setting('app.account_id', true))"
        )


def downgrade() -> None:
    # The old scalar cannot faithfully represent a successor schedule. Downgrade
    # retains only the initial value, which is adequate for a development rollback.
    # Tenancies created after this upgrade have no legacy scalar or schedule row;
    # map those to zero so the restored, required legacy column remains valid.
    op.add_column("tenancy", sa.Column("advance_payment_cents", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE tenancy t SET advance_payment_cents = p.amount_cents
        FROM advance_payment_period p
        WHERE p.tenancy_id = t.id AND p.predecessor_id IS NULL
        """
    )
    op.execute("UPDATE tenancy SET advance_payment_cents = 0 WHERE advance_payment_cents IS NULL")
    op.alter_column("tenancy", "advance_payment_cents", nullable=False)
    for table in _TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.execute(
        "DROP TRIGGER IF EXISTS advance_reconciliation_allocation_tenancy "
        "ON advance_reconciliation_allocation"
    )
    op.execute("DROP TRIGGER IF EXISTS advance_allocation_cap ON advance_allocation")
    op.execute("DROP TRIGGER IF EXISTS advance_payment_single_reversal ON advance_payment")
    op.execute(
        "DROP TRIGGER IF EXISTS advance_payment_period_successor_order ON advance_payment_period"
    )
    for table in reversed(_TABLES):
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS prevent_advance_rewrite()")
    op.execute("DROP FUNCTION IF EXISTS enforce_advance_reconciliation_allocation_tenancy()")
    op.execute("DROP FUNCTION IF EXISTS enforce_advance_allocation_cap()")
    op.execute("DROP FUNCTION IF EXISTS enforce_advance_payment_single_reversal()")
    op.execute("DROP FUNCTION IF EXISTS enforce_advance_payment_period_successor()")
