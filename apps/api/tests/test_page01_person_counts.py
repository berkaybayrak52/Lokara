"""D0 Fiktivbelegung: which person count, for which days (Slice B, B3c/B3d).

Spec: `docs/02-data-model.md` § 5 "D0 Fiktivbelegung — the vacancy person count
is derived, and it is a flagged convention", original Page 01 § 3.5 and § 4 D0
with edge cases E17/E18/E19, and the register row `Fiktivbelegung bei Leerstand`
(`Rechtsnatur: Konvention`, `verify-before-production`, Rechtsstand 07/2026).

Nothing here is settled law. LG Krefeld 2 S 56/09 applies a fictional occupancy
under the person key, BGH VIII ZR 159/05 keeps the vacant unit in the
Gesamtverteiler, and BGH VIII ZR 180/12 expressly leaves the Ansatz a Tatfrage
of the individual case. These tests pin Lokara's convention as `docs/02`
transcribes it, not a legal outcome.

`docs/02` § 5 settled the layering in Slice B as "the adapter derives, the engine
receives": `packages/nk-engine` already owns "a fictional occupancy is a
denominator weight on the landlord side" (see
`packages/nk-engine/tests/test_page01_vacancy_denominators.py` for `08-F22` /
`08-F23`). What is under test here is the other half —
`lokara_api.person_counts.person_count_inputs`, which answers *which number, for
which days*. That answer needs a person-count history reaching back **before**
the billing period, which is exactly why it cannot live in the pure engine, and
why this suite needs a real database.

Same skip contract as the other live suites: skips without a reachable DB, but
LOKARA_REQUIRE_DB (set in CI) forbids the skip.
"""

import os
import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from lokara_api.person_counts import person_count_inputs
from lokara_db import (
    Account,
    Building,
    DbSettings,
    FiktivbelegungMode,
    PersonCount,
    SelfUsePeriod,
    Tenancy,
    Unit,
    create_db_engine,
)
from lokara_domain import Occupancy, Period
from lokara_nk_engine import PersonCountPeriod
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"

ACCOUNT_ID = "acc_p01_person_counts"
BUILDING_ID = "bld_p01_person_counts"

# The billing window every expectation below is stated against: the ordinary
# calendar year, half-open, so 31.12.2025 is the last billed day.
WINDOW = Period(valid_from=date(2025, 1, 1), valid_to=date(2026, 1, 1))

# (unit_id, label, area m² × 100). Labels are numbered so the sort order the
# composition layer uses is visible in the expectations.
_UNITS: tuple[tuple[str, str, int], ...] = (
    ("unit_pc_full", "1 Dauermieter", 5000),
    ("unit_pc_mid", "2 Auszug im Zeitraum", 3000),
    ("unit_pc_before", "3 Ganzjährig leer", 2000),
    ("unit_pc_none", "4 Ohne Historie", 2500),
    ("unit_pc_zero", "5 Letzte Belegung null", 2500),
    ("unit_pc_later", "6 Neuvermietung im Zeitraum", 2500),
    ("unit_pc_selfuse", "7 Volle Eigennutzung", 4000),
    ("unit_pc_partial", "8 Teil-Eigennutzung", 4000),
)

# (tenancy_id, unit_id, valid_from, valid_to exclusive)
_TENANCIES: tuple[tuple[str, str, date, date | None], ...] = (
    ("ten_pc_full", "unit_pc_full", date(2024, 1, 1), None),
    ("ten_pc_mid", "unit_pc_mid", date(2023, 1, 1), date(2025, 4, 1)),
    ("ten_pc_before", "unit_pc_before", date(2022, 1, 1), date(2024, 6, 1)),
    ("ten_pc_zero", "unit_pc_zero", date(2022, 1, 1), date(2024, 6, 1)),
    ("ten_pc_old", "unit_pc_later", date(2022, 1, 1), date(2024, 6, 1)),
    ("ten_pc_new", "unit_pc_later", date(2025, 7, 1), None),
    ("ten_pc_selfuse", "unit_pc_selfuse", date(2020, 1, 1), date(2025, 3, 1)),
    ("ten_pc_partial", "unit_pc_partial", date(2020, 1, 1), date(2025, 3, 1)),
)

