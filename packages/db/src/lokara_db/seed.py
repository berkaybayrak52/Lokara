"""Demo seed — the €1,200 scenario from lokara-arch.md §10 (port of prisma/seed.ts).

One building, three units (50/30/20 m²), Renter 2 moves out 30 Jun 2025
(valid_to exclusive → 2025-07-01). Idempotent: merge() on fixed ids.

Unlike the TS seed this also creates the OWNER Membership — the FastAPI
account_session dependency really checks it (403 without).

Runs as the owner role (DIRECT_URL); locally that's the docker superuser which
bypasses the FORCEd RLS. TODO(supabase): the Supabase owner is a non-superuser,
so there the seed must set the app.account_id context first.
"""

from datetime import UTC, date, datetime, timedelta

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
    AdvancePaymentPeriod,
    AllocationKeyAssignment,
    BankAccount,
    Building,
    ConfirmedCostClassification,
    CostEntry,
    HeatingCostEntry,
    Membership,
    Meter,
    MeterReading,
    OperatingCostAgreement,
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
# The id StubBankGateway serves. Without a connected bank account row the
# M6-C2 import has no valid FK target, so the demo cannot exercise it.
DEMO_BANK_ACCOUNT_ID = "bank_acc_demo"

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
    session.merge(
        BankAccount(
            id=DEMO_BANK_ACCOUNT_ID,
            account_id=DEMO_ACCOUNT_ID,
            provider="finapi-stub",
            provider_account_id="demo-mietkonto",
            normalized_iban="DE02701500000000594937",
            display_name="Mietkonto Musterstraße 12",
            # docs/15 § 5.6: a pull needs a standing PSD2 consent, and the demo must
            # be able to pull. Computed rather than a fixed date on purpose — a
            # hard-coded far-future value would model a consent longer than the
            # 180-day ceiling (`AIS_CONSENT_MAX_DAYS`), which is exactly the state
            # the reconsent job is meant to flag. No calculation reads this column.
            consent_expires_at=datetime.now(UTC) + timedelta(days=180),
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
            )
        )
        session.merge(
            AdvancePaymentPeriod(
                # Matches migration 0015's deterministic backfill identity so
                # seed_demo remains idempotent on a database that existed before M6-A.
                id=f"app_backfill_{tenancy_id}",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                amount_cents=advance,
                valid_from=valid_from,
                predecessor_id=None,
                declaration_ref="Demo-Mietvertrag",
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
        session.merge(
            OperatingCostAgreement(
                id=f"oca_{tenancy_id}_2025",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                allocation_agreed=True,
                mehrbelastung_clause=True,
                named_other_costs=["muellbeseitigung", "sonstige"],
                contractual_keys={},
                valid_from=date(2025, 1, 1),
                valid_to=date(2026, 1, 1),
                revises_id=None,
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
    demo_classification = session.get(ConfirmedCostClassification, "classification_demo_garbage_1")
    if demo_classification is None:
        session.add(
            ConfirmedCostClassification(
                id="classification_demo_garbage_1",
                account_id=DEMO_ACCOUNT_ID,
                cost_entry_id="cost_demo_garbage",
                allocation_key_assignment_id="aka_demo_garbage_1",
                catalogue_id="muellbeseitigung",
                rule_source="BetrKV / Page 02",
                rule_rechtsstand="Rechtsstand 07/2026",
                source_amount_cents=120000,
                allocable_cents=120000,
                non_allocable_cents=0,
                labour_cents=None,
                key=AllocationKey.AREA,
                key_source="confirmed-seed",
                findings=["verify-before-production"],
                special_rule_evidence={},
                # The Page-02 demo cost is deliberately not tenant-deliverable:
                # the catalogue conventions remain verify-before-production.
                # Projection-isolation tests use an in-memory unblocked bundle,
                # never a misleadingly released demo record.
                production_blocked=True,
            )
        )
    elif (
        not demo_classification.production_blocked
        and session.get(ConfirmedCostClassification, "classification_demo_garbage_2") is None
    ):
        # Databases seeded by the short-lived pre-block fixture already carry
        # immutable evidence.  Correct them by appending the current confirmed
        # classification instead of rewriting or deleting history.
        session.add(
            ConfirmedCostClassification(
                id="classification_demo_garbage_2",
                account_id=DEMO_ACCOUNT_ID,
                cost_entry_id="cost_demo_garbage",
                allocation_key_assignment_id="aka_demo_garbage_1",
                catalogue_id="muellbeseitigung",
                rule_source="BetrKV / Page 02",
                rule_rechtsstand="Rechtsstand 07/2026",
                source_amount_cents=120000,
                allocable_cents=120000,
                non_allocable_cents=0,
                labour_cents=None,
                key=AllocationKey.AREA,
                key_source="confirmed-seed-correction",
                findings=["verify-before-production"],
                special_rule_evidence={},
                production_blocked=True,
            )
        )

    # The heating-system invoice: € 10.300,00 total, of which € 261,80 is the
    # CO₂ price on 4.000 kg — the numbers the CO2KostAufG split runs on. Those
    # two are the supplier's § 3 Abs. 1 CO2KostAufG disclosure for a 20.000 kWh
    # Erdgas delivery: 4.000 kg ÷ 20.000 kWh = 0,200 kg CO₂/kWh, and 261,80 € ÷
    # 4,000 t = 65,45 €/t = 55,00 €/t (§ 10 Abs. 2 BEHG, 2025) + 19 % USt. They
    # replace 2.000 kg / 300,00 € on 05.08.2026, which had implied 150 €/t and
    # an emission factor no fuel has — docs/06 → "Scenario 2 — the fuel, the
    # emissions and the CO₂ price". Held apart from CostEntry on purpose:
    # §§ 7-9 HeizkostenV dictate the split, so a heating cost never carries an
    # Umlageschlüssel.
    session.merge(
        HeatingCostEntry(
            id="hcost_demo_2025",
            account_id=DEMO_ACCOUNT_ID,
            building_id="bld_demo_muster12",
            label="Heizung & Warmwasser (Brennstoff, Wartung, Betriebsstrom)",
            amount_cents=1_030_000,
            period_from=date(2025, 1, 1),
            period_to=date(2026, 1, 1),
            co2_kg_x1000=4_000_000,  # 4.000 kg × 1000
            co2_cost_cents=26_180,  # 261,80 €
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
                valuation_factor_x1000=1000 if kind is MeterKind.HEAT else None,
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
    "statement",
    "self_use_period",
    "building_assignment",
    "landlord",
)


def reset_demo(session: Session) -> None:
    """Wipe this account's domain data and re-seed the exact demo scenario.

    For the pitch: a rehearsal, a headless test run or a live mis-click leaves
    stray buildings and readings behind, and "Objekte" then opens on a list
    full of *Testgasse 5*. This puts the account back to precisely the state
    `seed_demo` produces — same ids, same numbers, with one deliberate exception:
    `bank_account.consent_expires_at` is re-derived from the current instant, so a
    demo seeded months ago can still pull. No id, statement figure, allocation or
    PDF byte reads that column.

    Confirmed classifications, allocation-key history and cost entries are
    immutable evidence, so reset retains them (voided costs are excluded from
    previews).  It also preserves the seeded tenancy graph they reference and
    removes only additional buildings.  Scope is the session's RLS context.
    """
    for table in _RESET_ORDER:
        session.execute(text(f"DELETE FROM {table}"))
    # A non-canonical cost is evidence too.  It stays in the ledger, but must
    # not keep participating in previews while its surrounding rehearsal graph
    # is removed.  Page-02 classifications and allocation-key history remain
    # attached to their cost and are never deleted here.
    session.execute(
        text(
            "UPDATE cost_entry SET voided_at = now(), "
            "void_reason = 'Demo-Reset: Nicht-kanonisches Objekt' "
            "WHERE building_id <> 'bld_demo_muster12' AND voided_at IS NULL"
        )
    )
    # Remove only non-canonical object graphs. A direct allocation reference
    # is immutable evidence too, so its tenancy/unit survives under an archived
    # building; ordinary rehearsal tenancies are removed in child-first order.
    session.execute(
        text(
            "DELETE FROM operating_cost_agreement WHERE tenancy_id IN "
            "(SELECT t.id FROM tenancy t JOIN unit u ON u.id = t.unit_id "
            "WHERE u.building_id <> 'bld_demo_muster12' AND NOT EXISTS "
            "(SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = t.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM person_count WHERE tenancy_id IN "
            "(SELECT t.id FROM tenancy t JOIN unit u ON u.id = t.unit_id "
            "WHERE u.building_id <> 'bld_demo_muster12' AND NOT EXISTS "
            "(SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = t.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM tenancy_party WHERE tenancy_id IN "
            "(SELECT t.id FROM tenancy t JOIN unit u ON u.id = t.unit_id "
            "WHERE u.building_id <> 'bld_demo_muster12' AND NOT EXISTS "
            "(SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = t.id))"
        )
    )
    # M6-A schedule rows are children of tenancy and are not an archive or a
    # finalized record. Reset removes them before the disposable tenancy graph.
    session.execute(
        text(
            "DELETE FROM advance_payment_period WHERE tenancy_id IN "
            "(SELECT t.id FROM tenancy t JOIN unit u ON u.id = t.unit_id "
            "WHERE u.building_id <> 'bld_demo_muster12' AND NOT EXISTS "
            "(SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = t.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM tenancy WHERE unit_id IN "
            "(SELECT u.id FROM unit u WHERE u.building_id <> 'bld_demo_muster12' "
            "AND NOT EXISTS (SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = tenancy.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM unit WHERE building_id <> 'bld_demo_muster12' "
            "AND NOT EXISTS (SELECT 1 FROM tenancy t WHERE t.unit_id = unit.id) "
            "AND NOT EXISTS (SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_unit_id = unit.id)"
        )
    )
    # A cost keeps a non-cascading FK to its entered building. Archive that
    # otherwise-empty parent rather than violating the append-only evidence
    # contract; normal object routes filter it out, so reset still lists only
    # Musterstraße 12.
    session.execute(
        text(
            "UPDATE building SET archived_at = now() "
            "WHERE id <> 'bld_demo_muster12' AND EXISTS "
            "(SELECT 1 FROM cost_entry c WHERE c.building_id = building.id)"
        )
    )
    session.execute(
        text(
            "DELETE FROM building WHERE id <> 'bld_demo_muster12' "
            "AND NOT EXISTS (SELECT 1 FROM cost_entry c WHERE c.building_id = building.id)"
        )
    )
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
