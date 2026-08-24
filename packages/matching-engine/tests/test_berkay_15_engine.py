"""Executable RED fixtures for the pure bank-matching engine — `docs/15-bank-matching.md`.

Every expected number in this file is read out of the approved, data-only oracle
`packages/rules-store/tests/berkay_15_golden.py` (`PAGE_08_GOLDENS`, `MATCHING_CONTRACT`),
which `docs/15` line 11 names as the single location of the thirteen `BANKMATCH-F01`-`F13`
cases.  Nothing is restated as a literal: if the oracle ever drifts, these tests fail.
The oracle itself is imported through `conftest.py`, not copied.

**Why this file is RED.**  `packages/matching-engine/src/lokara_matching_engine/` contains
only `py.typed`.  The engine does not exist, so this module fails at import.  That is the
intended RED state: a different agent implements against these names.  The test author
writes no implementation (`CLAUDE.md` § 10: no agent may write both a test and the
implementation that satisfies it).

**What is asserted, and from where.**

- signals, confidence, decision -> `docs/15` § 4 and the oracle's `signals`
  / `candidate_signals` / `confidence` entries, in the order
  `(iban, amount, code_or_surname, e2e, period)`;
- Auto eligibility -> `docs/15` § 2 last paragraph: CSV row 171's "Auto = 40-79" is
  shorthand, *not* a general score threshold.  A unique known IBAN may Auto-Match at 60
  (`F04`, `F11`); a shared IBAN never Auto-Matches, not even at 65 (`F07`);
- settlement -> `docs/15` § 5.1 (§ 366 Abs. 1 designation before Page 08 FIFO, § 367
  costs -> interest -> principal, § 362 fulfilment) and § 5.2 (proportional split
  reconciled by Largest Remainder);
- reversal -> `docs/15` § 5.3;
- account isolation -> `docs/15` §§ 4 and 6.

**Where `docs/15` is silent, this file asserts the refusal, not a guess.**  § 5.2 states
that the tie-break between equal fractional remainders is missing from the authoritative
source and must be added there before an implementation may claim that branch.  The tie
test therefore requires `TieBreakUnspecifiedError`; it does not invent an ordering.
"""

from datetime import date
from typing import Final, cast

import pytest
from berkay_15_golden import MATCHING_CONTRACT, PAGE_08_GOLDENS
from lokara_matching_engine import (
    BankTransactionInput,
    CandidateScore,
    Decision,
    IbanOwnership,
    Proposal,
    ReceivableInput,
    RenterProfileInput,
    SettlementResult,
    TieBreakUnspecifiedError,
    parse_provider_amount_to_cents,
    propose,
    reverse,
    score_candidate,
    settle,
    should_learn_iban,
    split_principal,
)

EXPECTED_IDS: Final = {f"BANKMATCH-F{number:02}" for number in range(1, 14)}

# A scoring candidate is the account-scoped triple of § 4: the open receivable, the
# renter's matching profile and how many active renters in *this* account own the
# transaction's IBAN (§ 3.3 — ambiguity is resolved inside the account, before scoring).
Candidate = tuple[ReceivableInput, RenterProfileInput, IbanOwnership]
ProviderIdentity = tuple[str, str, str]


# --------------------------------------------------------------------------------------
# Oracle accessors — every expected value comes through one of these.
# --------------------------------------------------------------------------------------


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
    return cast(tuple[int, ...], value)


def _str(case: dict[str, object], key: str) -> str:
    value = case[key]
    assert isinstance(value, str)
    return value


def _signal_tuples(case: dict[str, object], key: str) -> tuple[tuple[int, ...], ...]:
    value = case[key]
    assert isinstance(value, tuple)
    return cast(tuple[tuple[int, ...], ...], value)


def _contract_int(key: str) -> int:
    value = MATCHING_CONTRACT[key]
    assert isinstance(value, int)
    return value


def _contract_strs(key: str) -> tuple[str, ...]:
    value = MATCHING_CONTRACT[key]
    assert isinstance(value, tuple)
    return cast(tuple[str, ...], value)


# --------------------------------------------------------------------------------------
# Shared, oracle-derived scenario data.
# --------------------------------------------------------------------------------------

ACCOUNT_A: Final = "account-a"
ACCOUNT_B: Final = "account-b"
BANK_ACCOUNT_A1: Final = "bank-account-a1"
BANK_ACCOUNT_A2: Final = "bank-account-a2"
BANK_ACCOUNT_B1: Final = "bank-account-b1"

RENTER_MUELLER: Final = "renter-mueller"
RENTER_SCHMIDT: Final = "renter-schmidt"
RENTER_BECKER: Final = "renter-becker"
RENTER_WEBER: Final = "renter-weber"
RENTER_FOREIGN: Final = "renter-foreign"

IBAN_MUELLER: Final = "DE02120300000000202051"
IBAN_SHARED: Final = "DE02100500000054540402"
IBAN_WEBER: Final = "DE02300209000106531065"

CODE_MUELLER: Final = "KDNR-4711"
CODE_SCHMIDT: Final = "KDNR-4712"
CODE_BECKER: Final = "KDNR-8899"

PERIOD_JULY: Final = "2026-07"
PERIOD_AUGUST: Final = "2026-08"
PERIOD_SEPTEMBER: Final = "2026-09"
STATEMENT_PERIOD: Final = "2025"

JULY_DUE: Final = date(2026, 7, 3)
AUGUST_DUE: Final = date(2026, 8, 3)

# The nominal rent components and the expected rent both come from `BANKMATCH-F11`.
# `docs/15` § 3.2 requires the components to sum to `expected_cents`; F11's nominal
# triple is (base_rent, nk_advance, heating_advance) and these fixtures rent no garage.
NOMINAL_RENT: Final = _ints(_case("BANKMATCH-F11"), "nominal_components")
RENT_COMPONENTS: Final = (*NOMINAL_RENT, 0)
RENT_EXPECTED: Final = _int(_case("BANKMATCH-F11"), "expected")

# Status words are read from the oracle too, never spelled out here.
STATUS_SETTLED: Final = _str(_case("BANKMATCH-F01"), "status_after")
STATUS_PARTIAL: Final = _str(_case("BANKMATCH-F11"), "status_after")
STATUS_OPEN: Final = _str(_case("BANKMATCH-F06"), "status_after")

_OWNERSHIP_BY_ORACLE_WORD: Final = {
    "unique": IbanOwnership.UNIQUE,
    "shared": IbanOwnership.SHARED,
}


