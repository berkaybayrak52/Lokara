"""Coverage and arithmetic checks for the data-only Page 08 oracle."""

from decimal import ROUND_HALF_UP, Decimal

from berkay_15_golden import MATCHING_CONTRACT, PAGE_08_GOLDENS

EXPECTED_IDS = {f"BANKMATCH-F{number:02}" for number in range(1, 14)}


def _case(case_id: str) -> dict[str, object]:
    case = PAGE_08_GOLDENS[case_id]
    assert isinstance(case, dict)
    return case


def _int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int)
    return value


def _ints(case: dict[str, object], key: str) -> tuple[int, ...]:
    value = case[key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) for item in value)
    return value


def _confidence(signals: tuple[int, ...]) -> int:
    cap = MATCHING_CONTRACT["confidence_cap"]
    assert isinstance(cap, int)
    return min(cap, sum(signals))


def _decimal_eur_to_cents(value: str) -> int:
    return int((Decimal(value) * 100).quantize(Decimal("1"), ROUND_HALF_UP))


def test_promised_fixture_id_surface_is_exact() -> None:
    assert set(PAGE_08_GOLDENS) == EXPECTED_IDS


def test_exactly_thirteen_cases_are_executable() -> None:
    assert len(PAGE_08_GOLDENS) == 13
    assert all(case["executable"] is True for case in PAGE_08_GOLDENS.values())


def test_f03_potential_duplicate_forces_review_and_assigns_nothing() -> None:
    case = _case("BANKMATCH-F03")
    assert _int(case, "amount") == 108_000
    assert _int(case, "open_before") == 108_000
    assert case["known_iban"] == "unique"
    assert case["purpose"] == "Miete Juli"
    assert case["is_potential_duplicate"] is True
    assert case["potential_duplicate_is_distinct_transaction"] is True
    assert _int(case, "unique_iban_signal") == 60
    assert MATCHING_CONTRACT["auto_requires_unique_known_iban"] is True
    assert case["potential_duplicate_decision"] == "needs_review"
    assert _int(case, "assigned_before_confirmation") == 0
    assert case["duplicate_confirmation_result"] == "discard_without_settlement"
    assert _int(case, "assigned_after_duplicate_confirmation") == 0
    assert case["genuine_payment_confirmation_result"] == "delegate_to_F04_fifo_and_credit"


def test_f03_exact_same_id_reimport_is_silently_deduplicated_before_scoring() -> None:
    case = _case("BANKMATCH-F03")
    assert case["exact_reimport_same_id"] is True
    assert case["exact_reimport_dedupe_stage"] == "before_channel_and_scoring"
    assert case["exact_reimport_second_scoring"] is False
    assert case["exact_reimport_second_review"] is False
    assert _int(case, "exact_reimport_settlement_count") == 1
    assert _int(case, "exact_reimport_total_assigned") == 108_000


def test_all_stated_signal_scores_are_exact() -> None:
    for case_id in ("BANKMATCH-F01", "BANKMATCH-F02", "BANKMATCH-F04", "BANKMATCH-F08"):
        case = _case(case_id)
        assert _confidence(_ints(case, "signals")) == _int(case, "confidence")

    for case_id in ("BANKMATCH-F09", "BANKMATCH-F11", "BANKMATCH-F12"):
        case = _case(case_id)
        assert _confidence(_ints(case, "signals")) == _int(case, "confidence")

    joint = _case("BANKMATCH-F07")
    candidate_signals = joint["candidate_signals"]
    assert isinstance(candidate_signals, tuple)
    assert (
        tuple(_confidence(signals) for signals in candidate_signals)
        == joint["candidate_confidences"]
    )

    first = _case("BANKMATCH-F13")
    assert _confidence(_ints(first, "initial_signals")) == _int(first, "initial_confidence")


def test_unique_iban_controls_auto_match_not_the_numeric_threshold() -> None:
    assert MATCHING_CONTRACT["auto_requires_unique_known_iban"] is True
    for case_id in (
        "BANKMATCH-F01",
        "BANKMATCH-F04",
        "BANKMATCH-F08",
        "BANKMATCH-F11",
        "BANKMATCH-F12",
    ):
        assert _case(case_id)["decision"] == "auto_match"

    assert _case("BANKMATCH-F04")["confidence"] == 60
    assert _case("BANKMATCH-F07")["decision"] == "needs_review"
    assert _case("BANKMATCH-F07")["candidate_confidences"] == (65, 50)


