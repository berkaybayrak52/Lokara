"""Structural tests on the mapped metadata — no database required.

These pin the docs/02 invariants at the schema level: every domain table
carries account_id, the uniqueness rules exist, and the RLS table list in
ACCOUNT_SCOPED_TABLES can never silently drift from the models.
"""

import ast
import re
from pathlib import Path

from lokara_db import ACCOUNT_SCOPED_TABLES, Base, DbSettings, sqlalchemy_url
from sqlalchemy import Boolean, CheckConstraint, Enum, Float, String, UniqueConstraint
from sqlalchemy.sql.schema import DefaultClause, Table

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_UI03_MIGRATION = _DB_PACKAGE_DIR / "alembic" / "versions" / "0026_ui03_building_metadata.py"
_GAS_METER_MIGRATION = _DB_PACKAGE_DIR / "alembic" / "versions" / "0033_add_gas_meter_type.py"

METER_DEVICE_FACTS = {
    ("HEAT_METER", "HEAT", "KWH"),
    ("HEAT_COST_ALLOCATOR", "HEAT", "HKV_UNITS"),
    ("WARM_WATER_METER", "WARM_WATER", "CUBIC_METRE"),
    ("COLD_WATER_METER", "COLD_WATER", "CUBIC_METRE"),
    ("GAS_METER", "HEAT", "CUBIC_METRE"),
}
_DEVICE_FACT_PATTERN = re.compile(
    r"device_type\s*=\s*'([^']+)'\s+AND\s+kind\s*=\s*'([^']+)'\s+"
    r"AND\s+measurement_unit\s*=\s*'([^']+)'"
)


def _server_default_text(table: Table, column: str) -> str:
    """Read a column's DDL-level server default as text."""
    default = table.columns[column].server_default
    assert isinstance(default, DefaultClause)
    return str(default.arg)


BUILDING_TYPES = {
    "WOHN_UND_GESCHAEFTSHAUS",
    "WOHNHAUS",
    "GEWERBEIMMOBILIE",
    "EINFAMILIENHAUS",
}

EXPECTED_TABLES = {
    "person",
    "account",
    "membership",
    "building_assignment",
    "landlord",
    "renter",
    "building",
    "unit",
    "unit_profile_version",
    "tenancy",
    "tenancy_party",
    "tenancy_contract_version",
    "tenancy_contract_position",
    "tenancy_rent_change",
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
    "statement_draft",
    "statement_document_archive",
    "statement_settlement",
    "tenancy_delivery_address",
    "owner_payment_credit_instruction",
    "cost_entry",
    "allocation_key_assignment",
    "operating_cost_agreement",
    "confirmed_cost_classification",
    "meter",
    "meter_lifecycle_event",
    "meter_reading",
    "heating_cost_entry",
    "heating_billing_mode_version",
    # M6-C2 bank matching (docs/15, docs/02 § 6, migration 0017).
    "bank_account",
    "bank_transaction",
    "bank_transaction_classification_event",
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

    def test_building_carries_ui03_metadata_and_nullable_coordinates(self) -> None:
        building = _table("building")
        assert {
            "building_type",
            "is_residential",
            "country",
            "latitude",
            "longitude",
        } <= set(building.columns.keys())

        assert isinstance(building.columns["building_type"].type, String)
        assert not isinstance(building.columns["building_type"].type, Enum)
        assert isinstance(building.columns["is_residential"].type, Boolean)
        assert isinstance(building.columns["country"].type, String)
        assert isinstance(building.columns["latitude"].type, Float)
        assert isinstance(building.columns["longitude"].type, Float)

        for name in ("building_type", "is_residential", "country"):
            assert not building.columns[name].nullable
            assert building.columns[name].server_default is not None
        assert _server_default_text(building, "building_type").strip("'") == "WOHNHAUS"
        assert _server_default_text(building, "is_residential").lower() == "true"
        assert _server_default_text(building, "country").strip("'") == "Deutschland"
        assert building.columns["latitude"].nullable
        assert building.columns["longitude"].nullable
        assert building.columns["latitude"].server_default is None
        assert building.columns["longitude"].server_default is None

    def test_building_type_uses_one_varchar_check_with_exactly_four_values(self) -> None:
        building = _table("building")
        checks = [
            constraint
            for constraint in building.constraints
            if isinstance(constraint, CheckConstraint)
            and "building_type" in str(constraint.sqltext)
        ]
        assert len(checks) == 1
        assert set(re.findall(r"'([^']+)'", str(checks[0].sqltext))) == BUILDING_TYPES

    def test_building_coordinates_have_named_nullable_world_range_checks(self) -> None:
        building = _table("building")
        checks = {
            constraint.name: " ".join(str(constraint.sqltext).lower().split())
            for constraint in building.constraints
            if isinstance(constraint, CheckConstraint)
        }
        assert {
            "ck_building_type",
            "ck_building_latitude_range",
            "ck_building_longitude_range",
        } <= set(checks)
        assert building.columns["latitude"].nullable
        assert building.columns["longitude"].nullable

        latitude = checks["ck_building_latitude_range"]
        longitude = checks["ck_building_longitude_range"]
        assert "latitude" in latitude and "-90" in latitude and "90" in latitude
        assert "longitude" in longitude and "-180" in longitude and "180" in longitude

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


class TestUi03BuildingMetadataMigration:
    def _migration_tree(self) -> ast.Module:
        assert _UI03_MIGRATION.exists(), (
            "UI-03 migration is missing: expected 0026_ui03_building_metadata.py "
            "because 0025 is reserved by paused M9"
        )
        return ast.parse(_UI03_MIGRATION.read_text())

    @staticmethod
    def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
        return next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
        )

    @staticmethod
    def _op_calls(function: ast.FunctionDef, operation: str) -> list[ast.Call]:
        return [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
            and node.func.attr == operation
        ]

    def test_revision_is_0026_directly_after_0024(self) -> None:
        tree = self._migration_tree()
        assignments = {
            target.id: node.value.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            for target in node.targets
            if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}
        }
        assert assignments == {"revision": "0026", "down_revision": "0024"}

    def test_upgrade_adds_five_columns_and_the_four_value_check(self) -> None:
        tree = self._migration_tree()
        upgrade = self._function(tree, "upgrade")
        add_column_calls = self._op_calls(upgrade, "add_column")
        added = {
            call.args[1].args[0].value
            for call in add_column_calls
            if len(call.args) >= 2
            and isinstance(call.args[1], ast.Call)
            and call.args[1].args
            and isinstance(call.args[1].args[0], ast.Constant)
        }
        assert added == {
            "building_type",
            "is_residential",
            "country",
            "latitude",
            "longitude",
        }
        created_checks = {
            call.args[0].value
            for call in self._op_calls(upgrade, "create_check_constraint")
            if call.args and isinstance(call.args[0], ast.Constant)
        }
        assert created_checks == {
            "ck_building_type",
            "ck_building_latitude_range",
            "ck_building_longitude_range",
        }
        source = _UI03_MIGRATION.read_text()
        assert "postgresql.ENUM" not in source
        for value in BUILDING_TYPES:
            assert value in source

    def test_downgrade_removes_check_and_all_five_columns(self) -> None:
        tree = self._migration_tree()
        downgrade = self._function(tree, "downgrade")
        dropped_checks = {
            call.args[0].value
            for call in self._op_calls(downgrade, "drop_constraint")
            if call.args and isinstance(call.args[0], ast.Constant)
        }
        assert dropped_checks == {
            "ck_building_type",
            "ck_building_latitude_range",
            "ck_building_longitude_range",
        }
        dropped = {
            call.args[1].value
            for call in self._op_calls(downgrade, "drop_column")
            if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant)
        }
        assert dropped == {
            "building_type",
            "is_residential",
            "country",
            "latitude",
            "longitude",
        }


