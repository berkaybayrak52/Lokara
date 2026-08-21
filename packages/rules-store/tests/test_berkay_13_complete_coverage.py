"""Coverage and arithmetic checks for the data-only Page 06 oracle."""

from decimal import ROUND_HALF_UP, Decimal

from berkay_10_golden import PAGE_03_GOLDENS
from berkay_11_golden import FUTURE_CONTRACTS as PAGE_04_FUTURE_CONTRACTS
from berkay_11_golden import PAGE_03_HANDOFF_FIELDS
from berkay_12_golden import PAGE_05_GOLDENS
from berkay_13_golden import (
    ARITHMETIC_AUDIT,
    COMPATIBILITY_ANCHORS,
    CORRESPONDENCE_RETIREMENT_FILES,
    EDGE_CASE_IDS,
    FORMULA_IDS,
    FUTURE_CONTRACTS,
    MISSING_SOURCE_CATALOGUES,
    PAGE_06_GOLDENS,
    PAGE_06_NON_GOALS,
    PAGE_06_REGISTER_PAGE,
    PAGE_06_REGISTER_ROWS,
    PAGE_06_SOURCE_EXCLUSIONS,
    PAGE_06_SOURCE_SECTIONS,
    UNRESOLVED_AUTHORITY,
)

EXPECTED_IDS = {f"CLAUSES-F{number:02}" for number in range(1, 20)}


def _case(case_id: str) -> dict[str, object]:
    return PAGE_06_GOLDENS[case_id]