def _transaction(
    *,
    account_id: str = ACCOUNT_A,
    bank_account_id: str = BANK_ACCOUNT_A1,
    provider_transaction_id: str = "prov-tx-1",
    amount_cents: int = RENT_EXPECTED,
    bank_booking_date: date = date(2026, 7, 5),
    finapi_booking_date: date | None = None,
    value_date: date | None = None,
    counterpart_iban: str | None = IBAN_MUELLER,
    counterpart_name: str | None = "Mueller",
    purpose: str | None = None,
    end_to_end_reference: str | None = None,
    counterpart_mandate_reference: str | None = None,
    bank_transaction_code: str | None = None,
    provider_type: str | None = None,
    is_potential_duplicate: bool = False,
) -> BankTransactionInput:
    """Build a normalized transaction (`docs/15` § 3.1)."""
    return BankTransactionInput(
        account_id=account_id,
        bank_account_id=bank_account_id,
        provider_transaction_id=provider_transaction_id,
        amount_cents=amount_cents,
        bank_booking_date=bank_booking_date,
        finapi_booking_date=(
            bank_booking_date if finapi_booking_date is None else finapi_booking_date
        ),
        value_date=bank_booking_date if value_date is None else value_date,
        counterpart_iban=counterpart_iban,
        counterpart_name=counterpart_name,
        purpose=purpose,
        end_to_end_reference=end_to_end_reference,
        counterpart_mandate_reference=counterpart_mandate_reference,
        bank_transaction_code=bank_transaction_code,
        provider_type=provider_type,
        is_potential_duplicate=is_potential_duplicate,
    )


def _receivable(
    *,
    receivable_id: str,
    period: str,
    due_date: date,
    account_id: str = ACCOUNT_A,
    renter_id: str = RENTER_MUELLER,
    tenancy_id: str = "tenancy-mueller-1",
    source_type: str = "recurring_rent",
    source_id: str | None = None,
    expected_cents: int = RENT_EXPECTED,
    open_cents: int | None = None,
    status: str = "open",
    category: str = "rent",
    principal_components: tuple[int, ...] = RENT_COMPONENTS,
    open_costs_cents: int = 0,
    open_interest_cents: int = 0,
    open_principal_cents: int | None = None,
) -> ReceivableInput:
    """Build a normalized receivable (`docs/15` § 3.2).

    `principal_components` is positional in the § 3.2 order
    `(base_rent, nk_advance, heating_advance, garage)` and sums to `expected_cents`.
    """
    resolved_open = expected_cents if open_cents is None else open_cents
    return ReceivableInput(
        id=receivable_id,
        account_id=account_id,
        renter_id=renter_id,
        tenancy_id=tenancy_id,
        source_type=source_type,
        source_id=source_id,
        period=period,
        due_date=due_date,
        expected_cents=expected_cents,
        open_cents=resolved_open,
        status=status,
        category=category,
        principal_components=principal_components,
        open_costs_cents=open_costs_cents,
        open_interest_cents=open_interest_cents,
        open_principal_cents=(
            resolved_open if open_principal_cents is None else open_principal_cents
        ),
    )


def _profile(
    *,
    renter_id: str = RENTER_MUELLER,
    account_id: str = ACCOUNT_A,
    payment_code: str | None = CODE_MUELLER,
    normalized_surname: str = "mueller",
    known_ibans: tuple[str, ...] = (IBAN_MUELLER,),
) -> RenterProfileInput:
    """Build a renter matching profile (`docs/15` § 3.3)."""
    return RenterProfileInput(
        account_id=account_id,
        renter_id=renter_id,
        payment_code=payment_code,
        normalized_surname=normalized_surname,
        known_ibans=known_ibans,
    )


def _july_rent(
    *,
    receivable_id: str = "receivable-july",
    account_id: str = ACCOUNT_A,
    renter_id: str = RENTER_MUELLER,
    open_costs_cents: int = 0,
    open_interest_cents: int = 0,
) -> ReceivableInput:
    return _receivable(
        receivable_id=receivable_id,
        period=PERIOD_JULY,
        due_date=JULY_DUE,
        account_id=account_id,
        renter_id=renter_id,
        open_costs_cents=open_costs_cents,
        open_interest_cents=open_interest_cents,
    )


def _august_rent(
    *,
    receivable_id: str = "receivable-august",
    account_id: str = ACCOUNT_A,
    renter_id: str = RENTER_MUELLER,
) -> ReceivableInput:
    return _receivable(
        receivable_id=receivable_id,
        period=PERIOD_AUGUST,
        due_date=AUGUST_DUE,
        account_id=account_id,
        renter_id=renter_id,
    )


def _propose(
    transaction: BankTransactionInput,
    candidates: tuple[Candidate, ...],
    already_imported: frozenset[ProviderIdentity] = frozenset(),
) -> Proposal:
    return propose(transaction, candidates, already_imported_provider_ids=already_imported)


def _assigned(result: SettlementResult) -> int:
    """Total cents actually applied to receivables (§ 5.1 steps 3-4)."""
    return sum(
        allocation.costs_cents + allocation.interest_cents + allocation.principal_cents
        for allocation in result.allocations
    )


def _assert_no_money_on_proposal(proposal: Proposal, assigned_before_confirmation: int) -> None:
    """`docs/15` § 4 step 6 and § 5: scoring and settlement are separate.

    A proposal is a proposal.  It carries no allocation, no credit and no assigned
    amount, so nothing can be settled before an Auto-Match or an explicit confirmation.
    """
    assert assigned_before_confirmation == 0
    assert proposal.decision is not Decision.AUTO_MATCH
    for money_attribute in ("allocations", "credit_cents", "assigned_cents", "amount_cents"):
        assert not hasattr(proposal, money_attribute), (
            f"a proposal must not carry {money_attribute!r}: docs/15 § 4 forbids settling "
            "any amount before Auto-Match or confirmation"
        )


# --------------------------------------------------------------------------------------
# BANKMATCH-F10 — the only float boundary in the system (docs/15 §§ 2 row 180, 3.1).
# --------------------------------------------------------------------------------------


def test_f10_provider_amount_is_imported_with_decimal_half_up() -> None:
    case = _case("BANKMATCH-F10")
    assert _str(case, "rounding") == MATCHING_CONTRACT["float_import_rounding"]
    imports = case["decimal_imports"]
    assert isinstance(imports, tuple)

    for provider_amount, expected_cents in imports:
        assert isinstance(provider_amount, str)
        assert isinstance(expected_cents, int)
        cents = parse_provider_amount_to_cents(provider_amount)
        assert cents == expected_cents
        assert type(cents) is int


def test_f10_float_input_is_rejected_at_the_import_boundary() -> None:
    """`docs/15` § 3.1: "binary-float arithmetic is forbidden".

    A provider amount arrives as a string and is parsed as `Decimal`.  Accepting a
    `float` would silently reintroduce binary rounding at the one boundary the contract
    isolates, so the parser must refuse it instead of quietly succeeding.
    """
    with pytest.raises((TypeError, ValueError)):
        parse_provider_amount_to_cents(cast(str, 1080.005))


# --------------------------------------------------------------------------------------
# Scoring and decision (docs/15 § 4).
# --------------------------------------------------------------------------------------