# (person_count_id, tenancy_id, count, valid_from, valid_to exclusive)
_PERSON_COUNTS: tuple[tuple[str, str, int, date, date | None], ...] = (
    ("pc_full", "ten_pc_full", 3, date(2024, 1, 1), None),
    ("pc_mid", "ten_pc_mid", 2, date(2023, 1, 1), date(2025, 4, 1)),
    ("pc_before", "ten_pc_before", 4, date(2022, 1, 1), date(2024, 6, 1)),
    # Zero is a real entered count (an empty but still-running lease) and the
    # `max(1, …)` floor is what keeps the derived branch off the `keine`
    # denominator — `docs/02` § 5 edge cases.
    ("pc_zero", "ten_pc_zero", 0, date(2022, 1, 1), date(2024, 6, 1)),
    ("pc_old", "ten_pc_old", 4, date(2022, 1, 1), date(2024, 6, 1)),
    ("pc_new", "ten_pc_new", 1, date(2025, 7, 1), None),
    ("pc_selfuse", "ten_pc_selfuse", 2, date(2020, 1, 1), date(2025, 3, 1)),
    ("pc_partial", "ten_pc_partial", 2, date(2020, 1, 1), date(2025, 3, 1)),
)

# (self_use_id, unit_id, m² × 100, valid_from, valid_to exclusive)
_SELF_USE: tuple[tuple[str, str, int, date, date | None], ...] = (
    # Full unit (40,00 m² of 40,00 m²) inside the vacancy gap: those days are
    # SELF_USED, not VACANT, so no fiction applies to them — and vacancy
    # survives on both sides of the self-use.
    ("su_full", "unit_pc_selfuse", 4000, date(2025, 5, 1), date(2025, 8, 1)),
    # Just over half the unit (20,50 m² of 40,00 m²). Page 01 has no rule for a
    # partial self-use overlapping a vacancy, so the days stay vacancy and the
    # document says so. The area is deliberately non-integral: `format_number_de`
    # suppresses trailing zeroes, so only a fractional area actually exercises
    # the German decimal comma in the finding below.
    ("su_partial", "unit_pc_partial", 2050, date(2025, 5, 1), date(2025, 8, 1)),
)

_RESET_ORDER: tuple[str, ...] = (
    "person_count",
    "self_use_period",
    "tenancy_party",
    "tenancy",
    "unit",
    "building",
)


def _wipe(session: Session) -> None:
    for table in _RESET_ORDER:
        session.execute(text(f"DELETE FROM {table} WHERE account_id = :a"), {"a": ACCOUNT_ID})


