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
    CalibrationDataState,
    HeatingCostCategory,
    MeasurementUnit,
    MeterDeviceType,
    MeterKind,
    MeterLifecycleEventType,
    ReadingReason,
    ReadingSource,
    RemoteReadability,
)
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .ids import new_id
from .models import (
    Account,
    AdvanceAllocation,
    AdvancePayment,
    AdvancePaymentPeriod,
    AdvanceReconciliation,
    AdvanceReconciliationAllocation,
    AllocationKeyAssignment,
    BankAccount,
    BankTransaction,
    BankTransactionClassificationEvent,
    Building,
    ConfirmedCostClassification,
    CostEntry,
    DeliveryAddress,
    HeatingCostEntry,
    InvestmentEntitlementEvent,
    MatchProposal,
    Membership,
    Meter,
    MeterLifecycleEvent,
    MeterReading,
    OperatingCostAgreement,
    PaymentAllocation,
    PaymentInstruction,
    PaymentLedgerEntry,
    Person,
    Receivable,
    Renter,
    Role,
    Tenancy,
    TenancyContractPosition,
    TenancyContractVersion,
    TenancyParty,
    Unit,
    UnitProfileVersion,
)
from .session import create_db_engine
from .settings import DbSettings

DEMO_ACCOUNT_ID = "acc_demo_lokara"
DEMO_PERSON_ID = "per_demo_owner"
# The id StubBankGateway serves. Without a connected bank account row the
# M6-C2 import has no valid FK target, so the demo cannot exercise it.
DEMO_BANK_ACCOUNT_ID = "bank_acc_demo"
_DEMO_BANK_ACCOUNTS = (
    (
        DEMO_BANK_ACCOUNT_ID,
        "demo-mietkonto-muster12",
        "DE02701500000000594937",
        "Mietkonto Musterstraße 12",
        180,
    ),
    (
        "bank_acc_demo_linden8",
        "demo-mietkonto-linden8",
        "DE02701500000000612844",
        "Mietkonto Lindenweg 8",
        12,
    ),
    (
        "bank_acc_demo_hafen27",
        "demo-mietkonto-hafen27",
        "DE02701500000000730518",
        "Mietkonto Hafenallee 27",
        180,
    ),
)
_CANONICAL_BUILDING_IDS_SQL = "('bld_demo_muster12', 'bld_demo_linden8', 'bld_demo_hafen27')"

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