def test_f01_unique_iban_and_designated_period_settle_the_july_debt() -> None:
    case = _case("BANKMATCH-F01")
    july = _july_rent()
    august = _august_rent()
    profile = _profile()
    # The purpose carries the receivable's own period token in the normalized `YYYY-MM`
    # form of § 3.2.  `docs/15` does not state which other purpose spellings (German
    # month names, "Juli 26") count as the period token, so no fixture depends on one.
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        purpose=f"Miete {PERIOD_JULY}",
    )

    score: CandidateScore = score_candidate(transaction, july, profile, IbanOwnership.UNIQUE)
    assert score.signals == _ints(case, "signals")
    assert score.confidence == _int(case, "confidence")
    assert score.confidence == min(_contract_int("confidence_cap"), sum(score.signals))

    proposal = _propose(transaction, ((july, profile, IbanOwnership.UNIQUE),))
    assert proposal.decision == _str(case, "decision")
    assert proposal.decision is Decision.AUTO_MATCH
    assert isinstance(proposal.reason, str)
    assert proposal.reason != ""

    assert _str(case, "settlement_order") == "designated_period"
    assert MATCHING_CONTRACT["designated_payment_precedes_fifo"] is True
    result = settle(transaction, (july, august), designated_period=PERIOD_JULY)

    assert tuple(allocation.receivable_id for allocation in result.allocations) == (july.id,)
    allocation = result.allocations[0]
    assert allocation.principal_cents == _int(case, "assigned")
    assert allocation.principal_components[:3] == _ints(case, "components_paid")
    assert sum(allocation.principal_components) == allocation.principal_cents
    assert allocation.open_cents == _int(case, "open_after")
    assert allocation.status == _str(case, "status_after")
    assert _assigned(result) == _int(case, "assigned")
    assert result.credit_cents == 0
    assert _assigned(result) + result.credit_cents == transaction.amount_cents


def test_f02_unknown_iban_with_surname_evidence_is_review_and_assigns_nothing() -> None:
    case = _case("BANKMATCH-F02")
    july = _july_rent()
    # The renter has no IBAN history yet, so the transaction's IBAN is owned by nobody
    # in this account (§ 3.3).
    profile = _profile(known_ibans=())
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        purpose="Zahlung Mueller",
    )

    score = score_candidate(transaction, july, profile, IbanOwnership.UNKNOWN)
    assert score.signals == _ints(case, "signals")
    assert score.confidence == _int(case, "confidence")
    assert score.confidence >= _contract_int("review_floor")

    proposal = _propose(transaction, ((july, profile, IbanOwnership.UNKNOWN),))
    assert proposal.decision == _str(case, "decision")
    ranked = proposal.ranked_candidates
    assert ranked[_int(case, "rank") - 1].receivable_id == july.id
    _assert_no_money_on_proposal(proposal, _int(case, "assigned_before_confirmation"))


def test_f09_payment_code_and_surname_are_mutually_exclusive() -> None:
    """`docs/15` § 4: "take 15 or 10, not both"."""
    case = _case("BANKMATCH-F09")
    assert case["counterpart_iban"] is None
    weights = MATCHING_CONTRACT["weights"]
    assert isinstance(weights, dict)

    july = _july_rent()
    profile = _profile(known_ibans=())
    # The purpose carries BOTH the payment code and the surname.  45, not 55, is the
    # whole point of this fixture.
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        counterpart_iban=None,
        counterpart_name=None,
        purpose=f"{CODE_MUELLER} Mueller",
    )

    score = score_candidate(transaction, july, profile, IbanOwnership.UNKNOWN)
    assert score.signals == _ints(case, "signals")
    assert score.confidence == _int(case, "confidence")
    assert score.signals[2] == weights["payment_code"]
    assert score.signals[2] != weights["payment_code"] + weights["surname"]

    proposal = _propose(transaction, ((july, profile, IbanOwnership.UNKNOWN),))
    assert proposal.decision == _str(case, "decision")
    _assert_no_money_on_proposal(proposal, _int(case, "assigned_before_confirmation"))


def test_f09_null_iban_is_never_learned() -> None:
    case = _case("BANKMATCH-F09")
    assert case["iban_learned"] is False
    assert MATCHING_CONTRACT["iban_history"] == "versioned_after_confirmed_non_null_match"

    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        counterpart_iban=None,
        counterpart_name=None,
        purpose=f"{CODE_MUELLER} Mueller",
    )
    # Even a confirmed match learns nothing when the counterpart IBAN is null (§ 3.3).
    assert should_learn_iban(transaction, True) is False


def test_f02_confirmed_non_null_iban_is_learned_but_an_unconfirmed_one_is_not() -> None:
    case = _case("BANKMATCH-F02")
    assert case["learns_non_null_iban_after_confirmation"] is True

    transaction = _transaction(amount_cents=_int(case, "amount"), purpose="Zahlung Mueller")
    assert should_learn_iban(transaction, True) is True
    # § 3.3: learned "only after a user confirms a Review proposal".
    assert should_learn_iban(transaction, False) is False


def test_f05_two_weak_candidates_stay_unmatched_and_assign_nothing() -> None:
    case = _case("BANKMATCH-F05")
    schmidt = _receivable(
        receivable_id="receivable-schmidt-july",
        period=PERIOD_JULY,
        due_date=JULY_DUE,
        renter_id=RENTER_SCHMIDT,
        tenancy_id="tenancy-schmidt",
    )
    becker = _receivable(
        receivable_id="receivable-becker-july",
        period=PERIOD_JULY,
        due_date=JULY_DUE,
        renter_id=RENTER_BECKER,
        tenancy_id="tenancy-becker",
    )
    profile_schmidt = _profile(
        renter_id=RENTER_SCHMIDT,
        payment_code=CODE_SCHMIDT,
        normalized_surname="schmidt",
        known_ibans=(),
    )
    profile_becker = _profile(
        renter_id=RENTER_BECKER,
        payment_code=CODE_BECKER,
        normalized_surname="becker",
        known_ibans=(),
    )
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        counterpart_iban=IBAN_SHARED,
        counterpart_name=None,
        purpose=None,
    )

    confidences = tuple(
        score_candidate(transaction, receivable, profile, IbanOwnership.UNKNOWN).confidence
        for receivable, profile in ((schmidt, profile_schmidt), (becker, profile_becker))
    )
    assert confidences == _ints(case, "candidate_confidences")
    assert all(confidence <= _contract_int("unmatched_maximum") for confidence in confidences)

    proposal = _propose(
        transaction,
        (
            (schmidt, profile_schmidt, IbanOwnership.UNKNOWN),
            (becker, profile_becker, IbanOwnership.UNKNOWN),
        ),
    )
    assert proposal.decision == _str(case, "decision")
    assert proposal.decision is Decision.UNMATCHED
    _assert_no_money_on_proposal(proposal, _int(case, "assigned"))


