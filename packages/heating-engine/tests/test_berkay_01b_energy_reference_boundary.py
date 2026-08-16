"""Ho/Hu at the engine boundary — a reference mismatch must be refused, not converted.

Spec: `docs/03-nk-heating-engines.md` -> "9.5 The Ho/Hu boundary" and § 1 (4) of
the Seite-01b transcription. Design: Berkay's, adopted unchanged. Values: the
Rechtsstand-Register rows *"Emissionsfaktor Erdgas (K4)"* and *"Emissionsfaktor
Gasoel / Fluessiggas (K4)"* — `Konvention`, `geprüft`, **Rechtsstand 07/2026**,
sourced to Anlage 2 Teil 4 EBeV 2030. They are fallback values, not law, and no
output may present them as law. For Erdgas the authoritative CSV records Hu
`0,201`, Ho `0,181` and conversion metadata `0,903`; the later 01b handoff
confirms that the CSV wins.

**Executable contract.** The engine accepts a referenced K4 factor only when
the input kWh carry the same reference. The rules-store metadata has a separate
fixture so a stale production flag cannot hide behind green arithmetic.

**Why it is worth a hard error.** German gas invoices bill **Brennwert (Ho)**
kWh; § 3 Abs. 1 Nr. 3 CO2KostAufG demands the **heizwertbezogene** (Hu) factor.
Multiplying Ho kWh by the Hu factor overstates the emissions by ~11 %:

    20.000 kWh Erdgas, 100 m² beheizte Flaeche
      Hu 0,201 -> 4.020 kg -> 40,2 kg/m²/a -> Stufe 37 - < 42 -> Vermieter 60 %
      Ho 0,181 -> 3.620 kg -> 36,2 kg/m²/a -> Stufe 32 - < 37 -> Vermieter 50 %

A whole Stufe, systematically against the landlord, on a document the tenant may
rely on (§ 7 Abs. 3/4 CO2KostAufG) — and it fails **silently**, because every
intermediate looks plausible. Hence: no conversion step anywhere, in either
direction. A `x 0,903` correction is a step somebody forgets, or applies twice.

**Scope.** The factor is `nur Fallback` (K4): it is read **only** where the
supplier stated no Brennstoffemissionen (§ 3 Abs. 1 Nr. 1 breach, E1). Where the
supplier states them — the normal case and the demo case — no factor is read and
the Ho/Hu question does not arise. That path is pinned here too, because
"harden the fallback" must not disturb it.

**Not in this slice** (`docs/03` § 9.5): a CO₂ *cost* fallback. It is forbidden:
missing supplier cost hard-refuses and is never derived. E1's warning + § 7
Abs. 4 risk flag for a derived mass remains an output-channel gap; it is
recorded there, deliberately not guessed at here.
"""

from decimal import Decimal

import pytest
from lokara_domain import (
    Co2Step,
    Co2Table,
    DegreeDayTable,
    EmissionFactor,
    EnergyReference,
    EnergyReferenceMismatchError,
    HeatingSplitBounds,
    Occupancy,
    WarmWaterFormula,
    cents,
    period,
)
from lokara_heating_engine import (
    Co2Input,
    HeatingInput,
    HeatingInputError,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    calculate_heating_statement,
)

# Rechtsstand-Register, K4 — mirrored as literals rather than imported from
# `lokara_rules_store`, which `packages/rules-store/tests/test_rule_data.py`
# pins: an engine fixture that resolved its own rule values could not tell a
# wrong engine from a changed table.
ERDGAS_HU = EmissionFactor(kg_co2_per_kwh=Decimal("0.201"), reference=EnergyReference.HU)
ERDGAS_HO = EmissionFactor(kg_co2_per_kwh=Decimal("0.181"), reference=EnergyReference.HO)
HEIZOEL_HU = EmissionFactor(kg_co2_per_kwh=Decimal("0.266"), reference=EnergyReference.HU)

YEAR_2025 = period("2025-01-01", "2026-01-01")

