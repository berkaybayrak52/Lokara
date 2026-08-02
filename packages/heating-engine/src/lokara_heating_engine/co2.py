"""CO2KostAufG 10-step split of the CO₂ cost portion of heating cost."""

from decimal import Decimal

from lokara_domain import Cents, Co2Table, distribute_cents

from .inputs import Co2Result, HeatingInputError


def landlord_share_percent_for_intensity(intensity_kg_per_sqm: Decimal, table: Co2Table) -> int:
    """Selects the step whose (exclusive) upper bound the intensity falls under."""
    for step in table:
        if (
            step.max_intensity_exclusive is None
            or intensity_kg_per_sqm < step.max_intensity_exclusive
        ):
            return step.landlord_share_percent
    raise HeatingInputError(
        f"CO₂ table has no step for intensity {intensity_kg_per_sqm} (missing open-ended step)"
    )


def split_co2_cost(
    total_co2_kg: Decimal,
    co2_cost: Cents,
    heated_area_sqm: Decimal,
    table: Co2Table,
    rechtsstand: str,
) -> Co2Result:
    if heated_area_sqm <= 0:
        raise HeatingInputError("CO₂ split requires a positive heated area")
    intensity = total_co2_kg / heated_area_sqm
    landlord_percent = landlord_share_percent_for_intensity(intensity, table)
    landlord_amount, renter_amount = distribute_cents(
        co2_cost, [landlord_percent, 100 - landlord_percent]
    )
    return Co2Result(
        intensity_kg_per_sqm=intensity,
        landlord_share_percent=landlord_percent,
        landlord_amount=landlord_amount,
        renter_amount=renter_amount,
        rechtsstand=rechtsstand,
    )
