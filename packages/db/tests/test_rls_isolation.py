"""RLS isolation tests against a live Postgres.

The whole ballgame (docs/02, CLAUDE.md rule 3): a session carrying account B's RLS
context must NOT see account A's rows, as the non-owner `lokara_app` role.

The suite is self-sufficient: it applies scripts/init-app-role.sql and
`alembic upgrade head` itself, so a plain `pytest` run only needs the
docker-compose Postgres (locally) or the CI service container.

Skips when Postgres is unreachable — unless LOKARA_REQUIRE_DB is set (CI sets
it, so the gate can never silently vanish there). Seeding runs as the local
superuser, which bypasses RLS even though the policies are FORCEd.
TODO(supabase): on Supabase the migration role is a non-superuser owner, so
FORCE binds it too — admin/seed flows there must set a context.
"""

import os
from collections.abc import Iterator
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import (
    Account,
    AdvanceAllocation,
    AdvancePayment,
    AdvancePaymentPeriod,
    AdvanceReconciliation,
    AdvanceReconciliationAllocation,
    AllocationKeyAssignment,
    BankAccount,
    BankTransaction,
    Building,
    BuildingAssignment,
    ConfirmedCostClassification,
    CostEntry,
    DbSettings,
    DeliveryAddress,
    HeatingCostEntry,
    IbanHistory,
    Landlord,
    MatchConfirmation,
    MatchProposal,
    MdlBranch,
    MdlStatement,
    MdlStatementPosition,
    Membership,
    Meter,
    MeterReading,
    OperatingCostAgreement,
    PaymentAllocation,
    PaymentInstruction,
    PaymentLedgerEntry,
    Person,
    PersonCount,
    Receivable,
    Renter,
    RenterMatchingProfile,
    Role,
    SelfUseKind,
    SelfUsePeriod,
    Statement,
    StatementArchive,
    StatementSettlement,
    StatementStatus,
    Tenancy,
    TenancyParty,
    Unit,
    account_scoped_session,
    create_db_engine,
    new_id,
)
from lokara_domain import (
    AllocationKey,
    MeasurementUnit,
    MeterKind,
    ReadingReason,
    ReadingSource,
)
from sqlalchemy import CursorResult, Engine, select, text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent


def _upgraded_engines() -> tuple[Engine, Engine]:
    """(owner engine, app engine) with role + schema guaranteed current."""
    settings = DbSettings()
    owner = create_db_engine(settings.direct_url)
    with owner.connect() as conn:
        conn.execute(text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()))
        conn.commit()
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    return owner, create_db_engine(settings.database_url)


@pytest.fixture(scope="module")
def engines() -> Iterator[tuple[Engine, Engine]]:
    try:
        owner, app = _upgraded_engines()
    except OperationalError as exc:  # DB not running
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    yield owner, app
    app.dispose()
    owner.dispose()


class _Seed:
    """Two accounts: A owns a person/membership/building/unit/tenancy/assignment/
    renter/statement; B is empty. Unique ids per run so reruns never collide."""

    def __init__(self) -> None:
        self.account_a = new_id()
        self.account_b = new_id()
        self.building_a = new_id()
        self.unit_a = new_id()
        self.tenancy_a = new_id()
        self.tenancy_party_a = new_id()
        self.renter_a = new_id()
        self.statement_a = new_id()
        self.person_a = new_id()
        self.membership_a = new_id()
        self.assignment_a = new_id()
        self.cost_a = new_id()
        self.key_assignment_a = new_id()
        self.agreement_a = new_id()
        self.classification_a = new_id()
        self.meter_a = new_id()
        self.reading_a = new_id()
        self.heating_cost_a = new_id()
        # Rows the composite-FK tests try to write from B. While the defect is
        # unfixed those inserts SUCCEED and commit, so the ids are fixed here
        # and the teardown below deletes them; once the FKs are composite the
        # inserts are rejected, the transaction rolls back and the deletes are
        # no-ops. `membership_b` is created per-test, not here — see its fixture.
        self.membership_b = new_id()
        self.building_b = new_id()
        self.leaked_unit_b = new_id()
        self.leaked_meter_b = new_id()
        self.leaked_assignment_b = new_id()
        # Personenschlüssel rows (Page 01 § 3.5 / docs/02 § 5). Created per test
        # by the `person_count_rows` fixture, not here, so the module-wide
        # "B sees zero rows" assertions above keep meaning what they say — but
        # the ids live on the seed so the teardown below can sweep them even if
        # a leaked insert commits, exactly like `leaked_assignment_b`.
        self.person_count_a = new_id()
        self.leaked_person_count_b = new_id()
        self.cross_tenancy_person_count_b = new_id()
        # Confirmed Messdienstleister statements (migration 0008, docs/03 H7).
        # Same arrangement as the Personenschlüssel ids above: the rows live in a
        # per-test fixture, the ids live here so the module teardown can sweep
        # anything a broken policy or a broken FK let through.
        self.mdl_statement_a = new_id()
        self.mdl_position_a = new_id()
        self.leaked_mdl_statement_b = new_id()
        self.leaked_mdl_position_b = new_id()
        self.cross_building_mdl_statement_b = new_id()
        self.cross_tenancy_mdl_position_b = new_id()
        self.cross_statement_mdl_position_b = new_id()
        # Rows B creates *legitimately* inside the cross-parent transactions, so
        # that only ONE link in the asserted row crosses accounts. They roll back
        # with the rejection; the ids exist for the sweep.
        self.own_mdl_statement_b = new_id()
        self.own_unit_b = new_id()
        self.own_tenancy_b = new_id()


@pytest.fixture(scope="module")
def seed(engines: tuple[Engine, Engine]) -> Iterator[_Seed]:
    owner, _ = engines
    ids = _Seed()
    with Session(owner) as session, session.begin():
        session.add(Account(id=ids.account_a, name="Konto A"))
        session.add(Account(id=ids.account_b, name="Konto B"))
        session.add(Person(id=ids.person_a, email=f"owner-{ids.person_a}@example.test"))
        session.add(
            Membership(
                id=ids.membership_a,
                person_id=ids.person_a,
                account_id=ids.account_a,
                role=Role.OWNER,
            )
        )
        session.add(
            Building(
                id=ids.building_a,
                account_id=ids.account_a,
                name="Haus A",
                street="Musterstraße 1",
                postal_code="10115",
                city="Berlin",
            )
        )
        session.add(
            Unit(
                id=ids.unit_a,
                account_id=ids.account_a,
                building_id=ids.building_a,
                label="WE 1",
                area_sqm_x100=7_500,
            )
        )
        session.add(
            BuildingAssignment(
                id=ids.assignment_a,
                account_id=ids.account_a,
                membership_id=ids.membership_a,
                building_id=ids.building_a,
            )
        )
        session.add(Renter(id=ids.renter_a, account_id=ids.account_a, legal_name="Mieter A"))
        session.add(
            Statement(
                id=ids.statement_a,
                account_id=ids.account_a,
                building_id=ids.building_a,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 12, 31),
                version=1,
                status=StatementStatus.DRAFT,
                total_cents=120000,
            )
        )
    with Session(owner) as session, session.begin():
        session.add(
            CostEntry(
                id=ids.cost_a,
                account_id=ids.account_a,
                building_id=ids.building_a,
                label="Müllabfuhr",
                amount_cents=120000,
                period_from=date(2025, 1, 1),
                period_to=date(2026, 1, 1),
            )
        )
        session.add(
            AllocationKeyAssignment(
                id=ids.key_assignment_a,
                account_id=ids.account_a,
                cost_entry_id=ids.cost_a,
                key=AllocationKey.AREA,
            )
        )
        session.add(
            OperatingCostAgreement(
                id=ids.agreement_a,
                account_id=ids.account_a,
                tenancy_id=ids.tenancy_a,
                allocation_agreed=True,
                mehrbelastung_clause=False,
                valid_from=date(2025, 1, 1),
                valid_to=None,
            )
        )
        session.add(
            ConfirmedCostClassification(
                id=ids.classification_a,
                account_id=ids.account_a,
                cost_entry_id=ids.cost_a,
                allocation_key_assignment_id=ids.key_assignment_a,
                catalogue_id="muellbeseitigung",
                rule_source="BetrKV / Page 02",
                rule_rechtsstand="Rechtsstand 07/2026",
                source_amount_cents=120000,
                allocable_cents=120000,
                non_allocable_cents=0,
                labour_cents=None,
                key=AllocationKey.AREA,
                key_source="test",
                findings=["verify-before-production"],
                special_rule_evidence={},
                production_blocked=True,
            )
        )
        session.add(
            HeatingCostEntry(
                id=ids.heating_cost_a,
                account_id=ids.account_a,
                building_id=ids.building_a,
                label="Heizung & Warmwasser",
                amount_cents=1_030_000,
                period_from=date(2025, 1, 1),
                period_to=date(2026, 1, 1),
                co2_kg_x1000=2_000_000,
                co2_cost_cents=30_000,
            )
        )
        session.add(
            Tenancy(
                id=ids.tenancy_a,
                account_id=ids.account_a,
                unit_id=ids.unit_a,
                valid_from=date(2025, 1, 1),
                valid_to=None,
                base_rent_cents=85_000,
            )
        )
        session.add(
            Meter(
                id=ids.meter_a,
                account_id=ids.account_a,
                building_id=ids.building_a,
                kind=MeterKind.HEAT,
                measurement_unit=MeasurementUnit.KWH,
                serial="WMZ-A-1",
                calibration_valid_until=date(2029, 12, 31),
            )
        )
    with Session(owner) as session, session.begin():
        session.add(
            TenancyParty(
                id=ids.tenancy_party_a,
                account_id=ids.account_a,
                tenancy_id=ids.tenancy_a,
                renter_id=ids.renter_a,
            )
        )
        session.add(
            MeterReading(
                id=ids.reading_a,
                account_id=ids.account_a,
                meter_id=ids.meter_a,
                read_at=date(2025, 1, 1),
                value_x1000=148_500_000,
                reason=ReadingReason.PERIODIC,
                source=ReadingSource.MDL,
            )
        )
    # Confirmed classifications are append-only evidence. This live RLS suite
    # retains its UUID-scoped fixture graph rather than deleting that evidence
    # or its referenced cost/account parents.
    yield ids