def test_f07_shared_iban_never_auto_matches_and_ranks_by_evidence() -> None:
    """`docs/15` § 2 last paragraph and § 4 step 4.

    65 is inside CSV row 171's "40-79" shorthand and still never Auto-Matches, because
    the shared IBAN — not the number — decides.
    """
    case = _case("BANKMATCH-F07")
    candidate_c = _receivable(
        receivable_id="receivable-c",
        period=PERIOD_JULY,
        due_date=JULY_DUE,
        renter_id=RENTER_SCHMIDT,
        tenancy_id="tenancy-schmidt",
    )
    candidate_d = _receivable(
        receivable_id="receivable-d",
        period=PERIOD_JULY,
        due_date=JULY_DUE,
        renter_id=RENTER_BECKER,
        tenancy_id="tenancy-becker",
    )
    profile_c = _profile(
        renter_id=RENTER_SCHMIDT,
        payment_code=CODE_SCHMIDT,
        normalized_surname="schmidt",
        known_ibans=(IBAN_SHARED,),
    )
    profile_d = _profile(
        renter_id=RENTER_BECKER,
        payment_code=CODE_BECKER,
        normalized_surname="becker",
        known_ibans=(IBAN_SHARED,),
    )
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        counterpart_iban=IBAN_SHARED,
        counterpart_name=None,
        purpose=CODE_SCHMIDT,
    )

    expected_signals = _signal_tuples(case, "candidate_signals")
    scored = tuple(
        score_candidate(transaction, receivable, profile, IbanOwnership.SHARED)
        for receivable, profile in ((candidate_c, profile_c), (candidate_d, profile_d))
    )
    assert tuple(score.signals for score in scored) == expected_signals
    assert tuple(score.confidence for score in scored) == _ints(case, "candidate_confidences")

    proposal = _propose(
        transaction,
        (
            (candidate_d, profile_d, IbanOwnership.SHARED),
            (candidate_c, profile_c, IbanOwnership.SHARED),
        ),
    )
    assert proposal.decision == _str(case, "decision")
    assert proposal.decision is not Decision.AUTO_MATCH
    assert MATCHING_CONTRACT["auto_requires_unique_known_iban"] is True

    ranks = _ints(case, "ranks")
    ranked = proposal.ranked_candidates
    assert len(ranked) == len(ranks)
    assert ranked[ranks[0] - 1].receivable_id == candidate_c.id
    assert ranked[ranks[1] - 1].receivable_id == candidate_d.id
    assert tuple(score.confidence for score in ranked) == _ints(case, "candidate_confidences")
    # The top candidate is above the Review floor and would be "Auto" under a naive
    # score-only reading of CSV row 171.  It is still Review.
    assert ranked[0].confidence >= _contract_int("review_floor")
    _assert_no_money_on_proposal(proposal, _int(case, "assigned_before_confirmation"))


def test_f04_a_unique_known_iban_auto_matches_at_sixty() -> None:
    case = _case("BANKMATCH-F04")
    july = _july_rent()
    profile = _profile()
    # 220_000 equals no open amount, so the amount signal is 0 and only the IBAN scores.
    transaction = _transaction(amount_cents=_int(case, "amount"), purpose=None)

    score = score_candidate(transaction, july, profile, IbanOwnership.UNIQUE)
    assert score.signals == _ints(case, "signals")
    assert score.confidence == _int(case, "confidence")

    proposal = _propose(transaction, ((july, profile, IbanOwnership.UNIQUE),))
    assert proposal.decision == _str(case, "decision")
    assert proposal.decision is Decision.AUTO_MATCH
    # Inside CSV row 171's "40-79" band and still Auto: the unique known IBAN decides.
    assert _contract_int("review_floor") <= score.confidence
    assert isinstance(proposal.reason, str)
    assert proposal.reason != ""


def test_f13_first_payment_is_review_and_confirmation_learns_the_iban() -> None:
    case = _case("BANKMATCH-F13")
    july = _receivable(
        receivable_id="receivable-weber-july",
        period=PERIOD_JULY,
        due_date=JULY_DUE,
        renter_id=RENTER_WEBER,
        tenancy_id="tenancy-weber",
    )
    profile = _profile(
        renter_id=RENTER_WEBER,
        payment_code=CODE_MUELLER,
        normalized_surname="weber",
        known_ibans=(),
    )
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        counterpart_iban=IBAN_WEBER,
        counterpart_name="Weber",
        purpose="Zahlung Weber",
    )

    score = score_candidate(transaction, july, profile, IbanOwnership.UNKNOWN)
    assert score.signals == _ints(case, "initial_signals")
    assert score.confidence == _int(case, "initial_confidence")

    proposal = _propose(transaction, ((july, profile, IbanOwnership.UNKNOWN),))
    assert proposal.decision == _str(case, "initial_decision")
    _assert_no_money_on_proposal(proposal, _int(case, "assigned_before_confirmation"))

    assert case["learns_non_null_iban_after_confirmation"] is True
    assert should_learn_iban(transaction, True) is True


def test_f13_the_learned_iban_makes_the_following_month_auto_match() -> None:
    case = _case("BANKMATCH-F13")
    august = _receivable(
        receivable_id="receivable-weber-august",
        period=PERIOD_AUGUST,
        due_date=AUGUST_DUE,
        renter_id=RENTER_WEBER,
        tenancy_id="tenancy-weber",
    )
    # The confirmed IBAN is now an active history row for exactly one renter (§ 3.3).
    profile = _profile(
        renter_id=RENTER_WEBER,
        payment_code=CODE_MUELLER,
        normalized_surname="weber",
        known_ibans=(IBAN_WEBER,),
    )
    transaction = _transaction(
        provider_transaction_id="prov-tx-2",
        amount_cents=_int(case, "amount"),
        bank_booking_date=date(2026, 8, 5),
        counterpart_iban=IBAN_WEBER,
        counterpart_name="Weber",
        purpose=None,
    )

    score = score_candidate(transaction, august, profile, IbanOwnership.UNIQUE)
    assert score.signals[0] == _int(case, "following_month_unique_iban_signal")

    proposal = _propose(transaction, ((august, profile, IbanOwnership.UNIQUE),))
    assert proposal.decision == _str(case, "following_month_decision")
    assert proposal.decision is Decision.AUTO_MATCH


# --------------------------------------------------------------------------------------
# BANKMATCH-F03 — potential duplicate versus exact re-import (docs/15 §§ 1, 3.1, 4, 7).
# --------------------------------------------------------------------------------------


def test_f03_potential_duplicate_forces_review_and_keeps_the_transaction() -> None:
    case = _case("BANKMATCH-F03")
    assert case["potential_duplicate_is_distinct_transaction"] is True
    assert MATCHING_CONTRACT["potential_duplicate_result"] == "needs_review"

    july = _july_rent()
    profile = _profile()
    ownership = _OWNERSHIP_BY_ORACLE_WORD[_str(case, "known_iban")]
    assert ownership is IbanOwnership.UNIQUE
    assert july.open_cents == _int(case, "open_before")

    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        purpose=_str(case, "purpose"),
        is_potential_duplicate=True,
    )

    score = score_candidate(transaction, july, profile, ownership)
    assert score.signals[0] == _int(case, "unique_iban_signal")

    proposal = _propose(transaction, ((july, profile, ownership),))
    # Decision order step 2 beats step 3: a unique known IBAN does not rescue it.
    assert proposal.decision == _str(case, "potential_duplicate_decision")
    # "keep the transaction and force Review; never silently discard it" (§ 3.1).
    # Asserted before the positive identity check: narrowing to NEEDS_REVIEW first would
    # make this provably true and `mypy --strict` rejects it as non-overlapping.
    assert proposal.decision is not Decision.DEDUPED
    assert proposal.decision is Decision.NEEDS_REVIEW
    assert proposal.ranked_candidates != ()
    _assert_no_money_on_proposal(proposal, _int(case, "assigned_before_confirmation"))

    # Confirming it as a "Doublette" settles nothing at all.
    assert _str(case, "duplicate_confirmation_result") == "discard_without_settlement"
    assert _int(case, "assigned_after_duplicate_confirmation") == 0


