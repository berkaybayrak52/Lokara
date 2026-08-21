"""Coverage and arithmetic checks for the data-only Page 07 oracle."""

from decimal import ROUND_HALF_UP, Decimal

from berkay_09_golden import NON_ALLOCABLE_CATALOGUE_IDS
from berkay_10_golden import PAGE_03_GOLDENS
from berkay_11_golden import FUTURE_CONTRACTS as PAGE_04_FUTURE_CONTRACTS
from berkay_11_golden import PAGE_03_HANDOFF_FIELDS
from berkay_14_golden import (
    ARITHMETIC_AUDIT,
    COMPATIBILITY_ANCHORS,
    CONVENTION_IDS,
    EDGE_CASE_IDS,
    FIXTURE_IDS,
    FORMULA_IDS,
    FUTURE_CONTRACTS,
    MISSING_REFERENCED_SOURCES,
    PAGE_07_GOLDENS,
    PAGE_07_NON_GOALS,
    PAGE_07_REGISTER_ROWS,
    PAGE_07_SOURCE_EXCLUSIONS,
    REFERENCE_INPUTS,
    SOURCE_ALIASES,
)


def half_up(numerator: int, denominator: int = 1) -> int:
    return int(
        (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def annuity(loan: int, interest_bp: int, monthly: int) -> tuple[int, int, int]:
    balance = loan
    interest_total = 0
    repayment_total = 0
    for _ in range(12):
        interest = half_up(balance * interest_bp, 120_000)
        repayment = monthly - interest
        if repayment <= 0:
            raise ValueError("non-positive repayment")
        balance -= repayment
        interest_total += interest
        repayment_total += repayment
    return interest_total, repayment_total, balance


def fixture_int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def fixture_int_rows(case: dict[str, object], key: str) -> tuple[tuple[int, ...], ...]:
    value = case[key]
    assert isinstance(value, tuple)
    rows: list[tuple[int, ...]] = []
    for raw_row in value:
        assert isinstance(raw_row, tuple)
        assert all(isinstance(item, int) and not isinstance(item, bool) for item in raw_row)
        rows.append(tuple(item for item in raw_row if isinstance(item, int)))
    return tuple(rows)


def test_identifier_alias_and_source_surfaces_are_exact() -> None:
    assert tuple(f"14-K{n:02}" for n in range(1, 20)) == CONVENTION_IDS
    assert tuple(f"14-E{n:02}" for n in range(1, 16)) == EDGE_CASE_IDS
    assert tuple(f"R{n}" for n in range(1, 11)) == FORMULA_IDS
    assert tuple(f"14-F{n:02}" for n in range(1, 15)) == FIXTURE_IDS
    assert set(PAGE_07_GOLDENS) == set(FIXTURE_IDS)
    assert len(SOURCE_ALIASES) == 58
    assert all(SOURCE_ALIASES[f"KPI-K{n:02}"] == f"14-K{n:02}" for n in range(1, 20))
    assert all(SOURCE_ALIASES[f"KPI-E{n:02}"] == f"14-E{n:02}" for n in range(1, 16))
    assert all(SOURCE_ALIASES[f"KPI-F{n:02}"] == f"14-F{n:02}" for n in range(1, 15))
    assert all(SOURCE_ALIASES[f"R{n}"] == f"R{n}" for n in range(1, 11))


def test_register_non_goals_exclusions_and_audit_are_exact() -> None:
    assert len(PAGE_07_REGISTER_ROWS) == 18
    assert len({row[0] for row in PAGE_07_REGISTER_ROWS}) == 18
    assert all(len(row) == 9 for row in PAGE_07_REGISTER_ROWS)
    flags = [row[2] for row in PAGE_07_REGISTER_ROWS]
    natures = [row[7] for row in PAGE_07_REGISTER_ROWS]
    assert flags.count("geprüft") == 2
    assert flags.count("verify-before-production") == 16
    assert natures.count("Konvention") == 13
    assert natures.count("Heuristik") == 3
    assert natures.count("Gesetz") == 2
    assert all(row[8] == "07/2026" for row in PAGE_07_REGISTER_ROWS)
    assert PAGE_07_NON_GOALS == (
        "no_multi_year_projection_resale_irr_npv_or_appreciation",
        "no_afa_calculation_or_15_percent_guard",
        "no_soli_church_tax_progression_or_loss_offset_limits",
        "no_variable_rates_refinancing_forward_loan_or_prepayment_optimization",
        "no_parking_other_income_or_commercial_vat_units_in_rent_kpis",
        "no_purchase_recommendation_winner_or_default_target_return",
        "bank_pdf_no_value_credit_appraisal_or_automatic_sending",
        "no_real_bank_rates_comparison_or_broker_connection",
    )
    assert PAGE_07_SOURCE_EXCLUSIONS == (
        "long_hold_exit_metrics",
        "afa_derivation",
        "tax_export_anlage_v_datev",
        "financing_beyond_first_twelve_fixed_payments",
        "surcharges_progression_and_loss_offset_rules",
        "other_commercial_income_and_pre_purchase_development",
        "purchase_ranking_recommendations",
        "bank_pdf_valuation_credit_and_application_claims",
    )
    assert ARITHMETIC_AUDIT == {
        "fixture_count": 14,
        "fixture_range": "KPI-F01…KPI-F14",
        "printed_cent_arithmetic": "exact",
        "clears_unverified_values": False,
    }


def test_future_contract_and_missing_source_surfaces_are_explicit() -> None:
    assert FUTURE_CONTRACTS == (
        "pruefobjekt_input_snapshot",
        "financing_and_afa_provenance",
        "partial_kpi_results",
        "twelve_month_annuity_schedule",
        "sensitivity_axes",
        "deterministic_bank_pdf_view",
    )
    assert MISSING_REFERENCED_SOURCES == (
        "Lokara_Investitionsmodul_Demo.html",
        "AfA-Wizard_Konzept_Entwurf.md",
    )
    assert COMPATIBILITY_ANCHORS["interest_ambiguity"] == "page_03_r13_vs_page_07_r3_unresolved"


def test_f01_recomputes_all_seven_kpis() -> None:
    c = PAGE_07_GOLDENS["14-F01"]
    i = REFERENCE_INPUTS
    annual_rent = i["monthly_actual_rent_cents"] * 12
    cash_costs = (
        i["administration_cents"]
        + i["maintenance_cents"]
        + i["reserve_cents"]
        + i["vacancy_risk_cents"]
    )
    deductible = i["administration_cents"] + i["maintenance_cents"]
    noi = annual_rent - cash_costs
    monthly = half_up(i["loan_cents"] * (i["interest_bp"] + i["initial_repayment_bp"]), 120_000)
    interest, repayment, _ = annuity(i["loan_cents"], i["interest_bp"], monthly)
    debt_service = monthly * 12
    basis = half_up(i["total_investment_cents"] * i["building_share_bp"], 10_000)
    afa = half_up(basis * i["afa_rate_bp"], 10_000)
    tax_base = annual_rent - deductible - interest - afa
    tax = half_up(tax_base * i["marginal_tax_bp"], 10_000)
    cf_before = noi - debt_service
    cf_after = cf_before - tax
    assert (
        annual_rent,
        cash_costs,
        deductible,
        noi,
        interest,
        repayment,
        debt_service,
        basis,
        afa,
        tax_base,
        tax,
        cf_before,
        cf_after,
    ) == (
        c["annual_actual_rent_cents"],
        c["cash_costs_cents"],
        c["deductible_costs_cents"],
        c["noi_cents"],
        c["annual_interest_cents"],
        c["annual_repayment_cents"],
        c["annual_debt_service_cents"],
        c["afa_basis_cents"],
        c["annual_afa_cents"],
        c["tax_base_cents"],
        c["tax_cents"],
        c["cashflow_before_year_cents"],
        c["cashflow_after_year_cents"],
    )
    assert c["factor_hundredths"] == half_up(i["purchase_price_cents"] * 100, annual_rent)
    assert c["gross_yield_bp"] == half_up(annual_rent * 10_000, i["purchase_price_cents"])
    assert c["net_yield_bp"] == half_up(noi * 10_000, i["total_investment_cents"])
    assert c["dscr_hundredths"] == half_up(noi * 100, debt_service)
    assert c["equity_return_before_bp"] == half_up(
        (cf_before + repayment) * 10_000, i["equity_cents"]
    )
    assert c["equity_return_after_bp"] == half_up(
        (cf_after + repayment) * 10_000, i["equity_cents"]
    )


def test_annuity_branches_all_equity_partial_vacancy_afa_guard_and_negative_case() -> None:
    f02 = PAGE_07_GOLDENS["14-F02"]
    schedule = fixture_int_rows(f02, "schedule")
    assert len(schedule) == 12
    assert all(opening - repayment == closing for opening, _, repayment, closing in schedule)
    assert sum(row[1] for row in schedule) == fixture_int(f02, "annual_interest_cents")
    assert sum(row[2] for row in schedule) == fixture_int(f02, "annual_repayment_cents")
    assert fixture_int(f02, "annual_interest_cents") + fixture_int(
        f02, "annual_repayment_cents"
    ) == fixture_int(f02, "annual_debt_service_cents")
    assert REFERENCE_INPUTS["loan_cents"] - fixture_int(
        f02, "annual_repayment_cents"
    ) == fixture_int(f02, "closing_balance_cents")

    for fixture in ("14-F03", "14-F10"):
        c = PAGE_07_GOLDENS[fixture]
        assert annuity(
            fixture_int(c, "loan_cents") if "loan_cents" in c else REFERENCE_INPUTS["loan_cents"],
            fixture_int(c, "interest_bp")
            if "interest_bp" in c
            else REFERENCE_INPUTS["interest_bp"],
            fixture_int(c, "monthly_annuity_cents"),
        ) == (
            fixture_int(c, "annual_interest_cents"),
            fixture_int(c, "annual_repayment_cents"),
            fixture_int(c, "closing_balance_cents")
            if "closing_balance_cents" in c
            else fixture_int(c, "loan_cents") - fixture_int(c, "annual_repayment_cents"),
        )

    all_equity = PAGE_07_GOLDENS["14-F04"]
    assert all_equity["dscr"] == "n/a (kein Fremdkapital)"
    assert fixture_int(all_equity, "tax_cents") == half_up(
        fixture_int(all_equity, "tax_base_cents") * 4_200, 10_000
    )
    assert fixture_int(all_equity, "cashflow_after_year_cents") == (
        fixture_int(all_equity, "cashflow_before_year_cents") - fixture_int(all_equity, "tax_cents")
    )
    assert fixture_int(all_equity, "equity_return_after_bp") == half_up(
        fixture_int(all_equity, "cashflow_after_year_cents") * 10_000,
        fixture_int(all_equity, "equity_cents"),
    )
    returns = PAGE_07_GOLDENS["14-F05"]
    reference = PAGE_07_GOLDENS["14-F01"]
    assert returns["equity_return_before_bp"] == reference["equity_return_before_bp"]
    assert returns["equity_return_after_bp"] == reference["equity_return_after_bp"]
    assert returns["cash_on_cash_after_bp"] == half_up(
        fixture_int(reference, "cashflow_after_year_cents") * 10_000,
        REFERENCE_INPUTS["equity_cents"],
    )
    assert PAGE_07_GOLDENS["14-F06"]["unavailable"] == (
        "net_yield",
        "dscr",
        "equity_return",
        "cashflow",
        "break_even",
    )
    vacancy = PAGE_07_GOLDENS["14-F07"]
    assert vacancy["effective_rent_cents"] == half_up(3_180_000 * 9_500, 10_000)
    assert vacancy["noi_cents"] == fixture_int(vacancy, "effective_rent_cents") - 723_600
    assert vacancy["tax_cents"] == half_up(fixture_int(vacancy, "tax_base_cents") * 4_200, 10_000)
    linked_afa = PAGE_07_GOLDENS["14-F08"]
    assert linked_afa["afa_provenance"] == "page_03_r13"
    assert linked_afa["tax_cents"] == half_up(
        fixture_int(linked_afa, "tax_base_cents") * 4_200, 10_000
    )
    assert linked_afa["cashflow_after_year_cents"] == (
        fixture_int(linked_afa, "cashflow_before_year_cents") - fixture_int(linked_afa, "tax_cents")
    )
    guard = PAGE_07_GOLDENS["14-F09"]
    assert (
        fixture_int(guard, "first_repayment_cents")
        == fixture_int(guard, "monthly_annuity_cents") - fixture_int(guard, "first_interest_cents")
        <= 0
    )
    negative = PAGE_07_GOLDENS["14-F10"]
    assert (
        fixture_int(negative, "tax_cents")
        == half_up(fixture_int(negative, "tax_base_cents") * 4_200, 10_000)
        < 0
    )
    assert negative["negative_tax_meaning"] == "flat_rate_scenario_only"


def test_reciprocal_bank_pdf_and_both_sensitivity_axes() -> None:
    reciprocal = PAGE_07_GOLDENS["14-F11"]
    assert (
        fixture_int(reciprocal, "factor_hundredths") * fixture_int(reciprocal, "gross_yield_bp")
        == reciprocal["product"]
    )
    assert fixture_int(reciprocal, "reciprocal_target") - fixture_int(
        reciprocal, "product"
    ) == fixture_int(reciprocal, "rounding_drift")
    pdf = PAGE_07_GOLDENS["14-F12"]
    assert pdf["ltv_purchase_bp"] == half_up(34_000_000 * 10_000, 42_000_000)
    assert pdf["ltv_total_bp"] == half_up(34_000_000 * 10_000, 45_360_000)
    assert pdf["renter_names_included"] is False and pdf["partial_pdf_renderable"] is True

    interest_steps = fixture_int_rows(PAGE_07_GOLDENS["14-F13"], "interest_steps")
    repayment_steps = fixture_int_rows(PAGE_07_GOLDENS["14-F14"], "repayment_steps")
    assert len(interest_steps) == 5
    assert tuple(row[0] for row in interest_steps) == (290, 340, 390, 440, 490)
    assert len(repayment_steps) == 4
    assert tuple(row[0] for row in repayment_steps) == (100, 200, 300, 400)
    assert all(
        annuity(34_000_000, row[0], row[1])[:2] == (row[3], row[4]) for row in interest_steps
    )
    for row in interest_steps:
        interest_bp, monthly, debt_service, interest, repayment = row[:5]
        dscr, cashflow, ek_before, ek_after, break_even = row[5:]
        tax = half_up((3_180_000 - 660_000 - interest - 680_400) * 4_200, 10_000)
        cashflow_before_year = 2_456_400 - debt_service
        cashflow_after_year = cashflow_before_year - tax
        tax_term = half_up(4_200 * (660_000 + interest + 680_400), 10_000)
        break_even_year = half_up((723_600 + debt_service - tax_term) * 10_000, 5_800)
        assert debt_service == monthly * 12
        assert dscr == half_up(2_456_400 * 100, debt_service)
        assert cashflow == half_up(cashflow_after_year, 12)
        assert ek_before == half_up((cashflow_before_year + repayment) * 10_000, 11_360_000)
        assert ek_after == half_up((cashflow_after_year + repayment) * 10_000, 11_360_000)
        assert break_even == half_up(break_even_year, 12)
        assert interest_bp in (290, 340, 390, 440, 490)
    assert [row[3] for row in repayment_steps] == sorted(
        (row[3] for row in repayment_steps), reverse=True
    )
    assert [row[5] for row in repayment_steps] == sorted(
        (row[5] for row in repayment_steps), reverse=True
    )
    assert [row[6] for row in repayment_steps] == sorted(row[6] for row in repayment_steps)
    for row in repayment_steps:
        repayment_bp, monthly, debt_service, dscr, cashflow, closing, equity_return = row
        interest, repayment, recomputed_closing = annuity(34_000_000, 390, monthly)
        tax = half_up((3_180_000 - 660_000 - interest - 680_400) * 4_200, 10_000)
        cashflow_after_year = 2_456_400 - debt_service - tax
        assert monthly == half_up(34_000_000 * (390 + repayment_bp), 120_000)
        assert debt_service == monthly * 12
        assert dscr == half_up(2_456_400 * 100, debt_service)
        assert cashflow == half_up(cashflow_after_year, 12)
        assert closing == recomputed_closing
        assert equity_return == half_up((cashflow_after_year + repayment) * 10_000, 11_360_000)


def test_approved_page_02_03_and_04_ownership_anchors_remain_compatible() -> None:
    assert {
        "verwaltungskosten",
        "instandhaltung",
        "instandhaltungsruecklage",
        "mietausfallwagnis",
    }.issubset(NON_ALLOCABLE_CATALOGUE_IDS)
    assert {"afaAbziehbarCent", "zinsAbziehbarCent"}.issubset(PAGE_03_HANDOFF_FIELDS)
    assert PAGE_03_GOLDENS["10-F04"]["annual_afa"] == 540_103
    assert "versioned_export_archive" in PAGE_04_FUTURE_CONTRACTS