class TestRuntimeRole:
    def test_app_role_cannot_bypass_rls(self, engines: tuple[Engine, Engine]) -> None:
        """If DATABASE_URL ever points at an owner/superuser, RLS silently stops
        applying — fail loudly here instead."""
        _, app = engines
        with Session(app) as session:
            row = session.execute(
                text(
                    "SELECT current_user, rolsuper, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            ).one()
        assert row.current_user == "lokara_app"
        assert not row.rolsuper
        assert not row.rolbypassrls


class TestCrossAccountIsolation:
    def test_cross_account_read_is_blocked(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """THE Phase B gate: account B's context must not see account A's rows."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            assert session.scalars(select(Building)).all() == []
            assert session.scalars(select(Unit)).all() == []
            assert session.scalars(select(Tenancy)).all() == []
            assert session.scalars(select(TenancyParty)).all() == []
            assert session.scalars(select(Renter)).all() == []
            assert session.scalars(select(Statement)).all() == []
            assert session.scalars(select(StatementArchive)).all() == []
            assert session.scalars(select(StatementSettlement)).all() == []
            assert session.scalars(select(DeliveryAddress)).all() == []
            assert session.scalars(select(PaymentInstruction)).all() == []
            assert session.scalars(select(Membership)).all() == []
            assert session.scalars(select(BuildingAssignment)).all() == []
            assert session.scalars(select(CostEntry)).all() == []
            assert session.scalars(select(AllocationKeyAssignment)).all() == []
            assert session.scalars(select(OperatingCostAgreement)).all() == []
            assert session.scalars(select(ConfirmedCostClassification)).all() == []
            assert session.scalars(select(Meter)).all() == []
            assert session.scalars(select(MeterReading)).all() == []
            assert session.scalars(select(HeatingCostEntry)).all() == []
            assert session.scalars(select(AdvancePaymentPeriod)).all() == []
            assert session.scalars(select(AdvancePayment)).all() == []
            assert session.scalars(select(AdvanceAllocation)).all() == []
            assert session.scalars(select(AdvanceReconciliation)).all() == []
            assert session.scalars(select(AdvanceReconciliationAllocation)).all() == []
            assert session.scalars(select(BankAccount)).all() == []
            assert session.scalars(select(BankTransaction)).all() == []
            assert session.scalars(select(Receivable)).all() == []
            assert session.scalars(select(RenterMatchingProfile)).all() == []
            assert session.scalars(select(IbanHistory)).all() == []
            assert session.scalars(select(MatchProposal)).all() == []
            assert session.scalars(select(MatchConfirmation)).all() == []
            assert session.scalars(select(PaymentLedgerEntry)).all() == []
            assert session.scalars(select(PaymentAllocation)).all() == []
            assert session.scalars(select(Account.id)).all() == [seed.account_b]

    def test_own_context_sees_own_rows(self, engines: tuple[Engine, Engine], seed: _Seed) -> None:
        """Non-vacuous control: the same query with A's context finds A's rows —
        so the empty results above are RLS at work, not an empty database."""
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            assert session.scalars(select(Building.id)).all() == [seed.building_a]
            assert session.scalars(select(Unit.id)).all() == [seed.unit_a]
            assert session.scalars(select(Tenancy.id)).all() == [seed.tenancy_a]
            assert session.scalars(select(TenancyParty.id)).all() == [seed.tenancy_party_a]
            assert session.scalars(select(Renter.id)).all() == [seed.renter_a]
            assert session.scalars(select(Statement.id)).all() == [seed.statement_a]
            assert session.scalars(select(BuildingAssignment.id)).all() == [seed.assignment_a]
            assert session.scalars(select(CostEntry.id)).all() == [seed.cost_a]
            assert session.scalars(select(AllocationKeyAssignment.id)).all() == [
                seed.key_assignment_a
            ]
            assert session.scalars(select(OperatingCostAgreement.id)).all() == [seed.agreement_a]
            assert session.scalars(select(ConfirmedCostClassification.id)).all() == [
                seed.classification_a
            ]
            assert session.scalars(select(Meter.id)).all() == [seed.meter_a]
            assert session.scalars(select(MeterReading.id)).all() == [seed.reading_a]
            assert session.scalars(select(HeatingCostEntry.id)).all() == [seed.heating_cost_a]
            assert session.scalars(select(Account.id)).all() == [seed.account_a]

    def test_missing_context_denies_by_default(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """No app.account_id set → current_setting returns NULL → zero rows."""
        _, app = engines
        with Session(app) as session:
            assert session.scalars(select(Building)).all() == []
            assert session.scalars(select(Account)).all() == []

    def test_cross_account_write_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """WITH CHECK: B's context cannot insert a row claiming account A."""
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Building(
                    account_id=seed.account_a,
                    name="Eingeschleust",
                    street="Leak-Allee 1",
                    postal_code="00000",
                    city="Nirgendwo",
                )
            )
            session.flush()


class TestU4CrossAccountWrites:
    """docs/16 § 12: every U4 table proves its WITH CHECK on a real INSERT."""

    def test_every_u4_table_rejects_a_cross_account_insert(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """U4-RLS-F01--F05: B cannot stamp UVI evidence with account A.

        Each statement supplies the complete intended row shape.  The exact
        row-level-security error matters: a NOT NULL, FK or append-only trigger
        error would not prove the policy's WITH CHECK side.
        """
        owner, app = engines
        monthly_reading_id = new_id()
        station_assignment_id = new_id()
        run_id = new_id()
        run_hash_params = {
            "tenancy": seed.tenancy_a,
            "unit": seed.unit_a,
            "month": date(2026, 7, 1),
            "inputs": '{"current_kwh":"100"}',
            "results": '{"block_a_kwh":"100"}',
            "vintage": "2025",
            "source_type": "METER_SERIES",
            "source_id": seed.reading_a,
            "assignment": station_assignment_id,
            "station_id": "00433",
            "distance": "12.345",
        }
        with owner.connect() as connection:
            run_sha256 = connection.scalar(
                text(
                    "SELECT encode(digest(convert_to(jsonb_build_object("
                    " 'tenancy_id', CAST(:tenancy AS text),"
                    " 'unit_id', CAST(:unit AS text), 'month', CAST(:month AS date),"
                    " 'inputs', CAST(:inputs AS jsonb), 'results', CAST(:results AS jsonb),"
                    " 'heizspiegel_vintage', CAST(:vintage AS text),"
                    " 'source_type', CAST(:source_type AS text),"
                    " 'source_id', CAST(:source_id AS text),"
                    " 'station_assignment_id', CAST(:assignment AS text),"
                    " 'station_id', CAST(:station_id AS text),"
                    " 'station_distance_km', CAST(:distance AS numeric(9,3))"
                    ")::text, 'UTF8'), 'sha256'), 'hex')"
                ),
                run_hash_params,
            )
        assert isinstance(run_sha256, str)
        inserts = (
            (
                "monthly_meter_reading",
                "INSERT INTO monthly_meter_reading"
                " (id, account_id, meter_id, tenancy_id, unit_id, month,"
                " consumption_x1000, reason, source, interpolation_method,"
                " supersedes_reading_id)"
                " VALUES (:id, :account_a, :meter, :tenancy, :unit, '2026-07-01',"
                " 1000, 'PERIODIC', 'MANUAL', 'NONE', NULL)",
                {
                    "id": monthly_reading_id,
                    "account_a": seed.account_a,
                    "meter": seed.meter_a,
                    "tenancy": seed.tenancy_a,
                    "unit": seed.unit_a,
                },
            ),
            (
                "monthly_meter_reading_source",
                "INSERT INTO monthly_meter_reading_source"
                " (id, account_id, monthly_meter_reading_id, meter_reading_id)"
                " VALUES (:id, :account_a, :monthly, :raw)",
                {
                    "id": new_id(),
                    "account_a": seed.account_a,
                    "monthly": monthly_reading_id,
                    "raw": seed.reading_a,
                },
            ),
            (
                "uvi_station_assignment",
                "INSERT INTO uvi_station_assignment"
                " (id, account_id, postal_code, month, station_id, distance_km,"
                " source_type, source_id)"
                " VALUES (:id, :account_a, '10115', '2026-07-01', '00433', 12.345,"
                " 'DWD_MONTHLY', '2026-07:00433')",
                {"id": station_assignment_id, "account_a": seed.account_a},
            ),
            (
                "dwd_climate_factor",
                "INSERT INTO dwd_climate_factor"
                " (id, account_id, postal_code, period_from, period_to, factor,"
                " source_type, source_id, published_at)"
                " VALUES (:id, :account_a, '10115', '2025-01-01', '2025-12-31', 1.14,"
                " 'DWD_CLIMATE_FACTOR', 'KF_20250101_20251231:10115',"
                " '2026-02-15T00:00:00+00:00')",
                {"id": new_id(), "account_a": seed.account_a},
            ),
            (
                "uvi_run",
                "INSERT INTO uvi_run"
                " (id, account_id, tenancy_id, unit_id, month, inputs, results,"
                " heizspiegel_vintage, source_type, source_id, station_assignment_id,"
                " station_id, station_distance_km, sha256)"
                " VALUES (:id, :account_a, :tenancy, :unit, '2026-07-01',"
                ' CAST(\'{"current_kwh":"100"}\' AS jsonb),'
                " CAST('{\"block_a_kwh\":\"100\"}' AS jsonb), '2025', 'METER_SERIES',"
                " :source_id, :station_assignment, '00433', 12.345, :sha256)",
                {
                    "id": run_id,
                    "account_a": seed.account_a,
                    "tenancy": seed.tenancy_a,
                    "unit": seed.unit_a,
                    "source_id": seed.reading_a,
                    "station_assignment": station_assignment_id,
                    "sha256": run_sha256,
                },
            ),
            (
                "uvi_delivery_event",
                "INSERT INTO uvi_delivery_event"
                " (id, account_id, uvi_run_id, status, occurred_at)"
                " VALUES (:id, :account_a, :run, 'GENERATED',"
                " '2026-08-01T00:00:00+00:00')",
                {
                    "id": new_id(),
                    "account_a": seed.account_a,
                    "run": run_id,
                },
            ),
        )
        refusals: dict[str, str] = {}
        for table_name, statement, params in inserts:
            with (
                pytest.raises(ProgrammingError) as refused,
                account_scoped_session(app, seed.account_b) as session,
            ):
                session.execute(text(statement), params)
            refusals[table_name] = str(refused.value)

        not_refused_by_policy = {
            table_name: message.splitlines()[0]
            for table_name, message in refusals.items()
            if "row-level security" not in message.lower()
        }
        assert not not_refused_by_policy, not_refused_by_policy


class TestM6BArchiveGuards:
    """M6-B rows are RLS-scoped evidence, not ordinary mutable cache rows."""

    def test_archive_rows_are_hidden_and_append_only(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        owner, app = engines
        address_id = new_id()
        instruction_id = new_id()
        archive_id = new_id()
        settlement_id = new_id()
        payload = b"immutable archived statement"
        with Session(owner) as session, session.begin():
            session.add_all(
                [
                    DeliveryAddress(
                        id=address_id,
                        account_id=seed.account_a,
                        tenancy_id=seed.tenancy_a,
                        version=1,
                        addressee="Mieter A",
                        street="Testweg 1",
                        postal_code="10115",
                        city="Berlin",
                        country="DE",
                        valid_from=date(2025, 1, 1),
                    ),
                    PaymentInstruction(
                        id=instruction_id,
                        account_id=seed.account_a,
                        version=1,
                        instruction_text="Bitte überweisen.",
                        valid_from=date(2025, 1, 1),
                    ),
                    StatementArchive(
                        id=archive_id,
                        account_id=seed.account_a,
                        statement_id=seed.statement_a,
                        audience="OWNER",
                        tenancy_id=None,
                        content_bytes=payload,
                        sha256=sha256(payload).hexdigest(),
                        mime_type="application/pdf",
                        filename="archiv.pdf",
                    ),
                    StatementSettlement(
                        id=settlement_id,
                        account_id=seed.account_a,
                        statement_id=seed.statement_a,
                        tenancy_id=seed.tenancy_a,
                        kind="RECEIVABLE",
                        amount_cents=1,
                        origin_saldo_cents=1,
                        late_positive_exception_reason=None,
                    ),
                ]
            )
        with account_scoped_session(app, seed.account_b) as session:
            assert session.get(StatementArchive, archive_id) is None
            assert session.get(DeliveryAddress, address_id) is None
            assert session.get(PaymentInstruction, instruction_id) is None
            assert session.get(StatementSettlement, settlement_id) is None
        with (
            pytest.raises(IntegrityError, match="append-only"),
            account_scoped_session(app, seed.account_a) as session,
        ):
            row = session.get(StatementArchive, archive_id)
            assert row is not None
            row.filename = "umgeschrieben.pdf"
            session.flush()
        immutable_rows = (
            ("tenancy_delivery_address", address_id),
            ("owner_payment_credit_instruction", instruction_id),
            ("statement_document_archive", archive_id),
            ("statement_settlement", settlement_id),
        )
        for table, row_id in immutable_rows:
            for operation in ("UPDATE", "DELETE"):
                sql = (
                    f"UPDATE {table} SET created_at = created_at WHERE id = :id"
                    if operation == "UPDATE"
                    else f"DELETE FROM {table} WHERE id = :id"
                )
                with (
                    pytest.raises(IntegrityError, match="append-only"),
                    account_scoped_session(app, seed.account_a) as session,
                ):
                    session.execute(text(sql), {"id": row_id})

        foreign_rows = (
            (
                "INSERT INTO tenancy_delivery_address (id, account_id, tenancy_id, addressee, "
                "street, postal_code, city, country, version, valid_from) VALUES (:id, "
                ":account_id, :tenancy_id, 'A', 'Weg 1', '10115', 'Berlin', 'DE', 99, "
                "DATE '2025-01-01')"
            ),
            (
                "INSERT INTO owner_payment_credit_instruction (id, account_id, version, "
                "instruction_text, valid_from) VALUES (:id, :account_id, 99, 'fremd', "
                "DATE '2025-01-01')"
            ),
            (
                "INSERT INTO statement_document_archive (id, account_id, statement_id, audience, "
                "tenancy_id, content_bytes, sha256, mime_type, filename) VALUES (:id, :account_id, "
                ":statement_id, 'TENANT', :tenancy_id, :payload, :hash, 'application/pdf', "
                "'fremd.pdf')"
            ),
            (
                "INSERT INTO statement_settlement (id, account_id, statement_id, tenancy_id, kind, "
                "amount_cents, origin_saldo_cents) VALUES (:id, :account_id, :statement_id, "
                ":tenancy_id, 'RECEIVABLE', 1, 1)"
            ),
        )
        for sql in foreign_rows:
            with (
                pytest.raises(ProgrammingError),
                account_scoped_session(app, seed.account_b) as session,
            ):
                session.execute(
                    text(sql),
                    {
                        "id": new_id(),
                        "account_id": seed.account_a,
                        "tenancy_id": seed.tenancy_a,
                        "statement_id": seed.statement_a,
                        "payload": payload,
                        "hash": sha256(payload).hexdigest(),
                    },
                )

    def test_archive_rejects_a_same_account_tenancy_from_another_building(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        _, app = engines
        building_id, unit_id, tenancy_id = new_id(), new_id(), new_id()
        payload = b"wrong building"
        with (
            pytest.raises(IntegrityError, match="same building"),
            account_scoped_session(app, seed.account_a) as session,
        ):
            session.add(
                Building(
                    id=building_id,
                    account_id=seed.account_a,
                    name="Haus Nebenan",
                    street="Nebenweg 2",
                    postal_code="10115",
                    city="Berlin",
                )
            )
            session.add(
                Unit(
                    id=unit_id,
                    account_id=seed.account_a,
                    building_id=building_id,
                    label="WE N",
                    area_sqm_x100=5_000,
                )
            )
            session.add(
                Tenancy(
                    id=tenancy_id,
                    account_id=seed.account_a,
                    unit_id=unit_id,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                    base_rent_cents=70_000,
                )
            )
            session.add(
                StatementArchive(
                    id=new_id(),
                    account_id=seed.account_a,
                    statement_id=seed.statement_a,
                    audience="TENANT",
                    tenancy_id=tenancy_id,
                    content_bytes=payload,
                    sha256=sha256(payload).hexdigest(),
                    mime_type="application/pdf",
                    filename="falsch.pdf",
                )
            )
            session.flush()

    def test_archive_hash_must_match_the_stored_bytes(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="SHA-256 does not match"),
            account_scoped_session(app, seed.account_a) as session,
        ):
            session.add(
                StatementArchive(
                    id=new_id(),
                    account_id=seed.account_a,
                    statement_id=seed.statement_a,
                    audience="TENANT",
                    tenancy_id=seed.tenancy_a,
                    content_bytes=b"actual bytes",
                    sha256="0" * 64,
                    mime_type="application/pdf",
                    filename="falsch.pdf",
                )
            )
            session.flush()

    def test_finalized_statement_cannot_change_evidence_while_superseding(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        owner, app = engines
        statement_id = new_id()
        with Session(owner) as session, session.begin():
            session.add(
                Statement(
                    id=statement_id,
                    account_id=seed.account_a,
                    building_id=seed.building_a,
                    period_start=date(2024, 1, 1),
                    period_end=date(2024, 12, 31),
                    version=1,
                    status=StatementStatus.FINALIZED,
                    total_cents=100,
                    content_hash="a" * 64,
                    finalized_snapshot={"frozen": True},
                )
            )
        with (
            pytest.raises(IntegrityError, match="only FINALIZED to SUPERSEDED"),
            account_scoped_session(app, seed.account_a) as session,
        ):
            row = session.get(Statement, statement_id)
            assert row is not None
            row.status = StatementStatus.SUPERSEDED
            row.total_cents = 101
            session.flush()

    def test_predecessor_must_share_the_finalized_building_and_period(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        owner, app = engines
        predecessor_id = new_id()
        with Session(owner) as session, session.begin():
            session.add(
                Statement(
                    id=predecessor_id,
                    account_id=seed.account_a,
                    building_id=seed.building_a,
                    period_start=date(2023, 1, 1),
                    period_end=date(2023, 12, 31),
                    version=1,
                    status=StatementStatus.FINALIZED,
                    total_cents=100,
                    content_hash="b" * 64,
                    finalized_snapshot={"frozen": True},
                )
            )
        with (
            pytest.raises(IntegrityError, match="share building and period"),
            account_scoped_session(app, seed.account_a) as session,
        ):
            session.add(
                Statement(
                    id=new_id(),
                    account_id=seed.account_a,
                    building_id=seed.building_a,
                    period_start=date(2022, 1, 1),
                    period_end=date(2022, 12, 31),
                    version=1,
                    status=StatementStatus.FINALIZED,
                    total_cents=100,
                    content_hash="c" * 64,
                    finalized_snapshot={"frozen": True},
                    supersedes_statement_id=predecessor_id,
                )
            )
            session.flush()

    def test_cross_account_reading_insert_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """meter_reading is append-only, so INSERT is its ONLY write path —
        which makes WITH CHECK the whole of its isolation. B must not be able
        to append a reading onto A's meter."""
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                MeterReading(
                    account_id=seed.account_a,
                    meter_id=seed.meter_a,
                    read_at=date(2025, 12, 31),
                    value_x1000=999_000_000,
                    reason=ReadingReason.CORRECTION,
                    source=ReadingSource.MANUAL,
                )
            )
            session.flush()

    def test_cross_account_tenancy_insert_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """WITH CHECK on tenancy: a lease is who-owes-what. B must not be able to
        stamp a tenancy onto A's unit — that would inject a payer into A's
        statement (base rent + Vorauszahlung) without ever reading A's data."""
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Tenancy(
                    account_id=seed.account_a,
                    unit_id=seed.unit_a,
                    valid_from=date(2025, 6, 1),
                    valid_to=None,
                    base_rent_cents=1,
                )
            )
            session.flush()

    def test_cross_account_tenancy_party_insert_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """WITH CHECK on tenancy_party: the join row is what makes a Renter liable
        for a lease. B attaching itself to A's tenancy must fail on INSERT — the
        SELECT block alone would not stop a blind write."""
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                TenancyParty(
                    account_id=seed.account_a,
                    tenancy_id=seed.tenancy_a,
                    renter_id=seed.renter_a,
                )
            )
            session.flush()

    def test_cross_account_tenancy_update_cannot_reach_foreign_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """USING on tenancy: B's UPDATE cannot see A's lease, so raising the rent
        touches 0 rows and A's figures are untouched afterwards."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            result: CursorResult[Any] = session.connection().execute(
                text("UPDATE tenancy SET base_rent_cents = 1 WHERE id = :tid"),
                {"tid": seed.tenancy_a},
            )
            assert result.rowcount == 0
        with account_scoped_session(app, seed.account_a) as session:
            tenancy = session.get(Tenancy, seed.tenancy_a)
            assert tenancy is not None and tenancy.base_rent_cents == 85_000

    def test_cross_account_tenancy_party_delete_cannot_reach_foreign_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """USING on tenancy_party: detaching A's Renter from A's lease under B's
        context must touch 0 rows — silent deletion is as damaging as a read."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            result: CursorResult[Any] = session.connection().execute(
                text("DELETE FROM tenancy_party WHERE id = :pid"),
                {"pid": seed.tenancy_party_a},
            )
            assert result.rowcount == 0
        with account_scoped_session(app, seed.account_a) as session:
            assert session.get(TenancyParty, seed.tenancy_party_a) is not None

    def test_cross_account_update_cannot_reach_foreign_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """UPDATE under B's context simply cannot see A's row — 0 rows touched,
        and A's data is unchanged afterwards."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            result: CursorResult[Any] = session.connection().execute(
                text("UPDATE building SET name = 'gekapert' WHERE id = :bid"),
                {"bid": seed.building_a},
            )
            assert result.rowcount == 0
        with account_scoped_session(app, seed.account_a) as session:
            building = session.get(Building, seed.building_a)
            assert building is not None and building.name == "Haus A"


class _M6AdvanceRows(NamedTuple):
    other_unit_id: str
    other_tenancy_id: str
    period_id: str
    payment_id: str
    allocation_id: str
    reconciliation_id: str
    reconciliation_allocation_id: str


@pytest.fixture
def m6_advance_rows(engines: tuple[Engine, Engine], seed: _Seed) -> Iterator[_M6AdvanceRows]:
    """One complete A-side M6-A graph, so RLS checks cannot pass vacuously."""
    owner, _ = engines
    rows = _M6AdvanceRows(*(new_id() for _ in range(7)))
    with Session(owner) as session, session.begin():
        session.add(
            Unit(
                id=rows.other_unit_id,
                account_id=seed.account_a,
                building_id=seed.building_a,
                label="M6-A Zweitwohnung",
                area_sqm_x100=4_000,
            )
        )
        session.flush()
        session.add_all(
            [
                Tenancy(
                    id=rows.other_tenancy_id,
                    account_id=seed.account_a,
                    unit_id=rows.other_unit_id,
                    valid_from=date(2024, 1, 1),
                    valid_to=None,
                    base_rent_cents=70_000,
                ),
                AdvancePaymentPeriod(
                    id=rows.period_id,
                    account_id=seed.account_a,
                    tenancy_id=seed.tenancy_a,
                    amount_cents=12_000,
                    valid_from=date(2025, 1, 1),
                    predecessor_id=None,
                    declaration_ref="M6A live RLS fixture",
                ),
                AdvancePayment(
                    id=rows.payment_id,
                    account_id=seed.account_a,
                    tenancy_id=seed.tenancy_a,
                    amount_cents=28_000,
                    payment_date=date(2025, 12, 31),
                    evidence_ref="M6A live RLS fixture",
                    reversal_of_id=None,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                AdvanceAllocation(
                    id=rows.allocation_id,
                    account_id=seed.account_a,
                    payment_id=rows.payment_id,
                    tenancy_id=seed.tenancy_a,
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    amount_cents=28_000,
                ),
                AdvanceReconciliation(
                    id=rows.reconciliation_id,
                    account_id=seed.account_a,
                    tenancy_id=seed.tenancy_a,
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    version=1,
                    total_cents=28_000,
                    supersedes_id=None,
                ),
            ]
        )
        session.flush()
        session.add(
            AdvanceReconciliationAllocation(
                id=rows.reconciliation_allocation_id,
                account_id=seed.account_a,
                reconciliation_id=rows.reconciliation_id,
                allocation_id=rows.allocation_id,
            )
        )
    yield rows
    with Session(owner) as session, session.begin():
        for table, row_id in (
            ("advance_reconciliation_allocation", rows.reconciliation_allocation_id),
            ("advance_reconciliation", rows.reconciliation_id),
            ("advance_allocation", rows.allocation_id),
            ("advance_payment", rows.payment_id),
            ("advance_payment_period", rows.period_id),
            ("tenancy", rows.other_tenancy_id),
            ("unit", rows.other_unit_id),
        ):
            session.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": row_id})


class TestM6AdvanceBoundaries:
    """M6A-F08--F11: all five advance tables need non-vacuous live proof."""

    def test_a_reads_its_complete_m6_graph_b_looks_up_nothing_and_cannot_write_it(
        self,
        engines: tuple[Engine, Engine],
        seed: _Seed,
        m6_advance_rows: _M6AdvanceRows,
    ) -> None:
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            assert session.scalars(select(AdvancePaymentPeriod.id)).all() == [
                m6_advance_rows.period_id
            ]
            assert session.scalars(select(AdvancePayment.id)).all() == [m6_advance_rows.payment_id]
            assert session.scalars(select(AdvanceAllocation.id)).all() == [
                m6_advance_rows.allocation_id
            ]
            assert session.scalars(select(AdvanceReconciliation.id)).all() == [
                m6_advance_rows.reconciliation_id
            ]
            assert session.scalars(select(AdvanceReconciliationAllocation.id)).all() == [
                m6_advance_rows.reconciliation_allocation_id
            ]
        with account_scoped_session(app, seed.account_b) as session:
            for model in (
                AdvancePaymentPeriod,
                AdvancePayment,
                AdvanceAllocation,
                AdvanceReconciliation,
                AdvanceReconciliationAllocation,
            ):
                assert session.scalars(select(model)).all() == []
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                AdvancePayment(
                    id=new_id(),
                    account_id=seed.account_a,
                    tenancy_id=seed.tenancy_a,
                    amount_cents=1,
                    payment_date=date(2025, 12, 31),
                    evidence_ref="foreign M6 write",
                    reversal_of_id=None,
                )
            )
            session.flush()

    def test_same_account_cross_tenancy_payment_link_is_rejected(
        self,
        engines: tuple[Engine, Engine],
        seed: _Seed,
        m6_advance_rows: _M6AdvanceRows,
    ) -> None:
        """RLS accepts an A row; the payment and tenancy still must agree."""
        _, app = engines
        with (
            account_scoped_session(app, seed.account_a) as session,
            pytest.raises(IntegrityError, match="advance_allocation_payment_id_fkey"),
        ):
            session.add(
                AdvanceAllocation(
                    id=new_id(),
                    account_id=seed.account_a,
                    payment_id=m6_advance_rows.payment_id,
                    tenancy_id=m6_advance_rows.other_tenancy_id,
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    amount_cents=1,
                )
            )
            session.flush()

    def test_allocations_cannot_exceed_their_positive_payment(
        self,
        engines: tuple[Engine, Engine],
        seed: _Seed,
        m6_advance_rows: _M6AdvanceRows,
    ) -> None:
        _, app = engines
        with (
            account_scoped_session(app, seed.account_a) as session,
            pytest.raises(IntegrityError, match="advance allocation exceeds payment"),
        ):
            session.add(
                AdvanceAllocation(
                    id=new_id(),
                    account_id=seed.account_a,
                    payment_id=m6_advance_rows.payment_id,
                    tenancy_id=seed.tenancy_a,
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    amount_cents=1,
                )
            )
            session.flush()

    def test_one_original_payment_has_at_most_one_reversal(
        self,
        engines: tuple[Engine, Engine],
        seed: _Seed,
        m6_advance_rows: _M6AdvanceRows,
    ) -> None:
        _, app = engines
        first_reversal_id = new_id()
        with account_scoped_session(app, seed.account_a) as session:
            session.add(
                AdvancePayment(
                    id=first_reversal_id,
                    account_id=seed.account_a,
                    tenancy_id=seed.tenancy_a,
                    amount_cents=28_000,
                    payment_date=date(2025, 12, 31),
                    evidence_ref="first reversal",
                    reversal_of_id=m6_advance_rows.payment_id,
                )
            )
            session.commit()
        try:
            with (
                account_scoped_session(app, seed.account_a) as session,
                pytest.raises(IntegrityError, match="advance payment already reversed"),
            ):
                session.add(
                    AdvancePayment(
                        id=new_id(),
                        account_id=seed.account_a,
                        tenancy_id=seed.tenancy_a,
                        amount_cents=28_000,
                        payment_date=date(2025, 12, 31),
                        evidence_ref="duplicate reversal",
                        reversal_of_id=m6_advance_rows.payment_id,
                    )
                )
                session.flush()
        finally:
            owner, _ = engines
            with Session(owner) as session, session.begin():
                reversal = session.get(AdvancePayment, first_reversal_id)
                if reversal is not None:
                    session.delete(reversal)

    def test_m6_rows_reject_every_direct_update_and_delete_except_demo_reset_schedule(
        self,
        engines: tuple[Engine, Engine],
        seed: _Seed,
        m6_advance_rows: _M6AdvanceRows,
    ) -> None:
        _, app = engines
        # The separate demo-reset API suite proves its sole exception: the app
        # role may delete a schedule for a non-canonical demo building.  None
        # of these ordinary rows (and no other evidence table) may inherit it.
        for table, row_id in (
            ("advance_payment_period", m6_advance_rows.period_id),
            ("advance_payment", m6_advance_rows.payment_id),
            ("advance_allocation", m6_advance_rows.allocation_id),
            ("advance_reconciliation", m6_advance_rows.reconciliation_id),
            (
                "advance_reconciliation_allocation",
                m6_advance_rows.reconciliation_allocation_id,
            ),
        ):
            for sql in (
                f"UPDATE {table} SET id = id WHERE id = :id",
                f"DELETE FROM {table} WHERE id = :id",
            ):
                with (
                    account_scoped_session(app, seed.account_a) as session,
                    pytest.raises(IntegrityError, match="append-only"),
                ):
                    session.execute(text(sql), {"id": row_id})


@pytest.fixture
def membership_b(engines: tuple[Engine, Engine], seed: _Seed) -> Iterator[str]:
    """A membership in account B — created per test, never in the module seed.

    `test_cross_account_read_is_blocked` asserts B's context sees zero
    memberships, and that assertion is worth keeping, so this row must not
    exist for the rest of the module. Its leaked child assignment (see below)
    goes with it.
    """
    owner, _ = engines
    with Session(owner) as session, session.begin():
        session.add(
            Membership(
                id=seed.membership_b,
                person_id=seed.person_a,  # one Person, two account contexts
                account_id=seed.account_b,
                role=Role.EMPLOYEE,
            )
        )
    yield seed.membership_b
    with Session(owner) as session, session.begin():
        for model, row_id in (
            (BuildingAssignment, seed.leaked_assignment_b),
            (Membership, seed.membership_b),
        ):
            obj = session.get(model, row_id)
            if obj is not None:
                session.delete(obj)


class TestPage02AppendOnlyAndForeignKeys:
    def test_classification_rejects_direct_update_and_delete(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """Human confirmation is evidence: corrections append, never rewrite."""
        _, app = engines
        for sql in (
            "UPDATE confirmed_cost_classification SET allocable_cents = 1 WHERE id = :id",
            "DELETE FROM confirmed_cost_classification WHERE id = :id",
        ):
            with (
                pytest.raises(IntegrityError, match="append-only"),
                account_scoped_session(app, seed.account_a) as session,
            ):
                session.execute(text(sql), {"id": seed.classification_a})

    def test_page02_parents_cannot_cross_accounts(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """Both Page-02 tables need composite FKs as well as their RLS policy."""
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="operating_cost_agreement_tenancy_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                OperatingCostAgreement(
                    id=new_id(),
                    account_id=seed.account_b,
                    tenancy_id=seed.tenancy_a,
                    allocation_agreed=True,
                    mehrbelastung_clause=True,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                )
            )
            session.flush()
        with (
            pytest.raises(IntegrityError, match="confirmed_cost_classification_cost_entry_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                ConfirmedCostClassification(
                    id=new_id(),
                    account_id=seed.account_b,
                    cost_entry_id=seed.cost_a,
                    allocation_key_assignment_id=seed.key_assignment_a,
                    catalogue_id="muellbeseitigung",
                    rule_source="test",
                    rule_rechtsstand="Rechtsstand 07/2026",
                    source_amount_cents=100,
                    allocable_cents=100,
                    non_allocable_cents=0,
                    labour_cents=None,
                    key=AllocationKey.AREA,
                    key_source="test",
                    findings=[],
                    special_rule_evidence={},
                    production_blocked=True,
                )
            )
            session.flush()


class TestCrossAccountForeignKeys:
    """Referential integrity is the THIRD enforcement point (docs/02 → "Isolation
    rule"). Postgres checks foreign keys with **RLS bypassed**, so a row that
    stamps `account_id = B` — and therefore passes `WITH CHECK` — can still point
    its parent link at a row owned by account A. `WITH CHECK` is necessary but not
    sufficient; only a composite FK on `(id, account_id)` makes the cross-account
    edge unrepresentable.

    These are three representative *shapes*, not a survey: completeness across all
    17 tenant-to-tenant edges is the job of the `scripts/check_fk_isolation.py`
    gate, which is what any NEW foreign key has to satisfy. These tests prove the
    mechanism behaves.

    Each `match=` names the **specific** constraint the test exists to prove. A
    generic "foreign key constraint" would be satisfied by a rejection from
    `*_account_id_fkey` — a different failure with a different meaning (a bad
    account link, not a cross-account edge) — and the test would pass while
    proving nothing.
    """

    def test_cross_account_unit_parent_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """Plain NOT NULL child (`unit.building_id` → `building.id`). B stamps the
        unit as its own — RLS is satisfied — but hangs it off A's building. Every
        allocation downstream (area shares, statements, PDFs) would then read a
        flat that lives in someone else's house."""
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="unit_building_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Unit(
                    id=seed.leaked_unit_b,
                    account_id=seed.account_b,
                    building_id=seed.building_a,
                    label="WE Fremdhaus",
                    area_sqm_x100=5_000,
                )
            )
            session.flush()

    def test_cross_account_nullable_parent_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """Nullable link (`meter.unit_id` → `unit.id`). B's meter sits in B's own
        building — that edge is clean — and only the OPTIONAL unit link crosses
        into A. The composite FK must still reject it, while `MATCH SIMPLE` keeps
        an unset `unit_id` (a building-level Hauptzähler) legal.

        The Building below is flushed in the same transaction as the Meter, so a
        failure on *its* insert would otherwise satisfy the test. Naming
        `meter_unit_id_fkey` closes that: a rejection of the Building (it has no
        tenant-to-tenant parent — only `building_account_id_fkey` or the PK could
        refuse it) no longer matches, and the test fails instead of passing for
        the wrong reason."""
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="meter_unit_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Building(
                    id=seed.building_b,
                    account_id=seed.account_b,
                    name="Haus B",
                    street="Bahnhofstraße 2",
                    postal_code="20095",
                    city="Hamburg",
                )
            )
            session.add(
                Meter(
                    id=seed.leaked_meter_b,
                    account_id=seed.account_b,
                    building_id=seed.building_b,
                    unit_id=seed.unit_a,
                    kind=MeterKind.HEAT,
                    measurement_unit=MeasurementUnit.KWH,
                    serial="WMZ-B-1",
                    calibration_valid_until=date(2029, 12, 31),
                )
            )
            session.flush()

    def test_cross_account_building_assignment_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, membership_b: str
    ) -> None:
        """Formerly transitive scope (`building_assignment.building_id` →
        `building.id`). Before migration 0004 this table had no `account_id` of its
        own: its RLS policy scoped it through `membership`, so a membership in B
        satisfied `WITH CHECK` and the building link was never checked against an
        account at all. An assignment is read access — B's employee would be
        granted A's building.

        The row below is the leak in its purest form and stays valid on its own
        terms: `account_id` and `membership_id` both say B, so `WITH CHECK` passes
        and the composite FK to `membership (id, account_id)` is satisfied. Only
        `building_id` crosses into A, so the FK on
        `(building_id, account_id) → building (id, account_id)` is the single
        constraint that refuses it."""
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="building_assignment_building_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                BuildingAssignment(
                    id=seed.leaked_assignment_b,
                    account_id=seed.account_b,
                    membership_id=membership_b,
                    building_id=seed.building_a,
                )
            )
            session.flush()