def test_f03_genuine_payment_confirmation_delegates_to_fifo_and_credit() -> None:
    case = _case("BANKMATCH-F03")
    assert _str(case, "genuine_payment_confirmation_result") == "delegate_to_F04_fifo_and_credit"

    july = _july_rent()
    august = _august_rent()
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        purpose=_str(case, "purpose"),
        is_potential_duplicate=True,
    )
    # Once confirmed as a genuine payment the amount follows § 5.1 unchanged: no
    # designation is passed, so Page 08 FIFO takes the older debt first.
    result = settle(transaction, (august, july))
    assert tuple(allocation.receivable_id for allocation in result.allocations) == (july.id,)
    assert _assigned(result) == _int(case, "amount")
    assert result.allocations[0].status == STATUS_SETTLED
    assert result.credit_cents == 0


def test_f03_exact_reimport_is_deduplicated_before_channel_and_scoring() -> None:
    case = _case("BANKMATCH-F03")
    assert case["exact_reimport_same_id"] is True
    assert _str(case, "exact_reimport_dedupe_stage") == "before_channel_and_scoring"
    assert MATCHING_CONTRACT["exact_reimport_result"] == "dedupe_by_provider_transaction_id"

    july = _july_rent()
    profile = _profile()
    candidates: tuple[Candidate, ...] = ((july, profile, IbanOwnership.UNIQUE),)

    first = _transaction(amount_cents=_int(case, "amount"), purpose=_str(case, "purpose"))
    identity: ProviderIdentity = (
        first.account_id,
        first.bank_account_id,
        first.provider_transaction_id,
    )

    first_proposal = _propose(first, candidates, frozenset())
    assert first_proposal.decision is Decision.AUTO_MATCH
    settlements = [settle(first, (july,))]

    # The very same movement is delivered again by the provider.
    reimport = _transaction(
        amount_cents=_int(case, "amount"),
        purpose=_str(case, "purpose"),
        provider_transaction_id=first.provider_transaction_id,
    )
    second_proposal = _propose(reimport, candidates, frozenset({identity}))

    # Negative first, for the same narrowing reason as the F03 duplicate test above.
    assert second_proposal.decision is not Decision.NEEDS_REVIEW
    assert second_proposal.decision is Decision.DEDUPED
    assert case["exact_reimport_second_scoring"] is False
    assert second_proposal.ranked_candidates == ()
    assert case["exact_reimport_second_review"] is False
    _assert_no_money_on_proposal(second_proposal, 0)

    # Step 1 of the decision order also precedes step 2: an exact re-import that happens
    # to carry `isPotentialDuplicate` is still deduplicated, not reviewed.
    flagged_reimport = _transaction(
        amount_cents=_int(case, "amount"),
        purpose=_str(case, "purpose"),
        provider_transaction_id=first.provider_transaction_id,
        is_potential_duplicate=True,
    )
    assert (
        _propose(flagged_reimport, candidates, frozenset({identity})).decision is Decision.DEDUPED
    )

    assert len(settlements) == _int(case, "exact_reimport_settlement_count")
    assert sum(_assigned(result) for result in settlements) == _int(
        case, "exact_reimport_total_assigned"
    )


def test_f03_provider_transaction_identity_is_account_and_bank_account_scoped() -> None:
    """`docs/15` §§ 3.1 and 6: identity is `(account_id, bank_account_id, provider_transaction_id)`.

    A provider ID is unique only together with its account and bank-account identity, so
    the same ID seen in another account or on another bank account is a different
    movement and must not be swallowed by the dedupe.
    """
    case = _case("BANKMATCH-F03")
    provider_transaction_id = "prov-tx-1"
    already_imported: frozenset[ProviderIdentity] = frozenset(
        {(ACCOUNT_A, BANK_ACCOUNT_A1, provider_transaction_id)}
    )

    july = _july_rent()
    profile = _profile()
    same_account_other_bank_account = _transaction(
        bank_account_id=BANK_ACCOUNT_A2,
        provider_transaction_id=provider_transaction_id,
        amount_cents=_int(case, "amount"),
        purpose=_str(case, "purpose"),
    )
    proposal = _propose(
        same_account_other_bank_account,
        ((july, profile, IbanOwnership.UNIQUE),),
        already_imported,
    )
    assert proposal.decision is not Decision.DEDUPED
    assert proposal.decision is Decision.AUTO_MATCH

    foreign_receivable = _receivable(
        receivable_id="receivable-foreign-july",
        period=PERIOD_JULY,
        due_date=JULY_DUE,
        account_id=ACCOUNT_B,
        renter_id=RENTER_FOREIGN,
        tenancy_id="tenancy-foreign",
    )
    foreign_profile = _profile(
        account_id=ACCOUNT_B,
        renter_id=RENTER_FOREIGN,
        normalized_surname="mueller",
        known_ibans=(IBAN_MUELLER,),
    )
    other_account = _transaction(
        account_id=ACCOUNT_B,
        bank_account_id=BANK_ACCOUNT_B1,
        provider_transaction_id=provider_transaction_id,
        amount_cents=_int(case, "amount"),
        purpose=_str(case, "purpose"),
    )
    foreign_proposal = _propose(
        other_account,
        ((foreign_receivable, foreign_profile, IbanOwnership.UNIQUE),),
        already_imported,
    )
    assert foreign_proposal.decision is not Decision.DEDUPED
    assert foreign_proposal.decision is Decision.AUTO_MATCH


# --------------------------------------------------------------------------------------
# Settlement (docs/15 § 5.1) — designation, FIFO, § 367 order, overpayment, credit.
# --------------------------------------------------------------------------------------


def test_f08_designated_advance_payment_settles_before_the_due_date() -> None:
    case = _case("BANKMATCH-F08")
    assert case["paid_in_advance"] is True
    booking_date = date.fromisoformat(_str(case, "bank_booking_date"))
    due_date = date.fromisoformat(_str(case, "due_date"))
    assert booking_date < due_date

    august = _receivable(
        receivable_id="receivable-august",
        period=PERIOD_AUGUST,
        due_date=due_date,
    )
    profile = _profile()
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        bank_booking_date=booking_date,
        purpose=f"Miete {PERIOD_AUGUST}",
    )

    score = score_candidate(transaction, august, profile, IbanOwnership.UNIQUE)
    assert score.signals == _ints(case, "signals")
    assert score.confidence == _int(case, "confidence")

    proposal = _propose(transaction, ((august, profile, IbanOwnership.UNIQUE),))
    assert proposal.decision == _str(case, "decision")

    assert _str(case, "settlement_order") == "designated_period"
    result = settle(transaction, (august,), designated_period=PERIOD_AUGUST)
    assert _assigned(result) == _int(case, "assigned")
    assert result.allocations[0].status == _str(case, "status_after")
    assert result.allocations[0].open_cents == 0
    assert result.credit_cents == 0


def test_f08_a_named_period_without_a_receivable_is_not_invented() -> None:
    """`docs/15` § 3.2: the amount becomes renter credit; no receivable is created.

    § 3.2 says the credit arises "after other valid allocation" but does not state
    whether a designation that names a nonexistent period then falls back to FIFO over
    unrelated open debts.  This fixture therefore uses a renter with no other open
    receivable and asserts only the stated outcome.
    """
    case = _case("BANKMATCH-F08")
    assert _str(case, "missing_period_receivable_result") == "credit"

    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        purpose=f"Miete {PERIOD_SEPTEMBER}",
    )
    result = settle(transaction, (), designated_period=PERIOD_SEPTEMBER)

    assert result.allocations == ()
    assert result.credit_cents == _int(case, "amount")
    assert _assigned(result) + result.credit_cents == transaction.amount_cents


