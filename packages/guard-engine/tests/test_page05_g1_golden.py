"""Executable G1 contract for Page-05 fixtures 12-F01-F06 and F11-F13."""

from datetime import date

import pytest
from lokara_guard_engine import (
    GuardResult,
    GuardSourceIdentity,
    MeterCalibrationInput,
    MeterCalibrationRuleBundle,
    RuleConflict,
    RuleEvidence,
    StatementDeadlineInput,
    StatementDeadlineRuleBundle,
    UviCadenceInput,
    UviCadenceRuleBundle,
    evaluate_meter_calibration,
    evaluate_statement_deadline,
    evaluate_uvi_cadence,
)

PAGE_05_SOURCE = "berkay-work/Spec-Seiten/05 · Wächter Fristen 3a95fd42073181038246e579777508f9.md"
G1_FIXTURE_IDS = {
    "12-F01",
    "12-F02",
    "12-F03",
    "12-F04",
    "12-F05",
    "12-F06",
    "12-F11",
    "12-F12",
    "12-F13",
}

W1_EVIDENCE = (
    RuleEvidence(
        source=PAGE_05_SOURCE,
        register_row="26",
        legal_basis="§ 556 Abs. 3 S. 2–3 BGB",
        rechtsstand="07/2026",
        verification_status="geprüft",
    ),
    RuleEvidence(
        source="berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv",
        register_row="126",
        legal_basis="§§ 187, 188 BGB; KONVENTION-D1/D4/D5",
        rechtsstand="07/2026",
        verification_status="verify-before-production",
    ),
)

W1_RULES = StatementDeadlineRuleBundle(
    evidence=W1_EVIDENCE,
    unresolved_conflicts=(
        RuleConflict(
            code="W1-D4-OBJECTION-END",
            description="Same-numbered day after 12 months versus month-end reading is unresolved.",
            production_blocking=True,
        ),
    ),
    months_after_period=12,
    warnings_de={
        "reminder_30_days": (
            "Noch 30 Tage: Die Betriebskostenabrechnung {year} muss dem Mieter bis "
            "{boundary_date} zugehen. Danach sind Nachforderungen in der Regel "
            "ausgeschlossen (§ 556 Abs. 3 BGB)."
        ),
        "expired": (
            "Frist abgelaufen: Für {year} ist eine Nachforderung in der Regel "
            "ausgeschlossen. Ein Guthaben müssen Sie dem Mieter weiterhin auszahlen."
        ),
    },
    channels_by_stage={
        "reminder_90_days": ("in_app",),
        "reminder_30_days": ("in_app", "email"),
        "last_day": ("email", "push"),
        "expired": ("email", "push"),
    },
    resolution_event="statement_sent",
)

W2_EVIDENCE = (
    RuleEvidence(
        source="berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv",
        register_row="128",
        legal_basis="§ 34 Abs. 2 MessEV; supersedes KONVENTION-D2",
        rechtsstand="08/2026",
        verification_status="geprüft",
    ),
    RuleEvidence(
        source="berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv",
        register_row="129",
        legal_basis="MessEV Anlage 7 Nr. 5.5.1/5.5.2 und 7.1/7.2",
        rechtsstand="08/2026",
        verification_status="geprüft",
    ),
)

W2_CONFLICT = RuleConflict(
    code="W2-RETROFIT-TRANSITION",
    description=(
        "The Dritte MessEV-ÄndV unified the period at six years from 04.11.2021. That it "
        "also covers devices whose five-year period was still running rests on provider "
        "communication; no transition clause was found in the ordinance text."
    ),
    production_blocking=False,
    applies_to_media=("warm_water", "heat_meter", "heat_exchanger_hot_water"),
)

W2_RULES = MeterCalibrationRuleBundle(
    evidence=W2_EVIDENCE,
    unresolved_conflicts=(W2_CONFLICT,),
    years_by_medium={
        "cold_water": 6,
        "warm_water": 6,
        "heat_meter": 6,
        "heat_exchanger_hot_water": 6,
        "electricity": 8,
        "gas": 8,
    },
    legacy_years_by_medium={
        "warm_water": 5,
        "heat_meter": 5,
        "heat_exchanger_hot_water": 5,
    },
    medium_labels_de={
        "cold_water": "Kaltwasser",
        "warm_water": "Warmwasser",
        "heat_meter": "Wärmemengen",
        "heat_exchanger_hot_water": "Wärmetauscher-Warmwasser",
        "electricity": "Strom",
        "gas": "Gas",
    },
    excluded_media=("heating_cost_allocator",),
    expiry_month=12,
    expiry_day=31,
    warning_de=(
        "Der {medium_label}-Zähler in {unit_label} ist ab {boundary_date} nicht mehr "
        "geeicht. Werte aus ungeeichten Zählern können bei der Abrechnung angreifbar "
        "sein — bitte Austausch/Nacheichung veranlassen."
    ),
    channels_by_stage={
        "notice": ("in_app",),
        "expiry_month": ("in_app", "email"),
        "exceeded": ("email",),
    },
    resolution_event="meter_replaced",
)

