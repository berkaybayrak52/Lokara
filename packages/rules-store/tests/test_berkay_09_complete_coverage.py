"""Green coverage and arithmetic checks for the data-only Page 02 oracle."""

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from runpy import run_path

from berkay_09_golden import (
    ALLOCABLE_CATALOGUE,
    NON_ALLOCABLE_CATALOGUE_IDS,
    PAGE_02_GOLDENS,
)

EXPECTED_IDS = {f"09-F{number:02}" for number in range(1, 33)}


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


def _assert_allocable_reconciliation(case_id: str) -> None:
    case = PAGE_02_GOLDENS[case_id]
    assert sum(_ints(case, "shares")) == _int(case, "renter_total")
    assert _int(case, "renter_total") + _int(case, "owner") == _int(case, "allocable")
    if "non_allocable" in case:
        assert _int(case, "allocable") + _int(case, "non_allocable") == _int(case, "gross")


def test_every_page_02_fixture_has_exactly_one_oracle() -> None:
    assert set(PAGE_02_GOLDENS) == EXPECTED_IDS


def test_catalogue_identity_surface_is_complete_and_unique() -> None:
    allocable_ids = [row[0] for row in ALLOCABLE_CATALOGUE]
    assert len(allocable_ids) == 32
    assert len(set(allocable_ids)) == 32
    assert len(NON_ALLOCABLE_CATALOGUE_IDS) == 11
    assert len(set(NON_ALLOCABLE_CATALOGUE_IDS)) == 11
    assert set(allocable_ids).isdisjoint(NON_ALLOCABLE_CATALOGUE_IDS)


def test_every_nr_17_catalogue_row_requires_specific_naming() -> None:
    nr_17_rows = [row for row in ALLOCABLE_CATALOGUE if row[2] == "2 Nr. 17"]
    assert len(nr_17_rows) == 5
    assert all(row[6] for row in nr_17_rows)
    assert all(not row[6] for row in ALLOCABLE_CATALOGUE if row[2] != "2 Nr. 17")


def test_plain_and_split_invoices_reconcile() -> None:
    for case_id in (
        "09-F01",
        "09-F04",
        "09-F05",
        "09-F06",
        "09-F15",
        "09-F16",
        "09-F17",
        "09-F18",
        "09-F27",
        "09-F28",
        "09-F31",
    ):
        _assert_allocable_reconciliation(case_id)


def test_wholly_non_allocable_cases_never_enter_a_denominator() -> None:
    for case_id in ("09-F02", "09-F03", "09-F10", "09-F13", "09-F30"):
        case = PAGE_02_GOLDENS[case_id]
        assert _int(case, "allocable") == 0
        assert _int(case, "non_allocable") == _int(case, "gross")


def test_key_and_lift_variants_reconcile_and_have_zero_sum_deltas() -> None:
    for case_id, first_prefix, second_prefix in (
        ("09-F07", "default", "contract"),
        ("09-F14", "default", "exception"),
    ):
        case = PAGE_02_GOLDENS[case_id]
        gross = _int(case, "gross")
        for prefix in (first_prefix, second_prefix):
            shares = _ints(case, f"{prefix}_shares")
            renter_total = _int(case, f"{prefix}_renter_total")
            owner = _int(case, f"{prefix}_owner")
            assert sum(shares) == renter_total
            assert renter_total + owner == gross
        assert sum(_ints(case, "delta")) == 0


def test_consumption_and_per_contract_naming_results_reconcile() -> None:
    for case_id in ("09-F08", "09-F09"):
        case = PAGE_02_GOLDENS[case_id]
        assert sum(_ints(case, "shares")) == _int(case, "renter_total")
        assert _int(case, "renter_total") + _int(case, "owner") == _int(case, "gross")


def test_date_and_fibre_caps_round_before_distribution() -> None:
    version = PAGE_02_GOLDENS["09-F11"]
    assert _half_up(
        _int(version, "gross") * _int(version, "allocable_days"),
        _int(version, "period_days"),
    ) == _int(version, "allocable")
    assert _int(version, "allocable") + _int(version, "non_allocable") == _int(version, "gross")

    fibre = PAGE_02_GOLDENS["09-F12"]
    assert _int(fibre, "units") * _int(fibre, "annual_cap_per_unit") == _int(fibre, "allocable")
    _assert_allocable_reconciliation("09-F12")


def test_labour_chain_reconciles_independently_of_cost_allocation() -> None:
    case = PAGE_02_GOLDENS["09-F17"]
    assert sum(_ints(case, "labour_shares")) == _int(case, "labour_renter_total")
    assert _int(case, "labour_renter_total") + _int(case, "labour_owner") == _int(case, "labour")
    assert _ints(case, "labour_shares")[2] == 5_738


