"""Demo seed — the €1,200 scenario from lokara-arch.md §10 (port of prisma/seed.ts).

One building, three units (50/30/20 m²), Renter 2 moves out 30 Jun 2025
(valid_to exclusive → 2025-07-01). Idempotent: merge() on fixed ids.

Unlike the TS seed this also creates the OWNER Membership — the FastAPI
account_session dependency really checks it (403 without).

Runs as the owner role (DIRECT_URL); locally that's the docker superuser which
bypasses the FORCEd RLS. TODO(supabase): the Supabase owner is a non-superuser,
so there the seed must set the app.account_id context first.
"""

from datetime import UTC, date, datetime

from lokara_domain import (
    AllocationKey,
    MeasurementUnit,
    MeterKind,
    ReadingReason,
    ReadingSource,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import (
    Account,
    AllocationKeyAssignment,
    Building,
    CostEntry,
    HeatingCostEntry,
    Membership,
    Meter,
    MeterReading,
    Person,
    Renter,
    Role,
    Tenancy,
    TenancyParty,
    Unit,
)
from .session import create_db_engine
from .settings import DbSettings

DEMO_ACCOUNT_ID = "acc_demo_lokara"
DEMO_PERSON_ID = "per_demo_owner"

_UNITS = (
    ("unit_demo_a", "Wohnung A (EG links)", 5000),
    ("unit_demo_b", "Wohnung B (EG rechts)", 3000),
    ("unit_demo_c", "Wohnung C (1. OG)", 2000),
)
_RENTERS = (
    ("ren_demo_1", "Anna Beispiel"),
    ("ren_demo_2", "Bernd Muster"),
    ("ren_demo_3", "Clara Vorlage"),
)
_TENANCIES = (
    # (id, unit, renter, valid_from, valid_to_exclusive, base_rent, advance)
    ("ten_demo_a1", "unit_demo_a", "ren_demo_1", date(2023, 4, 1), None, 95000, 22000),
    ("ten_demo_b1", "unit_demo_b", "ren_demo_2", date(2021, 9, 1), date(2025, 7, 1), 68000, 15000),
    ("ten_demo_c1", "unit_demo_c", "ren_demo_3", date(2024, 1, 1), None, 52000, 11000),
)

# ── Zähler (docs/06 Scenario 2: "consumption meters per unit, one warm-water
# meter"). The register PAIRS are the fixture: their differences are exactly the
# heating goldens — building 20.000 kWh / 40 m³, flats 600/250/150 HKV units and
# 20/12/8 m³. Values are × 1000 (fixed point).
#
# (meter_id, unit_id, kind, unit, serial, label, Eichfrist, opening, closing)
_METERS: tuple[
    tuple[
        str,
        str | None,
        MeterKind,
        MeasurementUnit,
        str,
        str | None,
        date | None,
        int,
        int,
    ],
    ...,
] = (
    (
        "met_demo_heat_main",
        None,
        MeterKind.HEAT,
        MeasurementUnit.KWH,
        "WMZ-2022-004711",
        "Wärmemengenzähler Heizzentrale",
        date(2027, 12, 31),
        148_500_000,
        168_500_000,
    ),
    (
        "met_demo_ww_main",
        None,
        MeterKind.WARM_WATER,
        MeasurementUnit.CUBIC_METRE,
        "WWZ-2022-118342",
        "Warmwasserzähler Heizzentrale",
        date(2027, 12, 31),
        812_000,
        852_000,
    ),
    # Heizkostenverteiler are NOT eichpflichtig → Eichfrist stays NULL.
    (
        "met_demo_heat_a",
        "unit_demo_a",
        MeterKind.HEAT,
        MeasurementUnit.HKV_UNITS,
        "HKV-A-100231",
        None,
        None,
        1_200_000,
        1_800_000,
    ),
    (
        "met_demo_heat_b",
        "unit_demo_b",
        MeterKind.HEAT,
        MeasurementUnit.HKV_UNITS,
        "HKV-B-100232",
        None,
        None,
        3_400_000,
        3_650_000,
    ),
    (
        "met_demo_heat_c",
        "unit_demo_c",
        MeterKind.HEAT,
        MeasurementUnit.HKV_UNITS,
        "HKV-C-100233",
        None,
        None,
        880_000,
        1_030_000,
    ),
    (
        "met_demo_ww_a",
        "unit_demo_a",
        MeterKind.WARM_WATER,
        MeasurementUnit.CUBIC_METRE,
        "WWZ-A-556101",
        None,
        date(2028, 12, 31),
        241_500,
        261_500,
    ),
    (
        "met_demo_ww_b",
        "unit_demo_b",
        MeterKind.WARM_WATER,
        MeasurementUnit.CUBIC_METRE,
        "WWZ-B-556102",
        None,
        date(2028, 12, 31),
        96_200,
        108_200,
    ),
    (
        "met_demo_ww_c",
        "unit_demo_c",
        MeterKind.WARM_WATER,
        MeasurementUnit.CUBIC_METRE,
        "WWZ-C-556103",
        None,
        date(2028, 12, 31),
        55_000,
        63_000,
    ),
    # Deliberately expired, and deliberately COLD water: it demonstrates the
    # Eichfrist warning on the Zähler page without touching a single number the
    # heating engine consumes.
    (
        "met_demo_kw_c",
        "unit_demo_c",
        MeterKind.COLD_WATER,
        MeasurementUnit.CUBIC_METRE,
        "KWZ-C-441097",
        None,
        date(2025, 12, 31),
        302_400,
        340_900,
    ),
)

_READ_FROM = date(2025, 1, 1)
_READ_TO = date(2025, 12, 31)
# Fixed so re-seeding never reshuffles which reading is the "latest" one.
_RECORDED_AT = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


def seed_demo(session: Session) -> None:
    session.merge(Person(id=DEMO_PERSON_ID, email="demo@lokara.example", name="Demo Vermieter"))
    session.merge(Account(id=DEMO_ACCOUNT_ID, name="Demo Konto"))
    session.merge(
        Membership(
            id="mem_demo_owner",
            person_id=DEMO_PERSON_ID,
            account_id=DEMO_ACCOUNT_ID,
            role=Role.OWNER,
        )
    )
    session.merge(
        Building(
            id="bld_demo_muster12",
            account_id=DEMO_ACCOUNT_ID,
            name="Musterstraße 12",
            street="Musterstraße 12",
            postal_code="60311",
            city="Frankfurt am Main",
        )
    )
    for unit_id, label, area in _UNITS:
        session.merge(
            Unit(
                id=unit_id,
                account_id=DEMO_ACCOUNT_ID,
                building_id="bld_demo_muster12",
                label=label,
                area_sqm_x100=area,
            )
        )
    for renter_id, legal_name in _RENTERS:
        session.merge(Renter(id=renter_id, account_id=DEMO_ACCOUNT_ID, legal_name=legal_name))
    for tenancy_id, unit_id, renter_id, valid_from, valid_to, rent, advance in _TENANCIES:
        session.merge(
            Tenancy(
                id=tenancy_id,
                account_id=DEMO_ACCOUNT_ID,
                unit_id=unit_id,
                valid_from=valid_from,
                valid_to=valid_to,
                base_rent_cents=rent,
                advance_payment_cents=advance,
            )
        )
        session.merge(
            TenancyParty(
                id=f"tp_{tenancy_id}",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                renter_id=renter_id,
            )
        )

    # The canonical €1,200.00 garbage cost as a REAL cost entry + its AREA key
    # (append-only assignment) — the statement computes from these rows, and
    # the golden numbers (600,00/178,52/181,48/240,00) must keep reproducing.
    session.merge(
        CostEntry(
            id="cost_demo_garbage",
            account_id=DEMO_ACCOUNT_ID,
            building_id="bld_demo_muster12",
            label="Müllabfuhr",
            amount_cents=120000,
            period_from=date(2025, 1, 1),
            period_to=date(2026, 1, 1),
        )
    )
    session.merge(
        AllocationKeyAssignment(
            id="aka_demo_garbage_1",
            account_id=DEMO_ACCOUNT_ID,
            cost_entry_id="cost_demo_garbage",
            key=AllocationKey.AREA,
        )
    )

    # The heating-system invoice: € 10.300,00 total, of which € 300,00 is the
    # CO₂ price on 2.000 kg — the numbers the CO2KostAufG split runs on. Held
    # apart from CostEntry on purpose: §§ 7-9 HeizkostenV dictate the split, so
    # a heating cost never carries an Umlageschlüssel.
    session.merge(
        HeatingCostEntry(
            id="hcost_demo_2025",
            account_id=DEMO_ACCOUNT_ID,
            building_id="bld_demo_muster12",
            label="Heizung & Warmwasser (Brennstoff, Wartung, Betriebsstrom)",
            amount_cents=1_030_000,
            period_from=date(2025, 1, 1),
            period_to=date(2026, 1, 1),
            co2_kg_x1000=2_000_000,
            co2_cost_cents=30_000,
        )
    )

    for (
        meter_id,
        meter_unit_id,
        kind,
        measurement_unit,
        serial,
        meter_label,
        eichfrist,
        opening,
        closing,
    ) in _METERS:
        session.merge(
            Meter(
                id=meter_id,
                account_id=DEMO_ACCOUNT_ID,
                building_id="bld_demo_muster12",
                unit_id=meter_unit_id,
                kind=kind,
                measurement_unit=measurement_unit,
                serial=serial,
                label=meter_label,
                calibration_valid_until=eichfrist,
            )
        )
        for suffix, read_at, value in (
            ("open", _READ_FROM, opening),
            ("close", _READ_TO, closing),
        ):
            session.merge(
                MeterReading(
                    id=f"mr_{meter_id}_{suffix}",
                    account_id=DEMO_ACCOUNT_ID,
                    meter_id=meter_id,
                    read_at=read_at,
                    value_x1000=value,
                    reason=ReadingReason.PERIODIC,
                    source=ReadingSource.MDL,
                    recorded_at=_RECORDED_AT,
                )
            )


# Child-before-parent, so every FK is satisfied as the rows go. `account`,
# `membership` and `person` are NOT here on purpose: wiping them would delete
# the caller's own membership and lock the session out of its own account.
_RESET_ORDER: tuple[str, ...] = (
    "meter_reading",
    "meter",
    "heating_cost_entry",
    "allocation_key_assignment",
    "cost_entry",
    "statement",
    "self_use_period",
    "tenancy_party",
    "tenancy",
    "unit",
    "building_assignment",
    "building",
    "renter",
    "landlord",
)


def reset_demo(session: Session) -> None:
    """Wipe this account's domain data and re-seed the exact demo scenario.

    For the pitch: a rehearsal, a headless test run or a live mis-click leaves
    stray buildings and readings behind, and "Objekte" then opens on a list
    full of *Testgasse 5*. This puts the account back to precisely the state
    `seed_demo` produces — same ids, same numbers.

    Scope is the session's RLS context: these DELETEs cannot reach another
    account's rows even though they name no account_id (the policy adds it).
    Destructive by definition, which is why the endpoint that calls it is
    behind the same flag as the seed itself.
    """
    for table in _RESET_ORDER:
        session.execute(text(f"DELETE FROM {table}"))
    session.flush()
    seed_demo(session)


def main() -> None:
    engine = create_db_engine(DbSettings().direct_url)
    with Session(engine) as session, session.begin():
        seed_demo(session)
    engine.dispose()
    print("Seed complete: demo account, building Musterstraße 12, 3 units, 3 tenancies.")


if __name__ == "__main__":
    main()