# ── M5a — identity schema + isolation (PLAN.md → M5a). ──────────────────────────
#
# Two things live below and they are NOT the same kind of claim:
#
#   * `landlord` / `self_use_period` already carry a FORCEd policy (migration 0001).
#     What was missing is that no test ever exercised them, which is exactly what
#     `scripts/check_rls_coverage.py` check 4 reports. These tests close the GATE,
#     not a database defect.
#   * `person` carries no RLS at all (relrowsecurity = f, zero policies). Those
#     tests fail against the live database, because the database really does hand
#     every account every human's row.


class _IdentityRows(NamedTuple):
    landlord_a: str
    self_use_a: str
    leaked_landlord_b: str
    leaked_self_use_b: str


@pytest.fixture
def identity_rows(engines: tuple[Engine, Engine], seed: _Seed) -> Iterator[_IdentityRows]:
    """A Landlord + a SelfUsePeriod in account A — created per test, never in the
    module seed, so the existing `test_cross_account_read_is_blocked` /
    `test_own_context_sees_own_rows` pair keeps asserting exactly the rows it
    was written to assert.

    The two `leaked_*` ids are the rows the WITH CHECK tests below try to write
    from B's context. Those inserts must be rejected and rolled back; the ids are
    fixed and swept here anyway, so that if a policy is ever dropped the suite
    fails on the assertion rather than poisoning every later run with a committed
    cross-account row.
    """
    owner, _ = engines
    rows = _IdentityRows(new_id(), new_id(), new_id(), new_id())
    with Session(owner) as session, session.begin():
        session.add(
            Landlord(
                id=rows.landlord_a,
                account_id=seed.account_a,
                legal_name="Vermieter A GbR",
                address="Musterstraße 1, 10115 Berlin",
            )
        )
        session.add(
            SelfUsePeriod(
                id=rows.self_use_a,
                account_id=seed.account_a,
                unit_id=seed.unit_a,
                sqm_x100=2_000,  # 20,00 m² of WE 1 owner-occupied
                kind=SelfUseKind.OWNER_OCCUPIED,
                valid_from=date(2025, 1, 1),
                valid_to=None,
            )
        )
    yield rows
    with Session(owner) as session, session.begin():
        for model, row_id in (
            (SelfUsePeriod, rows.leaked_self_use_b),
            (Landlord, rows.leaked_landlord_b),
            (SelfUsePeriod, rows.self_use_a),
            (Landlord, rows.landlord_a),
        ):
            obj = session.get(model, row_id)
            if obj is not None:
                session.delete(obj)


