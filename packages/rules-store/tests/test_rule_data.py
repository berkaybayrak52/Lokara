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
    def test_carries_the_vdi_2067_table_in_tenths_of_a_promille(self) -> None:
        """K3 - VDI 2067 Blatt 1, Ausgabe 12/1983, Tabelle 22, stored as
        Zehntelpromille with sum 10 000 (`docs/03` -> "Seite 01b … (2) K3").

        Replaces the unsourced `170 150 130 80 40 15 10 10 30 80 120 165`, which
        carried `TODO(verify)` and no citation. Four months move (Jun, Jul, Aug,
        Dez); the money consequence is the demo's 585/415 pair.
        """
        table = get_rule(DEGREE_DAY_TABLE, date(2025, 1, 1)).value
        assert table.tenth_promille_by_month == (
            1700,
            1500,
            1300,
            800,
            400,
            133,
            133,
            134,
            300,
            800,
            1200,
            1600,
        )
        assert sum(table.tenth_promille_by_month) == 10_000
        assert len(table.tenth_promille_by_month) == 12

    def test_the_source_names_the_vdi_edition_and_table(self) -> None:
        """A convention with a citation beats one without: the old rule pointed
        at "anerkannte Promilletabelle" and nothing else, so nobody could check
        it. § 9b Abs. 2 stays named, because the *method* is the statute."""
        source = get_rule(DEGREE_DAY_TABLE, date(2025, 1, 1)).source
        assert "§ 9b" in source
        assert "VDI 2067" in source
        assert "12/1983" in source
        assert "Tabelle 22" in source
        assert "keine Rechtsnorm" in source
        assert source.count("—") == 1
        assert source.endswith("— verify before production")

    def test_the_rechtsstand_dates_the_vdi_edition(self) -> None:
        """12/1983 is the edition of the table. The superseded stamp 01/1981 was
        attached to a table with no source at all. § 9b's own in-force date is
        still not asserted anywhere, so no output may pair the paragraph with
        this date as its Rechtsstand."""
        assert get_rule(DEGREE_DAY_TABLE, date(2025, 1, 1)).rechtsstand == "Rechtsstand 12/1983"

    def test_source_names_the_statute_the_method_rests_on(self) -> None:
        """§ 9b Abs. 2 HeizkostenV is what permits apportioning an unread period
        by Gradtagszahlen, Abs. 3 is what puts Grund- und Warmwasserkosten on
        Zeitanteile — exactly what the engine does. The store carried only the
        VDI table, so the statement could not cite the paragraph it applies:
        the page must never cite a paragraph the store does not carry.
        Spec: `docs/08-statement-document.md` → "The method's statutory basis
        (§ 9b HeizkostenV) is a prerequisite, not an assumption".
        """
        source = get_rule(DEGREE_DAY_TABLE, date(2025, 1, 1)).source
        assert source.startswith("§ 9b Abs. 2 und Abs. 3 HeizkostenV;")

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


class TestCo2FallbackEmissionFactors:
    """K4 - the fallback emission factors, and the energy reference they carry.

    Spec: `docs/03` -> "Seite 01b … (4) Ho/Hu". Source: the Rechtsstand-Register
    rows "Emissionsfaktor Erdgas / Heizöl / Flüssiggas (K4)", imported as-is
    (`CLAUDE.md` precedence rule 3), all `geprüft`, Rechtsnatur `Konvention`,
    Rechtsstand 07/2026, values from EBeV 2030 Anlage 2 Teil 4.

    ⚠️ **These are `nur Fallback`.** They apply only where the supplier has
    failed to state the mass under § 3 CO2KostAufG. The demo never reaches them
    (`docs/06` -> "The demo's energy reference").

    F02 is resolved: the authoritative CSV gives Erdgas Hu 0,201 / Ho 0,181
    plus conversion metadata 0,903. Approved `docs/03` decision 4 and Appendix C
    record that the register wins over the stale 0,2016 / 0,1820 pair.

    The values are imported inside the focused tests so the surrounding rules
    remain independently collectable if this rule's implementation regresses.
    """

    @staticmethod
    def _factors() -> object:
        from lokara_rules_store import CO2_FALLBACK_EMISSION_FACTORS

        return get_rule(CO2_FALLBACK_EMISSION_FACTORS, date(2025, 1, 1))

    def test_erdgas_carries_both_references_as_separate_values(self) -> None:
        from lokara_domain import EnergyReference

        factors = self._factors().value  # type: ignore[attr-defined]
        assert factors["erdgas"][EnergyReference.HU].kg_co2_per_kwh == Decimal("0.201")
        assert factors["erdgas"][EnergyReference.HO].kg_co2_per_kwh == Decimal("0.181")
        assert Decimal("0.201") * Decimal("0.903") == Decimal("0.181503")

    def test_heizoel_and_fluessiggas_exist_only_as_heizwert_values(self) -> None:
        """The register states no Brennwert counterpart for either. None is
        invented: an Ho quantity of oil or LPG has no factor and is refused
        rather than converted."""
        from lokara_domain import EnergyReference

        factors = self._factors().value  # type: ignore[attr-defined]
        assert factors["heizoel"][EnergyReference.HU].kg_co2_per_kwh == Decimal("0.266")
        assert factors["fluessiggas"][EnergyReference.HU].kg_co2_per_kwh == Decimal("0.236")
        assert EnergyReference.HO not in factors["heizoel"]
        assert EnergyReference.HO not in factors["fluessiggas"]

    def test_every_factor_declares_its_own_reference(self) -> None:
        """The reference travels **on the value**, not in a comment. That is
        what makes the mismatch checkable at all."""
        factors = self._factors().value  # type: ignore[attr-defined]
        for by_reference in factors.values():
            for reference, factor in by_reference.items():
                assert factor.reference is reference

    def test_the_public_source_keeps_fallback_scope_without_a_production_block_marker(self) -> None:
        """A statement must never present these as the invoiced factor: they are
        a substitute for a supplier's breach of § 3 CO2KostAufG."""
        resolved = self._factors()
        source = resolved.source  # type: ignore[attr-defined]
        assert "EBeV 2030" in source
        assert "§ 3 CO2KostAufG" in source
        assert "Fallback" in source
        assert "verify before production" not in source


class TestWarmWater:
    def test_formula_yields_125_kwh_per_m3(self) -> None:
        formula = get_rule(WARM_WATER_FORMULA, date(2025, 1, 1)).value
        assert formula.energy_kwh_for_volume(Decimal(1)) == Decimal(125)
        assert formula.area_fallback_kwh_per_sqm_year == Decimal(32)