# Portfolio-only demo graph for the Object/Unit dashboards. The canonical
# Musterstraße statement fixture above remains exactly the three units A/B/C;
# these rows belong only to the other two portfolio buildings and therefore do
# not enter the canonical statement allocation.
_PORTFOLIO_BUILDINGS = (
    ("bld_demo_linden8", "Lindenweg 8", "Lindenweg 8", "55116", "Mainz", "WOHNHAUS"),
    (
        "bld_demo_hafen27",
        "Hafenallee 27",
        "Hafenallee 27",
        "65183",
        "Wiesbaden",
        "WOHN_UND_GESCHAEFTSHAUS",
    ),
)
_PORTFOLIO_UNITS = (
    ("unit_demo_d", "bld_demo_linden8", "Wohnung D (1. OG rechts)", 4500, "RESIDENTIAL"),
    ("unit_demo_dg", "bld_demo_hafen27", "Dachgeschoss", 6200, "RESIDENTIAL"),
    ("unit_demo_laden", "bld_demo_hafen27", "Ladenlokal", 7800, "COMMERCIAL"),
    ("unit_demo_hof", "bld_demo_linden8", "Hofhaus", 4100, "RESIDENTIAL"),
    ("unit_demo_linden1", "bld_demo_linden8", "Wohnung 1 (EG)", 5800, "RESIDENTIAL"),
    ("unit_demo_linden2", "bld_demo_linden8", "Wohnung 2 (1. OG)", 4900, "RESIDENTIAL"),
    ("unit_demo_linden3", "bld_demo_linden8", "Wohnung 3 (2. OG)", 6600, "RESIDENTIAL"),
    ("unit_demo_hafen1", "bld_demo_hafen27", "Loft 1", 8200, "RESIDENTIAL"),
    ("unit_demo_hafen2", "bld_demo_hafen27", "Loft 2", 7400, "RESIDENTIAL"),
    ("unit_demo_hafen_buero", "bld_demo_hafen27", "Büroeinheit", 13200, "COMMERCIAL"),
)
_PORTFOLIO_PARTIES = (
    ("ren_demo_d", "David Sommer", "unit_demo_d", 78000),
    ("ren_demo_dg", "Eva König", "unit_demo_dg", 110000),
    ("ren_demo_laden", "Kiez Café GmbH", "unit_demo_laden", 145000),
    ("ren_demo_hof", "Maria Santos", "unit_demo_hof", 99000),
    ("ren_demo_l1", "Jonas Weber", "unit_demo_linden1", 89000),
    ("ren_demo_l2", "Lea Neumann", "unit_demo_linden2", 76000),
    ("ren_demo_h1", "Noah Richter", "unit_demo_hafen1", 125000),
    ("ren_demo_h2", "Sophie Klein", "unit_demo_hafen2", 108000),
    ("ren_demo_hb", "Rheinblick Design UG", "unit_demo_hafen_buero", 210000),
)
_HISTORICAL_REPLACEMENT = (
    "ren_demo_b2",
    "Fatma Yilmaz",
    "ten_demo_b2",
    68000,
    15000,
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


def _month_start(value: date, months_back: int) -> date:
    month_index = value.year * 12 + value.month - 1 - months_back
    return date(month_index // 12, month_index % 12 + 1, 1)


def _seed_payment_history(session: Session) -> None:
    """Three prior rent months plus ordinary movements from the portfolio demo pack."""
    demo_today = date.today()
    history_start = demo_today - timedelta(days=99)
    payment_specs = (
        (
            "anna",
            "ren_demo_1",
            "ten_demo_a1",
            DEMO_BANK_ACCOUNT_ID,
            "Anna Beispiel",
            95000,
            16000,
            6000,
        ),
        (
            "fatma",
            "ren_demo_b2",
            "ten_demo_b2",
            DEMO_BANK_ACCOUNT_ID,
            "Fatma Yilmaz",
            68000,
            11000,
            4000,
        ),
        (
            "clara",
            "ren_demo_3",
            "ten_demo_c1",
            DEMO_BANK_ACCOUNT_ID,
            "Clara Vorlage",
            52000,
            8000,
            3000,
        ),
        (
            "david",
            "ren_demo_d",
            "ten_demo_portfolio_1",
            DEMO_BANK_ACCOUNT_ID,
            "David Sommer",
            78000,
            14000,
            5000,
        ),
        (
            "eva",
            "ren_demo_dg",
            "ten_demo_portfolio_2",
            DEMO_BANK_ACCOUNT_ID,
            "Eva König",
            110000,
            18000,
            7000,
        ),
        (
            "kiez",
            "ren_demo_laden",
            "ten_demo_portfolio_3",
            DEMO_BANK_ACCOUNT_ID,
            "Kiez Café GmbH",
            145000,
            22000,
            8000,
        ),
        (
            "jonas",
            "ren_demo_l1",
            "ten_demo_portfolio_5",
            "bank_acc_demo_linden8",
            "Jonas Weber",
            89000,
            15500,
            5500,
        ),
        (
            "lea",
            "ren_demo_l2",
            "ten_demo_portfolio_6",
            "bank_acc_demo_linden8",
            "Lea Neumann",
            76000,
            13000,
            5000,
        ),
        (
            "noah",
            "ren_demo_h1",
            "ten_demo_portfolio_7",
            "bank_acc_demo_hafen27",
            "Noah Richter",
            125000,
            20000,
            8000,
        ),
        (
            "sophie",
            "ren_demo_h2",
            "ten_demo_portfolio_8",
            "bank_acc_demo_hafen27",
            "Sophie Klein",
            108000,
            17500,
            6500,
        ),
        (
            "rheinblick",
            "ren_demo_hb",
            "ten_demo_portfolio_9",
            "bank_acc_demo_hafen27",
            "Rheinblick Design UG",
            210000,
            33000,
            12000,
        ),
    )

    for months_back in (3, 2, 1):
        month = _month_start(demo_today, months_back)
        period = f"{month:%Y-%m}"
        first_booking = max(month, history_start)
        for index, (
            code,
            renter_id,
            tenancy_id,
            bank_account_id,
            counterpart,
            base_rent,
            nk_advance,
            heating_advance,
        ) in enumerate(payment_specs):
            expected = base_rent + nk_advance + heating_advance
            receivable_id = f"recv_demo_history_{period}_{code}"
            transaction_id = f"bank_tx_demo_history_{period}_{code}"
            proposal_id = f"proposal_demo_history_{period}_{code}"
            ledger_id = f"ledger_demo_history_{period}_{code}"
            allocation_id = f"allocation_demo_history_{period}_{code}"
            booking_date = first_booking + timedelta(days=index % 4)

            if session.get(Receivable, receivable_id) is None:
                session.add(
                    Receivable(
                        id=receivable_id,
                        account_id=DEMO_ACCOUNT_ID,
                        renter_id=renter_id,
                        tenancy_id=tenancy_id,
                        source_type="DEMO_RECURRING_RENT",
                        source_id=None,
                        period=period,
                        due_date=month + timedelta(days=2),
                        expected_cents=expected,
                        open_cents=0,
                        status="settled",
                        category="rent",
                        base_rent_cents=base_rent,
                        nk_advance_cents=nk_advance,
                        heating_advance_cents=heating_advance,
                        garage_cents=0,
                        open_costs_cents=0,
                        open_interest_cents=0,
                        open_principal_cents=0,
                        stored_reference=None,
                    )
                )
            if session.get(BankTransaction, transaction_id) is None:
                session.add(
                    BankTransaction(
                        id=transaction_id,
                        account_id=DEMO_ACCOUNT_ID,
                        bank_account_id=bank_account_id,
                        provider_transaction_id=f"demo-history-{period}-{code}",
                        amount_cents=expected,
                        bank_booking_date=booking_date,
                        finapi_booking_date=booking_date,
                        value_date=booking_date,
                        counterpart_iban=f"DE009900{months_back:02d}{index:012d}",
                        counterpart_name=counterpart,
                        purpose=f"Miete {period}",
                        end_to_end_reference=f"E2E-DEMO-{period}-{code}",
                        counterpart_mandate_reference=None,
                        bank_transaction_code="SEPA-CT",
                        provider_type="CREDIT",
                        is_potential_duplicate=False,
                    )
                )
            session.flush()
            if session.get(MatchProposal, proposal_id) is None:
                session.add(
                    MatchProposal(
                        id=proposal_id,
                        account_id=DEMO_ACCOUNT_ID,
                        bank_transaction_id=transaction_id,
                        receivable_id=receivable_id,
                        renter_id=renter_id,
                        rank=1,
                        signal_iban=60,
                        signal_amount=30,
                        signal_code_or_surname=10,
                        signal_e2e=0,
                        signal_period=0,
                        confidence=100,
                        decision="AUTO_MATCH",
                        convention_version="docs/15 07/2026",
                        reason_de="Bekannte IBAN und exakter Monatsbetrag.",
                    )
                )
            session.flush()
            if session.get(PaymentLedgerEntry, ledger_id) is None:
                session.add(
                    PaymentLedgerEntry(
                        id=ledger_id,
                        account_id=DEMO_ACCOUNT_ID,
                        bank_transaction_id=transaction_id,
                        match_proposal_id=proposal_id,
                        kind="PAYMENT",
                        amount_cents=expected,
                        credit_cents=0,
                        ordering_version="docs/15 § 366/367 BGB, Rechtsstand 07/2026",
                        reverses_entry_id=None,
                    )
                )
                session.flush()
                session.add(
                    PaymentAllocation(
                        id=allocation_id,
                        account_id=DEMO_ACCOUNT_ID,
                        ledger_entry_id=ledger_id,
                        receivable_id=receivable_id,
                        costs_cents=0,
                        interest_cents=0,
                        principal_cents=expected,
                        base_rent_cents=base_rent,
                        nk_advance_cents=nk_advance,
                        heating_advance_cents=heating_advance,
                        garage_cents=0,
                        resulting_status="settled",
                        before_open_costs_cents=0,
                        before_open_interest_cents=0,
                        before_open_principal_cents=expected,
                        before_open_cents=expected,
                        before_status="open",
                        after_open_costs_cents=0,
                        after_open_interest_cents=0,
                        after_open_principal_cents=0,
                        after_open_cents=0,
                        after_status="settled",
                    )
                )

        outgoing_specs = (
            ("bank_fee", DEMO_BANK_ACCOUNT_ID, -990, "Bankentgelt", "Kontoführung"),
            ("reserve", "bank_acc_demo_linden8", -50000, "Interne Umbuchung", "Rücklage"),
            (
                "insurance",
                "bank_acc_demo_hafen27",
                -18460,
                "Versicherung Demo",
                "Gebäudeversicherung",
            ),
        )
        for index, (code, bank_account_id, amount, counterpart, purpose) in enumerate(
            outgoing_specs
        ):
            transaction_id = f"bank_tx_demo_history_{period}_{code}"
            booking_date = first_booking + timedelta(days=10 + index)
            if session.get(BankTransaction, transaction_id) is None:
                session.add(
                    BankTransaction(
                        id=transaction_id,
                        account_id=DEMO_ACCOUNT_ID,
                        bank_account_id=bank_account_id,
                        provider_transaction_id=f"demo-history-{period}-{code}",
                        amount_cents=amount,
                        bank_booking_date=booking_date,
                        finapi_booking_date=booking_date,
                        value_date=booking_date,
                        counterpart_iban=None,
                        counterpart_name=counterpart,
                        purpose=purpose,
                        end_to_end_reference=f"E2E-DEMO-{period}-{code}",
                        counterpart_mandate_reference=None,
                        bank_transaction_code="SEPA-DD",
                        provider_type="DEBIT",
                        is_potential_duplicate=False,
                    )
                )
            session.flush()
            classification_id = f"classification_demo_history_{period}_{code}"
            if session.get(BankTransactionClassificationEvent, classification_id) is None:
                session.add(
                    BankTransactionClassificationEvent(
                        id=classification_id,
                        account_id=DEMO_ACCOUNT_ID,
                        bank_transaction_id=transaction_id,
                        action="IGNORED",
                        reason=(
                            "Interne Umbuchung"
                            if code == "reserve"
                            else "Bereits anderweitig erfasst"
                        ),
                        actor_person_id=DEMO_PERSON_ID,
                    )
                )


def _seed_payment_workspace(session: Session) -> None:
    """Persisted UI-07 demo facts; never frontend-generated money."""
    receivable_specs = (
        ("recv_demo_full", "ren_demo_1", "ten_demo_a1", 117000, 0, "settled", 95000, 22000),
        ("recv_demo_partial", "ren_demo_b2", "ten_demo_b2", 83000, 33000, "partial", 68000, 15000),
        ("recv_demo_review", "ren_demo_3", "ten_demo_c1", 63000, 63000, "open", 52000, 11000),
    )
    for (
        row_id,
        renter_id,
        tenancy_id,
        expected,
        open_cents,
        status,
        base,
        advance,
    ) in receivable_specs:
        if session.get(Receivable, row_id) is None:
            session.add(
                Receivable(
                    id=row_id,
                    account_id=DEMO_ACCOUNT_ID,
                    renter_id=renter_id,
                    tenancy_id=tenancy_id,
                    source_type="DEMO_RECURRING_RENT",
                    source_id=None,
                    period="2026-08",
                    due_date=date(2026, 8, 3),
                    expected_cents=expected,
                    open_cents=open_cents,
                    status=status,
                    category="rent",
                    base_rent_cents=base,
                    nk_advance_cents=advance,
                    heating_advance_cents=0,
                    garage_cents=0,
                    open_costs_cents=0,
                    open_interest_cents=0,
                    open_principal_cents=open_cents,
                    stored_reference=None,
                )
            )

    transaction_specs = (
        (
            "bank_tx_demo_full",
            DEMO_BANK_ACCOUNT_ID,
            117000,
            "Anna Beispiel",
            "Miete August 2026",
            False,
        ),
        (
            "bank_tx_demo_partial",
            DEMO_BANK_ACCOUNT_ID,
            50000,
            "Fatma Yilmaz",
            "Miete August Teilzahlung",
            False,
        ),
        (
            "bank_tx_demo_review",
            DEMO_BANK_ACCOUNT_ID,
            63000,
            "Clara Vorlage",
            "Miete August 2026",
            False,
        ),
        (
            "bank_tx_demo_unmatched",
            DEMO_BANK_ACCOUNT_ID,
            40000,
            "Unbekannter Absender",
            "Überweisung",
            False,
        ),
        (
            "bank_tx_demo_duplicate",
            DEMO_BANK_ACCOUNT_ID,
            63000,
            "Clara Vorlage",
            "Miete August doppelt?",
            True,
        ),
        (
            "bank_tx_demo_outgoing",
            DEMO_BANK_ACCOUNT_ID,
            -2599,
            "Supermarkt Demo",
            "Privater Einkauf",
            False,
        ),
        (
            "bank_tx_demo_linden",
            "bank_acc_demo_linden8",
            89000,
            "Jonas Weber",
            "Miete August 2026",
            False,
        ),
        (
            "bank_tx_demo_hafen",
            "bank_acc_demo_hafen27",
            125000,
            "Noah Richter",
            "Miete August 2026",
            False,
        ),
    )
    for index, (row_id, bank_account_id, amount, counterpart, purpose, duplicate) in enumerate(
        transaction_specs
    ):
        if session.get(BankTransaction, row_id) is None:
            booking_date = date(2026, 8, 20) - timedelta(days=index)
            session.add(
                BankTransaction(
                    id=row_id,
                    account_id=DEMO_ACCOUNT_ID,
                    bank_account_id=bank_account_id,
                    provider_transaction_id=f"demo-ui07-{index}",
                    amount_cents=amount,
                    bank_booking_date=booking_date,
                    finapi_booking_date=booking_date,
                    value_date=booking_date,
                    counterpart_iban=f"DE0012345678900000{index:02d}",
                    counterpart_name=counterpart,
                    purpose=purpose,
                    end_to_end_reference=f"E2E-DEMO-UI07-{index}",
                    counterpart_mandate_reference=None,
                    bank_transaction_code="SEPA-CT",
                    provider_type="CREDIT" if amount >= 0 else "DEBIT",
                    is_potential_duplicate=duplicate,
                )
            )
    session.flush()

    proposal_specs = (
        (
            "proposal_demo_full",
            "bank_tx_demo_full",
            "recv_demo_full",
            "ren_demo_1",
            "AUTO_MATCH",
            95,
            "Betrag und Mieter stimmen überein.",
        ),
        (
            "proposal_demo_partial",
            "bank_tx_demo_partial",
            "recv_demo_partial",
            "ren_demo_b2",
            "AUTO_MATCH",
            90,
            "Mieter erkannt; Betrag ist eine Teilzahlung.",
        ),
        (
            "proposal_demo_review",
            "bank_tx_demo_review",
            "recv_demo_review",
            "ren_demo_3",
            "NEEDS_REVIEW",
            72,
            "Betrag und Name passen; IBAN ist noch nicht bestätigt.",
        ),
        (
            "proposal_demo_duplicate",
            "bank_tx_demo_duplicate",
            "recv_demo_review",
            "ren_demo_3",
            "NEEDS_REVIEW",
            60,
            "Mögliche Dublette — bitte prüfen.",
        ),
    )
    for (
        proposal_id,
        transaction_id,
        receivable_id,
        renter_id,
        decision,
        confidence,
        reason,
    ) in proposal_specs:
        if session.get(MatchProposal, proposal_id) is None:
            session.add(
                MatchProposal(
                    id=proposal_id,
                    account_id=DEMO_ACCOUNT_ID,
                    bank_transaction_id=transaction_id,
                    receivable_id=receivable_id,
                    renter_id=renter_id,
                    rank=1,
                    signal_iban=0,
                    signal_amount=30,
                    signal_code_or_surname=10,
                    signal_e2e=0,
                    signal_period=max(0, confidence - 40),
                    confidence=confidence,
                    decision=decision,
                    convention_version="docs/15 07/2026",
                    reason_de=reason,
                )
            )
    session.flush()

    ledger_specs = (
        (
            "ledger_demo_full",
            "bank_tx_demo_full",
            "proposal_demo_full",
            117000,
            "recv_demo_full",
            117000,
            "settled",
            117000,
            0,
            95000,
            22000,
        ),
        (
            "ledger_demo_partial",
            "bank_tx_demo_partial",
            "proposal_demo_partial",
            50000,
            "recv_demo_partial",
            50000,
            "partial",
            83000,
            33000,
            50000,
            0,
        ),
    )
    for (
        ledger_id,
        transaction_id,
        proposal_id,
        amount,
        receivable_id,
        principal,
        status,
        before_open,
        after_open,
        base,
        advance,
    ) in ledger_specs:
        if session.get(PaymentLedgerEntry, ledger_id) is not None:
            continue
        entry = PaymentLedgerEntry(
            id=ledger_id,
            account_id=DEMO_ACCOUNT_ID,
            bank_transaction_id=transaction_id,
            match_proposal_id=proposal_id,
            kind="PAYMENT",
            amount_cents=amount,
            credit_cents=0,
            ordering_version="docs/15 07/2026",
            reverses_entry_id=None,
        )
        session.add(entry)
        session.flush()
        session.add(
            PaymentAllocation(
                id=f"allocation_{ledger_id}",
                account_id=DEMO_ACCOUNT_ID,
                ledger_entry_id=ledger_id,
                receivable_id=receivable_id,
                costs_cents=0,
                interest_cents=0,
                principal_cents=principal,
                base_rent_cents=base,
                nk_advance_cents=advance,
                heating_advance_cents=0,
                garage_cents=0,
                resulting_status=status,
                before_open_costs_cents=0,
                before_open_interest_cents=0,
                before_open_principal_cents=before_open,
                before_open_cents=before_open,
                before_status="open",
                after_open_costs_cents=0,
                after_open_interest_cents=0,
                after_open_principal_cents=after_open,
                after_open_cents=after_open,
                after_status=status,
            )
        )

    latest_classification = session.scalar(
        select(BankTransactionClassificationEvent)
        .where(BankTransactionClassificationEvent.bank_transaction_id == "bank_tx_demo_outgoing")
        .order_by(
            BankTransactionClassificationEvent.created_at.desc(),
            BankTransactionClassificationEvent.id.desc(),
        )
        .limit(1)
    )
    if latest_classification is None or latest_classification.action != "IGNORED":
        session.add(
            BankTransactionClassificationEvent(
                id=("classification_demo_outgoing" if latest_classification is None else new_id()),
                account_id=DEMO_ACCOUNT_ID,
                bank_transaction_id="bank_tx_demo_outgoing",
                action="IGNORED",
                reason=(
                    "Privat / nicht relevant"
                    if latest_classification is None
                    else "Demo-Zustand wiederhergestellt"
                ),
                actor_person_id=DEMO_PERSON_ID,
            )
        )

    _seed_payment_history(session)


def seed_demo(session: Session) -> None:
    session.merge(Person(id=DEMO_PERSON_ID, email="demo@lokara.example", name="Demo Vermieter"))
    session.merge(Account(id=DEMO_ACCOUNT_ID, name="Demo Konto"))
    session.merge(
        Membership(
            id="mem_demo_owner",
            person_id=DEMO_PERSON_ID,
            account_id=DEMO_ACCOUNT_ID,
            role=Role.OWNER,
            accepted_at=_RECORDED_AT,
        )
    )
    latest_investment_entitlement = session.scalar(
        select(InvestmentEntitlementEvent)
        .where(
            InvestmentEntitlementEvent.account_id == DEMO_ACCOUNT_ID,
            InvestmentEntitlementEvent.entitlement_key == "INVESTMENT",
        )
        .order_by(InvestmentEntitlementEvent.version.desc())
        .limit(1)
    )
    if latest_investment_entitlement is None or not latest_investment_entitlement.enabled:
        session.add(
            InvestmentEntitlementEvent(
                id=(
                    "investment_entitlement_demo_enabled"
                    if latest_investment_entitlement is None
                    else new_id()
                ),
                account_id=DEMO_ACCOUNT_ID,
                entitlement_key="INVESTMENT",
                version=(
                    1
                    if latest_investment_entitlement is None
                    else latest_investment_entitlement.version + 1
                ),
                enabled=True,
                supersedes_entitlement_event_id=(
                    None
                    if latest_investment_entitlement is None
                    else latest_investment_entitlement.id
                ),
                recorded_by_membership_id="mem_demo_owner",
                recorded_at=(
                    _RECORDED_AT if latest_investment_entitlement is None else datetime.now(UTC)
                ),
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
    for building_id, name, street, postal_code, city, building_type in _PORTFOLIO_BUILDINGS:
        session.merge(
            Building(
                id=building_id,
                account_id=DEMO_ACCOUNT_ID,
                name=name,
                street=street,
                postal_code=postal_code,
                city=city,
                building_type=building_type,
            )
        )
    for unit_id, building_id, label, area, _usage_type in _PORTFOLIO_UNITS:
        session.merge(
            Unit(
                id=unit_id,
                account_id=DEMO_ACCOUNT_ID,
                building_id=building_id,
                label=label,
                area_sqm_x100=area,
            )
        )
    for bank_id, provider_account_id, iban, display_name, consent_days in _DEMO_BANK_ACCOUNTS:
        session.merge(
            BankAccount(
                id=bank_id,
                account_id=DEMO_ACCOUNT_ID,
                provider="finapi-stub",
                provider_account_id=provider_account_id,
                normalized_iban=iban,
                display_name=display_name,
                # docs/15 § 5.6: the demo includes active and soon-expiring consent.
                # No calculation reads this value.
                consent_expires_at=datetime.now(UTC) + timedelta(days=consent_days),
            )
        )
    for renter_id, legal_name in _RENTERS:
        session.merge(Renter(id=renter_id, account_id=DEMO_ACCOUNT_ID, legal_name=legal_name))
    for renter_id, legal_name, _unit_id, _rent in _PORTFOLIO_PARTIES:
        session.merge(Renter(id=renter_id, account_id=DEMO_ACCOUNT_ID, legal_name=legal_name))
    session.merge(
        Renter(
            id=_HISTORICAL_REPLACEMENT[0],
            account_id=DEMO_ACCOUNT_ID,
            legal_name=_HISTORICAL_REPLACEMENT[1],
        )
    )
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

    for index, (renter_id, _name, unit_id, rent) in enumerate(_PORTFOLIO_PARTIES, start=1):
        tenancy_id = f"ten_demo_portfolio_{index}"
        session.merge(
            Tenancy(
                id=tenancy_id,
                account_id=DEMO_ACCOUNT_ID,
                unit_id=unit_id,
                valid_from=date(2024, 1, 1),
                valid_to=None,
                base_rent_cents=rent,
            )
        )
        advance_id = f"app_demo_portfolio_{index}"
        if session.get(AdvancePaymentPeriod, advance_id) is None:
            session.add(
                AdvancePaymentPeriod(
                    id=advance_id,
                    account_id=DEMO_ACCOUNT_ID,
                    tenancy_id=tenancy_id,
                    amount_cents=15000 if index < 9 else 20000,
                    valid_from=date(2024, 1, 1),
                    predecessor_id=None,
                    declaration_ref="Demo-Mietvertrag Portfolio",
                )
            )

        session.merge(
            TenancyParty(
                id=f"tp_demo_portfolio_{index}",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                renter_id=renter_id,
            )
        )
        session.merge(
            TenancyContractVersion(
                id=f"contract_version_demo_portfolio_{index}",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                version=1,
                effective_from=date(2024, 1, 1),
                contract_type=(
                    "COMMERCIAL_OPEN_ENDED"
                    if unit_id in {"unit_demo_hafen_buero", "unit_demo_laden"}
                    else "RESIDENTIAL_OPEN_ENDED"
                ),
                evidence_ref="Demo-Mietvertrag Portfolio",
            )
        )

    # UI-07 payment-only replacement tenancy. It lives on the portfolio's
    # otherwise vacant Lindenweg unit so canonical unit B remains vacant after
    # its documented 2025 move-out while the stable payment graph stays usable.
    session.merge(
        Tenancy(
            id="ten_demo_b2",
            account_id=DEMO_ACCOUNT_ID,
            unit_id="unit_demo_linden3",
            valid_from=date(2026, 1, 1),
            valid_to=None,
            base_rent_cents=68000,
        )
    )
    if session.get(AdvancePaymentPeriod, "app_backfill_ten_demo_b2") is None:
        session.add(
            AdvancePaymentPeriod(
                id="app_backfill_ten_demo_b2",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id="ten_demo_b2",
                amount_cents=15000,
                valid_from=date(2026, 1, 1),
                predecessor_id=None,
                declaration_ref="Demo-Mietvertrag Nachmieter",
            )
        )
    session.merge(
        TenancyParty(
            id="tp_ten_demo_b2",
            account_id=DEMO_ACCOUNT_ID,
            tenancy_id="ten_demo_b2",
            renter_id="ren_demo_b2",
        )
    )
    session.merge(
        TenancyContractVersion(
            id="contract_version_demo_ten_demo_b2",
            account_id=DEMO_ACCOUNT_ID,
            tenancy_id="ten_demo_b2",
            version=1,
            effective_from=date(2026, 1, 1),
            contract_type="RESIDENTIAL_OPEN_ENDED",
            evidence_ref="Demo-Mietvertrag Nachmieter",
        )
    )

    unit_profiles = {
        "unit_demo_a": (300, ["BALCONY", "CELLAR"], "Balkon zum Innenhof"),
        "unit_demo_b": (200, ["CELLAR"], None),
        "unit_demo_c": (100, ["FITTED_KITCHEN"], None),
    }
    for unit_id, (rooms_x100, amenities, amenity_note) in unit_profiles.items():
        profile_id = f"unit_profile_demo_{unit_id}"
        if session.get(UnitProfileVersion, profile_id) is None:
            session.add(
                UnitProfileVersion(
                    id=profile_id,
                    account_id=DEMO_ACCOUNT_ID,
                    unit_id=unit_id,
                    version=1,
                    effective_from=date(2025, 1, 1),
                    usage_type="RESIDENTIAL",
                    rooms_x100=rooms_x100,
                    amenities=amenities,
                    amenity_note=amenity_note,
                    evidence_ref="Demo-Objektunterlagen 2025",
                )
            )

    for unit_id, _building_id, _label, _area, usage_type in _PORTFOLIO_UNITS:
        profile_id = f"unit_profile_demo_{unit_id}"
        if session.get(UnitProfileVersion, profile_id) is None:
            session.add(
                UnitProfileVersion(
                    id=profile_id,
                    account_id=DEMO_ACCOUNT_ID,
                    unit_id=unit_id,
                    version=1,
                    effective_from=date(2024, 1, 1),
                    usage_type=usage_type,
                    rooms_x100=None,
                    amenities=[],
                    amenity_note=None,
                    evidence_ref="Demo-Objektunterlagen Portfolio",
                )
            )

    for tenancy_id, _unit_id, _renter_id, valid_from, _valid_to, _rent, _advance in _TENANCIES:
        contract_id = f"contract_version_demo_{tenancy_id}"
        if session.get(TenancyContractVersion, contract_id) is None:
            session.add(
                TenancyContractVersion(
                    id=contract_id,
                    account_id=DEMO_ACCOUNT_ID,
                    tenancy_id=tenancy_id,
                    version=1,
                    effective_from=valid_from,
                    contract_type="RESIDENTIAL_OPEN_ENDED",
                    evidence_ref="Demo-Mietvertrag",
                )
            )

    if session.get(TenancyContractPosition, "contract_position_demo_garage_a") is None:
        session.add(
            TenancyContractPosition(
                id="contract_position_demo_garage_a",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id="ten_demo_a1",
                position_type="GARAGE",
                inclusion_type="INCLUDED",
                label="Garage 1",
                monthly_amount_cents=None,
                valid_from=date(2023, 4, 1),
                valid_to=None,
                evidence_ref="Demo-Mietvertrag",
            )
        )

    # Complete, append-only evidence for the UI-05A demo statement. These rows
    # are mock data only; they do not change contractual schedules or engine
    # calculations. Conditional inserts keep the seed idempotent on databases
    # where a rehearsal already created newer evidence.
    delivery_addresses = {
        "ten_demo_a1": ("Anna Beispiel", "Musterstraße 12", "60311", "Frankfurt am Main"),
        "ten_demo_b1": ("Bernd Muster", "Parkweg 8", "60316", "Frankfurt am Main"),
        "ten_demo_c1": ("Clara Vorlage", "Musterstraße 12", "60311", "Frankfurt am Main"),
    }
    for tenancy_id, (addressee, street, postal_code, city) in delivery_addresses.items():
        address_id = f"address_demo_{tenancy_id}"
        existing_address = session.get(DeliveryAddress, address_id)
        previous_address_version = session.scalar(
            select(DeliveryAddress.version)
            .where(DeliveryAddress.tenancy_id == tenancy_id)
            .order_by(DeliveryAddress.version.desc())
            .limit(1)
        )
        if existing_address is None:
            session.add(
                DeliveryAddress(
                    id=address_id,
                    account_id=DEMO_ACCOUNT_ID,
                    tenancy_id=tenancy_id,
                    addressee=addressee,
                    street=street,
                    postal_code=postal_code,
                    city=city,
                    country="Deutschland",
                    version=(previous_address_version + 1 if previous_address_version else 1),
                    valid_from=date(2025, 1, 1),
                )
            )

    existing_instruction = session.scalar(
        select(PaymentInstruction.id)
        .where(PaymentInstruction.account_id == DEMO_ACCOUNT_ID)
        .limit(1)
    )
    if existing_instruction is None:
        session.add(
            PaymentInstruction(
                id="payment_instruction_demo_1",
                account_id=DEMO_ACCOUNT_ID,
                version=1,
                instruction_text=(
                    "Zahlung: Bitte überweisen Sie eine Nachzahlung innerhalb von 30 Tagen "
                    "auf das bekannte Mietkonto.\n"
                    "Guthaben: Ein Guthaben wird innerhalb von 14 Tagen auf das bekannte "
                    "Mietkonto ausgezahlt."
                ),
                valid_from=date(2025, 1, 1),
            )
        )

    annual_advances = {
        "ten_demo_a1": 264_000,
        "ten_demo_b1": 90_000,
        "ten_demo_c1": 132_000,
    }
    for tenancy_id, total_cents in annual_advances.items():
        existing_reconciliation = session.scalar(
            select(AdvanceReconciliation.id)
            .where(
                AdvanceReconciliation.tenancy_id == tenancy_id,
                AdvanceReconciliation.period_start == date(2025, 1, 1),
                AdvanceReconciliation.period_end == date(2025, 12, 31),
            )
            .limit(1)
        )
        if existing_reconciliation is not None:
            continue
        payment_id = f"advance_payment_demo_{tenancy_id}_2025"
        allocation_id = f"advance_allocation_demo_{tenancy_id}_2025"
        reconciliation_id = f"advance_reconciliation_demo_{tenancy_id}_2025"
        session.add(
            AdvancePayment(
                id=payment_id,
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                amount_cents=total_cents,
                payment_date=date(2025, 12, 31),
                evidence_ref="Demo-Kontoauszug 2025",
                reversal_of_id=None,
            )
        )
        session.flush()
        session.add(
            AdvanceAllocation(
                id=allocation_id,
                account_id=DEMO_ACCOUNT_ID,
                payment_id=payment_id,
                tenancy_id=tenancy_id,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 12, 31),
                amount_cents=total_cents,
            )
        )
        session.flush()
        session.add(
            AdvanceReconciliation(
                id=reconciliation_id,
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 12, 31),
                version=1,
                total_cents=total_cents,
                supersedes_id=None,
            )
        )
        session.flush()
        session.add(
            AdvanceReconciliationAllocation(
                id=f"advance_reconciliation_allocation_demo_{tenancy_id}_2025",
                account_id=DEMO_ACCOUNT_ID,
                reconciliation_id=reconciliation_id,
                allocation_id=allocation_id,
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
            category=HeatingCostCategory.FUEL_OR_HEAT_SUPPLY,
            label="Heizung & Warmwasser (Brennstoff, Wartung, Betriebsstrom)",
            amount_cents=1_030_000,
            period_from=date(2025, 1, 1),
            period_to=date(2026, 1, 1),
            co2_kg_x1000=4_000_000,  # 4.000 kg × 1000
            co2_cost_cents=26_180,  # 261,80 €
            source_ref="Demo-Energieabrechnung 2025",
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
        existing_meter = session.get(Meter, meter_id)
        installed_on = (
            existing_meter.installed_on if existing_meter is not None else date(2021, 1, 1)
        )
        session.merge(
            Meter(
                id=meter_id,
                account_id=DEMO_ACCOUNT_ID,
                building_id="bld_demo_muster12",
                unit_id=meter_unit_id,
                kind=kind,
                measurement_unit=measurement_unit,
                device_type=(
                    MeterDeviceType.HEAT_METER
                    if kind is MeterKind.HEAT and measurement_unit is MeasurementUnit.KWH
                    else (
                        MeterDeviceType.HEAT_COST_ALLOCATOR
                        if kind is MeterKind.HEAT
                        else (
                            MeterDeviceType.WARM_WATER_METER
                            if kind is MeterKind.WARM_WATER
                            else MeterDeviceType.COLD_WATER_METER
                        )
                    )
                ),
                serial=serial,
                label=meter_label,
                location=None,
                manufacturer=None,
                model=None,
                installed_on=installed_on,
                remote_readability=RemoteReadability.UNKNOWN,
                calibration_data_state=(
                    CalibrationDataState.NOT_APPLICABLE
                    if kind is MeterKind.HEAT and measurement_unit is MeasurementUnit.HKV_UNITS
                    else CalibrationDataState.DATA_AVAILABLE
                ),
                calibration_date=(
                    None
                    if kind is MeterKind.HEAT and measurement_unit is MeasurementUnit.HKV_UNITS
                    else date((eichfrist or date(2027, 12, 31)).year - 6, 6, 1)
                ),
                calibration_evidence_ref=(
                    None
                    if kind is MeterKind.HEAT and measurement_unit is MeasurementUnit.HKV_UNITS
                    else f"Demo-Gerätekennzeichnung {serial}"
                ),
                calibration_valid_until=eichfrist,
                valuation_factor_x1000=1000 if kind is MeterKind.HEAT else None,
            )
        )
        lifecycle_id = f"mle_{meter_id}_installed"
        installed_event_id = session.scalar(
            select(MeterLifecycleEvent.id)
            .where(
                MeterLifecycleEvent.meter_id == meter_id,
                MeterLifecycleEvent.event_type == MeterLifecycleEventType.INSTALLED,
            )
            .limit(1)
        )
        if installed_event_id is None:
            session.add(
                MeterLifecycleEvent(
                    id=lifecycle_id,
                    account_id=DEMO_ACCOUNT_ID,
                    building_id="bld_demo_muster12",
                    meter_id=meter_id,
                    event_type=MeterLifecycleEventType.INSTALLED,
                    effective_on=installed_on,
                    reason=None,
                    related_meter_id=None,
                )
            )
        for suffix, read_at, value in (
            ("open", _READ_FROM, opening),
            ("close", _READ_TO, closing),
        ):
            reading_id = f"mr_{meter_id}_{suffix}"
            if session.get(MeterReading, reading_id) is None:
                session.add(
                    MeterReading(
                        id=reading_id,
                        account_id=DEMO_ACCOUNT_ID,
                        meter_id=meter_id,
                        read_at=read_at,
                        value_x1000=value,
                        reason=ReadingReason.PERIODIC,
                        source=ReadingSource.MDL,
                        supersedes_reading_id=None,
                        confirmation_note=None,
                        recorded_at=_RECORDED_AT,
                    )
                )

    _seed_payment_workspace(session)


# Child-before-parent, so every FK is satisfied as the rows go. `account`,
# `membership` and `person` are NOT here on purpose: wiping them would delete
# the caller's own membership and lock the session out of its own account.
_RESET_ORDER: tuple[str, ...] = (
    "self_use_period",
    "building_assignment",
    "landlord",
)


def reset_demo(session: Session) -> None:
    """Reset disposable demo data and restore the canonical demo scenario.

    For the pitch: a rehearsal, a headless test run or a live mis-click leaves
    stray buildings behind, and "Objekte" then opens on a list full of
    *Testgasse 5*. Disposable rows are removed and canonical rows are restored.
    `bank_account.consent_expires_at` is re-derived from the current instant, so
    a demo seeded months ago can still pull. No id, statement figure, allocation
    or PDF byte reads that column.

    Confirmed classifications, allocation-key history, meter readings, meter
    lifecycle events, heating-mode versions and cost entries are immutable
    evidence, so reset retains them. It also preserves every tenancy, unit and
    building graph referenced by that evidence and archives non-canonical
    buildings instead of bypassing append-only database triggers. Scope is the
    session's RLS context.
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
            "WHERE building_id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} AND voided_at IS NULL"
        )
    )
    # Remove only non-canonical object graphs. A direct allocation reference
    # is immutable evidence too, so its tenancy/unit survives under an archived
    # building; ordinary rehearsal tenancies are removed in child-first order.
    session.execute(
        text(
            "DELETE FROM operating_cost_agreement WHERE tenancy_id IN "
            "(SELECT t.id FROM tenancy t JOIN unit u ON u.id = t.unit_id "
            "WHERE u.building_id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} AND NOT EXISTS "
            "(SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = t.id) AND NOT EXISTS "
            "(SELECT 1 FROM meter_reading mr WHERE mr.tenancy_id = t.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM person_count WHERE tenancy_id IN "
            "(SELECT t.id FROM tenancy t JOIN unit u ON u.id = t.unit_id "
            "WHERE u.building_id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} AND NOT EXISTS "
            "(SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = t.id) AND NOT EXISTS "
            "(SELECT 1 FROM meter_reading mr WHERE mr.tenancy_id = t.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM tenancy_party WHERE tenancy_id IN "
            "(SELECT t.id FROM tenancy t JOIN unit u ON u.id = t.unit_id "
            "WHERE u.building_id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} AND NOT EXISTS "
            "(SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = t.id) AND NOT EXISTS "
            "(SELECT 1 FROM meter_reading mr WHERE mr.tenancy_id = t.id))"
        )
    )
    # M6-A schedule rows are children of tenancy and are not an archive or a
    # finalized record. Reset removes them before the disposable tenancy graph.
    session.execute(
        text(
            "DELETE FROM advance_payment_period WHERE tenancy_id IN "
            "(SELECT t.id FROM tenancy t JOIN unit u ON u.id = t.unit_id "
            "WHERE u.building_id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} AND NOT EXISTS "
            "(SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = t.id) AND NOT EXISTS "
            "(SELECT 1 FROM meter_reading mr WHERE mr.tenancy_id = t.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM tenancy WHERE unit_id IN "
            "(SELECT u.id FROM unit u WHERE u.building_id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} "
            "AND NOT EXISTS (SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_tenancy_id = tenancy.id) "
            "AND NOT EXISTS (SELECT 1 FROM meter_reading mr "
            "WHERE mr.tenancy_id = tenancy.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM unit WHERE building_id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} "
            "AND NOT EXISTS (SELECT 1 FROM tenancy t WHERE t.unit_id = unit.id) "
            "AND NOT EXISTS (SELECT 1 FROM allocation_key_assignment a "
            "WHERE a.direct_unit_id = unit.id) "
            "AND NOT EXISTS (SELECT 1 FROM meter m WHERE m.unit_id = unit.id)"
        )
    )
    # A cost keeps a non-cascading FK to its entered building. Archive that
    # otherwise-empty parent rather than violating the append-only evidence
    # contract; normal object routes filter it out, so reset still lists only
    # Musterstraße 12.
    session.execute(
        text(
            "UPDATE building SET archived_at = now() "
            "WHERE id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} AND ("
            "EXISTS (SELECT 1 FROM cost_entry c WHERE c.building_id = building.id) "
            "OR EXISTS (SELECT 1 FROM meter m WHERE m.building_id = building.id) "
            "OR EXISTS (SELECT 1 FROM heating_cost_entry h "
            "WHERE h.building_id = building.id) "
            "OR EXISTS (SELECT 1 FROM heating_billing_mode_version hm "
            "WHERE hm.building_id = building.id))"
        )
    )
    session.execute(
        text(
            "DELETE FROM building WHERE id NOT IN "
            f"{_CANONICAL_BUILDING_IDS_SQL} "
            "AND NOT EXISTS (SELECT 1 FROM cost_entry c WHERE c.building_id = building.id) "
            "AND NOT EXISTS (SELECT 1 FROM meter m WHERE m.building_id = building.id) "
            "AND NOT EXISTS (SELECT 1 FROM heating_cost_entry h "
            "WHERE h.building_id = building.id) "
            "AND NOT EXISTS (SELECT 1 FROM heating_billing_mode_version hm "
            "WHERE hm.building_id = building.id)"
        )
    )
    session.flush()
    seed_demo(session)


def main() -> None:
    engine = create_db_engine(DbSettings().direct_url)
    with Session(engine) as session, session.begin():
        seed_demo(session)
    engine.dispose()
    print("Seed complete: demo account, 3 buildings, 13 units and persisted UI-07 payments.")


if __name__ == "__main__":
    main()