class TestLandlordAndSelfUseIsolation:
    """The last two tenant tables `scripts/check_rls_coverage.py` reports.

    Both are ENABLEd, FORCEd and policied since migration 0001 — the reported
    problem is check 4, "not named in the isolation test", i.e. the policy exists
    but nothing proves it behaves. AGENTS.md: *a table without a policy is a silent
    leak* — a policy without a test is a silent regression.
    """

    def test_cross_account_read_is_blocked(
        self, engines: tuple[Engine, Engine], seed: _Seed, identity_rows: _IdentityRows
    ) -> None:
        """B's context sees neither A's legal lessor nor A's Eigennutzung."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            assert session.scalars(select(Landlord)).all() == []
            assert session.scalars(select(SelfUsePeriod)).all() == []

    def test_own_context_sees_own_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed, identity_rows: _IdentityRows
    ) -> None:
        """Non-vacuous control: the same two queries under A's context find the
        rows, so the empty results above are the policy at work and not a fixture
        that never inserted anything."""
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            assert session.scalars(select(Landlord.id)).all() == [identity_rows.landlord_a]
            assert session.scalars(select(SelfUsePeriod.id)).all() == [identity_rows.self_use_a]

    def test_cross_account_landlord_insert_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, identity_rows: _IdentityRows
    ) -> None:
        """WITH CHECK on landlord. The Landlord is the legal lessor **named on the
        statement** (docs/02: a data entity, not a role). B stamping one into A's
        account would put a stranger's legal name and address on A's Abrechnung —
        a document that goes to a real Mieter."""
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Landlord(
                    id=identity_rows.leaked_landlord_b,
                    account_id=seed.account_a,
                    legal_name="Untergeschobener Vermieter",
                    address="Leak-Allee 1, 00000 Nirgendwo",
                )
            )
            session.flush()

    def test_cross_account_self_use_period_insert_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, identity_rows: _IdentityRows
    ) -> None:
        """WITH CHECK on self_use_period — the substantive one of the two.

        A SelfUsePeriod is an AREA over a period (docs/02: "Eigennutzung is NOT a
        Renter"), and self-used area falls on the landlord instead of being
        allocated. So a row written onto A's unit does not merely sit there: it
        silently removes that area from A's allocation base and moves cost onto
        A's landlord, on a statement A believes it controls. The write must fail
        at INSERT — there is no later read that would reveal it."""
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                SelfUsePeriod(
                    id=identity_rows.leaked_self_use_b,
                    account_id=seed.account_a,
                    unit_id=seed.unit_a,
                    sqm_x100=7_500,  # the whole flat — allocation base to zero
                    kind=SelfUseKind.OWNER_OCCUPIED,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                )
            )
            session.flush()


@pytest.fixture
def person_in_b(engines: tuple[Engine, Engine], seed: _Seed) -> Iterator[str]:
    """A Person who holds a Membership in account B — created per test.

    Per test, not in the module seed, for the same reason `membership_b` is:
    `test_cross_account_read_is_blocked` asserts B's context sees zero
    memberships, and that assertion is worth keeping.

    This person is the **control** for the person-RLS test. Without a person who
    is genuinely reachable from B, a policy that hid every `person` row from
    everybody would satisfy the isolation assertion and the test would prove
    nothing.
    """
    owner, _ = engines
    person_id, membership_id = new_id(), new_id()
    with Session(owner) as session, session.begin():
        session.add(Person(id=person_id, email=f"kollege-{person_id}@example.test"))
        session.add(
            Membership(
                id=membership_id,
                person_id=person_id,
                account_id=seed.account_b,
                role=Role.EMPLOYEE,
            )
        )
    yield person_id
    with Session(owner) as session, session.begin():
        for model, row_id in ((Membership, membership_id), (Person, person_id)):
            obj = session.get(model, row_id)
            if obj is not None:
                session.delete(obj)


class TestGlobalPersonIsolation:
    """`person` is the edge the composite-FK rule could not reach.

    docs/02 → "The `person` edge splits: READ is a policy (M5a), WRITE is an
    ordering rule (M10)". The READ half is what these tests own, and it is
    expressible precisely because it is not circular: the witness (`membership`)
    is an already-scoped table, and the row being tested is not the row that
    creates the relationship.

    The WRITE half — who may set `renter.person_id` — is deliberately NOT tested
    here. It is not a database property at any milestone: the person being linked
    has, by definition, no prior relationship to the account (that is what
    activation *is*), so no trigger or constraint can state it without forbidding
    the only legitimate write. It is an ordering rule owned by M10.

    Today `person` carries no RLS whatsoever (`relrowsecurity = f`,
    `relforcerowsecurity = f`, zero rows in `pg_policies`), so every one of these
    fails against the live database.
    """

    def test_person_is_visible_only_where_an_account_is_shared(
        self, engines: tuple[Engine, Engine], seed: _Seed, person_in_b: str
    ) -> None:
        """Both directions, and the control comes first on purpose.

        `person_in_b` holds a Membership in B and MUST stay visible from B —
        otherwise a policy of `USING (false)` would pass the isolation half of
        this test while breaking every account switcher in the product.
        `seed.person_a` holds a membership in A and no link of any kind into B,
        so it must not be visible from B.

        Deliberately stated as membership-vs-nothing rather than
        membership-vs-renter-link: docs/02 leaves OPEN whether a renter link also
        counts as "shares an account", and this test must not pre-decide it. Both
        candidate policies satisfy these two assertions.
        """
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            visible = set(session.scalars(select(Person.id)).all())
            assert person_in_b in visible, (
                "control failed: a person holding a Membership in this account must "
                "stay visible — a policy that hides everyone proves nothing"
            )
            assert seed.person_a not in visible, (
                "person row of an unrelated account is readable — `person` has no RLS"
            )
        with account_scoped_session(app, seed.account_a) as session:
            assert seed.person_a in set(session.scalars(select(Person.id)).all())

    def test_person_denies_by_default_without_a_context(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """No `app.account_id` → `current_setting(..., true)` is NULL → the EXISTS
        is false → zero rows, exactly like every other table
        (`test_missing_context_denies_by_default`).

        docs/02 flags the trap this creates: the login/bootstrap lookup (find the
        Person behind a Supabase Auth user, before any account exists) is an
        unscoped read and will hit this. It must be routed through a SECURITY
        DEFINER function or a dedicated role — NOT by adding
        `OR current_setting('app.account_id', true) IS NULL` to the policy, which
        would switch the policy off for every unscoped connection in the system.
        """
        _, app = engines
        with Session(app) as session:
            assert session.scalars(select(Person)).all() == []

    def test_person_has_rls_enabled_and_forced(self, engines: tuple[Engine, Engine]) -> None:
        """FORCE, not just ENABLE. Without FORCE the table owner bypasses the
        policy, and the table owner is exactly the connection a migration, a seed
        script or a careless admin task uses. Mirrors check 1 + 2 of
        `scripts/check_rls_coverage.py`, which cannot see `person` at all — it
        only inspects tables that carry an `account_id` column, and `person`
        deliberately has none."""
        _, app = engines
        with Session(app) as session:
            row = session.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relname = 'person'"
                )
            ).one()
        assert row.relrowsecurity, "person: RLS is not ENABLEd"
        assert row.relforcerowsecurity, "person: RLS is not FORCEd — the owner bypasses it"


# ── Slice B — Personenschlüssel: person_count isolation (Page 01 § 3.5, docs/02 § 5). ──
#
# `person_count` arrives with migration 0007 already ENABLEd, FORCEd and policied,
# so what follows closes check 4 of `scripts/check_rls_coverage.py` — the policy is
# exercised, not merely present — plus the composite-FK edge the policy cannot see.


@pytest.fixture
def person_count_rows(engines: tuple[Engine, Engine], seed: _Seed) -> Iterator[str]:
    """One PersonCount on account A's tenancy — created per test, never in the
    module seed, for the same reason `identity_rows` is: the existing
    `test_cross_account_read_is_blocked` / `test_own_context_sees_own_rows` pair
    must keep asserting exactly the rows it was written to assert.

    The two leaked ids the write tests below aim at are swept here as well. Those
    inserts must be rejected and rolled back, so the deletes are normally no-ops —
    but if a policy or the composite FK is ever dropped, the suite has to fail on
    the assertion instead of poisoning `tenancy` teardown for every later run.
    """
    owner, _ = engines
    with Session(owner) as session, session.begin():
        session.add(
            PersonCount(
                id=seed.person_count_a,
                account_id=seed.account_a,
                tenancy_id=seed.tenancy_a,
                count=2,
                valid_from=date(2025, 1, 1),
                valid_to=None,
            )
        )
    yield seed.person_count_a
    with Session(owner) as session, session.begin():
        for row_id in (
            seed.cross_tenancy_person_count_b,
            seed.leaked_person_count_b,
            seed.person_count_a,
        ):
            obj = session.get(PersonCount, row_id)
            if obj is not None:
                session.delete(obj)


class TestPersonCountIsolation:
    """`person_count` is a denominator, which is what makes it worth its own tests.

    A Personenzahl is not a display field: it forms the person-day denominator of
    every person-keyed cost type (docs/02 § 5). A row written into account A's
    tenancy therefore moves money on A's Abrechnung — silently, and on a document
    that goes to a real Mieter — without the writer ever reading one of A's rows.
    """

    def test_cross_account_read_is_blocked(
        self, engines: tuple[Engine, Engine], seed: _Seed, person_count_rows: str
    ) -> None:
        """B's context must not see how many people live in A's flats. The count
        is household data about named renters, not just an allocation input."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            assert session.scalars(select(PersonCount)).all() == []

    def test_own_context_sees_own_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed, person_count_rows: str
    ) -> None:
        """Non-vacuous control: the same query under A's context finds the row, so
        the empty result above is the policy at work and not a fixture that never
        inserted anything."""
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            assert session.scalars(select(PersonCount.id)).all() == [person_count_rows]

    def test_cross_account_insert_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, person_count_rows: str
    ) -> None:
        """WITH CHECK: B's context cannot stamp a count onto A's tenancy.

        INSERT is the whole of this table's isolation in practice — the count is
        history (`valid_from`/`valid_to`), so a correction is a new row rather
        than an UPDATE. A blind write of a large count would inflate A's
        person-day denominator and shrink every other renter's share, and no
        later read by A would reveal where it came from."""
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                PersonCount(
                    id=seed.leaked_person_count_b,
                    account_id=seed.account_a,
                    tenancy_id=seed.tenancy_a,
                    count=99,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                )
            )
            session.flush()

    def test_cross_account_tenancy_parent_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, person_count_rows: str
    ) -> None:
        """The composite FK, which is the half `WITH CHECK` cannot reach.

        This row stamps `account_id = B` and so passes the policy; only
        `tenancy_id` crosses into A. Postgres checks foreign keys with RLS
        bypassed, so nothing but the pair
        `(tenancy_id, account_id) → tenancy (id, account_id)` refuses it.

        `match=` names that constraint on purpose. A generic "foreign key
        constraint" would also be satisfied by `person_count_account_id_fkey` —
        a different failure with a different meaning — and the test would pass
        while proving nothing."""
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="person_count_tenancy_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                PersonCount(
                    id=seed.cross_tenancy_person_count_b,
                    account_id=seed.account_b,
                    tenancy_id=seed.tenancy_a,
                    count=3,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                )
            )
            session.flush()


