"""RLS isolation tests against a live Postgres — the Phase B gate.

The whole ballgame (MIGRATION-PLAN B.3): a session carrying account B's RLS
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
from datetime import date
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import (
    Account,
    AllocationKeyAssignment,
    Building,
    BuildingAssignment,
    CostEntry,
    DbSettings,
    HeatingCostEntry,
    Landlord,
    Membership,
    Meter,
    MeterReading,
    Person,
    Renter,
    Role,
    SelfUseKind,
    SelfUsePeriod,
    Statement,
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
                advance_payment_cents=15_000,
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
    yield ids
    with Session(owner) as session, session.begin():
        for model, row_id in (
            # Rows TestCrossAccountForeignKeys leaks while the composite FKs are
            # missing; no-ops once the database rejects those inserts.
            (Meter, ids.leaked_meter_b),
            (Unit, ids.leaked_unit_b),
            (BuildingAssignment, ids.leaked_assignment_b),
            (Membership, ids.membership_b),
            (Building, ids.building_b),
            (MeterReading, ids.reading_a),
            (Meter, ids.meter_a),
            (HeatingCostEntry, ids.heating_cost_a),
            (AllocationKeyAssignment, ids.key_assignment_a),
            (CostEntry, ids.cost_a),
            (Statement, ids.statement_a),
            (BuildingAssignment, ids.assignment_a),
            # FK order: party → tenancy → unit, before renter/building can go.
            (TenancyParty, ids.tenancy_party_a),
            (Tenancy, ids.tenancy_a),
            (Unit, ids.unit_a),
            (Renter, ids.renter_a),
            (Building, ids.building_a),
            (Membership, ids.membership_a),
            (Person, ids.person_a),
            (Account, ids.account_a),
            (Account, ids.account_b),
        ):
            obj = session.get(model, row_id)
            if obj is not None:
                session.delete(obj)


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
            assert session.scalars(select(Membership)).all() == []
            assert session.scalars(select(BuildingAssignment)).all() == []
            assert session.scalars(select(CostEntry)).all() == []
            assert session.scalars(select(AllocationKeyAssignment)).all() == []
            assert session.scalars(select(Meter)).all() == []
            assert session.scalars(select(MeterReading)).all() == []
            assert session.scalars(select(HeatingCostEntry)).all() == []
            assert session.scalars(select(Account.id)).all() == [seed.account_b]

    def test_own_context_sees_own_rows(
        self, engines: tuple[Engine, Engine], seed: _Seed
    ) -> None:
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
            assert session.scalars(select(Meter.id)).all() == [seed.meter_a]
            assert session.scalars(select(MeterReading.id)).all() == [seed.reading_a]
            assert session.scalars(select(HeatingCostEntry.id)).all() == [
                seed.heating_cost_a
            ]
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
                    advance_payment_cents=1,
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
    but nothing proves it behaves. MIGRATION-PLAN §8: *a table without a policy is
    a silent leak* — a policy without a test is a silent regression.
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

    def test_person_has_rls_enabled_and_forced(
        self, engines: tuple[Engine, Engine]
    ) -> None:
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
