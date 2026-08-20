"""Coverage and arithmetic checks for the data-only Page 05 oracle."""

from calendar import monthrange
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from berkay_12_golden import (
    CORRESPONDENCE_RETIREMENT_FILES,
    PAGE_05_GOLDENS,
    PAGE_05_NON_GOALS,
    PAGE_05_REGISTER_FLAGS,
    PAGE_05_REGISTER_ROWS,
    PAGE_05_SHARED_REGISTER_FLAGS,
    PAGE_05_SHARED_REGISTER_ROWS,
    PAGE_05_SOURCE_SECTIONS,
)

EXPECTED_IDS = {f"12-F{number:02}" for number in range(1, 25)}


def _case(case_id: str) -> dict[str, object]:
    return PAGE_05_GOLDENS[case_id]


def _int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int)
    return value


def _ints(case: dict[str, object], key: str) -> tuple[int, ...]:
    value = case[key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) for item in value)
    return value


def _bool(case: dict[str, object], key: str) -> bool:
    value = case[key]
    assert isinstance(value, bool)
    return value


def _text(case: dict[str, object], key: str) -> str:
    value = case[key]
    assert isinstance(value, str)
    return value


def _date(value: object) -> date:
    assert isinstance(value, str)
    return date.fromisoformat(value)


def _month_add(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _money_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def test_fixture_surface_is_exactly_12_f01_through_12_f24() -> None:
    assert set(PAGE_05_GOLDENS) == EXPECTED_IDS


def test_complete_source_register_non_goal_and_correspondence_surfaces() -> None:
    assert len(PAGE_05_SOURCE_SECTIONS) == 8
    assert len(set(PAGE_05_SOURCE_SECTIONS)) == 8
    assert len(PAGE_05_REGISTER_ROWS) == 18
    assert len(set(PAGE_05_REGISTER_ROWS)) == 18
    assert set(PAGE_05_REGISTER_FLAGS) == set(PAGE_05_REGISTER_ROWS)
    assert set(PAGE_05_REGISTER_FLAGS.values()) == {"verify-before-production"}
    assert len(PAGE_05_SHARED_REGISTER_ROWS) == 6
    assert len(set(PAGE_05_SHARED_REGISTER_ROWS)) == 6
    assert set(PAGE_05_SHARED_REGISTER_FLAGS) == set(PAGE_05_SHARED_REGISTER_ROWS)
    assert tuple(PAGE_05_SHARED_REGISTER_FLAGS.values()).count("geprüft") == 5
    assert tuple(PAGE_05_SHARED_REGISTER_FLAGS.values()).count("verify-before-production") == 1
    assert set(PAGE_05_REGISTER_ROWS).isdisjoint(PAGE_05_SHARED_REGISTER_ROWS)
    assert len(PAGE_05_NON_GOALS) == 10
    assert len(set(PAGE_05_NON_GOALS)) == 10
    assert len(CORRESPONDENCE_RETIREMENT_FILES) == 7
    assert len(set(CORRESPONDENCE_RETIREMENT_FILES)) == 7


def test_w1_date_arithmetic_and_deadline_states() -> None:
    normal = _case("12-F01")
    assert _month_add(_date(normal["period_end"]), 12) == _date(normal["deadline"])
    assert (_date(normal["deadline"]) - _date(normal["today"])).days == _int(
        normal, "days_until_deadline"
    )

    leap = _case("12-F02")
    assert _month_add(_date(leap["period_end"]), 12) == _date(leap["deadline"])
    assert (_date(leap["deadline"]) - _date(leap["today"])).days == _int(
        leap, "days_until_deadline"
    )

    expired = _case("12-F03")
    assert (_date(expired["deadline"]) - _date(expired["today"])).days == _int(
        expired, "days_until_deadline"
    )
    assert expired["stage"] == "expired"
    assert _bool(expired, "credit_remains_payable")

    resolved = _case("12-F04")
    assert _date(resolved["delivered_on"]) <= _date(resolved["deadline"])
    assert _month_add(_date(resolved["delivered_on"]), 12) == _date(
        resolved["renter_objection_deadline"]
    )
    assert _bool(resolved, "resolved")


def test_w2_keeps_the_meter_conflict_visible_and_missing_date_uncomputed() -> None:
    case = _case("12-F05")
    assert _int(case, "page_05_years") == 5
    assert _int(case, "conflicting_meter_spec_years") == 6
    assert _date(case["valid_until"]) == date(2025, 12, 31)
    assert _int(case, "months_until_expiry") == 4
    assert _bool(case, "production_blocked")

    missing = _case("12-F06")
    assert missing["calibration_date"] is None
    assert missing["calculation"] is None
    assert missing["warning_de"] == "Eichdatum erfassen"


def test_w3_arrears_thresholds_are_strict_and_f10_is_only_a_downgrade() -> None:
    two_dates = _case("12-F07")
    assert sum(_ints(two_dates, "open_installments_cents")) - sum(
        _ints(two_dates, "payments_cents")
    ) == _int(two_dates, "arrears_cents")
    assert _int(two_dates, "arrears_cents") > _int(two_dates, "threshold_3a_cents")
    assert _int(two_dates, "consecutive_open_dates") == 2
    assert _bool(two_dates, "triggers_3a")
    assert not _bool(two_dates, "triggers_3b")

    exact = _case("12-F08")
    assert _int(exact, "arrears_cents") == _int(exact, "threshold_3a_cents")
    assert not _bool(exact, "triggers_3a")

    three_dates = _case("12-F09")
    assert sum(_ints(three_dates, "open_installments_cents")) - sum(
        _ints(three_dates, "payments_cents")
    ) == _int(three_dates, "arrears_cents")
    assert _int(three_dates, "consecutive_open_dates") > 2
    assert _int(three_dates, "arrears_cents") >= _int(three_dates, "threshold_3b_cents")
    assert _bool(three_dates, "triggers_3b")

    downgrade = _case("12-F10")
    assert _int(downgrade, "arrears_before_cents") - _int(downgrade, "payment_cents") == _int(
        downgrade, "arrears_after_cents"
    )
    assert _int(downgrade, "arrears_after_cents") < _int(downgrade, "threshold_3b_cents")
    assert _int(downgrade, "arrears_after_cents") > _int(downgrade, "threshold_3a_cents")
    assert downgrade["stage_after"] == "3a"
    assert downgrade["disposition"] == "downgrade_3b_to_3a"
    assert not _bool(downgrade, "resolved")


def test_w4_monthly_uvi_cadence_and_remote_readability_gate() -> None:
    overdue = _case("12-F11")
    last_sent = _date(overdue["last_uvi_sent_on"])
    next_month = _month_add(last_sent, 1)
    due = date(next_month.year, next_month.month, monthrange(next_month.year, next_month.month)[1])
    assert due == _date(overdue["due_on"])
    assert _date(overdue["today"]) >= due
    assert overdue["stage"] == "overdue"

    retrofit = _case("12-F12")
    assert not _bool(retrofit, "uvi_guard_active")
    assert _bool(retrofit, "retrofit_notice_active")

    first = _case("12-F13")
    assert _date(first["today"]) < _date(first["due_on"])
    assert first["stage"] == "not_due"


def test_w5_rent_limits_round_in_cents_and_preserve_cap_only_mode() -> None:
    normal = _case("12-F14")
    expected_cap = _money_half_up(
        Decimal(_int(normal, "base_rent_3y_cents")) * (Decimal("1") + Decimal("0.20"))
    )
    assert expected_cap == _int(normal, "cap_ceiling_cents")
    assert min(expected_cap, _int(normal, "comparative_rent_cents")) == _int(
        normal, "maximum_new_rent_cents"
    )
    assert _int(normal, "maximum_new_rent_cents") - _int(normal, "net_cold_rent_cents") == _int(
        normal, "maximum_increase_cents"
    )

    tight = _case("12-F15")
    tight_cap = _money_half_up(
        Decimal(_int(tight, "base_rent_3y_cents")) * (Decimal("1") + Decimal("0.15"))
    )
    assert tight_cap == _int(tight, "cap_ceiling_cents")
    assert min(tight_cap, _int(tight, "comparative_rent_cents")) == _int(
        tight, "maximum_new_rent_cents"
    )

    cap_only = _case("12-F23")
    assert cap_only["comparative_rent_cents"] is None
    assert cap_only["mode"] == "cap_only"
    assert not _bool(cap_only, "legality_confirmed")

    no_increase = _case("12-F24")
    assert max(
        0,
        _int(no_increase, "maximum_new_rent_cents") - _int(no_increase, "net_cold_rent_cents"),
    ) == _int(no_increase, "maximum_increase_cents")
    assert not _bool(no_increase, "active")


def test_w5_calendar_chain_and_w6_staffel_intervals() -> None:
    blocked = _case("12-F16")
    assert _month_add(_date(blocked["last_increase_effective_on"]), 12) == _date(
        blocked["earliest_declaration_on"]
    )
    assert _month_add(_date(blocked["last_increase_effective_on"]), 15) == _date(
        blocked["earliest_effective_on"]
    )
    assert not _bool(blocked, "active")

    chain = _case("12-F17")
    received = _date(chain["request_received_on"])
    consent_month = _month_add(received, 2)
    assert date(
        consent_month.year,
        consent_month.month,
        monthrange(consent_month.year, consent_month.month)[1],
    ) == _date(chain["consent_deadline"])
    effective_month = _month_add(received, 3)
    assert date(effective_month.year, effective_month.month, 1) == _date(chain["effective_on"])
    assert _month_add(_date(chain["consent_deadline"]), 3) == _date(chain["action_deadline"])

    staffel = _case("12-F18")
    schedule = staffel["schedule"]
    assert isinstance(schedule, tuple)
    assert schedule[1][1] == _int(staffel, "active_step_cents")
    assert _bool(staffel, "adjustment_due")
    assert _bool(staffel, "valid")

    invalid = _case("12-F19")
    assert _int(invalid, "interval_months") < _int(invalid, "minimum_interval_months")
    assert _bool(invalid, "validation_error")


def test_w7_vpi_proportional_rounding_and_minimum_interval() -> None:
    case = _case("12-F20")
    factor = Decimal(_text(case, "new_index")) / Decimal(_text(case, "base_index"))
    assert factor == Decimal(_text(case, "factor"))
    unrounded = Decimal(_int(case, "net_cold_rent_cents")) * factor
    assert unrounded == Decimal(_text(case, "unrounded_new_rent_cents"))
    assert _money_half_up(unrounded) == _int(case, "new_rent_cents")
    assert _int(case, "new_rent_cents") - _int(case, "net_cold_rent_cents") == _int(
        case, "increase_cents"
    )
    assert _bool(case, "active")
    assert Decimal(_text(case, "deflation_index")) <= Decimal(_text(case, "base_index"))
    assert not _bool(case, "deflation_active")
    assert _int(case, "mismatched_basis_year") != _int(case, "base_year")
    assert case["mismatched_basis_calculation"] is None
    assert case["mismatched_basis_warning_de"] == "Index umrechnen (Umbasierung)"

    interval = _case("12-F21")
    assert _int(interval, "elapsed_months") < _int(interval, "minimum_interval_months")
    assert not _bool(interval, "active")


def test_w8_vacancy_uses_day_after_tenancy_end_and_half_up_money() -> None:
    case = _case("12-F22")
    vacancy_days = (_date(case["today"]) - _date(case["last_tenancy_ended_on"])).days
    assert vacancy_days == _int(case, "vacancy_days")
    lost = _money_half_up(
        Decimal(_int(case, "target_rent_cents")) * Decimal(vacancy_days) / Decimal(30)
    )
    assert lost == _int(case, "lost_rent_cents")
    assert vacancy_days > _int(case, "threshold_days")
    assert _bool(case, "active")
    assert not _bool(case, "active_tenancy_variant_active")
