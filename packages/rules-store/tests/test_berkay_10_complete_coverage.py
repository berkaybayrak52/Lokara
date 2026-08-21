"""Coverage and arithmetic checks for the data-only Page 03 AfA oracle."""

from decimal import ROUND_HALF_UP, Decimal

from berkay_10_golden import (
    PAGE_02_AFA_CLASS_PROPOSALS,
    PAGE_03_GOLDENS,
    PAGE_03_NON_GOALS,
    PAGE_03_REGISTER_PAGE,
    PAGE_03_REGISTER_ROWS,
    PAGE_03_SOURCE_SECTIONS,
    VARIANTE_S_FIXTURE_IDS,
)

EXPECTED_IDS = {f"10-F{number:02}" for number in range(1, 35)}


def _case(case_id: str) -> dict[str, object]:
    return PAGE_03_GOLDENS[case_id]


def _int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _ints(case: dict[str, object], key: str) -> tuple[int, ...]:
    value = case[key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    return value


def _half_up(numerator: int, denominator: int) -> int:
    return int(
        (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def test_fixture_surface_is_exactly_10_f01_through_10_f34() -> None:
    assert set(PAGE_03_GOLDENS) == EXPECTED_IDS


def test_complete_source_register_and_non_goal_surfaces() -> None:
    assert len(PAGE_03_SOURCE_SECTIONS) == 13
    assert len(set(PAGE_03_SOURCE_SECTIONS)) == 13
    assert PAGE_03_REGISTER_PAGE.startswith("03 · AfA (Abschreibung) (")
    assert PAGE_03_REGISTER_PAGE.endswith("?pvs=21)")
    assert len(PAGE_03_REGISTER_ROWS) == 46
    assert len({row[0] for row in PAGE_03_REGISTER_ROWS}) == 46
    assert all(len(row) == 9 for row in PAGE_03_REGISTER_ROWS)
    flags = tuple(row[2] for row in PAGE_03_REGISTER_ROWS)
    assert flags.count("geprüft") == 4
    assert flags.count("verify-before-production") == 42
    assert all(row[8] == "07/2026" for row in PAGE_03_REGISTER_ROWS)
    assert len(PAGE_03_NON_GOALS) == 13
    assert len(set(PAGE_03_NON_GOALS)) == 13


def test_acquisition_cost_ordering_and_all_three_allocation_routes_reconcile() -> None:
    costs = _case("10-F01")
    assert _int(costs, "purchase") + _int(costs, "tax") + _int(costs, "notary_acquisition") + _int(
        costs, "broker"
    ) == _int(costs, "acquisition_cost")
    assert _int(costs, "ancillary") == (
        _int(costs, "tax") + _int(costs, "notary_acquisition") + _int(costs, "broker")
    )
    assert _int(costs, "mortgage_notary") not in (
        _int(costs, "notary_acquisition"),
        _int(costs, "ancillary"),
    )

    bmf = _case("10-F02")
    assert _int(bmf, "building_cost") + _int(bmf, "land_cost") == _int(bmf, "acquisition_cost")
    assert bmf["production_blocked"] is True
    placeholder_inputs = bmf["placeholder_inputs"]
    assert isinstance(placeholder_inputs, tuple)
    assert all(isinstance(item, str) for item in placeholder_inputs)
    assert len(placeholder_inputs) == 4

    routes = _case("10-F03")
    assert _int(routes, "contract_building") + _int(routes, "contract_land") == _int(
        routes, "acquisition_cost"
    )
    assert _int(routes, "bmf_building") + _int(routes, "bmf_land") == _int(
        routes, "acquisition_cost"
    )
    assert _int(routes, "contract_building") - _int(routes, "bmf_building") == _int(
        routes, "building_delta"
    )
    assert _int(routes, "contract_annual_afa") - _int(routes, "bmf_annual_afa") == _int(
        routes, "annual_afa_delta"
    )
    assert _case("10-F33")["qualification"] == "oebuv"


def test_rates_first_year_final_year_and_sale_year_round_in_integer_cents() -> None:
    regular = _case("10-F04")
    assert _half_up(_int(regular, "basis") * _int(regular, "rate_bp"), 10_000) == _int(
        regular, "annual_afa"
    )
    new = _case("10-F05")
    assert _half_up(_int(new, "basis") * _int(new, "rate_bp"), 10_000) == _int(new, "annual_afa")
    assert _half_up(_int(new, "annual_afa") * _int(new, "months"), 12) == _int(
        new, "first_year_afa"
    )
    old = _case("10-F06")
    assert _half_up(_int(old, "basis") * _int(old, "rate_bp"), 10_000) == _int(old, "annual_afa")

    march = _case("10-F07")
    december = _case("10-F08")
    assert _half_up(_int(march, "annual_afa") * _int(march, "months"), 12) == _int(
        march, "first_year_afa"
    )
    assert _half_up(_int(december, "annual_afa") * _int(december, "months"), 12) == _int(
        december, "first_year_afa"
    )

    final = _case("10-F13")
    assert _int(final, "first_year_afa") + _int(final, "full_year_count") * _int(
        final, "full_year_afa"
    ) + _int(final, "final_residual") == _int(final, "basis")
    sale = _case("10-F14")
    assert _half_up(540_103 * _int(sale, "months"), 12) == _int(sale, "sale_year_afa")
    assert _int(sale, "opening_book_value") - _int(sale, "sale_year_afa") == _int(
        sale, "closing_book_value"
    )


def test_variante_s_is_isolated_and_self_use_never_changes_the_afa_basis() -> None:
    assert VARIANTE_S_FIXTURE_IDS == (
        "10-F09",
        "10-F10",
        "10-F11",
        "10-F12",
        "10-F24",
    )
    for case_id in VARIANTE_S_FIXTURE_IDS:
        assert _case(case_id)["variant"] == "S"

    for case_id in ("10-F09", "10-F10", "10-F12"):
        case = _case(case_id)
        assert _int(case, "deductible_afa") + _int(case, "non_deductible_afa") == _int(
            case, "annual_afa"
        )
        assert _int(case, "area_month_denominator") == 19_400 * 12

    choice = _case("10-F11")
    assert _int(choice, "month_result") - _int(choice, "day_result") == _int(choice, "delta")
    assert _int(choice, "month_result") + _int(choice, "month_non_deductible") == _int(
        choice, "annual_afa"
    )
    assert _int(choice, "day_result") + _int(choice, "day_non_deductible") == _int(
        choice, "annual_afa"
    )
    assert choice["production_blocked"] is True


def test_fifteen_percent_guard_keeps_service_end_and_reclassification_distinct() -> None:
    warning = _case("10-F15")
    assert sum(_ints(warning, "counted_measures")) == _int(warning, "cumulative")
    assert _int(warning, "cumulative") + _int(warning, "buffer") == _int(warning, "threshold")

    reclassified = _case("10-F16")
    later_costs = reclassified["later_costs_by_year"]
    assert isinstance(later_costs, tuple)
    assert sum(amount for _, amount in later_costs) == _int(reclassified, "cumulative")
    assert sum(_ints(reclassified, "afa_delta")) == 216_367
    assert tuple(
        new - old
        for old, new in zip(
            _ints(reclassified, "old_afa"), _ints(reclassified, "new_afa"), strict=True
        )
    ) == _ints(reclassified, "afa_delta")

    expansion = _case("10-F17")
    assert expansion["countable_for_15_percent"] is False
    assert _int(expansion, "amount") == _int(expansion, "later_production_cost")
    annual = _case("10-F18")
    assert sum(_ints(annual, "annual_parts")) == _int(annual, "annual_total")
    assert _int(annual, "annual_total") * 3 == _int(annual, "three_year_total")
    assert annual["countable_for_15_percent"] is False

    clock = _case("10-F19")
    assert clock["required_date_field"] == "leistungBis"
    assert _int(clock, "cumulative") + _int(clock, "buffer") == _int(clock, "threshold")
    assert _int(clock, "counterfactual_cumulative") == 4_920_000


def test_page_02_proposals_are_exact_and_never_infer_expansion() -> None:
    assert PAGE_02_AFA_CLASS_PROPOSALS == {
        "instandhaltung": "instandsetzungModernisierung",
        "erneuerung": "instandsetzungModernisierung",
        "schoenheitsreparaturen": "instandsetzungModernisierung",
    }
    assert "erweiterung" not in PAGE_02_AFA_CLASS_PROPOSALS


def test_later_production_cost_loan_interest_disagio_and_special_repayment_reconcile() -> None:
    later = _case("10-F20")
    assert _int(later, "old_basis") + _int(later, "later_production_cost") == _int(
        later, "new_basis"
    )
    assert _half_up(_int(later, "new_basis") * _int(later, "rate_bp"), 10_000) == _int(
        later, "new_annual_afa"
    )
    assert _int(later, "opening_book_value") + _int(later, "later_production_cost") - _int(
        later, "new_annual_afa"
    ) == _int(later, "closing_book_value")

    loan = _case("10-F21")
    assert sum(_ints(loan, "interest_schedule")) == _int(loan, "interest_year")
    assert sum(_ints(loan, "repayment_schedule")) == _int(loan, "repayment_year")
    assert _int(loan, "interest_year") + _int(loan, "repayment_year") == 9 * _int(
        loan, "monthly_annuity"
    )
    assert _int(loan, "nominal") - _int(loan, "repayment_year") == _int(loan, "closing_balance")

    disagio = _case("10-F22")
    assert _int(disagio, "non_market_first_year") + _int(disagio, "non_market_middle_years") + _int(
        disagio, "non_market_final_residual"
    ) == _int(disagio, "non_market_disagio")
    assert _int(disagio, "market_first_year_deduction") - _int(
        disagio, "non_market_first_year"
    ) == _int(disagio, "first_year_delta")

    special = _case("10-F23")
    assert _int(special, "scheduled_repayment") + _int(special, "special_repayment") == _int(
        special, "total_repayment"
    )
    assert 40_000_000 - _int(special, "total_repayment") == _int(special, "closing_balance")
    assert _int(loan, "interest_year") - _int(special, "interest_year") == _int(
        special, "interest_saving"
    )


def test_interest_allocation_financing_cost_and_movable_assets_reconcile() -> None:
    interest = _case("10-F24")
    assert _int(interest, "proportional_deductible") + _int(
        interest, "proportional_non_deductible"
    ) == _int(interest, "interest_year")
    assert _int(interest, "direct_rental_deductible") - _int(
        interest, "proportional_deductible"
    ) == _int(interest, "delta")

    notary = _case("10-F25")
    assert _int(notary, "wrong_building_cost") + _int(notary, "wrong_land_cost") == _int(
        notary, "wrong_acquisition_cost"
    )
    assert _int(notary, "correct_building_cost") + _int(notary, "correct_land_cost") == _int(
        notary, "correct_acquisition_cost"
    )
    assert _int(notary, "immediate_financing_cost") - (
        _int(notary, "wrong_annual_afa") - _int(notary, "correct_annual_afa")
    ) == _int(notary, "first_year_net_delta")

    movable = _case("10-F34")
    assert _int(movable, "purchase_after_split") + 5_553_600 == _int(movable, "acquisition_cost")
    assert _int(movable, "building_cost") + _int(movable, "land_cost") == _int(
        movable, "acquisition_cost"
    )
    assert _int(movable, "movable_asset_annual_afa_not_computed_here") == 80_000


def test_hard_blocks_and_residual_life_report_paths_never_invent_results() -> None:
    for case_id in ("10-F26", "10-F27"):
        case = _case(case_id)
        assert case["result"] == "hard_block"
        assert case["annual_afa"] is None

    missing_transfer = _case("10-F30")
    assert missing_transfer["result"] == "hard_block"
    assert missing_transfer["offered_prefill_only"] is True
    invalid_self_use = _case("10-F31")
    assert invalid_self_use["area_result"] == "hard_block"
    assert invalid_self_use["overlap_result"] == "hard_block"

    inherited = _case("10-F32")
    assert _int(inherited, "predecessor_share") + _int(inherited, "successor_share") == _int(
        inherited, "annual_afa"
    )
    assert _int(inherited, "opening_book_value") - _int(inherited, "annual_afa") == _int(
        inherited, "closing_book_value"
    )
    assert inherited["missing_predecessor_value_result"] == "no_result"

    report = _case("10-F33")
    assert _int(report, "twenty_five_year_product") + _int(report, "final_residual") == _int(
        report, "basis"
    )
    assert _int(report, "annual_afa") - _int(report, "regular_annual_afa") == _int(
        report, "annual_delta"
    )