W4_EVIDENCE = (
    RuleEvidence(
        source="berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv",
        register_row="4",
        legal_basis="§ 6a Abs. 1 Nr. 2 HeizkostenV",
        rechtsstand="07/2026",
        verification_status="geprüft",
    ),
    RuleEvidence(
        source="berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv",
        register_row="117",
        legal_basis="KONVENTION-D3; month-end due date",
        rechtsstand="10/2023",
        verification_status="verify-before-production",
    ),
    RuleEvidence(
        source="berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv",
        register_row="30",
        legal_basis="§ 5 Abs. 2 HeizkostenV",
        rechtsstand="07/2026",
        verification_status="geprüft",
    ),
)

W4_RULES = UviCadenceRuleBundle(
    evidence=W4_EVIDENCE,
    unresolved_conflicts=(
        RuleConflict(
            code="W4-YEAR-ROUND-OR-HEATING-SEASON",
            description="Year-round cadence versus heating-season-only cadence is unresolved.",
            production_blocking=True,
        ),
    ),
    retrofit_deadline=date(2026, 12, 31),
    warning_de=(
        "Für {unit_label} (fernablesbare Zähler) steht die monatliche "
        "Verbrauchsinformation für {month_label} noch aus. § 6a HeizkostenV "
        "verpflichtet zur monatlichen Information des Mieters."
    ),
    retrofit_warning_de="Nachrüstpflicht fernablesbar bis 31.12.2026",
    channels_by_stage={"due": ("in_app",), "overdue": ("email",)},
    resolution_event="uvi_sent",
)


def _assert_common_result(
    result: GuardResult,
    *,
    guard_code: str,
    source_identity: GuardSourceIdentity,
    evidence: tuple[RuleEvidence, ...],
) -> None:
    assert result.guard_code == guard_code
    assert result.source_identity == source_identity
    assert isinstance(result.stage, str)
    assert isinstance(result.active, bool)
    assert isinstance(result.resolved, bool)
    assert result.warning_de is None or isinstance(result.warning_de, str)
    assert isinstance(result.escalation_channels, tuple)
    assert result.boundary_date is None or isinstance(result.boundary_date, date)
    assert isinstance(result.resolution_event, str)
    assert result.rule_evidence == evidence
    assert isinstance(result.production_blockers, tuple)


def test_g1_fixture_surface_is_exactly_the_nine_selected_page_05_cases() -> None:
    assert {
        "12-F01",
        "12-F02",
        "12-F03",
        "12-F04",
        "12-F05",
        "12-F06",
        "12-F11",
        "12-F12",
        "12-F13",
    } == G1_FIXTURE_IDS


@pytest.mark.parametrize(
    ("fixture_id", "period_end", "today", "delivered_on", "stage", "boundary", "days"),
    (
        (
            "12-F01",
            date(2025, 12, 31),
            date(2026, 12, 1),
            None,
            "reminder_30_days",
            date(2026, 12, 31),
            30,
        ),
        (
            "12-F02",
            date(2024, 2, 29),
            date(2025, 1, 15),
            None,
            "none",
            date(2025, 2, 28),
            44,
        ),
        (
            "12-F03",
            date(2025, 12, 31),
            date(2027, 1, 15),
            None,
            "expired",
            date(2026, 12, 31),
            -15,
        ),
        (
            "12-F04",
            date(2025, 12, 31),
            date(2026, 12, 1),
            date(2026, 12, 20),
            "resolved",
            date(2026, 12, 31),
            30,
        ),
    ),
)
def test_12_f01_through_12_f04_execute_w1(
    fixture_id: str,
    period_end: date,
    today: date,
    delivered_on: date | None,
    stage: str,
    boundary: date,
    days: int,
) -> None:
    source_identity = GuardSourceIdentity(source_type="statement", source_id=fixture_id)
    result = evaluate_statement_deadline(
        StatementDeadlineInput(
            source_identity=source_identity,
            today=today,
            period_end=period_end,
            statement_delivered_on=delivered_on,
        ),
        W1_RULES,
    )

    _assert_common_result(
        result,
        guard_code="W1",
        source_identity=source_identity,
        evidence=W1_EVIDENCE,
    )
    assert result.stage == stage
    assert result.boundary_date == boundary
    assert result.days_until_deadline == days
    if fixture_id == "12-F01":
        assert result.escalation_channels == ("in_app", "email")
        assert result.warning_de is not None
        assert result.warning_de.startswith("Noch 30 Tage:")
    elif fixture_id == "12-F02":
        assert not result.active
    elif fixture_id == "12-F03":
        assert result.active
        assert result.credit_remains_payable
        assert result.warning_de is not None
        assert "Guthaben" in result.warning_de
    else:
        assert result.resolved
        assert result.resolution_event == "statement_sent"
        assert result.renter_objection_deadline == date(2027, 12, 20)


