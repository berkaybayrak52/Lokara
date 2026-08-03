"""ORM-mapping tests against a live Postgres — the composite-FK follow-up.

Migration `0004` made every tenant-to-tenant foreign key composite on
`(id, account_id)` (`docs/02-data-model.md` → "Isolation rule"). That put
`account_id` into the **local column set of every many-to-one relationship** in
`models.py`: it now belongs to `Meter.building` *and* to `Meter.unit`. So
SQLAlchemy synchronises it from whichever relationship it flushes last — and an
absent or cleared `unit` writes NULL into the tenant key:

    UPDATE meter SET account_id=NULL, unit_id=NULL WHERE meter.id = ...

A meter with `unit_id IS NULL` is the building-level **Hauptzähler** — the
Wärmemengenzähler whose kWh are the § 9 HeizkostenV denominator. It is the
documented normal case, cited by both `0004`'s docstring and `models.py` as the
reason `MATCH SIMPLE` was chosen, and it is currently unreachable through the
relationship API **even when the caller states `account_id` explicitly**: the
`unit=None` synchronisation overwrites the stated value with NULL.

The two controls below draw the boundary of the defect, so the diagnosis is
legible in this file rather than only in a commit message:

- writing the ids by hand (`building_id=…, account_id=…, unit_id=None`) works;
- so does the relationship form **as long as `unit` is never mentioned**
  (`building=<obj>, account_id=…`) — nothing then syncs a NULL. That narrow case
  is why the demo seed and `apps/api` are unaffected today: neither names `unit`
  when creating a Hauptzähler. It is a coincidence of usage, not a safe API.

**Where this lives.** Not `test_models.py`: that module is metadata-only ("no
database required") and every test in it runs green without docker — a property
worth keeping, and these need a live database to surface a NOT NULL violation at
flush. Not `test_rls_isolation.py`: nothing here is about cross-account
isolation. Same fixture style as the latter: self-sufficient (applies the app
role + `alembic upgrade head` itself), skipping when Postgres is unreachable
unless `LOKARA_REQUIRE_DB` is set.

Everything runs as the local superuser (the owner engine), which bypasses RLS —
these are mapping tests, so account context must not be part of the picture.
"""

import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from lokara_db import (
    Account,
    Building,
    DbSettings,
    Meter,
    Unit,
    create_db_engine,
    new_id,
)
from lokara_domain import MeasurementUnit, MeterKind
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent


def _upgraded_owner_engine() -> Engine:
    """Owner engine with role + schema guaranteed current (as in the RLS suite)."""
    settings = DbSettings()
    owner = create_db_engine(settings.direct_url)
    with owner.connect() as conn:
        conn.execute(text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()))
        conn.commit()
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    return owner


@pytest.fixture(scope="module")
def owner_engine() -> Iterator[Engine]:
    try:
        owner = _upgraded_owner_engine()
    except OperationalError as exc:  # DB not running
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    yield owner
    owner.dispose()


class _Fixture:
    """One account with one building and one unit. Fresh ids per run so reruns
    never collide; meters are created per test and swept in teardown."""

    def __init__(self) -> None:
        self.account = new_id()
        self.building = new_id()
        self.unit = new_id()


@pytest.fixture
def fx(owner_engine: Engine) -> Iterator[_Fixture]:
    ids = _Fixture()
    with Session(owner_engine) as session, session.begin():
        session.add(Account(id=ids.account, name="Konto Hauptzähler"))
        session.add(
            Building(
                id=ids.building,
                account_id=ids.account,
                name="Haus H",
                street="Heizweg 3",
                postal_code="10115",
                city="Berlin",
            )
        )
        session.add(
            Unit(
                id=ids.unit,
                account_id=ids.account,
                building_id=ids.building,
                label="WE 1",
                area_sqm_x100=7_500,
            )
        )
    yield ids
    with Session(owner_engine) as session, session.begin():
        for meter in session.query(Meter).filter(Meter.building_id == ids.building).all():
            session.delete(meter)
    with Session(owner_engine) as session, session.begin():
        for model, row_id in (
            (Unit, ids.unit),
            (Building, ids.building),
            (Account, ids.account),
        ):
            obj = session.get(model, row_id)
            if obj is not None:
                session.delete(obj)