CO2_TABLE: Co2Table = (
    Co2Step(max_intensity_exclusive=Decimal(12), landlord_share_percent=0),
    Co2Step(max_intensity_exclusive=Decimal(17), landlord_share_percent=10),
    Co2Step(max_intensity_exclusive=Decimal(22), landlord_share_percent=20),
    Co2Step(max_intensity_exclusive=Decimal(27), landlord_share_percent=30),
    Co2Step(max_intensity_exclusive=Decimal(32), landlord_share_percent=40),
    Co2Step(max_intensity_exclusive=Decimal(37), landlord_share_percent=50),
    Co2Step(max_intensity_exclusive=Decimal(42), landlord_share_percent=60),
    Co2Step(max_intensity_exclusive=Decimal(47), landlord_share_percent=70),
    Co2Step(max_intensity_exclusive=Decimal(52), landlord_share_percent=80),
    Co2Step(max_intensity_exclusive=None, landlord_share_percent=95),
)

RULES = HeatingRules(
    consumption_share=Decimal("0.7"),
    split_bounds=HeatingSplitBounds(
        min_consumption_share=Decimal("0.5"), max_consumption_share=Decimal("0.7")
    ),
    warm_water_formula=WarmWaterFormula(
        factor_kwh_per_m3_kelvin=Decimal("2.5"),
        hot_temp_c=Decimal(60),
        cold_temp_c=Decimal(10),
        area_fallback_kwh_per_sqm_year=Decimal(32),
    ),
    degree_days=DegreeDayTable(
        tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 133, 133, 134, 300, 800, 1200, 1600)
    ),
    co2_table=CO2_TABLE,
    co2_rechtsstand="Rechtsstand 01/2023",
)

# 50 + 30 + 20 = 100 m², fully let all year. This file is about the CO₂ input
# boundary, so nothing here *depends* on the residual rule — but one of its
# blocks is nonetheless one of the seven in the suite that the rule moves, and
# it is pinned below rather than left to be discovered (`docs/03` § 9.2).
# Amended 14.08.2026: the previous comment claimed the file was untouched by
# § 9.2, which stopped being true when the fully-let case gained an owner row.
UNITS = (
    HeatingUnit("unit-a", 5000, heat_consumption=Decimal(600)),
    HeatingUnit("unit-b", 3000, heat_consumption=Decimal(250)),
    HeatingUnit("unit-c", 2000, heat_consumption=Decimal(150)),
)
OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)

TOTAL_COST = 300_000  # 3.000,00 €
ENERGY_KWH = Decimal(20000)
# 261,80 € — 4,000 t x 65,45 €/t (55,00 € nach § 10 Abs. 2 BEHG 2025 + 19 % USt
# nach § 3 Abs. 3 CO2KostAufG). Stated by the supplier under § 3 Abs. 1 Nr. 2:
# only the *mass* falls back to K4 here, never the cost (docs/03 § 7 no. 5).
CO2_COST = 26_180


def _statement(co2: Co2Input, energy_reference: EnergyReference | None) -> HeatingResult:
    """`energy_reference=None` is built **without** the new argument on purpose,
    so that the one case which must already work today — the supplier stated the
    mass, no factor, no reference — does not fail merely on a keyword the engine
    has not grown yet."""
    if energy_reference is None:
        return calculate_heating_statement(
            HeatingInput(
                billing_period=YEAR_2025,
                total_cost=cents(TOTAL_COST),
                total_energy_kwh=ENERGY_KWH,
                units=UNITS,
                occupancies=OCCUPANCIES,
                rules=RULES,
                co2=co2,
            )
        )
    return calculate_heating_statement(
        HeatingInput(
            billing_period=YEAR_2025,
            total_cost=cents(TOTAL_COST),
            total_energy_kwh=ENERGY_KWH,
            energy_reference=energy_reference,
            units=UNITS,
            occupancies=OCCUPANCIES,
            rules=RULES,
            co2=co2,
        )
    )


