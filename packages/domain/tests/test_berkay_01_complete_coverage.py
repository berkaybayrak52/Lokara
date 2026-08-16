"""Green coverage and arithmetic checks for the data-only Page 01 oracle."""

from decimal import ROUND_HALF_UP, Decimal

from berkay_01_golden import PAGE_01_GOLDENS

EXPECTED_IDS = {f"08-F{number:02}" for number in range(1, 25)}


def _ints(case: dict[str, object], key: str) -> tuple[int, ...]:
    value = case[key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) for item in value)
    return value


def _int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int)
    return value


def _half_up(numerator: int, denominator: int) -> int:
    return int((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("1"), ROUND_HALF_UP))


def test_every_page_01_fixture_has_exactly_one_oracle() -> None:
    assert set(PAGE_01_GOLDENS) == EXPECTED_IDS


def test_f01_full_run_reconciles_costs_balances_and_owner_residuals() -> None:
    case = PAGE_01_GOLDENS["08-F01"]
    party_totals = _ints(case, "party_totals")
    advances = _ints(case, "advances")
    balances = _ints(case, "balances")

    calculated_balances = tuple(
        share - advance for share, advance in zip(party_totals, advances, strict=True)
    )
    assert calculated_balances == balances
    assert sum(party_totals) == _int(case, "allocated_total")
    assert sum(party_totals) + _int(case, "owner_residual") == _int(case, "cost_total")
    assert sum(_ints(case, "owner_residuals")) == _int(case, "owner_residual")
    assert sum(balance for balance in balances if balance > 0) == _int(case, "positive_balances")
    assert -sum(balance for balance in balances if balance < 0) == _int(case, "credits")


def test_f02_to_f05_balance_branches_are_internally_consistent() -> None:
    for fixture_id in ("08-F02", "08-F03", "08-F04", "08-F05"):
        case = PAGE_01_GOLDENS[fixture_id]
        assert _int(case, "share") - _int(case, "advance") == _int(case, "balance")


def test_f08_mixed_mdl_fallback_exposes_its_control_difference() -> None:
    case = PAGE_01_GOLDENS["08-F08"]
    assert _int(case, "share") - _int(case, "advance") == _int(case, "balance")
    assert _int(case, "allocated_heating") - _int(case, "heating_total") == _int(
        case, "control_difference"
    )


def test_f09_co2_box_reconciles() -> None:
    case = PAGE_01_GOLDENS["08-F09"]
    assert _int(case, "landlord_co2") + _int(case, "renter_co2_total") == _int(case, "co2_cost")
    assert sum(_ints(case, "renter_co2_shares")) == _int(case, "renter_co2_total")


def test_f11_keeps_credit_as_a_separate_rounded_line() -> None:
    case = PAGE_01_GOLDENS["08-F11"]
    assert _int(case, "gross_share") + _int(case, "credit_share") == _int(case, "linewise_share")
    assert _int(case, "linewise_share") - _int(case, "forbidden_net_first_share") == 1


def test_f12_zero_denominator_leaves_the_whole_line_with_the_owner() -> None:
    case = PAGE_01_GOLDENS["08-F12"]
    assert _int(case, "renter_share") == 0
    assert _int(case, "owner_residual") == 126_000
    assert _int(case, "share") - _int(case, "advance") == _int(case, "balance")


def test_f13_and_f14_period_arithmetic_is_exact() -> None:
    overlap = PAGE_01_GOLDENS["08-F13"]
    assert _int(overlap, "overlap_days") * _int(overlap, "area_sqm") == _int(
        overlap, "overallocated_area_days"
    )
    assert _int(overlap, "probe_total") - 98_000 == _int(overlap, "probe_overallocation")

    short = PAGE_01_GOLDENS["08-F14"]
    assert 194 * _int(short, "period_days") == _int(short, "total_area_days")
    assert 58 * _int(short, "usage_days") == _int(short, "party_area_days")
    assert _half_up(
        _int(short, "cost") * _int(short, "party_area_days"), _int(short, "total_area_days")
    ) == _int(short, "share")
    assert _int(short, "share") - _int(short, "advance") == _int(short, "balance")


def test_f20_leap_year_uses_366_days_without_a_special_money_rule() -> None:
    case = PAGE_01_GOLDENS["08-F20"]
    assert 194 * _int(case, "period_days") == _int(case, "total_area_days")
    assert 58 * _int(case, "period_days") == _int(case, "full_year_party_area_days")
    assert 74 * _int(case, "partial_usage_days") == _int(case, "partial_area_days")


def test_f21_later_answer_corrects_block_b_without_changing_block_a() -> None:
    case = PAGE_01_GOLDENS["08-F21"]
    assert sum(_ints(case, "vacancy_residuals")) == _int(case, "block_a_vacancy")
    assert sum(_ints(case, "block_b_non_allocable_parts")) == _int(case, "block_b_non_allocable")
    assert _int(case, "separately_computed_counterfactual") - _int(case, "block_a_vacancy") == 5
    assert _int(case, "block_a_vacancy") + _int(case, "block_b_non_allocable") + _int(
        case, "block_c_rounding"
    ) == _int(case, "owner_total_with_non_allocable")


def test_f22_fictional_occupancy_keeps_the_vacancy_with_the_owner() -> None:
    case = PAGE_01_GOLDENS["08-F22"]
    assert sum(_ints(case, "without_fiction")) == _int(case, "cost")
    assert sum(_ints(case, "with_fiction")) + _int(case, "owner_residual") == _int(case, "cost")
    assert _int(case, "person_days_with") - _int(case, "person_days_without") == 62


def test_f23_whole_period_vacancy_values_follow_the_printed_formulas() -> None:
    case = PAGE_01_GOLDENS["08-F23"]
    assert _int(case, "vacancy_days") * _int(case, "vacant_area_sqm") == _int(
        case, "vacant_area_days"
    )
    assert _half_up(
        _int(case, "property_tax") * _int(case, "vacant_area_days"),
        _int(case, "total_area_days"),
    ) == _int(case, "property_tax_owner")
    assert _half_up(
        _int(case, "waste_cost") * _int(case, "fictional_person_days"),
        _int(case, "total_person_days"),
    ) == _int(case, "waste_owner")


def test_f24_self_billing_path_reconciles_without_becoming_f01() -> None:
    case = PAGE_01_GOLDENS["08-F24"]
    heating = _ints(case, "heating_party_shares")
    party_totals = _ints(case, "party_totals")
    advances = _ints(case, "advances")
    balances = _ints(case, "balances")

    assert sum(heating) + _int(case, "heating_owner") == _int(case, "allocable_heating")
    assert _int(case, "allocable_heating") + _int(case, "co2_landlord") == _int(
        case, "gross_heating"
    )
    calculated_balances = tuple(
        share - advance for share, advance in zip(party_totals, advances, strict=True)
    )
    assert calculated_balances == balances
    assert sum(party_totals) == _int(case, "allocated_total")
    assert sum(party_totals) + _int(case, "owner_residual") == _int(case, "cost_total")
    assert sum(_ints(case, "co2_renter_shares")) == _int(case, "co2_renter_total")
    assert sum(balance for balance in balances if balance > 0) == _int(case, "positive_balances")
    assert -sum(balance for balance in balances if balance < 0) == _int(case, "credits")
