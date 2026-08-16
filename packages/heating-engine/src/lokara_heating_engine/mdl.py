"""Pure H7 primitives for confirmed Messdienstleister amounts.

This module does not parse or confirm OCR data.  It receives already confirmed
integer-cent positions, applies the Page 01b M3 control sum, and implements the
M2 gross branch without recomputing the Messdienst's distribution.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from lokara_domain import Cents, cents

from .inputs import HeatingInputError

_CENT = Decimal(1)


@dataclass(frozen=True)
class MdlGrossRescalingResult:
    """Validated H7 gross positions after the landlord's CO₂ deduction."""

    renter_totals: tuple[Cents, ...]
    owner_total: Cents
    source_difference: int
    tolerance: int
    scale: Decimal


def rescale_mdl_gross_positions(
    *,
    gross_positions: tuple[int, ...],
    gross_owner: int,
    gross_total: int,
    billable_total: int,
) -> MdlGrossRescalingResult:
    """Validate and proportionally rescale confirmed gross MDL positions.

    M3 permits at most one cent of source rounding per amount position.  The
    owner amount counts as one read position, but it is not independently
    rescaled: R5 commits the owner line as ``billable - sum(renters)`` so every
    accepted source residual remains visible in that one bucket.

    Each renter is rounded directly from the exact
    ``gross_position * billable_total / gross_total`` quotient.  No rounded
    scaling factor is reused for the money calculation.
    """
    renter_gross = tuple(cents(value) for value in gross_positions)
    owner_gross = cents(gross_owner)
    confirmed_gross_total = cents(gross_total)
    confirmed_billable_total = cents(billable_total)

    if any(value < 0 for value in (*renter_gross, owner_gross)):
        raise HeatingInputError("MDL amount positions must be >= 0")
    if confirmed_gross_total <= 0:
        raise HeatingInputError("MDL gross total must be > 0")
    if confirmed_billable_total < 0:
        raise HeatingInputError("MDL billable total must be >= 0")
    if confirmed_billable_total > confirmed_gross_total:
        raise HeatingInputError("MDL billable total cannot exceed its gross total")

    tolerance = len(renter_gross) + 1
    source_difference = abs(sum(renter_gross) + owner_gross - confirmed_gross_total)
    if source_difference > tolerance:
        raise HeatingInputError(
            "MDL control sum differs from the confirmed gross total by "
            f"{source_difference} ct; tolerance is {tolerance} ct"
        )

    renter_totals = tuple(
        cents(
            int(
                (
                    Decimal(gross_position)
                    * Decimal(confirmed_billable_total)
                    / Decimal(confirmed_gross_total)
                ).quantize(_CENT, rounding=ROUND_HALF_UP)
            )
        )
        for gross_position in renter_gross
    )
    owner_total = cents(int(confirmed_billable_total) - sum(renter_totals))
    scale = Decimal(confirmed_billable_total) / Decimal(confirmed_gross_total)

    assert sum(renter_totals) + owner_total == confirmed_billable_total
    return MdlGrossRescalingResult(
        renter_totals=renter_totals,
        owner_total=owner_total,
        source_difference=source_difference,
        tolerance=tolerance,
        scale=scale,
    )