def test_complete_catalogue_run_matches_page_01_and_answer_03() -> None:
    case = PAGE_02_GOLDENS["09-F19"]
    rows = case["catalogue_rows"]
    assert isinstance(rows, tuple)
    assert len(rows) == 13
    assert sum(row[1] for row in rows) == _int(case, "allocable")
    assert sum(row[2] for row in rows) == _int(case, "labour")
    assert sum(row[3] for row in rows) == _int(case, "renter_total")
    assert sum(row[4] for row in rows) == _int(case, "owner")
    assert sum(_ints(case, "non_allocable_parts")) == _int(case, "non_allocable")
    assert _int(case, "renter_total") + _int(case, "owner") + _int(case, "non_allocable") == _int(
        case, "invoice_total"
    )

    page_01_module = run_path(
        str(Path(__file__).parents[2] / "domain" / "tests" / "berkay_01_golden.py")
    )
    page_01 = page_01_module["PAGE_01_GOLDENS"]["08-F01"]
    page_01_f21 = page_01_module["PAGE_01_GOLDENS"]["08-F21"]
    assert _int(case, "allocable") == page_01["cost_total"]
    assert _int(case, "renter_total") == page_01["allocated_total"]
    assert _int(case, "owner") == page_01["owner_residual"]
    assert _int(case, "non_allocable") == page_01_f21["block_b_non_allocable"]


def test_unknown_zero_and_credit_lines_preserve_their_distinct_paths() -> None:
    unknown = PAGE_02_GOLDENS["09-F20"]
    assert _int(unknown, "unnamed_allocable") == 0
    assert _int(unknown, "unnamed_non_allocable") == _int(unknown, "gross")
    assert sum(_ints(unknown, "named_shares")) == _int(unknown, "named_renter_total")
    assert _int(unknown, "named_renter_total") + _int(unknown, "named_owner") == _int(
        unknown, "gross"
    )

    zero = PAGE_02_GOLDENS["09-F21"]
    assert _int(zero, "zero_gross") == 0
    assert zero["zero_printed"] is False
    assert sum(_ints(zero, "reference_shares")) == _int(zero, "reference_renter_total")
    assert _int(zero, "reference_renter_total") + _int(zero, "reference_owner") == _int(
        zero, "reference_gross"
    )

    credit = PAGE_02_GOLDENS["09-F22"]
    assert sum(_ints(credit, "credit_shares")) == _int(credit, "credit_renter_total")
    assert _int(credit, "credit_renter_total") + _int(credit, "credit_owner") == _int(
        credit, "credit"
    )
    assert _int(credit, "net_renter_total") + _int(credit, "net_owner") == _int(credit, "net_cost")


def test_invalid_amounts_are_hard_blocks() -> None:
    labour = PAGE_02_GOLDENS["09-F23"]
    assert _int(labour, "labour") > _int(labour, "allocable")
    assert labour["result"] == "hard_block"

    split = PAGE_02_GOLDENS["09-F24"]
    assert _int(split, "non_allocable") > _int(split, "gross")
    assert split["result"] == "hard_block"


def test_missing_consumption_keeps_all_three_explicit_paths() -> None:
    case = PAGE_02_GOLDENS["09-F25"]
    gross = _int(case, "gross")
    for prefix in ("measured", "area", "unconfirmed"):
        assert _int(case, f"{prefix}_renter_total") + _int(case, f"{prefix}_owner") == gross
    assert sum(_ints(case, "measured_shares")) == _int(case, "measured_renter_total")
    assert sum(_ints(case, "area_shares")) == _int(case, "area_renter_total")


def test_new_cost_cap_keeps_the_full_period_denominator() -> None:
    case = PAGE_02_GOLDENS["09-F26"]
    assert _half_up(
        _int(case, "gross") * _int(case, "service_days"), _int(case, "period_days")
    ) == _int(case, "with_clause_allocable")
    assert _int(case, "with_clause_allocable") + _int(case, "with_clause_non_allocable") == _int(
        case, "gross"
    )
    assert sum(_ints(case, "shares")) == _int(case, "renter_total")
    assert _int(case, "renter_total") + _int(case, "owner") == _int(case, "with_clause_allocable")


def test_payment_principle_and_duplicate_guard_reconcile() -> None:
    payment = PAGE_02_GOLDENS["09-F29"]
    assert sum(_ints(payment, "payments")) == _int(payment, "gross")
    assert sum(_ints(payment, "shares")) == _int(payment, "renter_total")
    assert _int(payment, "renter_total") + _int(payment, "owner") == _int(payment, "gross")

    duplicate = PAGE_02_GOLDENS["09-F32"]
    assert _int(duplicate, "before") - _int(duplicate, "duplicate") == _int(duplicate, "after")
    assert sum(_ints(duplicate, "shares")) == _int(duplicate, "renter_total")
    assert _int(duplicate, "renter_total") + _int(duplicate, "owner") == _int(duplicate, "after")
    assert sum(_ints(duplicate, "delta")) == -_int(duplicate, "duplicate")
