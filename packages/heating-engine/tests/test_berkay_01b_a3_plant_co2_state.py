"""Page 01b A3 RED contract: plant state controls the CO2 path.

Source: ``berkay-work/Spec-Seiten/01b · Heizkosten- & CO₂-Verteilung ….md``
§§ 3.1, H2 and fixtures F07-F10/F23.  Rechtsstand 07/2026; R8 was
superseded on 15.08.2026 and is transcribed in ``docs/03``.

This is a capability contract, not full self-billing closure.
"""

from decimal import Decimal
from typing import Any

import lokara_heating_engine
import pytest
from berkay_01b_golden import PAGE_01B_GOLDENS
from lokara_domain import Co2Step, Co2Table, cents, period
from lokara_heating_engine import HeatingInputError

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

FULL_YEAR_2025 = period("2025-01-01", "2026-01-01")
RECHTSSTAND = "Rechtsstand 01/2023"


def _plant(
    *,
    energy_source: str = "erdgas",
    building_type: str = "wohn",
    connected_plant: bool = True,
    protection_kind: str | None = None,
    protection_proof_ref: str | None = None,
    full_exclusion: bool = False,
    exclusion_proof_ref: str | None = None,
) -> Any:
    plant_type = getattr(lokara_heating_engine, "PlantCo2Input", None)
    assert callable(plant_type), "A3 PlantCo2Input is not implemented"
    return plant_type(
        energy_source=energy_source,
        building_type=building_type,
        connected_plant=connected_plant,
        protection_kind=protection_kind,
        protection_proof_ref=protection_proof_ref,
        full_exclusion=full_exclusion,
        exclusion_proof_ref=exclusion_proof_ref,
    )


def _evaluate(
    plant: Any,
    *,
    total_cost: int = 350_600,
    total_co2_kg: Decimal | None = Decimal(5_628),
    co2_cost: int | None = 30_954,
) -> Any:
    evaluate = getattr(lokara_heating_engine, "evaluate_plant_co2", None)
    assert callable(evaluate), "A3 plant/CO₂ applicability is not implemented"
    return evaluate(
        plant=plant,
        total_cost=cents(total_cost),
        total_co2_kg=total_co2_kg,
        co2_cost=None if co2_cost is None else cents(co2_cost),
        heated_area_sqm=Decimal(194),
        table=CO2_TABLE,
        rechtsstand=RECHTSSTAND,
        billing_period=FULL_YEAR_2025,
    )


def test_berkay_01b_f07_non_residential_uses_the_statutory_50_50_branch() -> None:
    case = PAGE_01B_GOLDENS["01b-F07"]
    result = _evaluate(
        _plant(
            energy_source=str(case["energy_source"]),
            building_type=str(case["building_type"]),
            connected_plant=bool(case["connected_plant"]),
        )
    )

    assert result.co2_module_enabled is True
    assert result.landlord_share_percent == case["landlord_percent"]
    assert int(result.landlord_amount) == case["co2_landlord"]
    assert int(result.billable_total) == case["billable_total"]
    assert result.step_indicator_required is False
    assert int(result.landlord_amount) + int(result.co2_renter_amount) == 30_954


@pytest.mark.parametrize("protection_kind", ["denkmalschutz", "milieuschutz"])
def test_berkay_01b_f08_protection_halves_the_step_share_with_stored_proof(
    protection_kind: str,
) -> None:
    case = PAGE_01B_GOLDENS["01b-F08"]
    proof_ref = f"proof://{protection_kind}/2025"
    result = _evaluate(
        _plant(
            protection_kind=protection_kind,
            protection_proof_ref=proof_ref,
        )
    )

    assert result.landlord_share_percent == case["landlord_percent"]
    assert int(result.landlord_amount) == case["co2_landlord"]
    assert int(result.billable_total) == case["billable_total"]
    assert result.applied_proof_ref == proof_ref


@pytest.mark.parametrize("protection_kind", ["denkmalschutz", "milieuschutz"])
def test_berkay_01b_f08_protection_without_proof_is_refused(protection_kind: str) -> None:
    with pytest.raises(HeatingInputError, match="Nachweis"):
        _evaluate(_plant(protection_kind=protection_kind))


def test_berkay_01b_f09_full_exclusion_wins_and_keeps_the_disclosure() -> None:
    case = PAGE_01B_GOLDENS["01b-F09"]
    proof_ref = "proof://section-9-2/exclusion-2025"
    result = _evaluate(
        _plant(
            protection_kind="denkmalschutz",
            protection_proof_ref="proof://denkmal/2025",
            full_exclusion=True,
            exclusion_proof_ref=proof_ref,
        )
    )

    assert result.landlord_share_percent == case["landlord_percent"]
    assert int(result.landlord_amount) == case["co2_landlord"]
    assert int(result.billable_total) == case["billable_total"]
    assert result.disclosure_required is True
    assert result.applied_proof_ref == proof_ref


def test_berkay_01b_f09_full_exclusion_without_proof_is_refused() -> None:
    with pytest.raises(HeatingInputError, match="Nachweis"):
        _evaluate(_plant(full_exclusion=True))


@pytest.mark.parametrize("energy_source", ["waermepumpe", "biomasse"])
def test_berkay_01b_f10_non_behg_sources_turn_the_whole_co2_module_off(
    energy_source: str,
) -> None:
    case = PAGE_01B_GOLDENS["01b-F10"]
    result = _evaluate(
        _plant(energy_source=energy_source),
        total_co2_kg=None,
        co2_cost=None,
    )

    assert result.co2_module_enabled is False
    assert result.intensity_kg_per_sqm is None
    assert result.landlord_share_percent is None
    assert int(result.landlord_amount) == case["co2_landlord"]
    assert int(result.billable_total) == case["billable_total"]
    assert result.disclosure_required is case["disclosure"]
    assert result.step_indicator_required is False
    assert result.warnings == ()


def test_connected_state_controls_only_the_warm_water_branch_not_co2_applicability() -> None:
    connected = _evaluate(_plant(connected_plant=True))
    separate = _evaluate(_plant(connected_plant=False))

    assert connected.warm_water_split_required is True
    assert separate.warm_water_split_required is False
    assert separate.co2_module_enabled is True
    assert separate.landlord_share_percent == connected.landlord_share_percent == 40
    assert int(separate.landlord_amount) == int(connected.landlord_amount) == 12_382


@pytest.mark.parametrize(
    ("intensity", "code"),
    [
        (Decimal("74.7"), "co2_intensity_above_plausibility_band"),
        (Decimal("4.1"), "co2_intensity_below_plausibility_band"),
    ],
)
def test_berkay_01b_f23_warning_carries_the_same_one_decimal_r8_value(
    intensity: Decimal,
    code: str,
) -> None:
    assess = getattr(lokara_heating_engine, "assess_co2_plausibility", None)
    assert callable(assess), "A3 CO₂ plausibility warning channel is not implemented"

    warnings = assess(intensity)
    assert len(warnings) == 1
    assert warnings[0].code == code
    assert warnings[0].intensity_kg_per_sqm == intensity
    assert warnings[0].blocking is False


@pytest.mark.parametrize("intensity", [Decimal("5.0"), Decimal("70.0")])
def test_f23_band_boundaries_do_not_warn(intensity: Decimal) -> None:
    assess = getattr(lokara_heating_engine, "assess_co2_plausibility", None)
    assert callable(assess), "A3 CO₂ plausibility warning channel is not implemented"
    assert assess(intensity) == ()
