from datetime import date
from decimal import Decimal

from lokara_domain import DegreeDayTable
from lokara_heating_engine import degree_day_weight

TABLE = DegreeDayTable(promille_by_month=(170, 150, 130, 80, 40, 15, 10, 10, 30, 80, 120, 165))


class TestDegreeDayWeight:
    def test_whole_months_are_exact_promille_sums(self) -> None:
        # Jan–Jun = 170+150+130+80+40+15 = 585; Jul–Dec = 415.
        assert degree_day_weight(date(2025, 1, 1), 181, TABLE) == Decimal(585)
        assert degree_day_weight(date(2025, 7, 1), 184, TABLE) == Decimal(415)
        assert degree_day_weight(date(2025, 1, 1), 365, TABLE) == Decimal(1000)

    def test_partial_month_is_pro_rated_by_day(self) -> None:
        # Jul 16–31 (16 of 31 days): 10 promille × 16/31.
        weight = degree_day_weight(date(2025, 7, 16), 16, TABLE)
        assert weight == Decimal(10) * Decimal(16) / Decimal(31)

    def test_mid_month_change_complements_sum_to_the_month(self) -> None:
        first = degree_day_weight(date(2025, 7, 1), 15, TABLE)
        second = degree_day_weight(date(2025, 7, 16), 16, TABLE)
        assert abs(first + second - Decimal(10)) < Decimal("1e-24")

    def test_spans_a_year_boundary(self) -> None:
        # Dec 2025 + Jan 2026 = 165 + 170.
        assert degree_day_weight(date(2025, 12, 1), 62, TABLE) == Decimal(335)