def test_f04_fifo_settles_the_older_debt_first_and_leaves_credit() -> None:
    case = _case("BANKMATCH-F04")
    assert _str(case, "settlement_order") == "fifo"
    assert _contract_strs("fifo_order") == ("due_before_not_due", "older_before_newer")

    july = _july_rent()
    august = _august_rent()
    transaction = _transaction(
        amount_cents=_int(case, "amount"),
        bank_booking_date=date(2026, 8, 5),
        finapi_booking_date=date(2026, 6, 1),
        purpose=None,
    )
    # Deliberately handed over newest-first: the engine orders, not the caller.
    result = settle(transaction, (august, july))

    assert tuple(allocation.receivable_id for allocation in result.allocations) == (
        july.id,
        august.id,
    )
    paid = tuple(
        allocation.costs_cents + allocation.interest_cents + allocation.principal_cents
        for allocation in result.allocations
    )
    assert paid == _ints(case, "receivables_paid")
    assert all(allocation.status == STATUS_SETTLED for allocation in result.allocations)
    assert all(allocation.open_cents == 0 for allocation in result.allocations)

    assert _assigned(result) == _int(case, "assigned")
    assert result.credit_cents == _int(case, "credit")
    assert _assigned(result) + result.credit_cents == transaction.amount_cents
    # "any final remainder becomes renter credit.  It is not paid out by Lokara."
    assert not hasattr(result, "payout_cents")


def test_due_ness_is_decided_by_bank_booking_date_not_finapi_booking_date() -> None:
    """`docs/15` § 3.1: `bank_booking_date`, not `finapi_booking_date`, decides due-ness.

    Under § 5.1 a due receivable is by construction always the older one, so the
    reference date can never flip the FIFO *order*.  What it can flip is whether the
    debt counts as due at all.  Here the August debt is due at the bank booking date
    (05.08.) and not yet due at the finAPI booking date (01.06.), and it is settled in
    full — an implementation that reads the finAPI date and treats a not-due debt as
    unavailable would leave it open and produce credit instead.
    """
    august = _august_rent()
    transaction = _transaction(
        amount_cents=RENT_EXPECTED,
        bank_booking_date=date(2026, 8, 5),
        finapi_booking_date=date(2026, 6, 1),
        purpose=None,
    )
    result = settle(transaction, (august,))

    assert tuple(allocation.receivable_id for allocation in result.allocations) == (august.id,)
    assert result.allocations[0].status == STATUS_SETTLED
    assert result.allocations[0].open_cents == 0
    assert result.credit_cents == 0


def test_within_one_debt_costs_precede_interest_and_principal() -> None:
    """§ 367 BGB, `docs/15` § 5.1 step 3 (CSV row 170, `geprüft`).

    No Page 08 fixture carries open costs or interest, so the amounts here are the
    author's; the asserted rule — the order and the exact reconciliation — is the
    source's.
    """
    assert _contract_strs("within_debt_order") == ("costs", "interest", "principal")

    july = _july_rent(open_costs_cents=2_000, open_interest_cents=1_000)
    transaction = _transaction(amount_cents=5_000, purpose=None)
    result = settle(transaction, (july,))

    allocation = result.allocations[0]
    assert allocation.costs_cents == july.open_costs_cents
    assert allocation.interest_cents == july.open_interest_cents
    assert allocation.principal_cents == 2_000
    assert (
        allocation.costs_cents + allocation.interest_cents + allocation.principal_cents
        == transaction.amount_cents
    )
    assert allocation.open_cents == july.open_cents - allocation.principal_cents
    assert allocation.status == STATUS_PARTIAL
    assert allocation.principal_components == split_principal(
        july.principal_components, allocation.principal_cents, july.expected_cents
    )
    assert sum(allocation.principal_components) == allocation.principal_cents
    assert result.credit_cents == 0


def test_f12_page_01_nachzahlung_is_designated_and_settled_cent_identically() -> None:
    case = _case("BANKMATCH-F12")
    assert _int(case, "statement_nachzahlung") == _int(case, "receivable_expected")

    # `docs/15` § 3.2 requires the component vector to sum to `expected_cents` but does
    # not state how a `nk_nachzahlung` Saldo decomposes into base rent / NK / heating /
    # garage.  OPEN QUESTION FOR BERKAY.  Nothing in this test asserts a component, and
    # the payment is full, so § 5.2's split is never reached.
    nachzahlung = _receivable(
        receivable_id="receivable-nachzahlung-2025",
        period=STATEMENT_PERIOD,
        due_date=date(2026, 9, 1),
        source_type="page_01_statement",
        source_id="statement-2025",
        expected_cents=_int(case, "receivable_expected"),
        category=_str(case, "category"),
        principal_components=(_int(case, "receivable_expected"), 0, 0, 0),
    )
    older_rent = _july_rent()
    profile = _profile()
    transaction = _transaction(
        amount_cents=_int(case, "payment"),
        bank_booking_date=date(2026, 9, 2),
        purpose="Nachzahlung Betriebskosten",
    )

    score = score_candidate(transaction, nachzahlung, profile, IbanOwnership.UNIQUE)
    assert score.signals == _ints(case, "signals")
    assert score.confidence == _int(case, "confidence")

    proposal = _propose(transaction, ((nachzahlung, profile, IbanOwnership.UNIQUE),))
    assert proposal.decision == _str(case, "decision")

    # The rent receivable is older and would win FIFO; the designation wins instead
    # (§ 366 Abs. 1 BGB, CSV row 176).
    assert _str(case, "settlement_order") == "designated_receivable"
    assert older_rent.due_date < nachzahlung.due_date
    result = settle(transaction, (older_rent, nachzahlung), designated_period=STATEMENT_PERIOD)

    assert tuple(allocation.receivable_id for allocation in result.allocations) == (nachzahlung.id,)
    assert _assigned(result) == _int(case, "assigned")
    assert result.allocations[0].status == _str(case, "status_after")
    assert result.allocations[0].open_cents == 0
    assert result.credit_cents == 0


# --------------------------------------------------------------------------------------
# Principal-component split (docs/15 § 5.2, CSV row 173).
# --------------------------------------------------------------------------------------