class TestTheFactorIsAppliedOnlyToItsOwnReference:
    """The two lawful readings of one and the same invoice. Both compute; which
    is right depends only on what the invoice's kWh mean, which is why the
    reference has to be carried and can never be assumed."""

    def test_heizwert_kwh_with_the_heizwert_factor(self) -> None:
        result = _statement(
            Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HU),
            EnergyReference.HU,
        )
        co2 = result.co2
        assert co2 is not None
        # Billable 284.292 ⇒ `heat_base_pot` 85.288 and `heat_cons_pot` 199.004,
        # both of which divide exactly, so this reading's Eigentümerzeile is
        # 0,00 € — unlike the Brennwert one below. It still renders.
        assert int(result.owner_residual.total) == 0
        # R4 keeps integer grams; R8 rounds the specific value before lookup.
        assert co2.total_co2_kg == Decimal(4020)
        assert co2.intensity_kg_per_sqm == Decimal("40.2")
        assert co2.landlord_share_percent == 60
        assert (co2.band_min_inclusive, co2.band_max_exclusive) == (Decimal(37), Decimal(42))
        assert int(co2.landlord_amount) == 15708  # 60 % of 261,80 €
        assert int(co2.renter_amount) == 10472
        assert int(co2.landlord_amount) + int(co2.renter_amount) == CO2_COST
        assert int(result.billable_cost) == TOTAL_COST - 15708
        assert result.total == TOTAL_COST

    def test_brennwert_kwh_with_the_brennwert_factor(self) -> None:
        result = _statement(
            Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HO),
            EnergyReference.HO,
        )
        co2 = result.co2
        assert co2 is not None
        assert co2.total_co2_kg == Decimal(3620)
        assert co2.intensity_kg_per_sqm == Decimal("36.2")
        assert co2.landlord_share_percent == 50
        assert (co2.band_min_inclusive, co2.band_max_exclusive) == (Decimal(32), Decimal(37))
        assert int(co2.landlord_amount) == 13090  # 50 % of 261,80 €
        assert int(co2.renter_amount) == 13090
        assert result.total == TOTAL_COST
        # ⚠️ **One of the seven blocks that move** under the Eigentümer-Residuum
        # (`docs/03` § 9.2 → the fan-out table). Billable 300.000 - 13.090 =
        # 286.910 ⇒ `heat_base_pot` = 86.073, split by 50/30/20: 43.036,5 →
        # **43.037** (R1 half-up, up from 43.036 under largest-remainder),
        # 25.821,9 → 25.822, 17.214,6 → 17.215. Σ = 86.074 ⇒ residual **-1**.
        # The HU reading above lands on 85.288 and divides exactly, which is why
        # only this one of the two moves.
        owner = result.owner_residual
        assert int(result.heat_base_pot) == 86_073
        assert [int(line.heating_base) for line in result.lines] == [43_037, 25_822, 17_215]
        assert int(owner.heating_base) == -1
        assert int(owner.total) == -1
        assert owner.origins == ()  # fully let ⇒ the whole line is block (c)
        assert (
            sum(int(line.total) for line in result.lines)
            + int(owner.total)
            + int(co2.landlord_amount)
            == TOTAL_COST
        )

    def test_the_reference_alone_moves_a_whole_stufe(self) -> None:
        """Same building, same 20.000 kWh, same invoice — 60 % vs 50 % of the
        CO₂ cost, i.e. 26,18 € shifted between landlord and renters by nothing
        but the Bezugsgroesse. This is the size of the silent failure, stated as
        an assertion so nobody has to take the docstring's word for it."""
        hu = _statement(
            Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HU),
            EnergyReference.HU,
        ).co2
        ho = _statement(
            Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HO),
            EnergyReference.HO,
        ).co2
        assert hu is not None and ho is not None
        assert hu.landlord_share_percent - ho.landlord_share_percent == 10
        assert int(hu.landlord_amount) - int(ho.landlord_amount) == 2618


