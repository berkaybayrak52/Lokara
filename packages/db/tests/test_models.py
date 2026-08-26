"""Structural tests on the mapped metadata — no database required.

These pin the docs/02 invariants at the schema level: every domain table
carries account_id, the uniqueness rules exist, and the RLS table list in
ACCOUNT_SCOPED_TABLES can never silently drift from the models.
"""

from lokara_db import ACCOUNT_SCOPED_TABLES, Base, DbSettings, sqlalchemy_url
from sqlalchemy import UniqueConstraint
from sqlalchemy.sql.schema import Table

EXPECTED_TABLES = {
    "person",
    "account",
    "membership",
    "building_assignment",
    "landlord",
    "renter",
    "building",
    "unit",
    "tenancy",
    "tenancy_party",
    "advance_payment_period",
    "advance_payment",
    "advance_allocation",
    "advance_reconciliation",
    "advance_reconciliation_allocation",
    "person_count",
    "mdl_statement",
    "mdl_statement_position",
    "self_use_period",
    "statement",
    "statement_document_archive",
    "statement_settlement",
    "tenancy_delivery_address",
    "owner_payment_credit_instruction",
    "cost_entry",
    "allocation_key_assignment",
    "operating_cost_agreement",
    "confirmed_cost_classification",
    "meter",
    "meter_reading",
    "heating_cost_entry",
    # M6-C2 bank matching (docs/15, docs/02 § 6, migration 0017).
    "bank_account",
    "bank_transaction",
    "receivable",
    "renter_matching_profile",
    "iban_history",
    "match_proposal",
    "match_confirmation",
    "payment_ledger_entry",
    "payment_allocation",
    # U4 UVI persistence (docs/16 §§ 3, 7.2, 9, 10, 12; migration 0022).
    "monthly_meter_reading",
    "monthly_meter_reading_source",
    "uvi_station_assignment",
    "dwd_climate_factor",
    "uvi_run",
    "uvi_delivery_event",
    # U4b authoritative normalized inputs (docs/16 § 3.1; migration 0023).
    "uvi_monthly_degree_day",
    "building_uvi_configuration",
    "uvi_building_monthly_evidence",
    "uvi_building_monthly_evidence_source",
    # M7 AfA and tax export persistence (docs/10–11; migration 0024).
    "afa_record_version",
    "tax_event",
    "tax_adviser_profile_version",
    "tax_mapping_version",
    "tax_export_readiness_attempt",
    "tax_export_archive",
    "tax_export_artifact",
    # M9 guards, delivery evidence and checklists (docs/12; migration 0025).
    "guard_evaluation",
    "guard_reminder",
    "guard_resolution_event",
    "delivery_schedule_version",
    "renter_delivery_artifact",
    "email_attempt",
    "email_delivery_status_event",
    "recipient_suppression_event",
    "checklist_instance",
    "checklist_item_event",
}


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _unique_column_sets(table: Table) -> set[frozenset[str]]:
    return {
        frozenset(col.name for col in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


class TestSchemaShape:
    def test_exactly_the_docs02_tables_exist(self) -> None:
        assert set(Base.metadata.tables) == EXPECTED_TABLES

    def test_every_account_scoped_table_carries_account_id(self) -> None:
        for name in ACCOUNT_SCOPED_TABLES:
            table = _table(name)
            assert "account_id" in table.columns, f"{name} is missing account_id"
            assert not table.columns["account_id"].nullable, f"{name}.account_id must be NOT NULL"

    def test_scoped_list_covers_all_domain_tables(self) -> None:
        # Only two tables are exempt: person = global identity (one human, many
        # accounts); account = IS the boundary, scoped by its own id. Everything
        # else MUST be in ACCOUNT_SCOPED_TABLES — a domain table cannot dodge RLS.
        #
        # building_assignment was the third entry here while its scope was derived
        # through membership. Migration 0004 gave it a real, NOT NULL account_id
        # (docs/02 → "Isolation rule"), which is exactly what this tuple means, so
        # it is an ordinary account-scoped table now — same as it already is in
        # scripts/check_rls_coverage.py, whose EXEMPT set no longer lists it.
        exempt = {"person", "account"}
        assert set(ACCOUNT_SCOPED_TABLES) == EXPECTED_TABLES - exempt

    def test_membership_is_unique_per_person_and_account(self) -> None:
        assert frozenset({"person_id", "account_id"}) in _unique_column_sets(_table("membership"))

    def test_tenancy_party_is_unique_per_tenancy_and_renter(self) -> None:
        assert frozenset({"tenancy_id", "renter_id"}) in _unique_column_sets(
            _table("tenancy_party")
        )

    def test_statement_version_chain_is_unique(self) -> None:
        assert frozenset({"building_id", "period_start", "period_end", "version"}) in (
            _unique_column_sets(_table("statement"))
        )

    def test_money_and_area_columns_are_integers(self) -> None:
        for table_name, column in (
            ("tenancy", "base_rent_cents"),
            ("statement", "total_cents"),
            ("unit", "area_sqm_x100"),
            ("self_use_period", "sqm_x100"),
            ("cost_entry", "amount_cents"),
        ):
            assert _table(table_name).columns[column].type.python_type is int

    def test_validity_columns_are_day_granular_dates(self) -> None:
        from datetime import date

        for table_name in ("tenancy", "self_use_period"):
            table = _table(table_name)
            assert table.columns["valid_from"].type.python_type is date
            assert table.columns["valid_to"].type.python_type is date
            assert table.columns["valid_to"].nullable  # NULL = open-ended (half-open period)
        cost = _table("cost_entry")
        assert cost.columns["period_from"].type.python_type is date
        assert cost.columns["period_to"].type.python_type is date

    def test_allocation_key_never_lives_on_the_cost_row(self) -> None:
        """docs/03: keys come from a per-period assignment, so re-keying a cost
        can never destroy entered data. A `key` column on cost_entry would be
        exactly that bug."""
        assert "key" not in _table("cost_entry").columns
        assert "key" in _table("allocation_key_assignment").columns

    def test_heating_costs_carry_no_allocation_key(self) -> None:
        """§§ 7-9 HeizkostenV dictate how heating costs split, so offering an
        Umlageschlüssel for them would be legally wrong — which is why they are
        their own table rather than a flag on cost_entry."""
        heating = _table("heating_cost_entry")
        assert "key" not in heating.columns
        assert "allocation_key" not in heating.columns
        assert not any(
            fk.column.table.name == "allocation_key_assignment"
            for col in heating.columns
            for fk in col.foreign_keys
        )

    def test_meter_readings_are_append_only_by_shape(self) -> None:
        """A reading has no mutable-state column (no `superseded`, no
        `replaced_by`): supersession is DERIVED from read_at + recorded_at, so
        a correction is a plain INSERT and history cannot be rewritten."""
        reading = _table("meter_reading")
        assert {"read_at", "value_x1000", "reason", "source", "recorded_at"} <= set(
            reading.columns.keys()
        )
        for forbidden in ("superseded", "replaced_by", "deleted_at", "updated_at"):
            assert forbidden not in reading.columns, forbidden

    def test_eichfrist_is_a_date_not_a_flag(self) -> None:
        """The expiry warning is computed from the date on every read — storing
        a boolean would go stale the day after it was written."""
        meter = _table("meter")
        assert "calibration_valid_until" in meter.columns
        # Nullable: Heizkostenverteiler are not eichpflichtig at all.
        assert meter.columns["calibration_valid_until"].nullable
        assert "calibration_expired" not in meter.columns

    def test_a_meter_may_belong_to_the_building_rather_than_a_unit(self) -> None:
        """The building's Wärmemengenzähler measures the whole system — its
        kWh are the § 9 denominator, so unit_id must be nullable."""
        assert _table("meter").columns["unit_id"].nullable

    def test_page01b_device_metadata_uses_exact_fixed_point_columns(self) -> None:
        meter = _table("meter")
        reading = _table("meter_reading")
        assert meter.columns["valuation_factor_x1000"].type.python_type is int
        assert meter.columns["valuation_factor_x1000"].nullable
        assert reading.columns["estimated_consumption_x1000"].type.python_type is int
        assert reading.columns["estimated_consumption_x1000"].nullable
        assert {"tenancy_id", "estimation_basis", "provenance_ref"} <= set(reading.columns.keys())
        assert reading.columns["tenancy_id"].nullable


class TestSettings:
    def test_libpq_url_is_normalized_to_psycopg(self) -> None:
        assert sqlalchemy_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
        assert sqlalchemy_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"

    def test_runtime_and_migration_roles_differ(self) -> None:
        # DATABASE_URL must be the non-owner app role — owners bypass RLS.
        settings = DbSettings()
        assert "lokara_app" in settings.database_sqlalchemy_url
        assert "lokara_app" not in settings.direct_sqlalchemy_url
