"""Mechanics of `degree_day_weight` — pro-rating, month boundaries, year rollover.

The unit is **Zehntelpromille** (Σ 10 000) since K3, `docs/03-nk-heating-engines.md`
→ "Seite 01b … (2) K3": VDI 2067 puts Jun/Jul/Aug at 400/3 ‰ each, which no
integer promille can carry. Display value = stored ÷ 10.

⚠️ `TABLE` below is **synthetic and is not the rules-store table.** It is the
shape of the superseded, unsourced 01/1981 table ×10, kept because whole-month
sums stay legible integers (585,0 ‰ / 415,0 ‰) and this file tests the
*arithmetic* of the weighting, not the values. The live table is VDI 2067
Blatt 1, Ausgabe 12/1983, Tabelle 22 and is pinned in
`packages/rules-store/tests/test_rule_data.py`. Do not copy this tuple back into
`packages/rules-store`.
"""

from datetime import date
from decimal import Decimal

from lokara_domain import DegreeDayTable
from lokara_heating_engine import degree_day_weight

TABLE = DegreeDayTable(
    tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 150, 100, 100, 300, 800, 1200, 1650)
)


class TestDegreeDayWeight:
    def test_whole_months_are_exact_tenth_promille_sums(self) -> None:
        # Jan–Jun = 1700+1500+1300+800+400+150 = 5850 (585,0 ‰); Jul–Dec = 4150.
        assert degree_day_weight(date(2025, 1, 1), 181, TABLE) == Decimal(5850)
        assert degree_day_weight(date(2025, 7, 1), 184, TABLE) == Decimal(4150)
        assert degree_day_weight(date(2025, 1, 1), 365, TABLE) == Decimal(10_000)

    def test_partial_month_is_pro_rated_by_day(self) -> None:
        # Jul 16–31 (16 of 31 days): 100 Zehntelpromille × 16/31.
        weight = degree_day_weight(date(2025, 7, 16), 16, TABLE)
        assert weight == Decimal(100) * Decimal(16) / Decimal(31)

    def test_mid_month_change_complements_sum_to_the_month(self) -> None:
        first = degree_day_weight(date(2025, 7, 1), 15, TABLE)
        second = degree_day_weight(date(2025, 7, 16), 16, TABLE)
        assert abs(first + second - Decimal(100)) < Decimal("1e-24")

    def test_spans_a_year_boundary(self) -> None:
        # Dec 2025 + Jan 2026 = 1650 + 1700.
        assert degree_day_weight(date(2025, 12, 1), 62, TABLE) == Decimal(3350)

    def test_a_full_heating_year_is_the_tables_whole_sum(self) -> None:
        """The scale is the invariant that makes a printed ‰ figure derivable:
        a full year is 10 000 Zehntelpromille = 1.000 ‰, so the renderer's
        ÷ 10 is the only de-scaling step anywhere (`docs/03` §(2) K3)."""
        assert degree_day_weight(date(2025, 1, 1), 365, TABLE) == Decimal(
            sum(TABLE.tenth_promille_by_month)
        )