# ── Slice B — confirmed Messdienstleister statements (migration 0008, docs/03 H7). ──
#
# `mdl_statement` and `mdl_statement_position` arrive ENABLEd, FORCEd and policied,
# so what follows closes check 4 of `scripts/check_rls_coverage.py` — the policy is
# exercised, not merely present — plus the two composite-FK edges the policy cannot
# see. `MdlStatement` / `MdlStatementPosition` are named as the mapped classes on
# purpose: that is what the coverage gate matches on, and it is also what the API
# writes through.


@pytest.fixture
def mdl_rows(engines: tuple[Engine, Engine], seed: _Seed) -> Iterator[tuple[str, str]]:
    """One confirmed statement on account A's building, with one position on A's
    tenancy — created per test, never in the module seed, so the module-wide
    "B sees zero rows" assertions keep meaning exactly what they say.

    The ids the write tests below aim at are swept in the module teardown rather
    than here, because two of those transactions also create B-owned parents
    (a building, a unit, a tenancy) that have to go in FK order with everything
    else. All of it is normally a no-op: the inserts must be rejected and rolled
    back, and if a policy or a composite FK is ever dropped the suite has to fail
    on the assertion instead of poisoning teardown for every later run.
    """
    owner, _ = engines
    with Session(owner) as session, session.begin():
        session.add(
            MdlStatement(
                id=seed.mdl_statement_a,
                account_id=seed.account_a,
                building_id=seed.building_a,
                branch=MdlBranch.NET,
                period_from=date(2025, 1, 1),
                period_to=date(2026, 1, 1),  # exclusive in storage
                confirmed_total_cents=120_000,
                owner_position_cents=20_000,
                source_ref="MDL-Abrechnung 2025 · Beleg 4711",
                version=1,
            )
        )
    with Session(owner) as session, session.begin():
        session.add(
            MdlStatementPosition(
                id=seed.mdl_position_a,
                account_id=seed.account_a,
                mdl_statement_id=seed.mdl_statement_a,
                tenancy_id=seed.tenancy_a,
                amount_cents=100_000,
            )
        )
    yield seed.mdl_statement_a, seed.mdl_position_a
    with Session(owner) as session, session.begin():
        position = session.get(MdlStatementPosition, seed.mdl_position_a)
        if position is not None:
            session.delete(position)
    with Session(owner) as session, session.begin():
        statement = session.get(MdlStatement, seed.mdl_statement_a)
        if statement is not None:
            session.delete(statement)