def test_f11_partial_payment_splits_the_principal_and_leaves_partial() -> None:
    case = _case("BANKMATCH-F11")
    july = _july_rent()
    profile = _profile()
    assert july.expected_cents == _int(case, "expected")
    assert july.principal_components[:3] == _ints(case, "nominal_components")

    transaction = _transaction(amount_cents=_int(case, "payment"), purpose=None)

    score = score_candidate(transaction, july, profile, IbanOwnership.UNIQUE)
    assert score.signals == _ints(case, "signals")
    assert score.confidence == _int(case, "confidence")
    proposal = _propose(transaction, ((july, profile, IbanOwnership.UNIQUE),))
    # A unique known IBAN Auto-Matches at 60 even though the amount signal is 0.
    assert proposal.decision == _str(case, "decision")
    assert proposal.decision is Decision.AUTO_MATCH

    result = settle(transaction, (july,))
    allocation = result.allocations[0]
    assert allocation.receivable_id == july.id
    assert allocation.principal_cents == _int(case, "payment")
    assert allocation.principal_components[:3] == _ints(case, "paid_components")
    assert allocation.principal_components[3] == 0
    assert sum(allocation.principal_components) == allocation.principal_cents
    # The paid NK advance feeds Page 01's annual actual-advance total (§ 5.2).
    assert allocation.principal_components[1] == _int(case, "nk_advance_paid")
    assert allocation.open_cents == _int(case, "open_after")
    assert allocation.status == _str(case, "status_after")
    assert _int(case, "payment") + _int(case, "open_after") == _int(case, "expected")
    assert result.credit_cents == 0
    assert _assigned(result) + result.credit_cents == transaction.amount_cents


def test_f11_split_principal_is_proportional_and_reconciled_by_largest_remainder() -> None:
    case = _case("BANKMATCH-F11")
    assert MATCHING_CONTRACT["partial_component_method"] == "proportional_largest_remainder"

    nominal = _ints(case, "nominal_components")
    payment = _int(case, "payment")
    expected = _int(case, "expected")
    assert sum(nominal) == expected

    shares = split_principal(nominal, payment, expected)
    assert shares == _ints(case, "paid_components")
    assert sum(shares) == payment
    assert all(type(share) is int for share in shares)


def test_largest_remainder_tie_break_is_unspecified_and_must_raise() -> None:
    """`docs/15` § 5.2 — OPEN QUESTION FOR BERKAY, not an implementation choice.

    "Page 08 does not specify the tie-break between equal fractional remainders; that
    missing deterministic convention must be added to the authoritative source before a
    future implementation claims the unexercised tie branch."

    Two equal nominal halves of a 2,000 ct debt against a 1,001 ct partial payment leave
    both raw shares at exactly 500.5, so one cent has to go somewhere and no source says
    where.  Asserting an invented order here would fabricate a convention, which
    `CLAUDE.md` § 4 forbids, so the engine must refuse instead.  Replace this test only
    when the authoritative source states the rule.
    """
    with pytest.raises(TieBreakUnspecifiedError):
        split_principal((1_000, 1_000), 1_001, 2_000)


# --------------------------------------------------------------------------------------
# Reversal (docs/15 § 5.3).
# --------------------------------------------------------------------------------------


def test_f06_reversal_resolves_by_reference_first_and_nets_the_ledger_to_zero() -> None:
    case = _case("BANKMATCH-F06")
    assert _str(case, "path") == "reversal"
    assert MATCHING_CONTRACT["payment_ledger"] == "append_only_with_compensating_reversals"

    july = _july_rent()
    reference = "E2E-2026-07-MUELLER"
    original = _transaction(
        amount_cents=_int(case, "original_payment"),
        end_to_end_reference=reference,
        counterpart_mandate_reference="MANDATE-4711",
        purpose=None,
    )
    original_settlement = settle(original, (july,))
    assert _assigned(original_settlement) == _int(case, "original_payment")

    # The return carries the same reference *and* the same (IBAN, amount, date) triple,
    # so this also pins the ordering: reference first, Page fallback "only then".
    returned = _transaction(
        provider_transaction_id="prov-tx-return",
        amount_cents=_int(case, "reversal_amount"),
        bank_booking_date=original.bank_booking_date,
        end_to_end_reference=reference,
        bank_transaction_code="RETURN",
        purpose=None,
    )
    result = reverse(returned, original, (original_settlement,))

    assert result.resolution == _str(case, "reference_match")

    entries = result.compensating_entries
    assert entries != ()
    assert sum(entry.amount_cents for entry in entries) == _int(case, "reversal_amount")
    assert _assigned(original_settlement) + sum(entry.amount_cents for entry in entries) == _int(
        case, "net_paid"
    )
    # "Do not [...] create a replacement positive payment."
    assert all(entry.amount_cents <= 0 for entry in entries)

    original_allocation = original_settlement.allocations[0]
    compensating = next(entry for entry in entries if entry.receivable_id == july.id)
    assert compensating.principal_components == tuple(
        -component for component in original_allocation.principal_components
    )

    restored = result.restored_receivables
    assert tuple(row.receivable_id for row in restored) == (july.id,)
    assert restored[0].open_cents == _int(case, "open_after")
    assert restored[0].status == _str(case, "status_after")
    assert restored[0].status == STATUS_OPEN
    assert result.guard_signal == _str(case, "guard_handoff")

    # "Do not rescore": a reversal result carries no candidates, signals or decision.
    for scoring_attribute in ("ranked_candidates", "signals", "confidence", "decision"):
        assert not hasattr(result, scoring_attribute), (
            f"a reversal must not expose {scoring_attribute!r}: docs/15 § 5.3 forbids rescoring"
        )


def test_f06_reversal_uses_the_iban_amount_date_fallback_only_without_a_reference() -> None:
    """`docs/15` § 5.3: "Resolve [...] by E2E or mandate reference; only then use the
    Page fallback `(IBAN, amount, date)`".

    The doc names the fallback triple but not which of the three normalized dates it
    compares, so the return reuses every date of the original movement.  The assertion
    is only that the fallback resolves and is not reported as a reference match.
    """
    case = _case("BANKMATCH-F06")
    july = _july_rent()
    original = _transaction(
        amount_cents=_int(case, "original_payment"),
        end_to_end_reference=None,
        counterpart_mandate_reference=None,
        purpose=None,
    )
    original_settlement = settle(original, (july,))

    returned = _transaction(
        provider_transaction_id="prov-tx-return",
        amount_cents=_int(case, "reversal_amount"),
        bank_booking_date=original.bank_booking_date,
        value_date=original.value_date,
        end_to_end_reference=None,
        counterpart_mandate_reference=None,
        bank_transaction_code="RETURN",
        purpose=None,
    )
    result = reverse(returned, original, (original_settlement,))

    assert result.resolution != _str(case, "reference_match")
    assert _assigned(original_settlement) + sum(
        entry.amount_cents for entry in result.compensating_entries
    ) == _int(case, "net_paid")
    assert result.restored_receivables[0].open_cents == _int(case, "open_after")
    assert result.restored_receivables[0].status == _str(case, "status_after")
    assert result.guard_signal == _str(case, "guard_handoff")


def test_full_return_of_overpayment_reverses_allocations_and_original_credit() -> None:
    """F04 + § 5.3: the bank returns the full movement, including unallocated credit.

    The compensating allocation rows negate only money that reached receivables. The
    original credit closes the remaining equality; it must not be fabricated as a debt
    allocation merely to make the signed transaction amount reconcile.
    """
    case = _case("BANKMATCH-F04")
    original = _transaction(
        amount_cents=_int(case, "amount"),
        end_to_end_reference="E2E-F04-RETURN",
        purpose=None,
    )
    settlement = settle(original, (_july_rent(), _august_rent()))
    assert _assigned(settlement) == _int(case, "assigned")
    assert settlement.credit_cents == _int(case, "credit")
    returned = _transaction(
        provider_transaction_id="prov-f04-full-return",
        amount_cents=-_int(case, "amount"),
        end_to_end_reference="E2E-F04-RETURN",
        purpose=None,
    )

    result = reverse(returned, original, (settlement,))
    compensated = sum(entry.amount_cents for entry in result.compensating_entries)

    assert compensated == -_int(case, "assigned")
    assert compensated - settlement.credit_cents == returned.amount_cents


