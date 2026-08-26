"""Executable M9 contract for the remaining Page-05 guard fixtures.

The approved, data-only oracle lives in ``berkay_12_golden.py``.  These tests
exercise the same values through the public pure-engine boundary.  They are
intentionally red until the W3 and W5-W8 public inputs, rule bundles, snapshots,
results, and evaluators exist.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import lokara_guard_engine as guard_engine

PAGE_05_SOURCE = "berkay-work/Spec-Seiten/05 · Wächter Fristen 3a95fd42073181038246e579777508f9.md"
REGISTER_SOURCE = "berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv"
M9_FIXTURE_IDS = {
    "12-F07",
    "12-F08",
    "12-F09",
    "12-F10",
    "12-F14",
    "12-F15",
    "12-F16",
    "12-F17",
    "12-F18",
    "12-F19",
    "12-F20",
    "12-F21",
    "12-F22",
    "12-F23",
    "12-F24",
}

REQUIRED_PUBLIC_API = {
    "ComparativeRentIncreaseInput",
    "ComparativeRentIncreaseRuleBundle",
    "GraduatedRentInput",
    "GraduatedRentRuleBundle",
    "GraduatedRentStep",
    "IndexRentInput",
    "IndexRentRuleBundle",
    "PaymentArrearsInput",
    "PaymentArrearsRuleBundle",
    "PaymentDueEntry",
    "PaymentEntry",
    "VacancyInput",
    "VacancyRuleBundle",
    "VpiSnapshot",
    "evaluate_comparative_rent_increase",
    "evaluate_graduated_rent",
    "evaluate_index_rent",
    "evaluate_payment_arrears",
    "evaluate_vacancy",
}


def _api(name: str) -> Any:
    return getattr(guard_engine, name)


def _evidence(
    register_row: str, legal_basis: str, *, rechtsstand: str = "07/2026"
) -> tuple[Any, ...]:
    return (
        guard_engine.RuleEvidence(
            source=PAGE_05_SOURCE,
            register_row="Page 05",
            legal_basis=legal_basis,
            rechtsstand=rechtsstand,
            verification_status="verify-before-production",
        ),
        guard_engine.RuleEvidence(
            source=REGISTER_SOURCE,
            register_row=register_row,
            legal_basis=legal_basis,
            rechtsstand=rechtsstand,
            verification_status="verify-before-production",
        ),
    )


def _blocking_conflict(code: str, description: str) -> Any:
    return guard_engine.RuleConflict(
        code=code,
        description=description,
        production_blocking=True,
    )


W3_EVIDENCE = _evidence("121,124,125,127", "§§ 543 Abs. 2 Nr. 3, 569 Abs. 3 BGB")
W3_BLOCK = _blocking_conflict(
    "W3-VERIFY-BEFORE-PRODUCTION",
    "The W3 tenancy-law rows require primary-source/legal verification before production.",
)

W5_EVIDENCE = _evidence("116,119,120,122,123,126,132", "§§ 558, 558b BGB")
W5_BLOCK = _blocking_conflict(
    "W5-VERIFY-BEFORE-PRODUCTION",
    "The W5 tenancy-law values and calendar reading require verification before production.",
)
W5_MARKET_BLOCK = _blocking_conflict(
    "W5-TIGHT-MARKET-LIST-MISSING",
    "No state regulation list is supplied; tight_market must remain caller supplied.",
)

W6_EVIDENCE = _evidence("130", "§ 557a Abs. 1–2 BGB")
W6_BLOCK = _blocking_conflict(
    "W6-VERIFY-BEFORE-PRODUCTION",
    "The W6 tenancy-law row requires primary-source/legal verification before production.",
)

W7_EVIDENCE = _evidence("131,132,133", "§ 557b BGB; KONVENTION-VPI")
W7_BLOCK = _blocking_conflict(
    "W7-VERIFY-BEFORE-PRODUCTION",
    "The W7 tenancy-law values require primary-source/legal verification before production.",
)
W7_METHOD_BLOCK = _blocking_conflict(
    "W7-PROPORTIONAL-METHOD-UNCERTAIN",
    "The proportional VPI method remains a convention and is not production-approved.",
)
W7_PROVIDER_BLOCK = _blocking_conflict(
    "W7-REAL-DESTatis-PROVIDER-MISSING",
    "The deterministic snapshot is test/demo data; no real GENESIS provider is selected.",
)

W8_EVIDENCE = _evidence("118", "KONVENTION-L1/L2; product heuristic")
W8_BLOCK = _blocking_conflict(
    "W8-VERIFY-BEFORE-PRODUCTION",
    "The vacancy threshold and lost-rent framing are a non-legal product heuristic.",
)


def _source(source_type: str, fixture_id: str) -> Any:
    return guard_engine.GuardSourceIdentity(source_type=source_type, source_id=fixture_id)


def _w3_rules() -> Any:
    return _api("PaymentArrearsRuleBundle")(
        evidence=W3_EVIDENCE,
        unresolved_conflicts=(W3_BLOCK,),
        warning_3a_de=(
            "Der Mietrückstand von {renter_label} beträgt {arrears} € und übersteigt eine "
            "Monatsmiete bei zwei aufeinanderfolgenden offenen Terminen — die Schwelle für "
            "eine fristlose Kündigung wegen Zahlungsverzugs (§ 543 Abs. 2 Nr. 3a BGB) ist "
            "erreicht. Hinweis: Eine Schonfristzahlung (§ 569 Abs. 3 Nr. 2 BGB) kann die "
            "Kündigung heilen."
        ),
        channels_by_stage={"info": ("in_app",), "3a": ("email",), "3b": ("push",)},
        resolution_event="payment_received",
    )


def _due_entries() -> tuple[Any, ...]:
    entry = _api("PaymentDueEntry")
    return (
        entry(due_date=date(2026, 1, 3), amount_cents=85_000),
        entry(due_date=date(2026, 2, 3), amount_cents=85_000),
        entry(due_date=date(2026, 3, 3), amount_cents=85_000),
    )


def _w3_result(fixture_id: str, *, due_count: int, payments: tuple[int, ...]) -> Any:
    payment = _api("PaymentEntry")
    return _api("evaluate_payment_arrears")(
        _api("PaymentArrearsInput")(
            source_identity=_source("renter_ledger", fixture_id),
            today=date(2026, 3, 31),
            gross_monthly_rent_cents=85_000,
            due_entries=_due_entries()[:due_count],
            payments=tuple(
                payment(payment_date=date(2026, 3, 20 + index), amount_cents=amount)
                for index, amount in enumerate(payments)
            ),
            renter_label="Mieter A",
        ),
        _w3_rules(),
    )


def _w5_rules() -> Any:
    return _api("ComparativeRentIncreaseRuleBundle")(
        evidence=W5_EVIDENCE,
        unresolved_conflicts=(W5_BLOCK, W5_MARKET_BLOCK),
        normal_cap_rate=Decimal("0.20"),
        tight_market_cap_rate=Decimal("0.15"),
        declaration_wait_months=12,
        effective_wait_months=15,
        consent_months=2,
        effective_after_request_months=3,
        action_months_after_consent_deadline=3,
        warning_full_check_de=(
            "Sie können die Miete für {unit_label} um bis zu {maximum_increase} € auf "
            "{maximum_new_rent} € erhöhen (§ 558 BGB). Begrenzt durch {limiting_rule}."
        ),
        warning_cap_only_de=(
            "Die Kappungsgrenze erlaubt für {unit_label} bis zu {maximum_new_rent} € "
            "(+{maximum_increase} €). Prüfen Sie zusätzlich selbst die ortsübliche "
            "Vergleichsmiete — die Erhöhung nach § 558 darf sie nicht übersteigen."
        ),
        channels_by_stage={"opportunity": ("in_app",), "action_deadline": ("in_app", "email")},
        resolution_event="rent_increase_consented",
    )


def _w5_result(
    fixture_id: str,
    *,
    today: date,
    net_cold_rent_cents: int = 80_000,
    base_rent_3y_cents: int = 80_000,
    comparative_rent_cents: int | None = 100_000,
    tight_market: bool = False,
    last_increase_effective_on: date = date(2025, 1, 1),
    request_received_on: date | None = None,
) -> Any:
    return _api("evaluate_comparative_rent_increase")(
        _api("ComparativeRentIncreaseInput")(
            source_identity=_source("tenancy", fixture_id),
            today=today,
            net_cold_rent_cents=net_cold_rent_cents,
            base_rent_3y_cents=base_rent_3y_cents,
            last_increase_effective_on=last_increase_effective_on,
            comparative_rent_cents=comparative_rent_cents,
            tight_market=tight_market,
            request_received_on=request_received_on,
            unit_label="WE 1",
        ),
        _w5_rules(),
    )


def _w6_rules() -> Any:
    return _api("GraduatedRentRuleBundle")(
        evidence=W6_EVIDENCE,
        unresolved_conflicts=(W6_BLOCK,),
        minimum_interval_months=12,
        warning_de="Neue Mietstaffel für {unit_label} ab {step_effective_on}: {amount} €.",
        channels_by_stage={"adjustment_due": ("in_app",)},
        resolution_event="target_rent_updated",
    )


def _snapshot(*, value: str, basis_year: int, reference_month: date) -> Any:
    return _api("VpiSnapshot")(
        value=Decimal(value),
        basis_year=basis_year,
        reference_month=reference_month,
        status="final",
        source="GENESIS 61111 deterministic test stub",
        captured_at=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
    )


def _w7_rules() -> Any:
    return _api("IndexRentRuleBundle")(
        evidence=W7_EVIDENCE,
        unresolved_conflicts=(W7_BLOCK, W7_METHOD_BLOCK, W7_PROVIDER_BLOCK),
        minimum_interval_months=12,
        rebasing_warning_de="Index umrechnen (Umbasierung)",
        warning_de=(
            "VPI von {base_index} auf {new_index} (+{delta_percent} %) → mögliche neue "
            "Miete {new_rent} € (+{increase} €)."
        ),
        channels_by_stage={"opportunity": ("in_app",)},
        resolution_event="index_adjustment_effective",
    )


def _w7_result(
    fixture_id: str,
    *,
    today: date = date(2026, 3, 1),
    last_adjustment_on: date = date(2025, 3, 1),
    base_value: str = "118.0",
    new_value: str = "122.3",
    base_year: int = 2020,
    new_basis_year: int = 2020,
) -> Any:
    return _api("evaluate_index_rent")(
        _api("IndexRentInput")(
            source_identity=_source("tenancy", fixture_id),
            today=today,
            net_cold_rent_cents=80_000,
            base_index=_snapshot(
                value=base_value,
                basis_year=base_year,
                reference_month=date(2025, 3, 1),
            ),
            new_index=_snapshot(
                value=new_value,
                basis_year=new_basis_year,
                reference_month=date(2026, 2, 1),
            ),
            last_adjustment_on=last_adjustment_on,
        ),
        _w7_rules(),
    )


def _w8_rules() -> Any:
    return _api("VacancyRuleBundle")(
        evidence=W8_EVIDENCE,
        unresolved_conflicts=(W8_BLOCK,),
        threshold_days=30,
        rent_period_days=30,
        warning_de=(
            "{unit_label} steht seit {vacancy_days} Tagen leer — ca. {lost_rent} € "
            "entgangene Miete."
        ),
        channels_by_stage={"vacancy": ("in_app",)},
        resolution_event="active_tenancy_started",
    )


def _assert_common(
    result: Any,
    guard_code: str,
    source_identity: Any,
    evidence: tuple[Any, ...],
) -> None:
    assert result.guard_code == guard_code
    assert result.source_identity == source_identity
    assert isinstance(result.stage, str)
    assert isinstance(result.active, bool)
    assert isinstance(result.resolved, bool)
    assert result.warning_de is None or isinstance(result.warning_de, str)
    assert isinstance(result.escalation_channels, tuple)
    assert result.boundary_date is None or isinstance(result.boundary_date, date)
    assert result.rule_evidence == evidence
    assert isinstance(result.production_blockers, tuple)


def test_m9_fixture_and_public_surface_is_complete() -> None:
    assert len(M9_FIXTURE_IDS) == 15
    missing = sorted(name for name in REQUIRED_PUBLIC_API if not hasattr(guard_engine, name))
    assert missing == [], f"missing M9 guard-engine public API: {', '.join(missing)}"


def test_12_f07_and_f08_enforce_the_strict_w3_3a_threshold() -> None:
    f07 = _w3_result("12-F07", due_count=2, payments=())
    f08 = _w3_result("12-F08", due_count=1, payments=())

    _assert_common(f07, "W3", _source("renter_ledger", "12-F07"), W3_EVIDENCE)
    assert (f07.arrears_cents, f07.consecutive_open_dates) == (170_000, 2)
    assert (f07.threshold_3a_cents, f07.threshold_3b_cents) == (85_000, 170_000)
    assert f07.stage == "3a"
    assert f07.triggers_3a and not f07.triggers_3b
    assert f07.escalation_channels == ("email",)
    assert f07.warning_de is not None and "Schonfristzahlung" in f07.warning_de
    assert W3_BLOCK.code in f07.production_blockers

    assert f08.arrears_cents == 85_000
    assert f08.stage == "info"
    assert not f08.triggers_3a


def test_12_f09_and_f10_trigger_3b_then_downgrade_to_3a_without_resolution() -> None:
    f09 = _w3_result("12-F09", due_count=3, payments=(20_000,))
    f10 = _w3_result("12-F10", due_count=3, payments=(20_000, 100_000))

    assert (f09.arrears_cents, f09.consecutive_open_dates, f09.stage) == (235_000, 3, "3b")
    assert f09.triggers_3b
    assert f09.escalation_channels == ("push",)
    assert (f10.arrears_cents, f10.consecutive_open_dates, f10.stage) == (135_000, 2, "3a")
    assert f10.triggers_3a and not f10.triggers_3b
    assert not f10.resolved
    assert f10.resolution_event == "payment_received"


def test_12_f14_and_f15_apply_normal_and_tight_caps_and_the_lower_ceiling() -> None:
    f14 = _w5_result("12-F14", today=date(2026, 1, 1))
    f15 = _w5_result(
        "12-F15",
        today=date(2026, 1, 1),
        comparative_rent_cents=88_000,
        tight_market=True,
    )

    _assert_common(f14, "W5", _source("tenancy", "12-F14"), W5_EVIDENCE)
    assert (f14.cap_rate, f14.cap_ceiling_cents) == (Decimal("0.20"), 96_000)
    assert (f14.maximum_new_rent_cents, f14.maximum_increase_cents) == (96_000, 16_000)
    assert (f14.mode, f14.limiting_rule) == ("full_check", "cap")
    assert W5_BLOCK.code in f14.production_blockers
    assert W5_MARKET_BLOCK.code in f14.production_blockers

    assert (f15.cap_rate, f15.cap_ceiling_cents) == (Decimal("0.15"), 92_000)
    assert (f15.maximum_new_rent_cents, f15.maximum_increase_cents) == (88_000, 8_000)
    assert (f15.mode, f15.limiting_rule) == ("full_check", "comparative_rent")


def test_12_f16_preserves_declaration_and_effective_waiting_periods() -> None:
    result = _w5_result(
        "12-F16",
        today=date(2026, 1, 1),
        last_increase_effective_on=date(2025, 3, 1),
    )

    assert result.earliest_declaration_on == date(2026, 3, 1)
    assert result.earliest_effective_on == date(2026, 6, 1)
    assert not result.active


def test_12_f17_uses_calendar_month_end_for_consent_effect_and_action_dates() -> None:
    result = _w5_result(
        "12-F17",
        today=date(2026, 4, 10),
        request_received_on=date(2026, 4, 10),
    )

    assert result.consent_deadline == date(2026, 6, 30)
    assert result.effective_on == date(2026, 7, 1)
    assert result.action_deadline == date(2026, 9, 30)


def test_12_f23_missing_comparative_rent_is_cap_only_and_never_confirms_legality() -> None:
    result = _w5_result(
        "12-F23",
        today=date(2026, 1, 1),
        comparative_rent_cents=None,
    )

    assert (result.maximum_new_rent_cents, result.maximum_increase_cents) == (96_000, 16_000)
    assert result.mode == "cap_only"
    assert not result.legality_confirmed
    assert result.warning_de is not None and "Vergleichsmiete" in result.warning_de


def test_12_f24_clamps_an_above_ceiling_current_rent_to_zero_increase() -> None:
    result = _w5_result(
        "12-F24",
        today=date(2026, 1, 1),
        net_cold_rent_cents=95_000,
        comparative_rent_cents=90_000,
    )

    assert result.maximum_new_rent_cents == 90_000
    assert result.maximum_increase_cents == 0
    assert not result.active


def test_12_f18_selects_the_active_graduated_rent_step() -> None:
    step = _api("GraduatedRentStep")
    source_identity = _source("tenancy", "12-F18")
    result = _api("evaluate_graduated_rent")(
        _api("GraduatedRentInput")(
            source_identity=source_identity,
            today=date(2026, 1, 5),
            schedule=(
                step(effective_on=date(2025, 1, 1), amount_cents=90_000),
                step(effective_on=date(2026, 1, 1), amount_cents=95_000),
                step(effective_on=date(2027, 1, 1), amount_cents=100_000),
            ),
            current_target_rent_cents=90_000,
            unit_label="WE 1",
        ),
        _w6_rules(),
    )

    _assert_common(result, "W6", source_identity, W6_EVIDENCE)
    assert result.valid
    assert result.validation_errors == ()
    assert result.active_step_cents == 95_000
    assert result.adjustment_due
    assert result.boundary_date == date(2026, 1, 1)
    assert W6_BLOCK.code in result.production_blockers


def test_12_f19_rejects_a_graduated_rent_interval_below_twelve_months() -> None:
    step = _api("GraduatedRentStep")
    result = _api("evaluate_graduated_rent")(
        _api("GraduatedRentInput")(
            source_identity=_source("tenancy", "12-F19"),
            today=date(2026, 3, 1),
            schedule=(
                step(effective_on=date(2025, 6, 1), amount_cents=90_000),
                step(effective_on=date(2026, 3, 1), amount_cents=95_000),
            ),
            current_target_rent_cents=90_000,
            unit_label="WE 1",
        ),
        _w6_rules(),
    )

    assert not result.valid
    assert result.stage == "invalid"
    assert result.validation_errors == ("schedule_interval_below_12_months",)
    assert not result.adjustment_due


def test_12_f20_uses_decimal_half_up_money_and_preserves_snapshot_provenance() -> None:
    result = _w7_result("12-F20")

    _assert_common(result, "W7", _source("tenancy", "12-F20"), W7_EVIDENCE)
    assert result.factor == Decimal("122.3") / Decimal("118.0")
    assert result.new_rent_cents == 82_915
    assert result.increase_cents == 2_915
    assert result.delta_percent_display == Decimal("3.64")
    assert result.active
    assert result.base_index.source == "GENESIS 61111 deterministic test stub"
    assert result.new_index.status == "final"
    assert W7_METHOD_BLOCK.code in result.production_blockers
    assert W7_PROVIDER_BLOCK.code in result.production_blockers


def test_12_f21_is_inactive_before_the_twelve_month_index_interval() -> None:
    result = _w7_result(
        "12-F21",
        today=date(2026, 3, 1),
        last_adjustment_on=date(2025, 9, 1),
    )

    assert result.elapsed_months == 6
    assert result.stage == "waiting_period"
    assert not result.active


def test_w7_basis_year_mismatch_blocks_money_and_requests_rebasing() -> None:
    result = _w7_result("w7-basis-year-mismatch", new_basis_year=2015)

    assert result.stage == "basis_year_mismatch"
    assert result.new_rent_cents is None
    assert result.increase_cents is None
    assert not result.active
    assert result.warning_de == "Index umrechnen (Umbasierung)"
    assert "basis_year_mismatch" in result.production_blockers


def test_w7_deflation_and_equality_produce_no_increase() -> None:
    for fixture_id, new_value in (("w7-deflation", "117.9"), ("w7-equality", "118.0")):
        result = _w7_result(fixture_id, new_value=new_value)
        assert result.stage == "no_increase"
        assert result.new_rent_cents is None
        assert result.increase_cents == 0
        assert not result.active
        assert result.warning_de is None


def test_12_f22_counts_fifty_days_and_rounds_lost_rent_half_up() -> None:
    source_identity = _source("unit", "12-F22")
    result = _api("evaluate_vacancy")(
        _api("VacancyInput")(
            source_identity=source_identity,
            today=date(2026, 7, 20),
            last_tenancy_ended_on=date(2026, 5, 31),
            active_tenancy=False,
            target_rent_cents=90_000,
            unit_label="WE 1",
        ),
        _w8_rules(),
    )

    _assert_common(result, "W8", source_identity, W8_EVIDENCE)
    assert result.vacancy_days == 50
    assert result.lost_rent_cents == 150_000
    assert result.active
    assert result.stage == "vacancy"
    assert result.escalation_channels == ("in_app",)
    assert W8_BLOCK.code in result.production_blockers


def test_w8_active_tenancy_suppresses_vacancy_and_money_framing() -> None:
    result = _api("evaluate_vacancy")(
        _api("VacancyInput")(
            source_identity=_source("unit", "w8-active-tenancy"),
            today=date(2026, 7, 20),
            last_tenancy_ended_on=date(2026, 5, 31),
            active_tenancy=True,
            target_rent_cents=90_000,
            unit_label="WE 1",
        ),
        _w8_rules(),
    )

    assert result.stage == "active_tenancy"
    assert result.vacancy_days is None
    assert result.lost_rent_cents is None
    assert not result.active
    assert result.warning_de is None