def test_review_and_unmatched_cases_assign_nothing_automatically() -> None:
    for case_id in ("BANKMATCH-F02", "BANKMATCH-F07", "BANKMATCH-F09", "BANKMATCH-F13"):
        case = _case(case_id)
        decision = case.get("decision", case.get("initial_decision"))
        assert decision == "needs_review"
        assert _int(case, "assigned_before_confirmation") == 0

    unmatched = _case("BANKMATCH-F05")
    assert unmatched["candidate_confidences"] == (30, 30)
    assert unmatched["decision"] == "unmatched"
    assert _int(unmatched, "assigned") == 0


def test_designated_payments_precede_fifo_and_settle_exactly() -> None:
    assert MATCHING_CONTRACT["designated_payment_precedes_fifo"] is True
    for case_id in ("BANKMATCH-F01", "BANKMATCH-F08", "BANKMATCH-F12"):
        case = _case(case_id)
        assert str(case["settlement_order"]).startswith("designated_")
        assert _int(case, "assigned") == _int(case, "amount" if "amount" in case else "payment")
        assert case["status_after"] == "settled"

    fifo = _case("BANKMATCH-F04")
    paid = _ints(fifo, "receivables_paid")
    assert fifo["settlement_order"] == "fifo"
    assert sum(paid) == _int(fifo, "assigned")
    assert sum(paid) + _int(fifo, "credit") == _int(fifo, "amount")


def test_reversal_is_the_exact_inverse_of_the_original_allocation() -> None:
    case = _case("BANKMATCH-F06")
    assert _int(case, "original_payment") + _int(case, "reversal_amount") == _int(case, "net_paid")
    assert _int(case, "open_after") == _int(case, "original_payment")
    assert case["status_after"] == "open"
    assert MATCHING_CONTRACT["payment_ledger"] == "append_only_with_compensating_reversals"


def test_partial_payment_component_split_and_open_amount_reconcile() -> None:
    case = _case("BANKMATCH-F11")
    expected = _int(case, "expected")
    payment = _int(case, "payment")
    nominal = _ints(case, "nominal_components")
    paid = _ints(case, "paid_components")

    calculated = tuple(
        int(
            (Decimal(component * payment) / Decimal(expected)).quantize(Decimal("1"), ROUND_HALF_UP)
        )
        for component in nominal
    )
    assert calculated == paid
    assert sum(nominal) == expected
    assert sum(paid) == payment
    assert payment + _int(case, "open_after") == expected
    assert _int(case, "nk_advance_paid") == paid[1]


def test_float_to_cent_conversion_uses_decimal_half_up_only_at_import() -> None:
    case = _case("BANKMATCH-F10")
    imports = case["decimal_imports"]
    assert isinstance(imports, tuple)
    for source, expected in imports:
        assert _decimal_eur_to_cents(source) == expected


def test_page_01_nachzahlung_handoff_is_cent_identical() -> None:
    case = _case("BANKMATCH-F12")
    assert _int(case, "statement_nachzahlung") == _int(case, "receivable_expected")
    assert _int(case, "receivable_expected") == _int(case, "payment")
    assert _int(case, "payment") == _int(case, "assigned")
    assert case["category"] == "nk_nachzahlung"


def test_duplicate_iban_learning_and_account_scope_contracts_remain_explicit() -> None:
    assert MATCHING_CONTRACT["potential_duplicate_result"] == "needs_review"
    assert MATCHING_CONTRACT["exact_reimport_result"] == "dedupe_by_provider_transaction_id"
    assert MATCHING_CONTRACT["iban_history"] == "versioned_after_confirmed_non_null_match"
    assert MATCHING_CONTRACT["cross_account_candidates"] == "forbidden"
    scoped = MATCHING_CONTRACT["account_scope_required_on"]
    assert isinstance(scoped, tuple)
    assert len(scoped) == 6