def test_w1_exact_thresholds_late_delivery_and_missing_copy_stay_explicit() -> None:
    for today, expected_stage, expected_channels in (
        (date(2026, 10, 2), "reminder_90_days", ("in_app",)),
        (date(2026, 12, 1), "reminder_30_days", ("in_app", "email")),
        (date(2026, 12, 31), "last_day", ("email", "push")),
    ):
        result = evaluate_statement_deadline(
            StatementDeadlineInput(
                source_identity=GuardSourceIdentity(
                    source_type="statement", source_id=f"threshold-{expected_stage}"
                ),
                today=today,
                period_end=date(2025, 12, 31),
                statement_delivered_on=None,
            ),
            W1_RULES,
        )
        assert result.stage == expected_stage
        assert result.escalation_channels == expected_channels
        if expected_stage in {"reminder_90_days", "last_day"}:
            assert result.warning_de is None
            assert f"missing_warning_copy:{expected_stage}" in result.production_blockers

    late = evaluate_statement_deadline(
        StatementDeadlineInput(
            source_identity=GuardSourceIdentity(source_type="statement", source_id="late-delivery"),
            today=date(2027, 1, 15),
            period_end=date(2025, 12, 31),
            statement_delivered_on=date(2027, 1, 10),
        ),
        W1_RULES,
    )
    assert late.stage == "expired"
    assert not late.resolved


def test_12_f05_executes_the_unified_six_year_warm_water_path() -> None:
    source_identity = GuardSourceIdentity(source_type="meter", source_id="12-F05")
    result = evaluate_meter_calibration(
        MeterCalibrationInput(
            source_identity=source_identity,
            today=date(2025, 8, 1),
            calibration_date=date(2020, 6, 1),
            medium="warm_water",
            unit_label="WE 1",
        ),
        W2_RULES,
    )

    _assert_common_result(
        result,
        guard_code="W2",
        source_identity=source_identity,
        evidence=W2_EVIDENCE,
    )
    # Page 05 prints 5 years, 31.12.2025 and the Hinweis stage for these inputs. The
    # unified six-year MessEV period moves the boundary a year out, so the case falls
    # outside the <= 6 months notice window and the guard is silent.
    assert result.stage == "none"
    assert not result.active
    assert result.validity_years == 6
    assert result.boundary_date == date(2026, 12, 31)
    assert result.months_until_expiry == 16
    assert result.escalation_channels == ()
    assert result.warning_de is None
    assert W2_CONFLICT in result.unresolved_conflicts
    assert result.production_blockers == ()


def test_12_f06_executes_missing_calibration_date_without_calculation() -> None:
    source_identity = GuardSourceIdentity(source_type="meter", source_id="12-F06")
    result = evaluate_meter_calibration(
        MeterCalibrationInput(
            source_identity=source_identity,
            today=date(2025, 8, 1),
            calibration_date=None,
            medium="warm_water",
            unit_label="WE 1",
        ),
        W2_RULES,
    )

    _assert_common_result(
        result,
        guard_code="W2",
        source_identity=source_identity,
        evidence=W2_EVIDENCE,
    )
    assert result.stage == "missing_calibration_date"
    assert result.boundary_date is None
    assert result.months_until_expiry is None
    assert result.warning_de == "Eichdatum erfassen"
    assert result.unresolved_conflicts == ()
    assert result.production_blockers == ()


def test_w2_expiry_month_ordering_and_heating_cost_allocator_exclusion() -> None:
    expiry_month = evaluate_meter_calibration(
        MeterCalibrationInput(
            source_identity=GuardSourceIdentity(source_type="meter", source_id="expiry-month"),
            today=date(2026, 12, 1),
            calibration_date=date(2020, 6, 1),
            medium="warm_water",
            unit_label="WE 1",
        ),
        W2_RULES,
    )
    exceeded = evaluate_meter_calibration(
        MeterCalibrationInput(
            source_identity=GuardSourceIdentity(source_type="meter", source_id="exceeded"),
            today=date(2027, 1, 1),
            calibration_date=date(2020, 6, 1),
            medium="warm_water",
            unit_label="WE 1",
        ),
        W2_RULES,
    )
    excluded = evaluate_meter_calibration(
        MeterCalibrationInput(
            source_identity=GuardSourceIdentity(source_type="meter", source_id="allocator"),
            today=date(2025, 8, 1),
            calibration_date=date(2020, 6, 1),
            medium="heating_cost_allocator",
            unit_label="WE 1",
        ),
        W2_RULES,
    )

    assert expiry_month.months_until_expiry == 0
    assert expiry_month.stage == "expiry_month"
    assert expiry_month.escalation_channels == ("in_app", "email")
    assert exceeded.months_until_expiry == -1
    assert exceeded.stage == "exceeded"
    assert exceeded.escalation_channels == ("email",)
    assert excluded.stage == "excluded"
    assert not excluded.active
    assert excluded.boundary_date is None
    assert excluded.warning_de is None
    assert excluded.unresolved_conflicts == ()
    assert excluded.production_blockers == ()


