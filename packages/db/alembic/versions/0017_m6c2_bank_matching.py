"""M6-C2 bank matching: transactions, receivables, IBAN history and the payment ledger."""
# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "bank_account",
    "bank_transaction",
    "receivable",
    "renter_matching_profile",
    "iban_history",
    "match_proposal",
    "match_confirmation",
    "payment_ledger_entry",
    "payment_allocation",
)

# docs/15 § 5.3: the payment ledger is append-only. A reversal appends compensating
# entries; past allocations are never edited or deleted. Everything else here is
# ordinary mutable projection data (a receivable's open_cents moves as it is paid).
_APPEND_ONLY = ("payment_ledger_entry", "payment_allocation")


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
    _table(
        "bank_account",
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_account_id", sa.String(), nullable=False),
        sa.Column("normalized_iban", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("consent_expires_at", sa.DateTime(timezone=True), nullable=True),
        constraints=(
            sa.UniqueConstraint(
                "account_id", "provider", "provider_account_id", name="uq_bank_account_provider"
            ),
        ),
    )

    _table(
        "bank_transaction",
        sa.Column("bank_account_id", sa.String(), nullable=False),
        sa.Column("provider_transaction_id", sa.String(), nullable=False),
        # Signed: negative is the § 5.3 reversal path, positive enters scoring, zero
        # is retained for import audit and ignored by matching.
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("bank_booking_date", sa.Date(), nullable=False),
        sa.Column("finapi_booking_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=False),
        sa.Column("counterpart_iban", sa.String(), nullable=True),
        sa.Column("counterpart_name", sa.String(length=80), nullable=True),
        sa.Column("purpose", sa.String(length=2000), nullable=True),
        sa.Column("end_to_end_reference", sa.String(), nullable=True),
        sa.Column("counterpart_mandate_reference", sa.String(), nullable=True),
        sa.Column("bank_transaction_code", sa.String(), nullable=True),
        sa.Column("provider_type", sa.String(), nullable=True),
        sa.Column(
            "is_potential_duplicate",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        constraints=(
            # docs/15 § 6: unique only together with account and bank-account identity.
            # Providers do not allocate ids globally, so a constraint on the provider
            # id alone would make one landlord's import collide with another's.
            sa.UniqueConstraint(
                "account_id",
                "bank_account_id",
                "provider_transaction_id",
                name="uq_bank_transaction_provider_identity",
            ),
        ),
    )
    _scoped_fk("bank_transaction", "bank_account_id", "bank_account")
    op.create_index(
        "ix_bank_transaction_booking", "bank_transaction", ["account_id", "bank_booking_date"]
    )

    _table(
        "receivable",
        sa.Column("renter_id", sa.String(), nullable=False),
        sa.Column("tenancy_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("expected_cents", sa.BigInteger(), nullable=False),
        sa.Column("open_cents", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("base_rent_cents", sa.BigInteger(), nullable=False),
        sa.Column("nk_advance_cents", sa.BigInteger(), nullable=False),
        sa.Column("heating_advance_cents", sa.BigInteger(), nullable=False),
        sa.Column("garage_cents", sa.BigInteger(), nullable=False),
        sa.Column("open_costs_cents", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "open_interest_cents", sa.BigInteger(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "open_principal_cents", sa.BigInteger(), nullable=False, server_default=sa.text("0")
        ),
        # docs/15 § 4 scores 15 points against a "stored reference" that §§ 3.2-3.3
        # never define. The column gives the field a home; nothing writes it and
        # `_end_to_end_signal` returns 0 until Berkay answers which field it is
        # (FRAGEN-an-Berkay-05.md). Binding the signal to a guess is the invented
        # convention M6-C1 removed.
        sa.Column("stored_reference", sa.String(), nullable=True),
        constraints=(
            sa.CheckConstraint(
                "base_rent_cents + nk_advance_cents + heating_advance_cents + garage_cents = expected_cents",
                name="ck_receivable_components_sum",
            ),
            sa.CheckConstraint(
                "open_cents >= 0 AND open_cents <= expected_cents",
                name="ck_receivable_open_range",
            ),
            sa.CheckConstraint(
                "status IN ('open', 'partial', 'settled')", name="ck_receivable_status"
            ),
            sa.CheckConstraint(
                "category IN ('rent', 'nk_nachzahlung')", name="ck_receivable_category"
            ),
        ),
    )
    _scoped_fk("receivable", "renter_id", "renter")
    _scoped_fk("receivable", "tenancy_id", "tenancy")
    op.create_index("ix_receivable_due", "receivable", ["account_id", "renter_id", "due_date"])

    _table(
        "renter_matching_profile",
        sa.Column("renter_id", sa.String(), nullable=False),
        sa.Column("payment_code", sa.String(), nullable=True),
        sa.Column("normalized_surname", sa.String(), nullable=False),
        constraints=(
            sa.UniqueConstraint(
                "account_id", "renter_id", name="uq_renter_matching_profile_renter"
            ),
        ),
    )
    _scoped_fk("renter_matching_profile", "renter_id", "renter")

    _table(
        "iban_history",
        sa.Column("renter_id", sa.String(), nullable=False),
        sa.Column("normalized_iban", sa.String(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("learned_from_transaction_id", sa.String(), nullable=True),
        sa.Column("confirmed_match_id", sa.String(), nullable=True),
        sa.Column("confirmed_by", sa.String(), nullable=True),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        constraints=(
            sa.CheckConstraint(
                "valid_to IS NULL OR valid_to >= valid_from", name="ck_iban_history_span"
            ),
        ),
    )
    _scoped_fk("iban_history", "renter_id", "renter")
    _scoped_fk("iban_history", "learned_from_transaction_id", "bank_transaction")
    op.create_index("ix_iban_history_lookup", "iban_history", ["account_id", "normalized_iban"])

    _table(
        "match_proposal",
        sa.Column("bank_transaction_id", sa.String(), nullable=False),
        sa.Column("receivable_id", sa.String(), nullable=True),
        sa.Column("renter_id", sa.String(), nullable=True),
        sa.Column("signal_iban", sa.Integer(), nullable=False),
        sa.Column("signal_amount", sa.Integer(), nullable=False),
        sa.Column("signal_code_or_surname", sa.Integer(), nullable=False),
        sa.Column("signal_e2e", sa.Integer(), nullable=False),
        sa.Column("signal_period", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("convention_version", sa.String(), nullable=False),
        sa.Column("reason_de", sa.String(), nullable=False),
        constraints=(
            sa.CheckConstraint(
                "decision IN ('AUTO_MATCH', 'NEEDS_REVIEW', 'UNMATCHED', 'DEDUPED')",
                name="ck_match_proposal_decision",
            ),
            sa.CheckConstraint(
                "confidence >= 0 AND confidence <= 100", name="ck_match_proposal_confidence"
            ),
        ),
    )
    _scoped_fk("match_proposal", "bank_transaction_id", "bank_transaction")
    _scoped_fk("match_proposal", "receivable_id", "receivable")
    _scoped_fk("match_proposal", "renter_id", "renter")
    op.create_index(
        "ix_match_proposal_transaction", "match_proposal", ["account_id", "bank_transaction_id"]
    )

    _table(
        "match_confirmation",
        sa.Column("match_proposal_id", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("confirmed_by", sa.String(), nullable=False),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        constraints=(
            sa.CheckConstraint(
                "outcome IN ('CONFIRMED', 'REJECTED', 'DUPLICATE')",
                name="ck_match_confirmation_outcome",
            ),
        ),
    )
    _scoped_fk("match_confirmation", "match_proposal_id", "match_proposal")

    _table(
        "payment_ledger_entry",
        sa.Column("bank_transaction_id", sa.String(), nullable=False),
        sa.Column("match_proposal_id", sa.String(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("credit_cents", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("ordering_version", sa.String(), nullable=False),
        sa.Column("reverses_entry_id", sa.String(), nullable=True),
        constraints=(
            sa.CheckConstraint("kind IN ('PAYMENT', 'REVERSAL')", name="ck_payment_ledger_kind"),
            sa.CheckConstraint("credit_cents >= 0", name="ck_payment_ledger_credit_positive"),
        ),
    )
    _scoped_fk("payment_ledger_entry", "bank_transaction_id", "bank_transaction")
    _scoped_fk("payment_ledger_entry", "match_proposal_id", "match_proposal")
    _scoped_fk("payment_ledger_entry", "reverses_entry_id", "payment_ledger_entry")
    op.create_index(
        "ix_payment_ledger_transaction",
        "payment_ledger_entry",
        ["account_id", "bank_transaction_id"],
    )

    _table(
        "payment_allocation",
        sa.Column("ledger_entry_id", sa.String(), nullable=False),
        sa.Column("receivable_id", sa.String(), nullable=False),
        sa.Column("costs_cents", sa.BigInteger(), nullable=False),
        sa.Column("interest_cents", sa.BigInteger(), nullable=False),
        sa.Column("principal_cents", sa.BigInteger(), nullable=False),
        sa.Column("base_rent_cents", sa.BigInteger(), nullable=False),
        sa.Column("nk_advance_cents", sa.BigInteger(), nullable=False),
        sa.Column("heating_advance_cents", sa.BigInteger(), nullable=False),
        sa.Column("garage_cents", sa.BigInteger(), nullable=False),
        sa.Column("resulting_status", sa.String(), nullable=False),
        constraints=(
            sa.CheckConstraint(
                "base_rent_cents + nk_advance_cents + heating_advance_cents + garage_cents = principal_cents",
                name="ck_payment_allocation_components_sum",
            ),
            sa.CheckConstraint(
                "resulting_status IN ('open', 'partial', 'settled')",
                name="ck_payment_allocation_status",
            ),
        ),
    )
    _scoped_fk("payment_allocation", "ledger_entry_id", "payment_ledger_entry")
    _scoped_fk("payment_allocation", "receivable_id", "receivable")
    op.create_index(
        "ix_payment_allocation_receivable", "payment_allocation", ["account_id", "receivable_id"]
    )

    # CLAUDE.md rule 3, and check_rls_coverage.py enforces it against the live
    # database: ENABLE alone is not enough. Without FORCE the table owner bypasses
    # every policy, and a migration or a careless script runs as the owner.
    for table in _TABLES:
        op.create_index(f"ix_{table}_account", table, ["account_id"])
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_isolation ON {table} USING (account_id = current_setting('app.account_id', true)) WITH CHECK (account_id = current_setting('app.account_id', true))"
        )

    op.execute("""
        CREATE FUNCTION prevent_payment_ledger_rewrite() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'payment ledger is append-only' USING ERRCODE = '23514';
        END; $$
    """)
    for table in _APPEND_ONLY:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prevent_payment_ledger_rewrite()"
        )


def downgrade() -> None:
    raise RuntimeError("M6-C2 payment evidence is intentionally not downgraded")
