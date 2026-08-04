from datetime import date
from decimal import Decimal

import pytest
from lokara_rules_store import (
    CO2_SPLIT_TABLE,
    DEFAULT_CONSUMPTION_SHARE,
    DEGREE_DAY_TABLE,
    HEATING_SPLIT_BOUNDS,
    WARM_WATER_FORMULA,
    RuleNotFoundError,
    get_rule,
)


class TestHeatingSplit:
    def test_bounds_are_50_to_70_percent_consumption(self) -> None:
        bounds = get_rule(HEATING_SPLIT_BOUNDS, date(2025, 1, 1)).value
        assert bounds.min_consumption_share == Decimal("0.5")
        assert bounds.max_consumption_share == Decimal("0.7")
        assert (
            bounds.min_consumption_share
            <= DEFAULT_CONSUMPTION_SHARE
            <= bounds.max_consumption_share
        )


class TestCo2Table:
    def test_not_in_force_before_2023(self) -> None:
        with pytest.raises(RuleNotFoundError):
            get_rule(CO2_SPLIT_TABLE, date(2022, 6, 1))

    def test_resolves_with_rechtsstand_01_2023(self) -> None:
        resolved = get_rule(CO2_SPLIT_TABLE, date(2025, 12, 31))
        assert resolved.rechtsstand == "Rechtsstand 01/2023"
        assert "CO2KostAufG" in resolved.source

    def test_has_10_contiguous_steps_from_0_to_95_percent(self) -> None:
        steps = get_rule(CO2_SPLIT_TABLE, date(2023, 1, 1)).value
        assert len(steps) == 10
        assert steps[0].landlord_share_percent == 0
        assert steps[-1].landlord_share_percent == 95
        assert steps[-1].max_intensity_exclusive is None
        bounds = [s.max_intensity_exclusive for s in steps[:-1]]
        assert bounds == [Decimal(v) for v in (12, 17, 22, 27, 32, 37, 42, 47, 52)]
        shares = [s.landlord_share_percent for s in steps]
        assert shares == sorted(shares)  # monotonically increasing landlord burden


class TestDegreeDays:
    def test_promille_table_sums_to_1000(self) -> None:
        table = get_rule(DEGREE_DAY_TABLE, date(2025, 1, 1)).value
        assert sum(table.promille_by_month) == 1000
        assert len(table.promille_by_month) == 12

    def test_source_names_the_statute_the_method_rests_on(self) -> None:
        """§ 9b Abs. 2 HeizkostenV is what permits apportioning an unread period
        by Gradtagszahlen, Abs. 3 is what puts Grund- und Warmwasserkosten on
        Zeitanteile — exactly what the engine does. The store carried only the
        VDI table, so the statement could not cite the paragraph it applies:
        the page must never cite a paragraph the store does not carry.
        Spec + exact string: `docs/08-statement-document.md` → "The method's
        statutory basis (§ 9b HeizkostenV) is a prerequisite, not an assumption".
        """
        source = get_rule(DEGREE_DAY_TABLE, date(2025, 1, 1)).source
        assert source == (
            "§ 9b Abs. 2 und Abs. 3 HeizkostenV; Gradtagszahlen nach anerkannter "
            "Promilletabelle (VDI-Konvention, keine Rechtsnorm) "
            "— verify before production"
        )

    def test_the_statute_and_the_convention_stay_distinguishable(self) -> None:
        """§ 9b is law; the promille numbers are not. A source that named only
        the paragraph would present the VDI table as statutory — the failure
        mode the "verify before production" marker exists to prevent."""
        resolved = get_rule(DEGREE_DAY_TABLE, date(2025, 1, 1))
        assert "§ 9b" in resolved.source
        assert "keine Rechtsnorm" in resolved.source
        # The internal marker is last, after the only em dash in the string, so
        # the renderer's "everything after the em dash never renders" rule holds.
        assert resolved.source.count("—") == 1
        assert resolved.source.endswith("— verify before production")

    def test_the_rechtsstand_still_dates_the_table_and_not_the_paragraph(self) -> None:
        """01/1981 is the promille table's stamp. § 9b's own in-force date is not
        verified anywhere (it would need the BGBl. history of the HeizkostenV),
        so no output may pair the paragraph with this date as its Rechtsstand."""
        assert get_rule(DEGREE_DAY_TABLE, date(2025, 1, 1)).rechtsstand == "Rechtsstand 01/1981"


class TestWarmWater:
    def test_formula_yields_125_kwh_per_m3(self) -> None:
        formula = get_rule(WARM_WATER_FORMULA, date(2025, 1, 1)).value
        assert formula.energy_kwh_for_volume(Decimal(1)) == Decimal(125)
        assert formula.area_fallback_kwh_per_sqm_year == Decimal(32)