@pytest.fixture(scope="module")
def session() -> Iterator[Session]:
    """A scenario account of its own, so no other suite's rows can move a count."""
    settings = DbSettings()
    try:
        engine = create_db_engine(settings.direct_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")

    with Session(engine) as setup, setup.begin():
        setup.merge(Account(id=ACCOUNT_ID, name="Fiktivbelegungs-Testkonto"))
        _wipe(setup)
        setup.add(
            Building(
                id=BUILDING_ID,
                account_id=ACCOUNT_ID,
                name="Fiktivbelegungshaus",
                street="Leerstandsweg 1",
                postal_code="60311",
                city="Frankfurt am Main",
                fiktivbelegung_mode=FiktivbelegungMode.LETZTE_BELEGUNG,
            )
        )
        for unit_id, label, area in _UNITS:
            setup.add(
                Unit(
                    id=unit_id,
                    account_id=ACCOUNT_ID,
                    building_id=BUILDING_ID,
                    label=label,
                    area_sqm_x100=area,
                )
            )
        for tenancy_id, unit_id, valid_from, valid_to in _TENANCIES:
            setup.add(
                Tenancy(
                    id=tenancy_id,
                    account_id=ACCOUNT_ID,
                    unit_id=unit_id,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    base_rent_cents=50000,
                )
            )
        for count_id, tenancy_id, count, valid_from, valid_to in _PERSON_COUNTS:
            setup.add(
                PersonCount(
                    id=count_id,
                    account_id=ACCOUNT_ID,
                    tenancy_id=tenancy_id,
                    count=count,
                    valid_from=valid_from,
                    valid_to=valid_to,
                )
            )
        for self_use_id, unit_id, sqm, valid_from, valid_to in _SELF_USE:
            setup.add(
                SelfUsePeriod(
                    id=self_use_id,
                    account_id=ACCOUNT_ID,
                    unit_id=unit_id,
                    sqm_x100=sqm,
                    valid_from=valid_from,
                    valid_to=valid_to,
                )
            )

    with Session(engine) as read_session:
        yield read_session

    with Session(engine) as teardown, teardown.begin():
        _wipe(teardown)
    engine.dispose()


@pytest.fixture
def units(session: Session) -> list[Unit]:
    return list(
        session.scalars(
            select(Unit).where(Unit.building_id == BUILDING_ID).order_by(Unit.label)
        ).all()
    )


@pytest.fixture
def occupancies(units: list[Unit]) -> tuple[Occupancy, ...]:
    """The one timeline both engines read (docs/06) — tenancy rows, nothing else.

    Vacancy is never passed in; `build_unit_segments` derives it as the
    remainder, which is precisely the set of days D0 applies to.
    """
    return tuple(
        Occupancy(
            unit_id=unit.id,
            tenancy_id=tenancy.id,
            period=Period(valid_from=tenancy.valid_from, valid_to=tenancy.valid_to),
        )
        for unit in units
        for tenancy in unit.tenancies
    )


def _derived(rows: tuple[PersonCountPeriod, ...]) -> list[PersonCountPeriod]:
    return [row for row in rows if row.tenancy_id is None]


def _entered(rows: tuple[PersonCountPeriod, ...]) -> list[PersonCountPeriod]:
    return [row for row in rows if row.tenancy_id is not None]


def _run(
    session: Session,
    units: list[Unit],
    occupancies: tuple[Occupancy, ...],
    mode: FiktivbelegungMode = FiktivbelegungMode.LETZTE_BELEGUNG,
    window: Period = WINDOW,
) -> tuple[tuple[PersonCountPeriod, ...], tuple[str, ...]]:
    result = person_count_inputs(
        session, units=units, occupancies=occupancies, window=window, mode=mode
    )
    return result.rows, result.findings


class TestEnteredCounts:
    def test_every_entered_row_becomes_a_per_tenancy_row(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        rows, _ = _run(session, units, occupancies)
        entered = {
            (row.tenancy_id, row.count, row.period.valid_from, row.period.valid_to)
            for row in _entered(rows)
        }
        assert entered == {
            (tenancy_id, count, valid_from, valid_to)
            for _, tenancy_id, count, valid_from, valid_to in _PERSON_COUNTS
        }

    def test_entered_rows_carry_no_unit_id(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """A renter row's unit comes from its tenancy; only a landlord row needs
        to name one (`PersonCountPeriod.unit_id`)."""
        rows, _ = _run(session, units, occupancies)
        assert all(row.unit_id is None for row in _entered(rows))

    def test_entered_rows_are_not_clipped_to_the_window(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """The engine intersects each row with the billing window itself; clipping
        twice is how a day goes missing. So a count that ended in 2024 still
        arrives with its own dates."""
        rows, _ = _run(session, units, occupancies)
        before = next(row for row in _entered(rows) if row.tenancy_id == "ten_pc_before")
        assert before.period.valid_from == date(2022, 1, 1)
        assert before.period.valid_to == date(2024, 6, 1)

    def test_entered_rows_arrive_in_a_stable_chronological_order(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        rows, _ = _run(session, units, occupancies)
        starts = [row.period.valid_from for row in _entered(rows)]
        assert starts == sorted(starts)

    def test_two_runs_produce_identical_input(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """Determinism is part of the engine contract (`CLAUDE.md` § 3.1)."""
        assert _run(session, units, occupancies) == _run(session, units, occupancies)


class TestLetzteBelegung:
    """`letzteBelegung` → `max(1, last known person count of that unit)`."""

    def test_the_derived_rows_are_exactly_the_vacancy_periods(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        rows, _ = _run(session, units, occupancies)
        assert [
            (row.unit_id, row.count, row.period.valid_from, row.period.valid_to)
            for row in _derived(rows)
        ] == [
            # A unit rented across the whole window contributes no D0 row at all.
            ("unit_pc_mid", 2, date(2025, 4, 1), date(2026, 1, 1)),
            ("unit_pc_before", 4, date(2025, 1, 1), date(2026, 1, 1)),
            ("unit_pc_none", 1, date(2025, 1, 1), date(2026, 1, 1)),
            ("unit_pc_zero", 1, date(2025, 1, 1), date(2026, 1, 1)),
            ("unit_pc_later", 4, date(2025, 1, 1), date(2025, 7, 1)),
            ("unit_pc_selfuse", 2, date(2025, 3, 1), date(2025, 5, 1)),
            ("unit_pc_selfuse", 2, date(2025, 8, 1), date(2026, 1, 1)),
            ("unit_pc_partial", 2, date(2025, 3, 1), date(2026, 1, 1)),
        ]

    def test_a_derived_row_is_a_landlord_row_naming_its_unit(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """`docs/02` § 5: the fictional occupancy is a denominator weight on the
        landlord side — never a party line, never a `Renter`."""
        rows, _ = _run(session, units, occupancies)
        derived = _derived(rows)
        assert derived
        assert all(row.tenancy_id is None for row in derived)
        assert all(row.unit_id is not None for row in derived)

    def test_a_fully_rented_unit_gets_no_row(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        rows, _ = _run(session, units, occupancies)
        assert all(row.unit_id != "unit_pc_full" for row in _derived(rows))

    def test_the_gap_starts_the_day_the_tenancy_ends(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """Day-exact: `ten_pc_mid` runs to 2025-04-01 exclusive, so 275 vacancy
        days follow it and 2 × 275 = 550 fictional person-days reach the
        denominator."""
        rows, _ = _run(session, units, occupancies)
        [row] = [row for row in _derived(rows) if row.unit_id == "unit_pc_mid"]
        assert row.period.valid_to is not None
        assert (row.period.valid_to - row.period.valid_from).days == 275
        assert row.count * 275 == 550

    def test_a_unit_vacant_all_year_uses_history_from_before_the_window(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """The single sentence that forced this out of the pure engine: a unit
        with no in-period history still has a last known count, and it comes from
        the tenancy that ended in June 2024."""
        rows, _ = _run(session, units, occupancies)
        [row] = [row for row in _derived(rows) if row.unit_id == "unit_pc_before"]
        assert row.count == 4
        assert row.period.valid_from == WINDOW.valid_from
        assert row.period.valid_to == WINDOW.valid_to

    def test_no_history_at_all_falls_back_to_one(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """Page 01 § 3.5 `wohnung.letzteBelegungPersonen`: "integer, ≥ 1 …
        fallback 1"."""
        rows, _ = _run(session, units, occupancies)
        [row] = [row for row in _derived(rows) if row.unit_id == "unit_pc_none"]
        assert row.count == 1

    def test_a_last_known_count_of_zero_is_floored_at_one(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """`max(1, …)` is not cosmetic: a zero would collapse the derived branch
        into the `keine` denominator, the constellation BGH VIII ZR 159/05 and
        LG Krefeld 2 S 56/09 reject (`docs/02` § 5 edge cases)."""
        rows, _ = _run(session, units, occupancies)
        [row] = [row for row in _derived(rows) if row.unit_id == "unit_pc_zero"]
        assert row.count == 1

    def test_the_count_comes_from_the_last_ENDED_tenancy_not_a_later_one(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """`unit_pc_later` stood empty Jan–Jun and was re-let on 01.07.2025 with
        1 person. The gap must be weighted with the 4 persons who lived there
        *before* it, not with the incoming renter's count."""
        rows, _ = _run(session, units, occupancies)
        [row] = [row for row in _derived(rows) if row.unit_id == "unit_pc_later"]
        assert row.count == 4
        assert row.period.valid_to == date(2025, 7, 1)


class TestImmer1:
    def test_every_vacancy_period_weighs_exactly_one_person(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        rows, _ = _run(session, units, occupancies, FiktivbelegungMode.IMMER_1)
        derived = _derived(rows)
        assert derived
        assert {row.count for row in derived} == {1}

    def test_the_periods_are_the_same_ones_letzte_belegung_produces(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """Only the count differs between the modes — the vacancy timeline does not."""
        immer1, _ = _run(session, units, occupancies, FiktivbelegungMode.IMMER_1)
        letzte, _ = _run(session, units, occupancies, FiktivbelegungMode.LETZTE_BELEGUNG)
        assert [(r.unit_id, r.period) for r in _derived(immer1)] == [
            (r.unit_id, r.period) for r in _derived(letzte)
        ]


class TestKeine:
    def test_no_landlord_row_is_emitted_at_all(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """Not a zero-count row: a zero landlord line would print as a party
        contributing nothing, which is a different statement from "this building
        applies no fictional occupancy"."""
        rows, _ = _run(session, units, occupancies, FiktivbelegungMode.KEINE)
        assert _derived(rows) == []

    def test_the_entered_counts_are_untouched(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        keine, _ = _run(session, units, occupancies, FiktivbelegungMode.KEINE)
        letzte, _ = _run(session, units, occupancies, FiktivbelegungMode.LETZTE_BELEGUNG)
        assert _entered(keine) == _entered(letzte)


class TestSelfUseInsideAVacancy:
    """`docs/02` § 4 separates VACANT ("neither rented nor self-used") from
    SELF_USED, and Page 01 § 4 D0 runs "for each Leerstandsperiode"."""

    def test_a_full_unit_self_use_leaves_vacancy_on_both_uncovered_sides(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        rows, _ = _run(session, units, occupancies)
        pieces = [row for row in _derived(rows) if row.unit_id == "unit_pc_selfuse"]
        assert [(row.period.valid_from, row.period.valid_to) for row in pieces] == [
            (date(2025, 3, 1), date(2025, 5, 1)),
            (date(2025, 8, 1), date(2026, 1, 1)),
        ]

    def test_the_self_used_days_carry_no_fictional_occupancy(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """The gap is 306 days; 92 of them are self-used, so 214 remain vacancy."""
        rows, _ = _run(session, units, occupancies)
        pieces = [row for row in _derived(rows) if row.unit_id == "unit_pc_selfuse"]
        days = sum(
            (row.period.valid_to - row.period.valid_from).days
            for row in pieces
            if row.period.valid_to is not None
        )
        assert (date(2026, 1, 1) - date(2025, 3, 1)).days == 306
        assert days == 214

    def test_a_full_unit_self_use_emits_no_finding(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        rows, findings = _run(session, units, occupancies)
        assert rows  # the run produced input
        assert all("7 Volle Eigennutzung" not in finding for finding in findings)

    def test_a_partial_self_use_leaves_the_whole_gap_as_vacancy(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """The conservative direction. Dropping the fiction here would hand the
        renters the person-keyed fixed cost, which is what BGH VIII ZR 159/05 and
        LG Krefeld 2 S 56/09 reject; Page 01 has no rule for the constellation."""
        rows, _ = _run(session, units, occupancies)
        [row] = [row for row in _derived(rows) if row.unit_id == "unit_pc_partial"]
        assert row.period.valid_from == date(2025, 3, 1)
        assert row.period.valid_to == date(2026, 1, 1)

    def test_the_partial_self_use_finding_is_german_and_says_what_it_could_not_do(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        _, findings = _run(session, units, occupancies)
        [finding] = [f for f in findings if f.startswith("8 Teil-Eigennutzung")]
        assert "Teil-Eigennutzung" in finding
        assert "vom 01.05.2025 bis 31.07.2025" in finding
        assert "Fiktivbelegung" in finding
        assert "nicht abgegrenzt" in finding

    def test_the_partial_self_use_finding_prints_german_decimals(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """Statement-facing copy is German (`CLAUDE.md` § 9.3), and a German
        number separates decimals with a comma — the repository has
        `lokara_pdf.format_number_de` for exactly this.

        Two things are guarded: the separator is a comma, and the area reaches
        the string through a `Decimal` and the shared formatter rather than an
        f-string over `sqm_x100 / 100`, which would print `20.50` and route an
        area through a binary float.

        The expected literal is `20,5 m² von 40 m²`, not `20,50 … 40,00`. That is
        not a weakening: `format_number_de` suppresses trailing zeroes for the
        whole repository by design (docs/08, "Display rounding of a fractional
        Bemessung"), so an integral area prints without decimals — the unit's
        40,00 m² prints as `40`. Introducing a second, two-decimal area format
        for this one finding would contradict that committed display rule, so
        the assertion moves to what the shared formatter contracts to produce.
        The self-use area in the fixture is fractional so the comma is exercised.
        """
        _, findings = _run(session, units, occupancies)
        [finding] = [f for f in findings if f.startswith("8 Teil-Eigennutzung")]
        # Only the areas — the dates in the same sentence legitimately contain
        # dots, so they must not mask an English decimal point in an area.
        [areas] = re.findall(r"\(([^)]*m²[^)]*)\)", finding)
        assert areas == "20,5 m² von 40 m²"
        assert "." not in areas

    def test_an_open_ended_self_use_is_clipped_to_the_window(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """A shorter window must not let a self-use reach past its own end: the
        gap 01.03.–01.06.2025 minus the 01.05.–01.06. self-use leaves exactly the
        two months before it."""
        window = Period(valid_from=date(2025, 1, 1), valid_to=date(2025, 6, 1))
        rows, _ = _run(session, units, occupancies, window=window)
        pieces = [row for row in _derived(rows) if row.unit_id == "unit_pc_selfuse"]
        assert [(row.period.valid_from, row.period.valid_to) for row in pieces] == [
            (date(2025, 3, 1), date(2025, 5, 1)),
        ]


class TestRumpfperiode:
    def test_a_shorter_window_moves_the_derived_periods_day_exactly(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        """`docs/08` "Period boundary": a shorter Rumpfperiode is day-exact."""
        window = Period(valid_from=date(2025, 5, 1), valid_to=date(2025, 9, 1))
        rows, _ = _run(session, units, occupancies, window=window)
        [mid] = [row for row in _derived(rows) if row.unit_id == "unit_pc_mid"]
        assert mid.period.valid_from == date(2025, 5, 1)
        assert mid.period.valid_to == date(2025, 9, 1)

    def test_a_window_before_the_vacancy_produces_no_derived_row_for_that_unit(
        self, session: Session, units: list[Unit], occupancies: tuple[Occupancy, ...]
    ) -> None:
        window = Period(valid_from=date(2025, 1, 1), valid_to=date(2025, 4, 1))
        rows, _ = _run(session, units, occupancies, window=window)
        assert all(row.unit_id != "unit_pc_mid" for row in _derived(rows))
