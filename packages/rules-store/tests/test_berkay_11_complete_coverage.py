"""Coverage and arithmetic checks for the data-only Page 04 tax-export oracle."""

from berkay_11_golden import (
    ARITHMETIC_AUDIT,
    CONVENTION_IDS,
    CORRESPONDENCE_RETIREMENT_FILES,
    EDGE_05_SUBCASES,
    EDGE_CASE_IDS,
    EXTF_WORKING_CONVENTION,
    FUTURE_CONTRACTS,
    PAGE_03_HANDOFF_FIELDS,
    PAGE_04_DELEGATED_BOUNDARIES,
    PAGE_04_GOLDENS,
    PAGE_04_NON_GOALS,
    PAGE_04_REGISTER_PAGE,
    PAGE_04_REGISTER_ROWS,
    PAGE_04_SOURCE_SECTIONS,
    READINESS_FINDINGS,
    RULE_IDS,
    UNMAPPED_HANDOFF_GAPS,
    UNVERIFIED_BLOCKERS,
    UNVERIFIED_REFERENCE_MAPPING,
)

EXPECTED_IDS = {f"11-F{number:02}" for number in range(1, 17)}


def _case(case_id: str) -> dict[str, object]:
    return PAGE_04_GOLDENS[case_id]


def _int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _ints(case: dict[str, object], key: str) -> tuple[int, ...]:
    value = case[key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    return value


def test_fixture_and_namespace_surfaces_are_exact() -> None:
    assert set(PAGE_04_GOLDENS) == EXPECTED_IDS
    assert tuple(f"11-K{number:02}" for number in range(1, 12)) == CONVENTION_IDS
    assert tuple(f"R{number}" for number in range(1, 10)) == RULE_IDS
    assert tuple(f"11-E{number:02}" for number in range(1, 16)) == EDGE_CASE_IDS
    assert EDGE_05_SUBCASES == ("11-E05a", "11-E05b", "11-E05c")


def test_complete_source_register_non_goal_and_correspondence_surfaces() -> None:
    assert len(PAGE_04_SOURCE_SECTIONS) == 14
    assert len(set(PAGE_04_SOURCE_SECTIONS)) == 14
    assert PAGE_04_REGISTER_PAGE.startswith("04 · Anlage V + DATEV-Export (")
    assert PAGE_04_REGISTER_PAGE.endswith("?pvs=21)")

    assert len(PAGE_04_REGISTER_ROWS) == 13
    assert len({row[0] for row in PAGE_04_REGISTER_ROWS}) == 13
    assert all(len(row) == 9 for row in PAGE_04_REGISTER_ROWS)
    flags = tuple(row[2] for row in PAGE_04_REGISTER_ROWS)
    assert flags.count("geprüft") == 7
    assert flags.count("verify-before-production") == 6
    assert all(row[3] == "28. Juli 2026 17:16" for row in PAGE_04_REGISTER_ROWS)
    assert all(row[8] == "07/2026" for row in PAGE_04_REGISTER_ROWS)

    assert len(PAGE_04_NON_GOALS) == 8
    assert len(set(PAGE_04_NON_GOALS)) == 8
    assert PAGE_04_DELEGATED_BOUNDARIES == (
        "AfA-, Zins- und Disagio-Berechnung kommt fertig von Seite 03",
        "Umlageschlüssel, NK-Arithmetik, Fristen und UVI bleiben auf Seiten 01/02/05",
    )
    assert len(CORRESPONDENCE_RETIREMENT_FILES) == 7
    assert len(set(CORRESPONDENCE_RETIREMENT_FILES)) == 7


def test_future_contract_and_blocker_surfaces_stay_data_only_and_unverified() -> None:
    assert FUTURE_CONTRACTS == (
        "payment_ledger_snapshot",
        "page_03_afa_handoff",
        "tax_adviser_profile",
        "year_versioned_tax_category_mapping",
        "immutable_readiness_result",
        "versioned_export_archive",
    )
    assert PAGE_03_HANDOFF_FIELDS == (
        "afaAbziehbarCent",
        "zinsAbziehbarCent",
        "disagioAbziehbarCent",
        "erhaltungsaufwandCent",
    )
    assert UNMAPPED_HANDOFF_GAPS == (
        "disagio_anlage_v_line",
        "erhaltungsaufwand_line_and_ledger_instandhaltung_deduplication",
    )
    assert len(UNVERIFIED_BLOCKERS) == 6
    assert "anlage_v_lines_by_tax_year" in UNVERIFIED_BLOCKERS
    assert "skr03_skr04_default_accounts" in UNVERIFIED_BLOCKERS
    assert "extf_soll_haben_orientation" in UNVERIFIED_BLOCKERS
    assert "ten_day_rule_bfh_case_number" in UNVERIFIED_BLOCKERS

    assert len(UNVERIFIED_REFERENCE_MAPPING) == 14
    assert len({row[0] for row in UNVERIFIED_REFERENCE_MAPPING}) == 14
    assert {row[0] for row in UNVERIFIED_REFERENCE_MAPPING} >= {
        "kaltmiete",
        "nk_vorauszahlung",
        "nk_nachzahlung",
        "nk_guthaben",
        "afa",
        "schuldzinsen",
        "kaution",
        "bank",
    }
    assert ARITHMETIC_AUDIT == {
        "fixture_count": 16,
        "fixture_range": "11-F01…11-F16",
        "printed_cent_arithmetic": "exact",
        "clears_unverified_values": False,
    }


def test_reference_income_costs_and_result_reconcile_in_integer_cents() -> None:
    income = _case("11-F01")
    assert _int(income, "cold_rent_month") * _int(income, "months") == _int(
        income, "cold_rent_year"
    )
    assert _int(income, "advance_month") * _int(income, "months") == _int(income, "advance_year")
    assert _int(income, "cold_rent_year") + _int(income, "advance_year") == _int(
        income, "income_total"
    )

    costs = _case("11-F02")
    assert sum(_ints(costs, "cash_costs")) == _int(costs, "cash_cost_total")
    assert _int(costs, "cash_cost_total") + _int(costs, "afa_handoff") + _int(
        costs, "interest_proposal"
    ) == _int(costs, "advertising_cost_total")
    assert costs["interest_confirmation"] == "yellow"

    result = _case("11-F03")
    assert _int(result, "income_total") - _int(result, "advertising_cost_total") == _int(
        result, "result"
    )


def test_section_11_cash_basis_assigns_all_four_year_cases() -> None:
    settlement = _case("11-F04")
    assert settlement["recurring"] is False
    assert settlement["tax_year"] == 2025
    assert _int(settlement, "reference_income_before") + _int(settlement, "amount") == _int(
        settlement, "reference_income_after"
    )

    december_advance = _case("11-F05")
    assert december_advance["both_dates_in_window"] is True
    assert december_advance["tax_year"] == 2026
    assert december_advance["assignment_label_required"] is True

    january_payment = _case("11-F06")
    assert january_payment["both_dates_in_window"] is True
    assert january_payment["tax_year"] == 2025

    old_debt = _case("11-F07")
    assert old_debt["both_dates_in_window"] is False
    assert old_debt["tax_year"] == 2026


def test_full_partial_and_overpayment_splits_reconcile_without_invented_cash() -> None:
    full = _case("11-F08")
    assert _int(full, "cold_rent_share") + _int(full, "advance_share") == _int(full, "payment")
    assert full["rounding"] == "none"

    partial = _case("11-F09")
    assert _int(partial, "cold_rent_share") + _int(partial, "advance_share") == _int(
        partial, "payment"
    )
    assert _int(partial, "cold_rent_share") + _int(partial, "cold_rent_open") == _int(
        partial, "cold_rent_due"
    )
    assert _int(partial, "advance_share") + _int(partial, "advance_open") == _int(
        partial, "advance_due"
    )
    assert partial["open_amounts_exported"] is False

    overpayment = _case("11-F15")
    assert _int(overpayment, "cold_rent_share") + _int(overpayment, "advance_share") + _int(
        overpayment, "renter_credit"
    ) == _int(overpayment, "payment")
    assert _int(overpayment, "cold_rent_share") + _int(overpayment, "advance_share") == _int(
        overpayment, "income_booked"
    )
    assert overpayment["renter_credit_is_income"] is False


def test_refund_and_deposit_treatments_are_result_safe() -> None:
    refund = _case("11-F10")
    assert _int(refund, "advance_income_before") - _int(refund, "amount") == _int(
        refund, "advance_income_after"
    )
    assert refund["direction"] == "ausgabe"
    assert refund["datev_booking"] == "reverse_revenue_payment"

    deposit = _case("11-F11")
    assert _int(deposit, "anlage_v_effect") == 0
    assert deposit["datev_account_kind"] == "clearing"
    assert deposit["return_is_result_neutral"] is True
    assert deposit["production_blocked"] is True


def test_skr_variants_and_debit_credit_arithmetic_keep_format_values_blocked() -> None:
    balance = _case("11-F13")
    assert sum(_ints(balance, "debit_parts")) == _int(balance, "debit_total")
    assert sum(_ints(balance, "credit_parts")) == _int(balance, "credit_total")
    assert _int(balance, "debit_total") == _int(balance, "credit_total")
    assert balance["extf_single_row_orientation_unverified"] is True

    variants = _case("11-F14")
    assert variants["skr03_expense"] != variants["skr04_expense"]
    assert variants["skr03_bank"] != variants["skr04_bank"]
    assert variants["only_accounts_change"] is True
    assert variants["missing_account_readiness"] == "yellow"
    assert variants["production_blocked"] is True


def test_readiness_has_exact_red_and_yellow_severity_contract() -> None:
    assert set(READINESS_FINDINGS) == {
        "R-r1",
        "R-r2",
        "R-r3",
        "R-g1",
        "R-g2",
        "R-g3",
        "R-g4",
        "R-g5",
        "R-g6",
        "R-g7",
        "R-g8",
    }
    severities = tuple(value[0] for value in READINESS_FINDINGS.values())
    assert severities.count("rot") == 3
    assert severities.count("gelb") == 8
    assert READINESS_FINDINGS["R-r1"] == ("rot", "payment_without_date")
    assert READINESS_FINDINGS["R-r2"] == (
        "rot",
        "datev_without_adviser_or_client_number",
    )
    assert READINESS_FINDINGS["R-g8"] == ("gelb", "vat_case_detected")


def test_vat_warning_and_windows_1252_crlf_contract_are_exact() -> None:
    vat = _case("11-F16")
    assert _int(vat, "net_reference_only") + _int(vat, "vat_reference_only") == _int(
        vat, "gross_amount"
    )
    assert _int(vat, "exported_amount") == _int(vat, "gross_amount")
    assert vat["readiness"] == "yellow"
    assert vat["bu_key"] is None
    assert vat["vat_split_performed"] is False
    assert vat["warning"] == (
        "USt-Fall erkannt — dieser Export enthält keine Umsatzsteuer-Logik. "
        "Bitte mit Ihrem Steuerberater klären."
    )

    booking = _case("11-F12")
    probe = booking["encoding_probe"]
    assert isinstance(probe, str)
    encoded = probe.encode("windows-1252")
    assert encoded.decode("windows-1252") == probe
    assert booking["line_ending"] == "\r\n"
    assert b"\r\n" in (probe + "\r\n").encode("windows-1252")
    assert EXTF_WORKING_CONVENTION["encoding"] == "windows-1252"
    assert EXTF_WORKING_CONVENTION["line_ending"] == "\r\n"
    assert EXTF_WORKING_CONVENTION["production_blocked"] is True