class TestBuildingLevelMeterMapping:
    """A Hauptzähler must be creatable and reachable through the relationship
    API, with its `account_id` intact. Composite FKs are an isolation mechanism;
    they may not cost the model its documented normal case."""

    def test_hauptzaehler_via_relationship_keeps_its_account(
        self, owner_engine: Engine, fx: _Fixture
    ) -> None:
        """[1] `Meter(building=<obj>, unit=None, account_id=<explicit>)` — the
        documented normal case, written the way the fix requires.

        `account_id` is **stated by the caller**, not inferred from the building:
        the intended fix takes `account_id` out of every relationship's local
        column set, so no relationship may be relied on to supply it (the same
        implicit-`account_id` asymmetry commit `5c119f3` removed for
        `building_assignment`). Stating it does not help today — the `unit=None`
        sync overwrites the stated value with NULL and the INSERT is rejected.
        That is the whole defect: a value the caller supplied is destroyed by a
        relationship that was set to *nothing*.
        """
        with Session(owner_engine) as session, session.begin():
            building = session.get(Building, fx.building)
            assert building is not None
            meter = Meter(
                account_id=fx.account,  # stated explicitly — and still nulled below
                building=building,
                unit=None,  # building-level Hauptzähler — § 9 HeizkostenV denominator
                kind=MeterKind.HEAT,
                measurement_unit=MeasurementUnit.KWH,
                serial="WMZ-HAUPT-1",
                calibration_valid_until=date(2029, 12, 31),
            )
            session.add(meter)
            session.flush()
            meter_id = meter.id

        with Session(owner_engine) as session:
            stored = session.get(Meter, meter_id)
            assert stored is not None
            assert stored.account_id == fx.account
            assert stored.building_id == fx.building
            assert stored.unit_id is None

    def test_hauptzaehler_via_ids_keeps_its_account(
        self, owner_engine: Engine, fx: _Fixture
    ) -> None:
        """[2] Control — the same row written as ids rather than relationships
        works today. It is here so the diagnosis is legible: the defect is in
        the relationship↔column synchronisation, not in the schema, and not in
        the `MATCH SIMPLE` FK that keeps `unit_id IS NULL` legal."""
        meter_id = new_id()
        with Session(owner_engine) as session, session.begin():
            session.add(
                Meter(
                    id=meter_id,
                    account_id=fx.account,
                    building_id=fx.building,
                    unit_id=None,
                    kind=MeterKind.HEAT,
                    measurement_unit=MeasurementUnit.KWH,
                    serial="WMZ-HAUPT-2",
                    calibration_valid_until=date(2029, 12, 31),
                )
            )

        with Session(owner_engine) as session:
            stored = session.get(Meter, meter_id)
            assert stored is not None
            assert stored.account_id == fx.account
            assert stored.building_id == fx.building
            assert stored.unit_id is None

    def test_hauptzaehler_via_relationship_without_touching_unit_works(
        self, owner_engine: Engine, fx: _Fixture
    ) -> None:
        """[B] Second control, and the narrow reason this defect has not bitten
        yet: the relationship form is fine **as long as `unit` is never
        mentioned**. Nothing then synchronises the `unit` side, so the stated
        `account_id` survives and `unit_id` simply defaults to NULL.

        The demo seed and `apps/api` sit inside exactly this case — they never
        name `unit` when creating a Hauptzähler. That is a coincidence of how the
        callers happen to be written, not a property of the API: `unit=None`
        means the same thing to a reader and breaks (test [1]). This control
        exists so the boundary is recorded rather than rediscovered."""
        with Session(owner_engine) as session, session.begin():
            building = session.get(Building, fx.building)
            assert building is not None
            meter = Meter(
                account_id=fx.account,
                building=building,
                # `unit` deliberately not mentioned at all
                kind=MeterKind.HEAT,
                measurement_unit=MeasurementUnit.KWH,
                serial="WMZ-HAUPT-3",
                calibration_valid_until=date(2029, 12, 31),
            )
            session.add(meter)
            session.flush()
            meter_id = meter.id

        with Session(owner_engine) as session:
            stored = session.get(Meter, meter_id)
            assert stored is not None
            assert stored.account_id == fx.account
            assert stored.building_id == fx.building
            assert stored.unit_id is None

    def test_detaching_a_meter_from_its_unit_keeps_its_account(
        self, owner_engine: Engine, fx: _Fixture
    ) -> None:
        """[3] `m.unit = None` on an existing meter — a real operation: a
        Wohnungszähler is re-declared as serving the whole building (or the unit
        is dissolved). Today SQLAlchemy emits
        `UPDATE meter SET account_id=NULL, unit_id=NULL` and the row loses its
        tenant key.

        The detach block below re-states **nothing**: `account_id` is expected to
        simply persist from the INSERT. That is deliberate — re-stating it after
        `m.unit = None` does not save it either (the relationship sync still
        wins, verified against the live schema), so a re-statement would only
        disguise the defect without curing it. Do not add one here.
        """
        meter_id = new_id()
        with Session(owner_engine) as session, session.begin():
            session.add(
                Meter(
                    id=meter_id,
                    account_id=fx.account,
                    building_id=fx.building,
                    unit_id=fx.unit,
                    kind=MeterKind.COLD_WATER,
                    measurement_unit=MeasurementUnit.CUBIC_METRE,
                    serial="KWZ-1",
                    calibration_valid_until=date(2030, 12, 31),
                )
            )

        with Session(owner_engine) as session, session.begin():
            meter = session.get(Meter, meter_id)
            assert meter is not None
            meter.unit = None
            session.flush()

        with Session(owner_engine) as session:
            stored = session.get(Meter, meter_id)
            assert stored is not None
            assert stored.account_id == fx.account
            assert stored.building_id == fx.building
            assert stored.unit_id is None