# --------------------------------------------------------------------------------------
# Account isolation and money typing (docs/15 §§ 3.1, 4, 6; CLAUDE.md §§ 3.1, 3.3).
# --------------------------------------------------------------------------------------


def test_cross_account_candidates_are_never_produced_or_scored() -> None:
    """`docs/15` § 4: candidates are only receivables of renters in the transaction's
    `account_id`; § 6: candidate selection is restricted to one account "before any score
    is calculated".

    Both accounts hold a renter with the same surname, the same IBAN and an identical
    open amount.  The foreign candidate is deliberately offered to the engine.  It must
    never appear in the output and must never be scored — if it leaked, its unique-IBAN
    signal would turn this Unmatched proposal into an Auto-Match across the isolation
    boundary.

    `docs/15` does not say whether a cross-account candidate handed to the engine is
    dropped or rejected outright; this fixture requires that it is never *produced*.  If
    an implementation prefers to raise instead, renegotiate this expectation with the
    fixture author rather than editing it away.
    """
    assert MATCHING_CONTRACT["cross_account_candidates"] == "forbidden"
    scoped = _contract_strs("account_scope_required_on")
    for table in ("bank_transaction", "receivable", "renter_matching_profile", "match_proposal"):
        assert table in scoped

    own = _july_rent()
    own_profile = _profile(known_ibans=())
    foreign = _receivable(
        receivable_id="receivable-foreign-july",
        period=PERIOD_JULY,
        due_date=JULY_DUE,
        account_id=ACCOUNT_B,
        renter_id=RENTER_FOREIGN,
        tenancy_id="tenancy-foreign",
    )
    foreign_profile = _profile(
        account_id=ACCOUNT_B,
        renter_id=RENTER_FOREIGN,
        normalized_surname="mueller",
        known_ibans=(IBAN_MUELLER,),
    )
    transaction = _transaction(amount_cents=RENT_EXPECTED, purpose=None)
    assert transaction.account_id != foreign.account_id

    proposal = _propose(
        transaction,
        (
            (own, own_profile, IbanOwnership.UNKNOWN),
            (foreign, foreign_profile, IbanOwnership.UNIQUE),
        ),
    )

    produced = proposal.ranked_candidates
    assert all(candidate.receivable_id != foreign.id for candidate in produced)
    assert all(candidate.renter_id != RENTER_FOREIGN for candidate in produced)
    assert proposal.decision is not Decision.AUTO_MATCH
    assert proposal.decision == _str(_case("BANKMATCH-F05"), "decision")


def test_settlement_money_is_integer_cents_only() -> None:
    """`CLAUDE.md` § 3.1 and `docs/15` § 3: integer cents everywhere after import.

    `bool` is a subclass of `int`, so identity of the type is checked, not `isinstance`.
    """
    case = _case("BANKMATCH-F01")
    july = _july_rent()
    transaction = _transaction(amount_cents=_int(case, "amount"), purpose=f"Miete {PERIOD_JULY}")
    result = settle(transaction, (july,), designated_period=PERIOD_JULY)

    allocation = result.allocations[0]
    money_values = (
        allocation.costs_cents,
        allocation.interest_cents,
        allocation.principal_cents,
        allocation.open_cents,
        result.credit_cents,
        *allocation.principal_components,
    )
    for value in money_values:
        assert type(value) is int


# --------------------------------------------------------------------------------------
# Coverage — no Page 08 fixture may be silently skipped.
# --------------------------------------------------------------------------------------

#: Which test in this module drives each of the thirteen promised cases.  Declared
#: statically so the check holds under `-k` selection and under any run order.
COVERAGE: Final[dict[str, tuple[str, ...]]] = {
    "BANKMATCH-F01": (
        "test_f01_unique_iban_and_designated_period_settle_the_july_debt",
        "test_settlement_money_is_integer_cents_only",
    ),
    "BANKMATCH-F02": (
        "test_f02_unknown_iban_with_surname_evidence_is_review_and_assigns_nothing",
        "test_f02_confirmed_non_null_iban_is_learned_but_an_unconfirmed_one_is_not",
    ),
    "BANKMATCH-F03": (
        "test_f03_potential_duplicate_forces_review_and_keeps_the_transaction",
        "test_f03_genuine_payment_confirmation_delegates_to_fifo_and_credit",
        "test_f03_exact_reimport_is_deduplicated_before_channel_and_scoring",
        "test_f03_provider_transaction_identity_is_account_and_bank_account_scoped",
    ),
    "BANKMATCH-F04": (
        "test_f04_a_unique_known_iban_auto_matches_at_sixty",
        "test_f04_fifo_settles_the_older_debt_first_and_leaves_credit",
    ),
    "BANKMATCH-F05": (
        "test_f05_two_weak_candidates_stay_unmatched_and_assign_nothing",
        "test_cross_account_candidates_are_never_produced_or_scored",
    ),
    "BANKMATCH-F06": (
        "test_f06_reversal_resolves_by_reference_first_and_nets_the_ledger_to_zero",
        "test_f06_reversal_uses_the_iban_amount_date_fallback_only_without_a_reference",
    ),
    "BANKMATCH-F07": ("test_f07_shared_iban_never_auto_matches_and_ranks_by_evidence",),
    "BANKMATCH-F08": (
        "test_f08_designated_advance_payment_settles_before_the_due_date",
        "test_f08_a_named_period_without_a_receivable_is_not_invented",
    ),
    "BANKMATCH-F09": (
        "test_f09_payment_code_and_surname_are_mutually_exclusive",
        "test_f09_null_iban_is_never_learned",
    ),
    "BANKMATCH-F10": (
        "test_f10_provider_amount_is_imported_with_decimal_half_up",
        "test_f10_float_input_is_rejected_at_the_import_boundary",
    ),
    "BANKMATCH-F11": (
        "test_f11_partial_payment_splits_the_principal_and_leaves_partial",
        "test_f11_split_principal_is_proportional_and_reconciled_by_largest_remainder",
    ),
    "BANKMATCH-F12": ("test_f12_page_01_nachzahlung_is_designated_and_settled_cent_identically",),
    "BANKMATCH-F13": (
        "test_f13_first_payment_is_review_and_confirmation_learns_the_iban",
        "test_f13_the_learned_iban_makes_the_following_month_auto_match",
    ),
}


def test_all_thirteen_page_08_fixtures_are_exercised_by_this_suite() -> None:
    assert set(PAGE_08_GOLDENS) == EXPECTED_IDS
    assert set(COVERAGE) == EXPECTED_IDS
    assert len(COVERAGE) == 13

    module_globals = globals()
    for case_id, test_names in COVERAGE.items():
        assert test_names, f"{case_id} claims no test"
        for test_name in test_names:
            assert callable(module_globals.get(test_name)), (
                f"{case_id} names a test that does not exist in this module: {test_name}"
            )