class TestAMismatchIsRefusedAndNeverConverted:
    def test_brennwert_kwh_against_the_heizwert_factor_raises(self) -> None:
        with pytest.raises(EnergyReferenceMismatchError):
            _statement(
                Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HU),
                EnergyReference.HO,
            )

    def test_heizwert_kwh_against_the_brennwert_factor_raises(self) -> None:
        with pytest.raises(EnergyReferenceMismatchError):
            _statement(
                Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HO),
                EnergyReference.HU,
            )

    def test_the_error_reaches_the_caller_unwrapped_and_in_german(self) -> None:
        """Not re-raised as a `HeatingInputError` with the engine's own wording:
        the type is what an API layer branches on and the German text is what a
        landlord reads. Wrapping it would lose both."""
        with pytest.raises(EnergyReferenceMismatchError) as raised:
            _statement(
                Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HU),
                EnergyReference.HO,
            )
        assert not isinstance(raised.value, HeatingInputError)
        message = str(raised.value)
        assert "Brennwert (Ho)" in message
        assert "Heizwert (Hu)" in message
        assert "eine Umrechnung findet bewusst nicht statt" in message

    def test_no_result_is_produced_at_a_ratio_close_to_the_conversion_factor(self) -> None:
        """0,181 / 0,201 = 0,900… — close enough to the register's `x 0,903`
        that a "helpful" coercion would look right. There is no such step, in
        either direction: the mismatch raises before any number is computed."""
        with pytest.raises(EnergyReferenceMismatchError):
            _statement(
                Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HO),
                EnergyReference.HU,
            )

    def test_an_ho_quantity_of_heizoel_is_refused_because_no_ho_factor_exists(self) -> None:
        """The register states **no** Ho counterpart for Heizöl or Fluessiggas
        (`docs/03` § 7 no. 4). None is invented: an Ho quantity of oil meets the
        Hu factor and is refused. The refusal *is* the behaviour — do not close
        this gap by deriving 0,266 x 0,903."""
        with pytest.raises(EnergyReferenceMismatchError):
            _statement(
                Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=HEIZOEL_HU),
                EnergyReference.HO,
            )


class TestTheInputCombinationsThatAreRefusedOutright:
    def test_a_factor_without_a_declared_reference_is_refused(self) -> None:
        """An undeclared Bezugsgroesse is never defaulted. Defaulting to Hu on
        an Ho invoice is precisely the 11 % error, and it would be applied to
        every building whose data model has not caught up yet."""
        with pytest.raises(HeatingInputError):
            _statement(
                Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=ERDGAS_HU),
                None,
            )

    def test_a_missing_mass_with_no_fallback_factor_is_refused(self) -> None:
        """The § 3 Abs. 1 Nr. 1 breach is reported, not guessed around."""
        with pytest.raises(HeatingInputError):
            _statement(
                Co2Input(total_co2_kg=None, co2_cost=cents(CO2_COST), emission_factor=None),
                EnergyReference.HU,
            )

    def test_a_factor_next_to_a_supplier_stated_mass_is_refused_not_ignored(self) -> None:
        """K4 is `nur Fallback`. Silently ignoring the factor is how a wrong one
        survives in the data until the day a supplier stops stating the mass."""
        with pytest.raises(HeatingInputError):
            _statement(
                Co2Input(
                    total_co2_kg=Decimal(4000),
                    co2_cost=cents(CO2_COST),
                    emission_factor=ERDGAS_HU,
                ),
                EnergyReference.HU,
            )


class TestTheNormalPathIsUntouched:
    """§ 3 Abs. 1 Nr. 1: the supplier states the mass, the landlord copies it,
    no factor is read and no reference is needed. Green today, and hardening the
    fallback may not disturb it — the demo path is this path."""

    def test_a_stated_mass_still_needs_no_energy_reference(self) -> None:
        result = _statement(Co2Input(total_co2_kg=Decimal(4000), co2_cost=cents(CO2_COST)), None)
        co2 = result.co2
        assert co2 is not None
        assert co2.total_co2_kg == Decimal(4000)
        assert co2.intensity_kg_per_sqm == Decimal("40.0")
        assert co2.landlord_share_percent == 60
        assert int(co2.landlord_amount) == 15708
        assert result.total == TOTAL_COST
