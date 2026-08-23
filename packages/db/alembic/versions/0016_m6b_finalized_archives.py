"""M6-B immutable final statement snapshots, archives and Saldo consequences."""
# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _scoped_fk(table: str, column: str, parent: str) -> None:
    op.create_foreign_key(
        f"{table}_{column}_fkey",
        table,
        parent,
        [column, "account_id"],
        ["id", "account_id"],
    )


def _table(name: str, *columns: sa.Column[object], constraints: tuple[object, ...] = ()) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("account.id"), nullable=False),
        *columns,
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("id", "account_id", name=f"uq_{name}_id_account"),
        *constraints,
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # `statement` predates the composite-FK migration's parent set.  The
    # correction edge below is account-scoped, so this redundant pair is the
    # referenceable target required by PostgreSQL.
    op.create_unique_constraint("uq_statement_id_account", "statement", ["id", "account_id"])
    op.add_column(
        "statement",
        sa.Column(
            "finalized_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")
        ),
    )
    op.add_column("statement", sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("statement", sa.Column("supersedes_statement_id", sa.String(), nullable=True))
    _scoped_fk("statement", "supersedes_statement_id", "statement")

    _table(
        "tenancy_delivery_address",
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("addressee", sa.String(), nullable=False),
        sa.Column("street", sa.String(), nullable=False),
        sa.Column("postal_code", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        constraints=(
            sa.UniqueConstraint(
                "tenancy_id", "version", name="uq_tenancy_delivery_address_version"
            ),
        ),
    )
    _scoped_fk("tenancy_delivery_address", "tenancy_id", "tenancy")
    _table(
        "owner_payment_credit_instruction",
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("instruction_text", sa.String(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        constraints=(
            sa.UniqueConstraint(
                "account_id", "version", name="uq_owner_payment_credit_instruction_version"
            ),
        ),
    )
    _table(
        "statement_document_archive",
        sa.Column("statement_id", sa.String(), nullable=False),
        sa.Column("audience", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=True),
        sa.Column("content_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        constraints=(
            sa.UniqueConstraint(
                "statement_id", "audience", "tenancy_id", name="uq_statement_archive_audience"
            ),
            sa.CheckConstraint(
                "(audience = 'OWNER' AND tenancy_id IS NULL) OR (audience = 'TENANT' AND tenancy_id IS NOT NULL)",
                name="ck_statement_archive_audience_tenancy",
            ),
            sa.CheckConstraint("length(sha256) = 64", name="ck_statement_archive_sha256"),
        ),
    )
    _scoped_fk("statement_document_archive", "statement_id", "statement")
    _scoped_fk("statement_document_archive", "tenancy_id", "tenancy")
    op.create_index(
        "uq_statement_document_archive_owner",
        "statement_document_archive",
        ["statement_id", "audience"],
        unique=True,
        postgresql_where=sa.text("audience = 'OWNER' AND tenancy_id IS NULL"),
    )
    _table(
        "statement_settlement",
        sa.Column("statement_id", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("origin_saldo_cents", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("late_positive_exception_reason", sa.String(), nullable=True),
        constraints=(
            sa.UniqueConstraint(
                "statement_id", "tenancy_id", name="uq_statement_settlement_tenancy"
            ),
            sa.CheckConstraint("amount_cents > 0", name="ck_statement_settlement_positive"),
            sa.CheckConstraint(
                "kind IN ('RECEIVABLE', 'CREDIT_REFUND')", name="ck_statement_settlement_kind"
            ),
        ),
    )
    _scoped_fk("statement_settlement", "statement_id", "statement")
    _scoped_fk("statement_settlement", "tenancy_id", "tenancy")

    op.execute("""
        CREATE FUNCTION enforce_statement_archive_hash() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.sha256 <> encode(digest(NEW.content_bytes, 'sha256'), 'hex') THEN
            RAISE EXCEPTION 'archive SHA-256 does not match stored bytes' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute("""
        CREATE FUNCTION enforce_statement_tenancy_scope() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE statement_building_id text;
        DECLARE tenancy_building_id text;
        BEGIN
          SELECT building_id INTO statement_building_id FROM statement WHERE id = NEW.statement_id;
          SELECT u.building_id INTO tenancy_building_id FROM tenancy t JOIN unit u ON u.id = t.unit_id WHERE t.id = NEW.tenancy_id;
          IF statement_building_id IS DISTINCT FROM tenancy_building_id THEN
            RAISE EXCEPTION 'statement and tenancy must belong to the same building' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute("""
        CREATE FUNCTION enforce_statement_predecessor_scope() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE predecessor statement%ROWTYPE;
        BEGIN
          IF NEW.supersedes_statement_id IS NULL THEN RETURN NEW; END IF;
          SELECT * INTO predecessor FROM statement WHERE id = NEW.supersedes_statement_id;
          IF predecessor.building_id IS DISTINCT FROM NEW.building_id
             OR predecessor.period_start IS DISTINCT FROM NEW.period_start
             OR predecessor.period_end IS DISTINCT FROM NEW.period_end THEN
            RAISE EXCEPTION 'statement predecessor must share building and period' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER statement_archive_hash_guard BEFORE INSERT ON statement_document_archive FOR EACH ROW EXECUTE FUNCTION enforce_statement_archive_hash()"
    )
    op.execute(
        "CREATE TRIGGER statement_archive_tenancy_scope BEFORE INSERT OR UPDATE ON statement_document_archive FOR EACH ROW WHEN (NEW.tenancy_id IS NOT NULL) EXECUTE FUNCTION enforce_statement_tenancy_scope()"
    )
    op.execute(
        "CREATE TRIGGER statement_settlement_tenancy_scope BEFORE INSERT OR UPDATE ON statement_settlement FOR EACH ROW EXECUTE FUNCTION enforce_statement_tenancy_scope()"
    )
    op.execute(
        "CREATE TRIGGER statement_predecessor_scope BEFORE INSERT OR UPDATE ON statement FOR EACH ROW WHEN (NEW.supersedes_statement_id IS NOT NULL) EXECUTE FUNCTION enforce_statement_predecessor_scope()"
    )

    for table in (
        "tenancy_delivery_address",
        "owner_payment_credit_instruction",
        "statement_document_archive",
        "statement_settlement",
    ):
        op.create_index(f"ix_{table}_account", table, ["account_id"])
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_isolation ON {table} USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))"
        )

    op.execute("""
        CREATE FUNCTION prevent_m6b_rewrite() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'final statement evidence is append-only' USING ERRCODE = '23514';
        END; $$
    """)
    for table in (
        "tenancy_delivery_address",
        "owner_payment_credit_instruction",
        "statement_document_archive",
        "statement_settlement",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prevent_m6b_rewrite()"
        )
    op.execute("""
        CREATE FUNCTION enforce_statement_finalization() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            IF OLD.status IN ('FINALIZED', 'SUPERSEDED') THEN
              RAISE EXCEPTION 'final statement is append-only' USING ERRCODE = '23514';
            END IF;
            RETURN OLD;
          END IF;
          IF OLD.status = 'DRAFT' AND NEW.status = 'FINALIZED' THEN RETURN NEW; END IF;
          IF OLD.status = 'FINALIZED' AND NEW.status = 'SUPERSEDED'
             AND (to_jsonb(NEW) - 'status') IS NOT DISTINCT FROM (to_jsonb(OLD) - 'status')
          THEN RETURN NEW; END IF;
          IF OLD.status IN ('FINALIZED', 'SUPERSEDED') THEN
            RAISE EXCEPTION 'only FINALIZED to SUPERSEDED is permitted' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER statement_finalization_guard BEFORE UPDATE OR DELETE ON statement FOR EACH ROW EXECUTE FUNCTION enforce_statement_finalization()"
    )


def downgrade() -> None:
    raise RuntimeError("M6-B finalized evidence is intentionally not downgraded")
