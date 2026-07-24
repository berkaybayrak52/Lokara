from decimal import Decimal

import pytest
from lokara_domain import NonIntegerCentsError, add_cents, cents, distribute_cents, format_eur


class TestCents:
    def test_accepts_integers_and_rejects_non_integers(self) -> None:
        assert cents(120000) == 120000
        with pytest.raises(NonIntegerCentsError):
            cents(1200.5)  # type: ignore[arg-type]
        with pytest.raises(NonIntegerCentsError):
            cents(True)
        with pytest.raises(NonIntegerCentsError):
            cents("1200")  # type: ignore[arg-type]

    def test_adds_without_drift(self) -> None:
        assert add_cents(cents(1), cents(2), cents(3)) == 6


class TestFormatEur:
    def test_formats_german_currency(self) -> None:
        assert format_eur(cents(120000)) == "1.200,00 €"

    def test_formats_negative_and_small_amounts(self) -> None:
        assert format_eur(cents(-1)) == "-0,01 €"
        assert format_eur(cents(5)) == "0,05 €"
        assert format_eur(cents(123456789)) == "1.234.567,89 €"


class TestDistributeCents:
    def test_reconciles_the_1200_eur_garbage_cost_example_to_the_cent(self) -> None:
        # Weights are m²·days: Unit A (50m²·365d), Unit B renter (30m²·181d),
        # Unit B vacancy (30m²·184d), Unit C (20m²·365d) — lokara-arch.md §10 / docs/03.
        shares = distribute_cents(cents(120000), [18250, 5430, 5520, 7300])
        assert shares == [60000, 17852, 18148, 24000]
        assert sum(shares) == 120000

    def test_always_reconciles_to_the_total(self) -> None:
        shares = distribute_cents(cents(100), [1, 1, 1])
        assert sum(shares) == 100
        assert shares == [34, 33, 33]

    def test_is_deterministic_on_ties_lowest_index_wins_the_extra_cent(self) -> None:
        assert distribute_cents(cents(101), [1, 1]) == [51, 50]

    def test_handles_zero_weights(self) -> None:
        assert distribute_cents(cents(100), [0, 1]) == [0, 100]

    def test_accepts_decimal_weights(self) -> None:
        weights = [Decimal("45.5"), Decimal("30.25"), Decimal("24.25")]
        shares = distribute_cents(cents(90000), weights)
        assert shares == [40950, 27225, 21825]
        assert sum(shares) == 90000

    def test_rejects_empty_negative_and_all_zero_weights(self) -> None:
        with pytest.raises(ValueError):
            distribute_cents(cents(100), [])
        with pytest.raises(ValueError):
            distribute_cents(cents(100), [-1, 2])
        with pytest.raises(ValueError):
            distribute_cents(cents(100), [0, 0])