class TestGasMeterMigration:
    def _source_and_tree(self) -> tuple[str, ast.Module]:
        assert _GAS_METER_MIGRATION.exists(), (
            "approved GAS_METER slice requires new migration 0033_add_gas_meter_type.py"
        )
        source = _GAS_METER_MIGRATION.read_text()
        return source, ast.parse(source)

    @staticmethod
    def _function_source(source: str, tree: ast.Module, name: str) -> str:
        function = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
        )
        assert function.end_lineno is not None
        return "\n".join(source.splitlines()[function.lineno - 1 : function.end_lineno])

    def test_0033_is_new_history_directly_after_ui08(self) -> None:
        source, _ = self._source_and_tree()
        assert 'revision = "0033"' in source
        assert 'down_revision = "0032"' in source

    def test_0033_upgrade_opens_exactly_one_new_device_tuple(self) -> None:
        source, tree = self._source_and_tree()
        upgrade = self._function_source(source, tree, "upgrade")
        assert set(_DEVICE_FACT_PATTERN.findall(upgrade)) == METER_DEVICE_FACTS

    def test_0033_downgrade_restores_exactly_the_four_ui08_tuples(self) -> None:
        source, tree = self._source_and_tree()
        downgrade = self._function_source(source, tree, "downgrade")
        assert set(_DEVICE_FACT_PATTERN.findall(downgrade)) == METER_DEVICE_FACTS - {
            ("GAS_METER", "HEAT", "CUBIC_METRE")
        }

    def test_0034_repairs_legacy_combined_factors_without_relabelling_evidence(self) -> None:
        """GAS-MIGRATION-01: schema changes never rewrite immutable legacy evidence."""
        source_0033, tree_0033 = self._source_and_tree()
        upgrade_0033 = self._function_source(source_0033, tree_0033, "upgrade")
        repairs = list((_DB_PACKAGE_DIR / "alembic" / "versions").glob("0034_*.py"))
        assert len(repairs) == 1, "legacy gas evidence requires one forward migration 0034"
        source_0034 = repairs[0].read_text()
        tree_0034 = ast.parse(source_0034)
        upgrade_0034 = self._function_source(source_0034, tree_0034, "upgrade")

        assert 'revision = "0034"' in source_0034
        assert 'down_revision = "0033"' in source_0034
        assert re.search(
            r"op\.add_column\(\s*[\"']building_uvi_configuration[\"']\s*,\s*"
            r"sa\.Column\(\s*[\"']condition_number[\"'].*?nullable=True",
            upgrade_0033,
            re.DOTALL,
        )
        for upgrade in (upgrade_0033, upgrade_0034):
            assert not re.search(
                r"UPDATE\s+(?:public\.)?building_uvi_configuration\b",
                upgrade,
                re.IGNORECASE,
            )
            assert not re.search(
                r"SET\s+condition_number\s*=",
                upgrade,
                re.IGNORECASE,
            )

        assert "calorific_factor IS NOT NULL AND condition_number IS NULL" in upgrade_0034
        paired_branch = re.search(
            r"calorific_factor IS NOT NULL AND condition_number IS NOT NULL(?P<body>.*?)"
            r"name=\"ck_building_uvi_configuration_conversion_components\"",
            upgrade_0034,
            re.DOTALL,
        )
        assert paired_branch is not None
        for required_fact in (
            "energy_source = 'Erdgas'",
            "energy_reference = 'HO'",
            "source_type = 'SUPPLIER_INVOICE'",
            "rechtsstand = '08/2026'",
            "verification_status = 'verify-before-production'",
        ):
            assert required_fact in paired_branch.group("body")
