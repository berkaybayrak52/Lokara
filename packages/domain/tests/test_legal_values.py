from decimal import Decimal

import pytest
from lokara_domain import DegreeDayTable, WarmWaterFormula


class TestDegreeDayTable:
    """K3 - VDI 2067 Blatt 1, Ausgabe 12/1983, Tabelle 22.

    Spec: `docs/03-nk-heating-engines.md` -> "Seite 01b … (2) K3". Source:
    `berkay-work/…/01b · Heizkosten- & CO₂-Verteilung ….md` § 2 (K3) and the
    Rechtsstand-Register row "Gradtagszahltabelle VDI (K3)".

    **The stored unit is Zehntelpromille, sum 10 000 - not promille, sum 1000.**
    That is forced by the table itself: Jun/Jul/Aug are 13,3 / 13,3 / 13,4 ‰,
    i.e. 400/3 split three ways, which no integer promille can represent. The
    field name carries the unit so a caller cannot mistake the scale, and the
    invariant moves with it. Display value = stored / 10.

    Written before the type change exists: fails today with `TypeError:
    unexpected keyword argument 'tenth_promille_by_month'`.
    """

    VDI_2067_TAB_22 = (1700, 1500, 1300, 800, 400, 133, 133, 134, 300, 800, 1200, 1600)

    def test_carries_the_vdi_table_in_tenths_of_a_promille(self) -> None:
        table = DegreeDayTable(tenth_promille_by_month=self.VDI_2067_TAB_22)
        assert table.tenth_promille_by_month == self.VDI_2067_TAB_22
        assert sum(table.tenth_promille_by_month) == 10_000
        assert len(table.tenth_promille_by_month) == 12

    def test_rejects_tables_not_summing_to_10000(self) -> None:
        with pytest.raises(ValueError):
            DegreeDayTable(tenth_promille_by_month=(1000,) * 12)

    def test_rejects_the_old_promille_table_that_summed_to_1000(self) -> None:
        """The superseded, unsourced table `170 150 130 80 40 15 10 10 30 80 120
        165`. It sums to 1000, so under the old invariant it was valid and under
        the new one it is an error - which is exactly the protection the unit
        change buys: a table in the wrong scale cannot be constructed silently.
        """
        superseded = (170, 150, 130, 80, 40, 15, 10, 10, 30, 80, 120, 165)
        with pytest.raises(ValueError):
            DegreeDayTable(tenth_promille_by_month=superseded)

    def test_the_four_months_that_moved(self) -> None:
        """Eight months agree with the old table, four do not. Both sum to their
        respective totals, so only a value-by-value check catches this."""
        table = DegreeDayTable(tenth_promille_by_month=self.VDI_2067_TAB_22)
        june, july, august, december = (table.tenth_promille_by_month[i] for i in (5, 6, 7, 11))
        assert (june, july, august, december) == (133, 133, 134, 1600)  # was 150/100/100/1650

    def test_the_half_year_split_the_demo_prints(self) -> None:
        """Jan-Jun 583,3 permille and Jul-Dec 416,7 permille, replacing 585/415.

        This is the whole money consequence of K3: the demo's unit-B heating row
        re-bases 778,79 € / 552,47 € -> **776,52 € / 554,74 €** (`docs/06`).
        """
        table = DegreeDayTable(tenth_promille_by_month=self.VDI_2067_TAB_22)
        months = table.tenth_promille_by_month
        assert sum(months[:6]) == 5833
        assert sum(months[6:]) == 4167
        assert Decimal(sum(months[:6])) / 10 == Decimal("583.3")


class TestWarmWaterFormula:
    """DO NOT MOVE - independently confirmed against Berkay Seite 01b.

    The § 9 Abs. 2 substitute equation `Q = 2,5 x V x (tw - 10)` with tw = 60 °C
    (K5) and the § 9 Abs. 3 fallback `Q = 32 x A_Wohn` both survived the audit
    unchanged. Recorded in `docs/03`
    -> "What did not move".
    """

    def test_computes_energy_for_volume(self) -> None:
        formula = WarmWaterFormula(
            factor_kwh_per_m3_kelvin=Decimal("2.5"),
            hot_temp_c=Decimal(60),
            cold_temp_c=Decimal(10),
            area_fallback_kwh_per_sqm_year=Decimal(32),
        )
        # § 9 Abs. 2 HeizkostenV: 2.5 kWh/(m³·K) × V × 50 K = 125 kWh per m³.
        assert formula.energy_kwh_for_volume(Decimal(40)) == Decimal(5000)