def _int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _ints(case: dict[str, object], key: str) -> tuple[int, ...]:
    value = case[key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    return value


def _decimal(case: dict[str, object], key: str) -> Decimal:
    value = case[key]
    assert isinstance(value, Decimal)
    return value


def _half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def test_fixture_and_named_rule_surfaces_are_exact() -> None:
    assert set(PAGE_06_GOLDENS) == EXPECTED_IDS
    assert tuple(f"B{number}" for number in range(1, 9)) == FORMULA_IDS
    assert tuple(f"E{number}" for number in range(1, 12)) == EDGE_CASE_IDS
    assert ARITHMETIC_AUDIT == {
        "fixture_count": 19,
        "fixture_range": "CLAUSES-F01…CLAUSES-F19",
        "printed_cent_arithmetic": "exact",
        "clears_unverified_values": False,
    }


def test_complete_source_register_non_goal_exclusion_and_correspondence_surfaces() -> None:
    assert len(PAGE_06_SOURCE_SECTIONS) == 8
    assert len(set(PAGE_06_SOURCE_SECTIONS)) == 8
    assert PAGE_06_REGISTER_PAGE.startswith("06 · Vertragsklauseln — Risiko-Memo (")
    assert PAGE_06_REGISTER_PAGE.endswith("?pvs=21)")

    assert len(PAGE_06_REGISTER_ROWS) == 17
    assert len({row[0] for row in PAGE_06_REGISTER_ROWS}) == 17
    assert all(len(row) == 9 for row in PAGE_06_REGISTER_ROWS)
    flags = tuple(row[2] for row in PAGE_06_REGISTER_ROWS)
    assert flags.count("geprüft") == 9
    assert flags.count("verify-before-production") == 8
    assert all(row[8] == "07/2026" for row in PAGE_06_REGISTER_ROWS)

    assert len(PAGE_06_NON_GOALS) == 7
    assert len(set(PAGE_06_NON_GOALS)) == 7
    assert len(PAGE_06_SOURCE_EXCLUSIONS) == 11
    assert len(set(PAGE_06_SOURCE_EXCLUSIONS)) == 11
    assert len(CORRESPONDENCE_RETIREMENT_FILES) == 7
    assert len(set(CORRESPONDENCE_RETIREMENT_FILES)) == 7


def test_future_contracts_keep_missing_catalogues_and_authority_visible() -> None:
    assert FUTURE_CONTRACTS == (
        "versioned_clause_reference",
        "contract_composition",
        "compatibility_and_signature_gate",
        "immutable_risk_result",
        "sepa_mandate_capture",
        "action_workflow_input",
    )
    assert MISSING_SOURCE_CATALOGUES == (
        "complete_clause_text_and_version_catalogue",
        "complete_rent_increase_letter_body",
        "complete_termination_letter_body",
        "complete_reminder_letter_body",
    )
    assert UNRESOLVED_AUTHORITY == (
        "index_decline_product_behavior",
        "section_559_six_year_window_start",
        "state_regulation_coverage",
        "small_repair_default_limits",
        "planned_tenancy_law_ii_changes",
        "sepa_mandate_expiry",
        "fixed_term_signature_fixture",
    )


def test_staffel_and_index_cases_use_absolute_steps_exact_decimal_and_half_up() -> None:
    graduated = _case("CLAUSES-F01")
    assert _int(graduated, "previous_rent_cents") + _int(graduated, "increase_cents") == _int(
        graduated, "next_absolute_rent_cents"
    )
    assert _int(graduated, "interval_months") == 12
    assert graduated["effective"] is True

    indexed = _case("CLAUSES-F02")
    unrounded = (
        Decimal(_int(indexed, "old_rent_cents"))
        * _decimal(indexed, "new_index")
        / _decimal(indexed, "old_index")
    )
    assert unrounded == _decimal(indexed, "unrounded_new_rent_cents")
    assert _half_up(unrounded) == _int(indexed, "new_rent_cents")
    assert _decimal(indexed, "factor") == _decimal(indexed, "new_index") / _decimal(
        indexed, "old_index"
    )

    invalid = _case("CLAUSES-F12")
    assert _int(invalid, "interval_months") < 12
    assert invalid["effective"] is False
    assert _int(invalid, "resulting_rent_cents") == _int(invalid, "previous_rent_cents")


def test_section_558_and_559_paths_cap_the_correct_amounts() -> None:
    for case_id in ("CLAUSES-F03", "CLAUSES-F04", "CLAUSES-F13"):
        case = _case(case_id)
        cap = _half_up(
            Decimal(_int(case, "current_rent_cents")) * (Decimal("1") + _decimal(case, "cap_rate"))
        )
        assert cap == _int(case, "cap_cents")
        assert min(cap, _int(case, "comparative_rent_cents")) == _int(case, "target_rent_cents")
        assert _int(case, "target_rent_cents") - _int(case, "current_rent_cents") == _int(
            case, "increase_cents"
        )

    standard = _case("CLAUSES-F05")
    annual = _half_up(
        Decimal(_int(standard, "modernization_cost_cents")) * _decimal(standard, "annual_rate")
    )
    assert annual == _int(standard, "annual_allocation_cents")
    assert _half_up(Decimal(annual) / Decimal(12)) == _int(standard, "monthly_cents")
    assert _int(standard, "cap_cents_per_sqm") * int(_decimal(standard, "area_sqm")) == _int(
        standard, "cap_cents"
    )
    assert min(_int(standard, "monthly_cents"), _int(standard, "cap_cents")) == _int(
        standard, "increase_cents"
    )

    low_rent = _case("CLAUSES-F06")
    assert _int(low_rent, "starting_rent_cents_per_sqm") < 700
    assert _int(low_rent, "cap_cents_per_sqm") == 200
    assert min(_int(low_rent, "monthly_cents"), _int(low_rent, "cap_cents")) == _int(
        low_rent, "increase_cents"
    )

    cumulative = _case("CLAUSES-F14")
    assert _int(cumulative, "first_increase_cents") + _int(
        cumulative, "second_unconstrained_increase_cents"
    ) == _int(cumulative, "unconstrained_cumulative_cents")
    assert _int(cumulative, "six_year_cap_cents") - _int(
        cumulative, "first_increase_cents"
    ) == _int(cumulative, "second_allowed_increase_cents")
    assert _int(cumulative, "first_increase_cents") + _int(
        cumulative, "second_allowed_increase_cents"
    ) == _int(cumulative, "resulting_cumulative_cents")
    assert cumulative["window_start"] == "unresolved"


def test_small_repairs_and_deposit_reconcile_in_integer_cents() -> None:
    repairs = _case("CLAUSES-F07")
    annual_limit = _half_up(
        Decimal(_int(repairs, "annual_net_cold_rent_cents"))
        * _decimal(repairs, "annual_limit_rate")
    )
    assert annual_limit == _int(repairs, "annual_limit_cents")
    assert sum(_ints(repairs, "chargeable_repairs_cents")) == _int(repairs, "renter_share_cents")
    assert sum(_ints(repairs, "repairs_cents")) == _int(repairs, "renter_share_cents") + _int(
        repairs, "landlord_share_cents"
    )
    assert repairs["limits_unverified"] is True

    deposit = _case("CLAUSES-F08")
    assert _int(deposit, "net_cold_rent_cents") * 3 == _int(deposit, "maximum_deposit_cents")
    assert _int(deposit, "installment_cents") * _int(deposit, "installment_count") == _int(
        deposit, "installment_sum_cents"
    )
    assert _int(deposit, "installment_sum_cents") == _int(deposit, "maximum_deposit_cents")


def test_arrears_thresholds_preserve_strict_and_inclusive_comparisons() -> None:
    two_dates = _case("CLAUSES-F09")
    assert sum(_ints(two_dates, "open_installments_cents")) == _int(two_dates, "arrears_cents")
    assert _int(two_dates, "arrears_cents") > _int(two_dates, "threshold_cents")
    assert two_dates["comparison"] == "strictly_greater"
    assert two_dates["eligible"] is True

    longer = _case("CLAUSES-F10")
    assert _int(longer, "monthly_shortfall_cents") * _int(longer, "month_count") == _int(
        longer, "arrears_cents"
    )
    assert _int(longer, "arrears_cents") >= _int(longer, "threshold_cents")
    assert longer["comparison"] == "greater_or_equal"
    assert longer["eligible"] is True


def test_risk_signature_rent_brake_sepa_and_self_use_routing_are_exact() -> None:
    decline = _case("CLAUSES-F11")
    unrounded = (
        Decimal(_int(decline, "old_rent_cents"))
        * _decimal(decline, "new_index")
        / _decimal(decline, "old_index")
    )
    assert _half_up(unrounded) == _int(decline, "calculated_rent_cents")
    assert decline["automatic_adjustment"] is False
    assert decline["product_behavior"] == "unresolved"

    signature = _case("CLAUSES-F15")
    assert signature["signature_gate"] == "blocked"
    assert signature["route"] == "paper_or_qes"
    assert signature["cent_result"] is None
    assert signature["fixed_term_over_one_year_fixture_present"] is False

    no_exception = _case("CLAUSES-F16")
    assert _half_up(
        Decimal(_int(no_exception, "comparative_rent_cents"))
        * _decimal(no_exception, "maximum_rent_rate")
    ) == _int(no_exception, "maximum_rent_cents")
    assert _int(no_exception, "agreed_rent_cents") - _int(
        no_exception, "maximum_rent_cents"
    ) == _int(no_exception, "excess_cents")
    assert no_exception["outcome"] == "warn_only_continue"
    assert no_exception["rent_capped_by_lokara"] is False

    declared = _case("CLAUSES-F17")
    assert declared["exception_verified_by_lokara"] is False
    assert declared["outcome"] == "notice_continue"
    assert declared["rent_capped_by_lokara"] is False
    assert declared["timestamp_required"] is True

    mandate = _case("CLAUSES-F18")
    reference = mandate["mandate_reference"]
    assert isinstance(reference, str)
    assert len(reference) == _int(mandate, "reference_length")
    assert len(reference) <= _int(mandate, "maximum_reference_length")
    assert mandate["future_date_valid"] is False
    assert mandate["future_date_blocks_contract"] is False
    assert mandate["collection_enabled"] is False

    self_use = _case("CLAUSES-F19")
    assert self_use["tenancy_created"] is False
    assert self_use["rent_clause_routes_active"] is False
    assert self_use["page_03_route"] == "self_use_period_reduces_deductible_afa"
    assert self_use["page_03_afa_basis_reduced"] is False
    assert _int(self_use, "page_04_tax_income_cents") == 0
    assert _int(self_use, "page_06_cent_result") == 0
    assert self_use["source_basis_wording_superseded"] is True


def test_approved_page_03_04_and_05_ownership_stays_compatible() -> None:
    assert COMPATIBILITY_ANCHORS == {
        "docs/10-afa.md": "self_use_reduces_deductible_afa_not_basis",
        "docs/11-tax-export.md": "tax_income_and_cash_basis_owned_by_page_04",
        "docs/12-guards-deadlines.md": "dates_thresholds_and_guard_state_owned_by_page_05",
        "superseded_page_06_wording": "afa_basis_reduction",
    }

    page_03 = PAGE_03_GOLDENS["10-F09"]
    assert _int(page_03, "annual_afa") == _int(page_03, "deductible_afa") + _int(
        page_03, "non_deductible_afa"
    )
    assert "afaAbziehbarCent" in PAGE_03_HANDOFF_FIELDS
    assert "payment_ledger_snapshot" in PAGE_04_FUTURE_CONTRACTS

    page_05_arrears = PAGE_05_GOLDENS["12-F07"]
    page_06_arrears = _case("CLAUSES-F09")
    assert (
        page_05_arrears["gross_monthly_rent_cents"] == page_06_arrears["gross_monthly_rent_cents"]
    )
    assert page_05_arrears["threshold_3a_cents"] == page_06_arrears["threshold_cents"]

    page_05_staffel = PAGE_05_GOLDENS["12-F18"]
    assert _int(page_05_staffel, "minimum_interval_months") == 12
    assert _int(_case("CLAUSES-F12"), "interval_months") < _int(
        page_05_staffel, "minimum_interval_months"
    )
