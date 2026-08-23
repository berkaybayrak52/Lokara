"""docs/15 § 3.1: what the AIS adapter must hand to the matching engine.

`BANKMATCH-F10` is the fixture that lives here rather than in the engine: the
Decimal-to-cent conversion is an *import* rule, so no engine test can pin it. The
oracle value is in `packages/rules-store/tests/berkay_15_golden.py`.
"""

from datetime import date
from decimal import Decimal

import pytest
from lokara_adapters import (
    BankGateway,
    BankTransaction,
    StubBankGateway,
    cents_from_provider_amount,
)


class TestProviderAmountConversion:
    """docs/15 § 3.1: parse as Decimal, ×100, ROUND_HALF_UP. Never binary float."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("1080.00", 108_000),
            # BANKMATCH-F10's second half, and the reason ROUND_HALF_UP is named
            # explicitly: banker's rounding would give 108_000 here.
            ("1080.005", 108_001),
        ],
    )
    def test_f10_decimal_imports(self, raw: str, expected: int) -> None:
        assert cents_from_provider_amount(raw) == expected

    def test_a_negative_amount_keeps_its_sign(self) -> None:
        """§ 3.1: a negative amount is the § 5.3 reversal path, not an error."""
        assert cents_from_provider_amount("-1080.00") == -108_000

    def test_zero_is_retained(self) -> None:
        """§ 3.1: zero is kept for import audit and ignored by matching."""
        assert cents_from_provider_amount("0.00") == 0

    def test_float_is_refused(self) -> None:
        """CLAUDE.md § 3.1: money never touches binary float. Refusing at the
        boundary is what keeps that true of everything downstream."""
        with pytest.raises(TypeError, match="float"):
            cents_from_provider_amount(1080.005)  # type: ignore[arg-type]

    def test_decimal_input_is_accepted_unchanged(self) -> None:
        assert cents_from_provider_amount(Decimal("1080.005")) == 108_001


class TestNormalizedTransactionShape:
    def test_the_stub_yields_the_full_section_3_1_record(self) -> None:
        gateway: BankGateway = StubBankGateway()
        transactions = gateway.list_transactions(
            "bank_acc_demo", date(2025, 1, 1), date(2026, 1, 1)
        )
        first = transactions[0]

        assert isinstance(first, BankTransaction)
        assert isinstance(first.amount_cents, int)
        # The three dates are separate fields on purpose: § 3.1 makes
        # bank_booking_date -- not finapi_booking_date -- decide whether a
        # receivable is due.
        assert isinstance(first.bank_booking_date, date)
        assert isinstance(first.finapi_booking_date, date)
        assert isinstance(first.value_date, date)
        assert first.is_potential_duplicate is False
        for optional in (
            first.counterpart_iban,
            first.counterpart_name,
            first.purpose,
            first.end_to_end_reference,
            first.counterpart_mandate_reference,
            first.bank_transaction_code,
            first.provider_type,
        ):
            assert optional is None or isinstance(optional, str)

    def test_a_debit_is_a_negative_amount_not_a_direction_flag(self) -> None:
        """§ 3.1 replaced the old positive-amount-plus-direction pair with one
        signed integer, because the sign is what § 5.3 reads to find a reversal."""
        gateway: BankGateway = StubBankGateway()
        transactions = gateway.list_transactions(
            "bank_acc_demo", date(2025, 1, 1), date(2026, 1, 1)
        )
        by_id = {t.provider_transaction_id: t for t in transactions}

        assert by_id["tx_stub_001"].amount_cents == 117_000
        assert by_id["tx_stub_004"].amount_cents == -120_000

    def test_counterpart_name_is_capped_at_the_sepa_length(self) -> None:
        assert all(
            t.counterpart_name is None or len(t.counterpart_name) <= 80
            for t in StubBankGateway().list_transactions(
                "bank_acc_demo", date(2025, 1, 1), date(2026, 1, 1)
            )
        )


class TestStubHonoursItsBankAccount:
    """docs/15 § 10 names the old stub's ignored `bank_account_id` as the reason it
    could not prove account isolation or provider-ID uniqueness."""

    def test_an_unknown_bank_account_yields_nothing(self) -> None:
        gateway: BankGateway = StubBankGateway()
        assert (
            gateway.list_transactions("not-a-connected-account", date(2025, 1, 1), date(2026, 1, 1))
            == ()
        )

    def test_every_returned_row_names_the_requested_bank_account(self) -> None:
        gateway: BankGateway = StubBankGateway()
        transactions = gateway.list_transactions(
            "bank_acc_demo", date(2025, 1, 1), date(2026, 1, 1)
        )
        assert transactions
        assert {t.bank_account_id for t in transactions} == {"bank_acc_demo"}

    def test_window_is_half_open(self) -> None:
        gateway: BankGateway = StubBankGateway()
        assert [
            t.provider_transaction_id
            for t in gateway.list_transactions("bank_acc_demo", date(2025, 1, 3), date(2025, 1, 5))
        ] == ["tx_stub_001"]
        assert gateway.list_transactions("bank_acc_demo", date(2024, 1, 1), date(2025, 1, 1)) == ()

    def test_provider_transaction_ids_are_unique_within_one_bank_account(self) -> None:
        """§ 3.1 identity is (account, bank account, provider id). The stub must not
        hand the importer a collision the database would then reject."""
        transactions = StubBankGateway().list_transactions(
            "bank_acc_demo", date(2025, 1, 1), date(2026, 1, 1)
        )
        ids = [t.provider_transaction_id for t in transactions]
        assert len(ids) == len(set(ids))