@pytest.mark.parametrize(
    ("medium", "validity_years", "has_transition_conflict"),
    (
        ("cold_water", 6, False),
        ("warm_water", 6, True),
        ("heat_meter", 6, True),
        ("heat_exchanger_hot_water", 6, True),
        ("electricity", 8, False),
        ("gas", 8, False),
    ),
)
def test_w2_uses_the_complete_caller_supplied_registered_year_table(
    medium: str, validity_years: int, has_transition_conflict: bool
) -> None:
    result = evaluate_meter_calibration(
        MeterCalibrationInput(
            source_identity=GuardSourceIdentity(
                source_type="meter", source_id=f"registered-years-{medium}"
            ),
            today=date(2020, 1, 1),
            calibration_date=date(2020, 6, 1),
            medium=medium,
            unit_label="WE 1",
        ),
        W2_RULES,
    )

    assert result.validity_years == validity_years
    assert result.boundary_date == date(2020 + validity_years, 12, 31)
    if has_transition_conflict:
        assert result.unresolved_conflicts == (W2_CONFLICT,)
    else:
        assert result.unresolved_conflicts == ()
    # The transition uncertainty is labelled, not production-blocking.
    assert result.production_blockers == ()


@pytest.mark.parametrize(
    (
        "fixture_id",
        "remote_readable",
        "last_sent",
        "start_month",
        "today",
        "stage",
        "boundary",
    ),
    (
        (
            "12-F11",
            True,
            date(2026, 5, 31),
            None,
            date(2026, 7, 5),
            "overdue",
            date(2026, 6, 30),
        ),
        (
            "12-F12",
            False,
            None,
            None,
            date(2026, 7, 5),
            "retrofit_notice",
            date(2026, 12, 31),
        ),
        (
            "12-F13",
            True,
            None,
            date(2026, 5, 1),
            date(2026, 6, 3),
            "not_due",
            date(2026, 6, 30),
        ),
    ),
)
def test_12_f11_through_12_f13_execute_w4(
    fixture_id: str,
    remote_readable: bool,
    last_sent: date | None,
    start_month: date | None,
    today: date,
    stage: str,
    boundary: date,
) -> None:
    source_identity = GuardSourceIdentity(source_type="renter_unit", source_id=fixture_id)
    result = evaluate_uvi_cadence(
        UviCadenceInput(
            source_identity=source_identity,
            today=today,
            remote_readable=remote_readable,
            last_uvi_sent_on=last_sent,
            start_month=start_month,
            uvi_sent_in_current_month=False,
            unit_label="WE 1",
        ),
        W4_RULES,
    )

    _assert_common_result(
        result,
        guard_code="W4",
        source_identity=source_identity,
        evidence=W4_EVIDENCE,
    )
    assert result.stage == stage
    assert result.boundary_date == boundary
    if fixture_id == "12-F11":
        assert result.active
        assert result.uvi_guard_active
        assert result.escalation_channels == ("email",)
        assert result.warning_de is not None
        assert "monatliche Verbrauchsinformation" in result.warning_de
    elif fixture_id == "12-F12":
        assert not result.uvi_guard_active
        assert result.retrofit_notice_active
        assert result.warning_de == "Nachrüstpflicht fernablesbar bis 31.12.2026"
    else:
        assert not result.active
        assert result.uvi_guard_active
        assert not result.retrofit_notice_active


def test_w4_after_retrofit_deadline_preserves_missing_source_behavior() -> None:
    result = evaluate_uvi_cadence(
        UviCadenceInput(
            source_identity=GuardSourceIdentity(
                source_type="renter_unit", source_id="post-retrofit-gap"
            ),
            today=date(2027, 1, 1),
            remote_readable=False,
            last_uvi_sent_on=None,
            start_month=None,
            uvi_sent_in_current_month=False,
            unit_label="WE 1",
        ),
        W4_RULES,
    )

    assert result.stage == "source_missing"
    assert not result.active
    assert not result.uvi_guard_active
    assert not result.retrofit_notice_active
    assert result.warning_de is None
    assert "missing_post_retrofit_rule" in result.production_blockers
