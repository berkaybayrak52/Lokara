"""Plant-state boundary for the Page 01b CO₂ calculation path."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from lokara_domain import (
    Cents,
    Co2Table,
    Period,
    cents,
    distribute_cents_half_up,
)

from .co2 import split_co2_cost
from .inputs import HeatingInputError

EnergySource = Literal[
    "erdgas",
    "heizoel",
    "fluessiggas",
    "fernwaerme",
    "waermepumpe",
    "biomasse",
]
BuildingType = Literal["wohn", "nichtwohn", "gemischt"]
ProtectionKind = Literal["denkmalschutz", "milieuschutz"]

_ENERGY_SOURCES = frozenset(
    {"erdgas", "heizoel", "fluessiggas", "fernwaerme", "waermepumpe", "biomasse"}
)
_BUILDING_TYPES = frozenset({"wohn", "nichtwohn", "gemischt"})
_PROTECTION_KINDS = frozenset({"denkmalschutz", "milieuschutz"})
_MODULE_OFF_SOURCES = frozenset({"waermepumpe", "biomasse"})
_RENTER_SIDE = 1
_ZERO = cents(0)


@dataclass(frozen=True)
class PlantCo2Input:
    energy_source: EnergySource
    building_type: BuildingType
    connected_plant: bool
    protection_kind: ProtectionKind | None = None
    protection_proof_ref: str | None = None
    full_exclusion: bool = False
    exclusion_proof_ref: str | None = None


@dataclass(frozen=True)
class Co2PlausibilityWarning:
    code: str
    intensity_kg_per_sqm: Decimal
    blocking: bool = False


@dataclass(frozen=True)
class PlantCo2Result:
    co2_module_enabled: bool
    intensity_kg_per_sqm: Decimal | None
    landlord_share_percent: Decimal | None
    landlord_amount: Cents
    co2_renter_amount: Cents
    billable_total: Cents
    disclosure_required: bool
    step_indicator_required: bool
    warm_water_split_required: bool
    applied_proof_ref: str | None
    warnings: tuple[Co2PlausibilityWarning, ...]
    rechtsstand: str | None


def assess_co2_plausibility(
    intensity_kg_per_sqm: Decimal,
) -> tuple[Co2PlausibilityWarning, ...]:
    """Return the non-blocking F23 plausibility signal for an R8 value."""
    if not intensity_kg_per_sqm.is_finite() or intensity_kg_per_sqm < 0:
        raise HeatingInputError("CO₂-Intensität muss endlich und nicht negativ sein")
    if intensity_kg_per_sqm < Decimal(5):
        code = "co2_intensity_below_plausibility_band"
    elif intensity_kg_per_sqm > Decimal(70):
        code = "co2_intensity_above_plausibility_band"
    else:
        return ()
    return (
        Co2PlausibilityWarning(
            code=code,
            intensity_kg_per_sqm=intensity_kg_per_sqm,
        ),
    )


def _validate_plant(plant: PlantCo2Input) -> None:
    if plant.energy_source not in _ENERGY_SOURCES:
        raise HeatingInputError(f"Unbekannter Energieträger: {plant.energy_source}")
    if plant.building_type not in _BUILDING_TYPES:
        raise HeatingInputError(f"Unbekannter Gebäudetyp: {plant.building_type}")
    if plant.protection_kind is not None and plant.protection_kind not in _PROTECTION_KINDS:
        raise HeatingInputError(f"Unbekannte Schutzart: {plant.protection_kind}")
    if plant.protection_kind is not None and not plant.protection_proof_ref:
        raise HeatingInputError(
            "Nachweis für Denkmal- oder Milieuschutz fehlt; die Halbierung wird nicht angewendet"
        )
    if plant.protection_kind is None and plant.protection_proof_ref is not None:
        raise HeatingInputError("Schutznachweis ist ohne Denkmal- oder Milieuschutz nicht zulässig")
    if plant.full_exclusion and not plant.exclusion_proof_ref:
        raise HeatingInputError(
            "Nachweis für den vollständigen Ausschluss nach § 9 Abs. 2 CO2KostAufG fehlt"
        )
    if not plant.full_exclusion and plant.exclusion_proof_ref is not None:
        raise HeatingInputError(
            "Ausschlussnachweis ist ohne vollständigen Ausschluss nicht zulässig"
        )


def evaluate_plant_co2(
    *,
    plant: PlantCo2Input,
    total_cost: Cents,
    total_co2_kg: Decimal | None,
    co2_cost: Cents | None,
    heated_area_sqm: Decimal,
    table: Co2Table,
    rechtsstand: str,
    billing_period: Period,
) -> PlantCo2Result:
    """Apply plant applicability before the existing H2/R8 calculation."""
    _validate_plant(plant)
    if plant.energy_source in _MODULE_OFF_SOURCES:
        return PlantCo2Result(
            co2_module_enabled=False,
            intensity_kg_per_sqm=None,
            landlord_share_percent=None,
            landlord_amount=_ZERO,
            co2_renter_amount=_ZERO,
            billable_total=total_cost,
            disclosure_required=False,
            step_indicator_required=False,
            warm_water_split_required=plant.connected_plant,
            applied_proof_ref=None,
            warnings=(),
            rechtsstand=None,
        )

    if co2_cost is None:
        raise HeatingInputError(
            "CO₂-Kosten des Lieferanten fehlen. Die CO₂-Aufteilung wird nicht berechnet."
        )
    if total_co2_kg is None:
        raise HeatingInputError(
            "Brennstoffemissionen des Lieferanten fehlen. Ohne bestätigten Emissionsfaktor "
            "wird keine CO₂-Masse geschätzt."
        )

    statutory = split_co2_cost(
        total_co2_kg=total_co2_kg,
        co2_cost=co2_cost,
        heated_area_sqm=heated_area_sqm,
        table=table,
        rechtsstand=rechtsstand,
        billing_period=billing_period,
    )
    share = (
        Decimal(50)
        if plant.building_type == "nichtwohn"
        else Decimal(statutory.landlord_share_percent)
    )
    applied_proof_ref: str | None = None
    if plant.protection_kind is not None:
        share /= Decimal(2)
        applied_proof_ref = plant.protection_proof_ref
    if plant.full_exclusion:
        share = Decimal(0)
        applied_proof_ref = plant.exclusion_proof_ref

    landlord_amount, renter_amount = distribute_cents_half_up(
        co2_cost,
        [share, Decimal(100) - share],
        residual_index=_RENTER_SIDE,
    )
    return PlantCo2Result(
        co2_module_enabled=True,
        intensity_kg_per_sqm=statutory.intensity_kg_per_sqm,
        landlord_share_percent=share,
        landlord_amount=landlord_amount,
        co2_renter_amount=renter_amount,
        billable_total=cents(int(total_cost) - int(landlord_amount)),
        disclosure_required=True,
        step_indicator_required=plant.building_type != "nichtwohn",
        warm_water_split_required=plant.connected_plant,
        applied_proof_ref=applied_proof_ref,
        warnings=assess_co2_plausibility(statutory.intensity_kg_per_sqm),
        rechtsstand=rechtsstand,
    )
