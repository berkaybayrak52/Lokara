"""Close the Slice B database integrity gaps.

Confirmed MDL documents are evidence: `lokara_app` may read them and append a
new version, but cannot UPDATE or DELETE either the document or a delivered
position. The schema owner remains able to perform administrative cleanup.

`person_count` is a half-open temporal fact. Its GiST exclusion constraint
prevents two counts for the same tenancy covering the same day.

The building's Fiktivbelegung mode and waiver are immutable after creation. A
mutable current-value mode would silently recalculate an already closed period
under a later convention; an effective-dated replacement requires a separate,
explicit future schema decision.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MDL_TABLES = ("mdl_statement", "mdl_statement_position")


def upgrade() -> None:
    # The prior FOR ALL policy made a same-account MDL row writable. Keep its
    # account-scoped visibility, but expose writes only through INSERT so a
    # correction is necessarily a new version/position.
    for table in _MDL_TABLES:
        op.execute(f"DROP POLICY {table}_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_isolation ON {table}
            FOR SELECT
            USING (account_id = current_setting('app.account_id', true))
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_append ON {table}
            FOR INSERT
            WITH CHECK (account_id = current_setting('app.account_id', true))
            """
        )

    # `=` on text needs btree_gist; leave the extension installed on downgrade
    # because it may be shared by independently migrated constraints.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_check_constraint(
        "ck_person_count_period_ordered",
        "person_count",
        "valid_to IS NULL OR valid_to > valid_from",
    )
    # Alembic's create_exclude_constraint treats a string expression as a quoted
    # column name. This is an expression, so issue the PostgreSQL DDL directly.
    op.execute(
        """
        ALTER TABLE person_count
        ADD CONSTRAINT ex_person_count_tenancy_period_no_overlap
        EXCLUDE USING gist (
            account_id WITH =,
            tenancy_id WITH =,
            daterange(valid_from, valid_to, '[)') WITH &&
        )
        """
    )

    op.execute(
        """
        CREATE FUNCTION prevent_fiktivbelegung_rewrite()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.fiktivbelegung_mode IS DISTINCT FROM OLD.fiktivbelegung_mode
               OR NEW.fiktivbelegung_waiver_note IS DISTINCT FROM OLD.fiktivbelegung_waiver_note
            THEN
                RAISE EXCEPTION 'fiktivbelegung mode is immutable after building creation'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER building_fiktivbelegung_immutable
        BEFORE UPDATE OF fiktivbelegung_mode, fiktivbelegung_waiver_note ON building
        FOR EACH ROW EXECUTE FUNCTION prevent_fiktivbelegung_rewrite()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER building_fiktivbelegung_immutable ON building")
    op.execute("DROP FUNCTION prevent_fiktivbelegung_rewrite()")
    op.execute("ALTER TABLE person_count DROP CONSTRAINT ex_person_count_tenancy_period_no_overlap")
    op.drop_constraint("ck_person_count_period_ordered", "person_count", type_="check")

    for table in _MDL_TABLES:
        op.execute(f"DROP POLICY {table}_append ON {table}")
        op.execute(f"DROP POLICY {table}_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_isolation ON {table}
            USING (account_id = current_setting('app.account_id', true))
            WITH CHECK (account_id = current_setting('app.account_id', true))
            """
        )