class TestMdlStatementIsolation:
    """A confirmed Messdienstleister statement is money and a named renter.

    `docs/03` H7 — "validate and pass through; never recompute MDL amounts" —
    means every cent in these two tables reaches a real Mieter's Abrechnung
    unchanged. A row visible across an account boundary discloses what a
    third-party document said about somebody else's tenants; a row *writable*
    across one puts a foreign figure on this account's statement, and because
    nothing recomputes it, no later arithmetic would contradict it.

    Both tables are covered here. The position table is not merely a child: it
    carries the per-renter amount and the tenancy it belongs to, which is the
    part a reader of the statement actually sees.
    """

    def test_cross_account_read_is_blocked(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """THE gate for these tables: B's context sees neither the confirmation
        nor its positions."""
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            assert session.scalars(select(MdlStatement)).all() == []
            assert session.scalars(select(MdlStatementPosition)).all() == []

    def test_own_context_sees_own_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """Non-vacuous control: the same two queries under A's context find the
        rows, so the empty results above are the policy at work and not a fixture
        that never inserted anything."""
        statement_id, position_id = mdl_rows
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            assert session.scalars(select(MdlStatement.id)).all() == [statement_id]
            assert session.scalars(select(MdlStatementPosition.id)).all() == [position_id]

    def test_own_context_cannot_update_a_confirmed_statement(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """A same-account app session may append a correction, never alter it.

        RLS account scoping alone is insufficient here: it deliberately exposes
        account A's own row to A, and the generic policy consequently permits an
        UPDATE today.  A confirmed MDL document is legally relevant evidence;
        its correction path is a new version, not an overwrite.
        """
        statement_id, _ = mdl_rows
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            result: CursorResult[Any] = session.connection().execute(
                text("UPDATE mdl_statement SET source_ref = 'ueberschrieben' WHERE id = :id"),
                {"id": statement_id},
            )
            assert result.rowcount == 0

    def test_own_context_cannot_delete_a_confirmed_statement(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """The original document must remain readable after every correction.

        This parent has no positions, so a baseline failure cannot be mistaken
        for its child FK refusing the deletion for an unrelated reason.
        """
        del mdl_rows
        owner, app = engines
        statement_id = new_id()
        with Session(owner) as session, session.begin():
            session.add(
                MdlStatement(
                    id=statement_id,
                    account_id=seed.account_a,
                    building_id=seed.building_a,
                    branch=MdlBranch.NET,
                    period_from=date(2024, 1, 1),
                    period_to=date(2025, 1, 1),
                    confirmed_total_cents=20_000,
                    owner_position_cents=20_000,
                    source_ref="leere bestätigte MDL-Abrechnung",
                    version=1,
                )
            )
        try:
            with account_scoped_session(app, seed.account_a) as session:
                result: CursorResult[Any] = session.connection().execute(
                    text("DELETE FROM mdl_statement WHERE id = :id"), {"id": statement_id}
                )
                assert result.rowcount == 0
        finally:
            with Session(owner) as session, session.begin():
                row = session.get(MdlStatement, statement_id)
                if row is not None:
                    session.delete(row)

    def test_own_context_cannot_update_a_confirmed_position(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """The renter amount is part of the confirmed pass-through document."""
        _, position_id = mdl_rows
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            result: CursorResult[Any] = session.connection().execute(
                text("UPDATE mdl_statement_position SET amount_cents = 1 WHERE id = :id"),
                {"id": position_id},
            )
            assert result.rowcount == 0

    def test_own_context_cannot_delete_a_confirmed_position(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """Deleting a line would change the already-confirmed control sum."""
        _, position_id = mdl_rows
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            result: CursorResult[Any] = session.connection().execute(
                text("DELETE FROM mdl_statement_position WHERE id = :id"), {"id": position_id}
            )
            assert result.rowcount == 0

    def test_cross_account_statement_insert_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """WITH CHECK: B's context cannot file a confirmation into account A.

        INSERT is where this table's isolation is decided, because a correction
        is a new version rather than an UPDATE (`CLAUDE.md` § 3.2): a blind write
        of a higher `version` for A's building period is what the reader would
        then bill from, and A never had to read anything for that to happen.
        """
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                MdlStatement(
                    id=seed.leaked_mdl_statement_b,
                    account_id=seed.account_a,
                    building_id=seed.building_a,
                    branch=MdlBranch.NET,
                    period_from=date(2025, 1, 1),
                    period_to=date(2026, 1, 1),
                    confirmed_total_cents=999_000,
                    owner_position_cents=0,
                    source_ref="untergeschobene Abrechnung",
                    version=2,
                )
            )
            session.flush()

    def test_cross_account_position_insert_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """The same check on the child, which is where the per-renter amount is.

        Every link in this row is internally consistent — A's statement, A's
        tenancy — and only the writer is foreign, so nothing but `WITH CHECK`
        refuses it. Without the policy, B could add a position to a confirmed
        document of A's and change what one of A's renters owes.
        """
        statement_id, _ = mdl_rows
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                MdlStatementPosition(
                    id=seed.leaked_mdl_position_b,
                    account_id=seed.account_a,
                    mdl_statement_id=statement_id,
                    tenancy_id=seed.tenancy_a,
                    amount_cents=500_000,
                )
            )
            session.flush()

    def test_cross_account_building_parent_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """The composite FK, which is the half `WITH CHECK` cannot reach.

        This statement stamps `account_id = B` and so passes the policy; only
        `building_id` crosses into A. Postgres checks foreign keys with RLS
        bypassed, so nothing but the pair
        `(building_id, account_id) → building (id, account_id)` refuses it.

        `match=` names that constraint on purpose. A generic "foreign key
        constraint" would also be satisfied by `mdl_statement_account_id_fkey` —
        a different failure with a different meaning — and the test would pass
        while proving nothing.

        The period is 2024 rather than the fixture's 2025 so that the *unique*
        constraint on `(building_id, period_from, period_to, version)` cannot
        fire first. That constraint is not account-scoped — it does not need to
        be, since a `building_id` belongs to exactly one account — but a
        colliding period would make Postgres reject this row for the wrong
        reason and leave the composite FK unexercised.
        """
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="mdl_statement_building_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                MdlStatement(
                    id=seed.cross_building_mdl_statement_b,
                    account_id=seed.account_b,
                    building_id=seed.building_a,
                    branch=MdlBranch.NET,
                    period_from=date(2024, 1, 1),
                    period_to=date(2025, 1, 1),
                    confirmed_total_cents=120_000,
                    owner_position_cents=20_000,
                    source_ref="fremdes Objekt",
                    version=1,
                )
            )
            session.flush()

    def test_cross_account_tenancy_parent_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """A position whose only foreign link is the renter it names.

        B builds its own house and files its own confirmation in the same
        transaction, so `account_id` and `mdl_statement_id` are both clean and
        the row passes `WITH CHECK`. Only `tenancy_id` points into A — one of A's
        Mietverhältnisse would then appear on B's statement with an amount B
        chose. `(tenancy_id, account_id) → tenancy (id, account_id)` is the
        single constraint that refuses it, and naming it keeps a rejection of the
        Building or the MdlStatement from satisfying this test instead.
        """
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="mdl_statement_position_tenancy_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Building(
                    id=seed.building_b,
                    account_id=seed.account_b,
                    name="Haus B",
                    street="Bahnhofstraße 2",
                    postal_code="20095",
                    city="Hamburg",
                )
            )
            session.add(
                MdlStatement(
                    id=seed.own_mdl_statement_b,
                    account_id=seed.account_b,
                    building_id=seed.building_b,
                    branch=MdlBranch.NET,
                    period_from=date(2025, 1, 1),
                    period_to=date(2026, 1, 1),
                    confirmed_total_cents=80_000,
                    owner_position_cents=10_000,
                    source_ref="eigene Abrechnung B",
                    version=1,
                )
            )
            session.add(
                MdlStatementPosition(
                    id=seed.cross_tenancy_mdl_position_b,
                    account_id=seed.account_b,
                    mdl_statement_id=seed.own_mdl_statement_b,
                    tenancy_id=seed.tenancy_a,
                    amount_cents=70_000,
                )
            )
            session.flush()

    def test_cross_account_statement_parent_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, mdl_rows: tuple[str, str]
    ) -> None:
        """The mirror image: the renter is B's own, the document is A's.

        B builds a house, a unit and a tenancy of its own, so `tenancy_id` is
        clean and the policy is satisfied — and hangs the position off A's
        confirmed statement. That edge would let B read A's document by joining
        to it and, worse, alter the control sum of a statement A has already
        sent. Only `(mdl_statement_id, account_id) → mdl_statement (id,
        account_id)` refuses it.
        """
        statement_id, _ = mdl_rows
        _, app = engines
        with (
            pytest.raises(IntegrityError, match="mdl_statement_position_mdl_statement_id_fkey"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Building(
                    id=seed.building_b,
                    account_id=seed.account_b,
                    name="Haus B",
                    street="Bahnhofstraße 2",
                    postal_code="20095",
                    city="Hamburg",
                )
            )
            session.add(
                Unit(
                    id=seed.own_unit_b,
                    account_id=seed.account_b,
                    building_id=seed.building_b,
                    label="WE B1",
                    area_sqm_x100=6_000,
                )
            )
            session.add(
                Tenancy(
                    id=seed.own_tenancy_b,
                    account_id=seed.account_b,
                    unit_id=seed.own_unit_b,
                    valid_from=date(2025, 1, 1),
                    valid_to=None,
                    base_rent_cents=70_000,
                )
            )
            session.add(
                MdlStatementPosition(
                    id=seed.cross_statement_mdl_position_b,
                    account_id=seed.account_b,
                    mdl_statement_id=statement_id,
                    tenancy_id=seed.own_tenancy_b,
                    amount_cents=60_000,
                )
            )
            session.flush()


class _M6C2BankRows(NamedTuple):
    bank_account_id: str
    second_bank_account_id: str
    transaction_id: str
    receivable_id: str
    profile_id: str
    iban_history_id: str
    proposal_id: str
    confirmation_id: str
    ledger_entry_id: str
    allocation_id: str
    provider_transaction_id: str


@pytest.fixture(scope="module")
def m6c2_bank_rows(engines: tuple[Engine, Engine], seed: _Seed) -> _M6C2BankRows:
    """One complete A-side M6-C2 graph, so the RLS checks cannot pass vacuously.

    Module-scoped and never torn down, for the same reason the seed graph is:
    `payment_ledger_entry` and `payment_allocation` are append-only evidence, and
    their trigger rejects the teardown DELETE exactly as it is supposed to. The ids
    are UUIDs generated per run, so nothing collides across runs.
    """
    owner, _ = engines
    ids = _M6C2BankRows(*(new_id() for _ in range(11)))
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                BankAccount(
                    id=ids.bank_account_id,
                    account_id=seed.account_a,
                    provider="finapi",
                    provider_account_id=f"prov-{ids.bank_account_id}",
                    normalized_iban="DE02120300000000202051",
                    display_name="Mietkonto",
                ),
                BankAccount(
                    id=ids.second_bank_account_id,
                    account_id=seed.account_a,
                    provider="finapi",
                    provider_account_id=f"prov-{ids.second_bank_account_id}",
                    normalized_iban="DE02500105170137075030",
                    display_name="Zweitkonto",
                ),
                RenterMatchingProfile(
                    id=ids.profile_id,
                    account_id=seed.account_a,
                    renter_id=seed.renter_a,
                    payment_code="MIETE-A1",
                    normalized_surname="beispiel",
                ),
                Receivable(
                    id=ids.receivable_id,
                    account_id=seed.account_a,
                    renter_id=seed.renter_a,
                    tenancy_id=seed.tenancy_a,
                    source_type="RECURRING_RENT",
                    source_id=None,
                    period="2025-07",
                    due_date=date(2025, 7, 3),
                    expected_cents=108_000,
                    open_cents=108_000,
                    status="open",
                    category="rent",
                    base_rent_cents=85_000,
                    nk_advance_cents=15_000,
                    heating_advance_cents=8_000,
                    garage_cents=0,
                    open_costs_cents=0,
                    open_interest_cents=0,
                    open_principal_cents=108_000,
                    stored_reference=None,
                ),
            ]
        )
        session.flush()
        session.add(
            BankTransaction(
                id=ids.transaction_id,
                account_id=seed.account_a,
                bank_account_id=ids.bank_account_id,
                provider_transaction_id=ids.provider_transaction_id,
                amount_cents=108_000,
                bank_booking_date=date(2025, 7, 2),
                finapi_booking_date=date(2025, 7, 2),
                value_date=date(2025, 7, 2),
                counterpart_iban="DE02120300000000202051",
                counterpart_name="Anna Beispiel",
                purpose="Miete 2025-07",
                end_to_end_reference="E2E-1",
                counterpart_mandate_reference=None,
                bank_transaction_code="SEPA-CT",
                provider_type="CREDIT",
                is_potential_duplicate=False,
            )
        )
        session.flush()
        session.add_all(
            [
                MatchProposal(
                    id=ids.proposal_id,
                    account_id=seed.account_a,
                    bank_transaction_id=ids.transaction_id,
                    receivable_id=ids.receivable_id,
                    renter_id=seed.renter_a,
                    signal_iban=60,
                    signal_amount=30,
                    signal_code_or_surname=15,
                    signal_e2e=0,
                    signal_period=5,
                    confidence=100,
                    decision="NEEDS_REVIEW",
                    convention_version="docs/15 07/2026",
                    reason_de="Eindeutige IBAN, exakter Betrag, Zahlungscode und Periode.",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                MatchConfirmation(
                    id=ids.confirmation_id,
                    account_id=seed.account_a,
                    match_proposal_id=ids.proposal_id,
                    outcome="CONFIRMED",
                    confirmed_by=seed.person_a,
                ),
                PaymentLedgerEntry(
                    id=ids.ledger_entry_id,
                    account_id=seed.account_a,
                    bank_transaction_id=ids.transaction_id,
                    match_proposal_id=ids.proposal_id,
                    kind="PAYMENT",
                    amount_cents=108_000,
                    credit_cents=0,
                    ordering_version="§ 366/367 BGB",
                    reverses_entry_id=None,
                ),
            ]
        )
        session.flush()
        # docs/15 § 3.3 / F09: an IBAN is learned only *after* a confirmation exists,
        # which is why this row is created here and cites `confirmation_id`.
        session.add(
            IbanHistory(
                id=ids.iban_history_id,
                account_id=seed.account_a,
                renter_id=seed.renter_a,
                normalized_iban="DE02120300000000202051",
                valid_from=datetime(2025, 7, 2, tzinfo=UTC),
                valid_to=None,
                learned_from_transaction_id=ids.transaction_id,
                confirmed_match_id=ids.confirmation_id,
                confirmed_by=seed.person_a,
            )
        )
        session.add(
            PaymentAllocation(
                id=ids.allocation_id,
                account_id=seed.account_a,
                ledger_entry_id=ids.ledger_entry_id,
                receivable_id=ids.receivable_id,
                costs_cents=0,
                interest_cents=0,
                principal_cents=108_000,
                base_rent_cents=85_000,
                nk_advance_cents=15_000,
                heating_advance_cents=8_000,
                garage_cents=0,
                resulting_status="settled",
            )
        )
    return ids


class TestM6C2BankBoundaries:
    """docs/15 § 6: every matching row is account-scoped, and money is append-only."""

    def test_a_reads_its_bank_graph_and_b_sees_none_of_it(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            assert session.scalars(select(BankTransaction.id)).all() == [
                m6c2_bank_rows.transaction_id
            ]
            assert session.scalars(select(Receivable.id)).all() == [m6c2_bank_rows.receivable_id]
            assert session.scalars(select(RenterMatchingProfile.id)).all() == [
                m6c2_bank_rows.profile_id
            ]
            assert session.scalars(select(IbanHistory.id)).all() == [m6c2_bank_rows.iban_history_id]
            assert session.scalars(select(MatchProposal.id)).all() == [m6c2_bank_rows.proposal_id]
            assert session.scalars(select(MatchConfirmation.id)).all() == [
                m6c2_bank_rows.confirmation_id
            ]
            assert session.scalars(select(PaymentLedgerEntry.id)).all() == [
                m6c2_bank_rows.ledger_entry_id
            ]
            assert session.scalars(select(PaymentAllocation.id)).all() == [
                m6c2_bank_rows.allocation_id
            ]
            assert set(session.scalars(select(BankAccount.id)).all()) == {
                m6c2_bank_rows.bank_account_id,
                m6c2_bank_rows.second_bank_account_id,
            }
        with account_scoped_session(app, seed.account_b) as session:
            assert session.scalars(select(BankAccount)).all() == []
            assert session.scalars(select(BankTransaction)).all() == []
            assert session.scalars(select(Receivable)).all() == []
            assert session.scalars(select(RenterMatchingProfile)).all() == []
            assert session.scalars(select(IbanHistory)).all() == []
            assert session.scalars(select(MatchProposal)).all() == []
            assert session.scalars(select(MatchConfirmation)).all() == []
            assert session.scalars(select(PaymentLedgerEntry)).all() == []
            assert session.scalars(select(PaymentAllocation)).all() == []

    def test_provider_transaction_id_is_unique_per_bank_account_not_globally(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """docs/15 § 3.1: identity is (account_id, bank_account_id, provider_transaction_id).

        Re-importing the same id on the same bank account is the dedupe case and must
        be rejected. The same id on a *different* bank account is a different movement:
        providers do not allocate ids globally, so a constraint on the id alone would
        make one import collide with another's.
        """
        owner, _ = engines
        with pytest.raises(IntegrityError), Session(owner) as session, session.begin():
            session.add(
                BankTransaction(
                    id=new_id(),
                    account_id=seed.account_a,
                    bank_account_id=m6c2_bank_rows.bank_account_id,
                    provider_transaction_id=m6c2_bank_rows.provider_transaction_id,
                    amount_cents=108_000,
                    bank_booking_date=date(2025, 7, 2),
                    finapi_booking_date=date(2025, 7, 2),
                    value_date=date(2025, 7, 2),
                    is_potential_duplicate=False,
                )
            )

        # Non-vacuous control: the identical provider id on the second bank account
        # is accepted, so the rejection above is the composite key and not a blanket
        # uniqueness on provider_transaction_id.
        accepted = new_id()
        with Session(owner) as session, session.begin():
            session.add(
                BankTransaction(
                    id=accepted,
                    account_id=seed.account_a,
                    bank_account_id=m6c2_bank_rows.second_bank_account_id,
                    provider_transaction_id=m6c2_bank_rows.provider_transaction_id,
                    amount_cents=108_000,
                    bank_booking_date=date(2025, 7, 2),
                    finapi_booking_date=date(2025, 7, 2),
                    value_date=date(2025, 7, 2),
                    is_potential_duplicate=False,
                )
            )
        # 0019 made bank_transaction append-only (§ 147 AO), so the accepted probe row
        # is retained like the rest of this module's evidence graph. Its id and
        # provider id are per-run UUIDs, so reruns never collide.

    def test_payment_ledger_and_allocations_reject_update_and_delete(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """docs/15 § 5.3: the ledger is append-only. A reversal appends; it never edits."""
        _, app = engines
        for table, row_id in (
            ("payment_ledger_entry", m6c2_bank_rows.ledger_entry_id),
            ("payment_allocation", m6c2_bank_rows.allocation_id),
        ):
            for sql in (
                f"UPDATE {table} SET id = id WHERE id = :id",
                f"DELETE FROM {table} WHERE id = :id",
            ):
                with (
                    account_scoped_session(app, seed.account_a) as session,
                    pytest.raises(IntegrityError, match="append-only"),
                ):
                    session.execute(text(sql), {"id": row_id})

    def test_cross_account_receivable_parent_is_rejected(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """The composite (receivable_id, account_id) edge makes a cross-account
        allocation unrepresentable, not merely invisible: the insert below stamps
        account B and points at account A's receivable."""
        owner, _ = engines
        with pytest.raises(IntegrityError), Session(owner) as session, session.begin():
            session.add(
                PaymentAllocation(
                    id=new_id(),
                    account_id=seed.account_b,
                    ledger_entry_id=m6c2_bank_rows.ledger_entry_id,
                    receivable_id=m6c2_bank_rows.receivable_id,
                    costs_cents=0,
                    interest_cents=0,
                    principal_cents=1,
                    base_rent_cents=1,
                    nk_advance_cents=0,
                    heating_advance_cents=0,
                    garage_cents=0,
                    resulting_status="partial",
                )
            )

    def test_every_m6c2_table_rejects_a_cross_account_write(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """The gap the boundary audit named: this slice asserted reads only.

        Four earlier tests here proved B *reads* nothing and that the composite FKs
        hold, but two of them ran on the owner engine, which bypasses RLS entirely.
        Nothing exercised `WITH CHECK` on any of the nine tables — and
        `check_rls_coverage.py` still passed, because it asks whether the class is
        *named* in this file and an import line satisfies that. M6-A got this right
        (`..._b_looks_up_nothing_and_cannot_write_it`); M6-C2 did not.

        One insert per table, as `lokara_app` in B's context, stamped with A's
        account. Every one must be refused by the policy, not by a foreign key.
        """
        _, app = engines
        rows = m6c2_bank_rows
        builders = (
            lambda: BankAccount(
                id=new_id(),
                account_id=seed.account_a,
                provider="finapi",
                provider_account_id=new_id(),
                normalized_iban="DE00",
                display_name="Eingeschleust",
            ),
            lambda: BankTransaction(
                id=new_id(),
                account_id=seed.account_a,
                bank_account_id=rows.bank_account_id,
                provider_transaction_id=new_id(),
                amount_cents=1,
                bank_booking_date=date(2025, 7, 2),
                finapi_booking_date=date(2025, 7, 2),
                value_date=date(2025, 7, 2),
                is_potential_duplicate=False,
            ),
            lambda: Receivable(
                id=new_id(),
                account_id=seed.account_a,
                renter_id=seed.renter_a,
                tenancy_id=seed.tenancy_a,
                source_type="RECURRING_RENT",
                source_id=None,
                period="2025-08",
                due_date=date(2025, 8, 3),
                expected_cents=100,
                open_cents=100,
                status="open",
                category="rent",
                base_rent_cents=100,
                nk_advance_cents=0,
                heating_advance_cents=0,
                garage_cents=0,
                open_costs_cents=0,
                open_interest_cents=0,
                open_principal_cents=100,
                stored_reference=None,
            ),
            lambda: RenterMatchingProfile(
                id=new_id(),
                account_id=seed.account_a,
                renter_id=seed.renter_a,
                payment_code=None,
                normalized_surname="eingeschleust",
            ),
            lambda: IbanHistory(
                id=new_id(),
                account_id=seed.account_a,
                renter_id=seed.renter_a,
                normalized_iban="DE00",
                valid_from=datetime(2025, 7, 2, tzinfo=UTC),
                valid_to=None,
                learned_from_transaction_id=None,
                confirmed_match_id=rows.confirmation_id,
                confirmed_by=seed.person_a,
            ),
            lambda: MatchProposal(
                id=new_id(),
                account_id=seed.account_a,
                bank_transaction_id=rows.transaction_id,
                receivable_id=rows.receivable_id,
                renter_id=seed.renter_a,
                signal_iban=0,
                signal_amount=0,
                signal_code_or_surname=0,
                signal_e2e=0,
                signal_period=0,
                confidence=0,
                decision="UNMATCHED",
                convention_version="docs/15 07/2026",
                reason_de="Eingeschleust.",
            ),
            lambda: MatchConfirmation(
                id=new_id(),
                account_id=seed.account_a,
                match_proposal_id=rows.proposal_id,
                outcome="REJECTED",
                confirmed_by=seed.person_a,
            ),
            lambda: PaymentLedgerEntry(
                id=new_id(),
                account_id=seed.account_a,
                bank_transaction_id=rows.transaction_id,
                match_proposal_id=None,
                kind="PAYMENT",
                amount_cents=1,
                credit_cents=0,
                ordering_version="§ 366/367 BGB",
                reverses_entry_id=None,
            ),
            lambda: PaymentAllocation(
                id=new_id(),
                account_id=seed.account_a,
                ledger_entry_id=rows.ledger_entry_id,
                receivable_id=rows.receivable_id,
                costs_cents=0,
                interest_cents=0,
                principal_cents=1,
                base_rent_cents=1,
                nk_advance_cents=0,
                heating_advance_cents=0,
                garage_cents=0,
                resulting_status="partial",
            ),
        )
        # M6C3R-R18 — finding M5 of the 23.08.2026 boundary audit re-run.
        #
        # `(ProgrammingError, IntegrityError)` for all nine was too wide to prove
        # anything about two of them. `payment_allocation` is refused with "payment
        # allocation names no ledger entry in its own account" and `iban_history` with
        # "iban history cites no confirmation in its own account" — both CheckViolation,
        # i.e. IntegrityError, raised by a BEFORE trigger of 0019/0020. Drop either RLS
        # policy and this loop still passes, so it never covered their WITH CHECK.
        #
        # Both now have to come back as the policy itself, the way
        # `TestIdentityAndAgreementCrossAccountWrites` below already requires. Verified
        # ordering (PostgreSQL 16, non-superuser role, FORCE RLS): a BEFORE ROW trigger
        # runs before `WCO_RLS_INSERT_CHECK`, an AFTER ROW trigger after it. So the
        # honest repair is the trigger's timing, not its strength — the trigger must
        # keep failing closed when it cannot see the parent.
        #
        # `receivable` stays deliberately wide: its 0019 parent-scope trigger is a
        # BEFORE trigger whose RLS-scoped tenancy_party lookup finds nothing in B's
        # context, so the row dies on "renter is not a party to its tenancy". That is
        # defence in depth working, and this slice does not re-time it.
        policy_must_refuse = ("payment_allocation", "iban_history")
        refusals: dict[str, str] = {}
        for build in builders:
            row = build()
            table = type(row).__tablename__
            with (
                pytest.raises((ProgrammingError, IntegrityError)) as refused,
                account_scoped_session(app, seed.account_b) as session,
            ):
                session.add(row)
                session.flush()
            refusals[table] = str(refused.value)
        # Every table is refused; for these two it has to be the policy that says so.
        trigger_refused = {
            table: refusals[table].splitlines()[0]
            for table in policy_must_refuse
            if "row-level security" not in refusals[table]
        }
        assert not trigger_refused, (
            f"refused by a trigger, not by RLS: {trigger_refused}. Drop either "
            f"isolation policy and this insert is still rejected, so nothing here "
            f"covers its WITH CHECK. A BEFORE ROW trigger runs before "
            f"WCO_RLS_INSERT_CHECK; an AFTER ROW trigger runs after it."
        )


class TestPage02CrossAccountWrites:
    """The write side of three policies that only ever had read coverage.

    `check_rls_coverage.py` was strengthened on 23.08.2026 to require each tenant
    table to appear in a test that actually attempts a refused cross-account write —
    "named in the isolation test" turned out to be satisfied by an import line. It
    immediately named these three, which predate M6-C2. Their policies were correct
    all along; nothing proved it.
    """

    def test_cost_and_allocation_tables_reject_a_cross_account_write(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        _, app = engines
        builders = (
            lambda: CostEntry(
                id=new_id(),
                account_id=seed.account_a,
                building_id=seed.building_a,
                label="Eingeschleust",
                amount_cents=1,
                period_from=date(2025, 1, 1),
                period_to=date(2025, 12, 31),
            ),
            lambda: HeatingCostEntry(
                id=new_id(),
                account_id=seed.account_a,
                building_id=seed.building_a,
                label="Eingeschleust",
                amount_cents=1,
                period_from=date(2025, 1, 1),
                period_to=date(2025, 12, 31),
            ),
            lambda: AllocationKeyAssignment(
                id=new_id(),
                account_id=seed.account_a,
                cost_entry_id=seed.cost_a,
                key=AllocationKey.AREA,
            ),
        )
        for build in builders:
            with (
                pytest.raises(ProgrammingError, match="row-level security"),
                account_scoped_session(app, seed.account_b) as session,
            ):
                session.add(build())
                session.flush()


class TestIdentityAndAgreementCrossAccountWrites:
    """The write side of the last four policies that only ever had read coverage.

    Same reason as `TestPage02CrossAccountWrites` above: the 23.08.2026 repair of
    `check_rls_coverage.py`'s write matcher named these four next. Their policies
    were correct all along; nothing proved it.

    `building_assignment` is the instructive one. It *looked* covered by
    `test_cross_account_building_assignment_is_rejected` — but that row stamps
    `account_id`/`membership_id` with B, so its `WITH CHECK` **passes** and only the
    composite FK on `(building_id, account_id)` refuses it. That is an FK-isolation
    test. The row below stamps A instead, so the policy is what has to refuse it.

    Every assertion here therefore matches on `row-level security` rather than
    accepting any `IntegrityError`: two of these rows would also duplicate a
    seeded unique pair (see the individual docstrings), and a matcher wide enough
    to accept a unique violation would go green with the policy dropped — the exact
    false positive this class exists to remove. Nothing is committed: each insert is
    refused and its transaction rolls back.
    """

    def test_membership_rejects_a_cross_account_write(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """A membership is the authorization row itself: writing one into another
        account grants a person a role there. `person` is deliberately not
        account-scoped, so `person_a` is a legitimate FK parent from either context
        and `account_id` is the only thing that crosses.

        `(person_a, account_a)` is also the seeded unique pair, so this row could not
        commit even without RLS — but the policy's `WITH CHECK` is evaluated before
        any index entry is written, so `row-level security` is what comes back, and
        it is the only outcome this test accepts. A second Person cannot be created
        to avoid the duplicate: `person` carries SELECT-only policies, so no context
        may insert one.
        """
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                Membership(
                    id=new_id(),
                    person_id=seed.person_a,
                    account_id=seed.account_a,
                    role=Role.EMPLOYEE,
                )
            )
            session.flush()

    def test_building_assignment_rejects_a_cross_account_write(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """The half `test_cross_account_building_assignment_is_rejected` does not
        reach. Both FK parents are A's own (`membership_a`, `building_a`), so both
        composite FKs to `(id, account_id)` are satisfied and the stamped
        `account_id` = A is the single fact B's context may not write.

        `(membership_a, building_a)` is the seeded assignment's unique pair, and the
        seed exposes no second building or membership in A to vary it — so, as with
        `membership` above, this asserts the RLS message specifically rather than any
        integrity error.
        """
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                BuildingAssignment(
                    id=new_id(),
                    account_id=seed.account_a,
                    membership_id=seed.membership_a,
                    building_id=seed.building_a,
                )
            )
            session.flush()

    def test_operating_cost_agreement_rejects_a_cross_account_write(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """Contract facts decide what may be allocated at all (docs/02 → Umlage-
        vereinbarung), so a forged agreement in a foreign account is a forged lease
        term. `tenancy_a` is A's tenancy and the period sits after the seeded row's
        `valid_from`, so nothing but `account_id` is wrong: no unique pair, no
        `revises_id`, and the ordered-period check constraint holds.
        """
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                OperatingCostAgreement(
                    id=new_id(),
                    account_id=seed.account_a,
                    tenancy_id=seed.tenancy_a,
                    allocation_agreed=True,
                    mehrbelastung_clause=False,
                    valid_from=date(2026, 1, 1),
                    valid_to=None,
                )
            )
            session.flush()

    def test_confirmed_cost_classification_rejects_a_cross_account_write(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
        """The table is append-only by trigger, which covers rewriting a confirmation
        but says nothing about who may append one. Both parents are A's
        (`cost_a`, `key_assignment_a`), the row reconciles
        (`source = allocable + non_allocable`) and the id is fresh, so the append is
        valid in every respect except the account it claims.
        """
        _, app = engines
        with (
            pytest.raises(ProgrammingError, match="row-level security"),
            account_scoped_session(app, seed.account_b) as session,
        ):
            session.add(
                ConfirmedCostClassification(
                    id=new_id(),
                    account_id=seed.account_a,
                    cost_entry_id=seed.cost_a,
                    allocation_key_assignment_id=seed.key_assignment_a,
                    catalogue_id="muellbeseitigung",
                    rule_source="BetrKV / Page 02",
                    rule_rechtsstand="Rechtsstand 07/2026",
                    source_amount_cents=120000,
                    allocable_cents=120000,
                    non_allocable_cents=0,
                    labour_cents=None,
                    key=AllocationKey.AREA,
                    key_source="test",
                    findings=["verify-before-production"],
                    special_rule_evidence={},
                    production_blocked=True,
                )
            )
            session.flush()


class TestM6C2MoneyInvariants:
    """What the boundary audit found the schema was not enforcing (docs/15 §§ 5-6).

    Account isolation was never the gap — RLS and the composite FKs hold. The gap is
    everything *inside* one account: which parent a row may name, how much a payment
    may settle, and what a reversal has to look like. M6-A already enforces the
    equivalent rules (`enforce_advance_allocation_cap`,
    `enforce_advance_payment_single_reversal`), so these are the same invariants one
    ledger later.
    """

    def test_a_receivable_cannot_name_a_renter_who_is_not_a_party_to_its_tenancy(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """docs/15 § 6: a match never moves money between renters. A debt that cites
        a lease the renter is not party to is where that starts."""
        owner, _ = engines
        stranger = new_id()
        with Session(owner) as session, session.begin():
            session.add(
                Renter(id=stranger, account_id=seed.account_a, legal_name="Fremde Mieterin")
            )
        with (
            pytest.raises(IntegrityError, match="tenancy"),
            Session(owner) as session,
            session.begin(),
        ):
            session.add(
                Receivable(
                    id=new_id(),
                    account_id=seed.account_a,
                    renter_id=stranger,
                    tenancy_id=seed.tenancy_a,
                    source_type="RECURRING_RENT",
                    source_id=None,
                    period="2025-09",
                    due_date=date(2025, 9, 3),
                    expected_cents=100,
                    open_cents=100,
                    status="open",
                    category="rent",
                    base_rent_cents=100,
                    nk_advance_cents=0,
                    heating_advance_cents=0,
                    garage_cents=0,
                    open_costs_cents=0,
                    open_interest_cents=0,
                    open_principal_cents=100,
                    stored_reference=None,
                )
            )

    def test_an_allocation_cannot_settle_more_than_its_entry_carried(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """The entry carried 108,000. A second allocation against it must not push the
        settled total past that — otherwise a payment settles money that never arrived."""
        owner, _ = engines
        with (
            pytest.raises(IntegrityError, match="allocation"),
            Session(owner) as session,
            session.begin(),
        ):
            session.add(
                PaymentAllocation(
                    id=new_id(),
                    account_id=seed.account_a,
                    ledger_entry_id=m6c2_bank_rows.ledger_entry_id,
                    receivable_id=m6c2_bank_rows.receivable_id,
                    costs_cents=0,
                    interest_cents=0,
                    principal_cents=500_000,
                    base_rent_cents=500_000,
                    nk_advance_cents=0,
                    heating_advance_cents=0,
                    garage_cents=0,
                    resulting_status="settled",
                )
            )

    def test_allocation_components_cannot_be_negative(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """A negative component cancels inside the sum check and passes it. § 5.2's
        "the reconciled components must sum exactly to P" then means nothing, and the
        negative NK-advance feeds Page 01's actual-advance total as a negative advance."""
        owner, _ = engines
        with (
            pytest.raises(IntegrityError, match="negative"),
            Session(owner) as session,
            session.begin(),
        ):
            session.add(
                PaymentAllocation(
                    id=new_id(),
                    account_id=seed.account_a,
                    ledger_entry_id=m6c2_bank_rows.ledger_entry_id,
                    receivable_id=m6c2_bank_rows.receivable_id,
                    costs_cents=0,
                    interest_cents=0,
                    principal_cents=0,
                    base_rent_cents=100_000,
                    nk_advance_cents=-100_000,
                    heating_advance_cents=0,
                    garage_cents=0,
                    resulting_status="partial",
                )
            )

    def test_a_reversal_must_be_negative_and_must_name_what_it_reverses(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """docs/15 § 5.3 and F06: the ledger nets to zero. A positive REVERSAL, or one
        that names no original, cannot do that."""
        owner, _ = engines
        for kwargs, match in (
            ({"kind": "REVERSAL", "amount_cents": 108_000, "reverses_entry_id": None}, "reversal"),
            ({"kind": "PAYMENT", "amount_cents": 1, "reverses_entry_id": None}, None),
        ):
            if match is None:
                continue
            with (
                pytest.raises(IntegrityError, match=match),
                Session(owner) as session,
                session.begin(),
            ):
                session.add(
                    PaymentLedgerEntry(
                        id=new_id(),
                        account_id=seed.account_a,
                        bank_transaction_id=m6c2_bank_rows.transaction_id,
                        match_proposal_id=None,
                        credit_cents=0,
                        ordering_version="§ 366/367 BGB",
                        **kwargs,
                    )
                )

    def test_one_payment_has_at_most_one_reversal(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """Two reversals of one payment reopen twice the debt against a renter who
        paid once, and the ledger is append-only, so nothing can correct it after."""
        owner, _ = engines
        first = new_id()
        with Session(owner) as session, session.begin():
            session.add(
                PaymentLedgerEntry(
                    id=first,
                    account_id=seed.account_a,
                    bank_transaction_id=m6c2_bank_rows.transaction_id,
                    match_proposal_id=None,
                    kind="REVERSAL",
                    amount_cents=-108_000,
                    credit_cents=0,
                    ordering_version="§ 366/367 BGB",
                    reverses_entry_id=m6c2_bank_rows.ledger_entry_id,
                )
            )
            session.flush()
            # Migration 0021 reconciles every ledger entry at deferred commit.
            # This first reversal is the valid baseline for the uniqueness probe,
            # so it must compensate the original fixture allocation exactly.
            session.add(
                PaymentAllocation(
                    id=new_id(),
                    account_id=seed.account_a,
                    ledger_entry_id=first,
                    receivable_id=m6c2_bank_rows.receivable_id,
                    costs_cents=0,
                    interest_cents=0,
                    principal_cents=-108_000,
                    base_rent_cents=-85_000,
                    nk_advance_cents=-15_000,
                    heating_advance_cents=-8_000,
                    garage_cents=0,
                    resulting_status="open",
                )
            )
        with (
            pytest.raises(IntegrityError),
            Session(owner) as session,
            session.begin(),
        ):
            session.add(
                PaymentLedgerEntry(
                    id=new_id(),
                    account_id=seed.account_a,
                    bank_transaction_id=m6c2_bank_rows.transaction_id,
                    match_proposal_id=None,
                    kind="REVERSAL",
                    amount_cents=-108_000,
                    credit_cents=0,
                    ordering_version="§ 366/367 BGB",
                    reverses_entry_id=m6c2_bank_rows.ledger_entry_id,
                )
            )

    def test_a_learned_iban_cannot_exist_without_its_confirmation(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """docs/15 § 3.3 and F09: a non-null IBAN is learned only after a user confirms
        a Review proposal. Without this the +60 unique-IBAN signal can be created by
        anything that can insert."""
        owner, _ = engines
        with (
            pytest.raises(IntegrityError, match="confirm"),
            Session(owner) as session,
            session.begin(),
        ):
            session.add(
                IbanHistory(
                    id=new_id(),
                    account_id=seed.account_a,
                    renter_id=seed.renter_a,
                    normalized_iban="DE99999999999999999999",
                    valid_from=datetime(2025, 7, 2, tzinfo=UTC),
                    valid_to=None,
                    learned_from_transaction_id=None,
                    confirmed_match_id=None,
                    confirmed_by=None,
                )
            )

    def test_a_learned_iban_cannot_be_rewritten_or_deleted(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """CLAUDE.md § 3.2 names IBAN history in the immutable/versioned list. Flipping
        one row redirects the unique-IBAN signal to another renter, so their next
        payment Auto-Matches onto someone else's debt with no review step."""
        _, app = engines
        for sql in (
            "UPDATE iban_history SET normalized_iban = 'DE00' WHERE id = :id",
            "DELETE FROM iban_history WHERE id = :id",
        ):
            with (
                account_scoped_session(app, seed.account_a) as session,
                pytest.raises(IntegrityError, match="append-only"),
            ):
                session.execute(text(sql), {"id": m6c2_bank_rows.iban_history_id})

    def test_closing_an_iban_period_is_the_one_permitted_update(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """Versioned, not frozen: a mapping ends by having its open period closed.
        Everything else about the row stays put."""
        _, app = engines
        with account_scoped_session(app, seed.account_a) as session:
            session.execute(
                text("UPDATE iban_history SET valid_to = :d WHERE id = :id"),
                {
                    "d": datetime(2026, 1, 1, tzinfo=UTC),
                    "id": m6c2_bank_rows.iban_history_id,
                },
            )

    def test_a_bank_transaction_and_a_proposal_cannot_be_rewritten(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """§ 147 AO: the provider fact and the reason a payment was auto-assigned must
        be re-derivable years later. Both were freely mutable."""
        _, app = engines
        for sql, row_id in (
            (
                "UPDATE bank_transaction SET amount_cents = 999999 WHERE id = :id",
                m6c2_bank_rows.transaction_id,
            ),
            (
                "UPDATE match_proposal SET confidence = 100,"
                " decision = 'AUTO_MATCH' WHERE id = :id",
                m6c2_bank_rows.proposal_id,
            ),
        ):
            with (
                account_scoped_session(app, seed.account_a) as session,
                pytest.raises(IntegrityError, match="append-only"),
            ):
                session.execute(text(sql), {"id": row_id})

    def test_a_proposal_can_be_confirmed_only_once(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """M6-C3 will drive ledger entries off confirmations. One proposal confirmed
        twice is one payment booked twice."""
        owner, _ = engines
        with (
            pytest.raises(IntegrityError),
            Session(owner) as session,
            session.begin(),
        ):
            session.add(
                MatchConfirmation(
                    id=new_id(),
                    account_id=seed.account_a,
                    match_proposal_id=m6c2_bank_rows.proposal_id,
                    outcome="REJECTED",
                    confirmed_by=seed.person_a,
                )
            )

    def test_a_settled_receivable_cannot_still_be_open(
        self, engines: tuple[Engine, Engine], seed: _Seed, m6c2_bank_rows: _M6C2BankRows
    ) -> None:
        """M6C3R-R19 — § 5.1 walks costs, then interest, then principal. A row that
        calls itself `settled` while 500,00 € of costs are still open makes the
        settlement engine and the arrears guard read different totals from it.

        Finding M6 of the 23.08.2026 boundary audit re-run: this test was vacuous.
        Its old row carried `open_cents=0` with `open_principal_cents=108_000`, which
        `0020`'s `ck_receivable_open_components` (`open_principal_cents = open_cents`)
        rejects **first**, and `match="settled"` then matched the word "settled" in the
        failing row's DETAIL line rather than any constraint name — so
        `ck_receivable_settled_has_nothing_open` could be dropped and this stayed green.

        The shape below is discriminating: `open_cents = open_principal_cents = 0`
        satisfies the components check, so the only rule left to refuse it is the
        settled rule, and the match is on the constraint's own name.
        """
        owner, _ = engines
        with (
            pytest.raises(IntegrityError, match="ck_receivable_settled_has_nothing_open"),
            Session(owner) as session,
            session.begin(),
        ):
            session.add(
                Receivable(
                    id=new_id(),
                    account_id=seed.account_a,
                    renter_id=seed.renter_a,
                    tenancy_id=seed.tenancy_a,
                    source_type="RECURRING_RENT",
                    source_id=None,
                    period="2025-10",
                    due_date=date(2025, 10, 3),
                    expected_cents=108_000,
                    open_cents=0,
                    status="settled",
                    category="rent",
                    base_rent_cents=108_000,
                    nk_advance_cents=0,
                    heating_advance_cents=0,
                    garage_cents=0,
                    open_costs_cents=50_000,
                    open_interest_cents=0,
                    open_principal_cents=0,
                    stored_reference=None,
                )
            )
