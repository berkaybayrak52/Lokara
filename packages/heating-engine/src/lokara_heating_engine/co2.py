"""CO2KostAufG 10-step split of the CO₂ cost portion of heating cost.

The Anlage's bounds are per **year** (`kg CO2/m2/a`), so a billing period shorter
than a year is classified against a *shortened* table — § 5 Abs. 1 S. 4
CO2KostAufG: *"Ist ein Abrechnungszeitraum von unter einem Jahr vereinbart, so
sind die Werte der Einstufungstabelle in der Anlage anteilig zu kürzen."*

The statute shortens the table; it does not extrapolate the emissions. So the
disclosed `intensity_kg_per_sqm` stays the **period** figure (§ 7 Abs. 3) and only
the finite bounds are scaled. Spec + the day-based `period_factor` convention:
`docs/03-nk-heating-engines.md` § "The Stufenmodell is a per-year table".
Rechtsstand 01/2023.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lokara_domain import Cents, Co2Step, Co2Table, Period, days_between, distribute_cents

from .inputs import Co2Result, HeatingInputError

_ONE = Decimal(1)


@dataclass(frozen=True)
class _PeriodBasis:
    """The three figures § 5 Abs. 1 S. 4 needs, derived once. `Co2Result` carries
    all three because the factor alone cannot be un-divided back into the days."""

    period_days: int
    reference_year_days: int
    factor: Decimal


def _reference_year_days(start: date) -> int:
    """Days in [start, same calendar date one year later).

    Anchoring the reference year on the period's own `valid_from` is what makes a
    full leap year 366/366 = 1 rather than 366/365 — a leap year is not *more*
    than a year. A 29 Feb start rolls to 1 Mar (docs/03).
    """
    try:
        end = start.replace(year=start.year + 1)
    except ValueError:  # 29 Feb has no counterpart in the following year
        end = date(start.year + 1, 3, 1)
    return days_between(start, end)


def period_factor_for(billing_period: Period) -> Decimal:
    """`min(1, days(billing_period) / days(reference year))` — exact, never float."""
    return _period_basis_for(billing_period).factor


def _period_basis_for(billing_period: Period) -> _PeriodBasis:
    """The factor and the two day counts it came from, computed together.

    Raises for a period longer than its reference year: § 5 Abs. 1 S. 4 shortens
    the table only for periods *under* a year, and stretching the bounds upward
    would push the building into a lower Stufe at the renter's expense (docs/03
    § "Why a period > 12 months is refused rather than scaled").
    """
    if billing_period.valid_to is None:
        raise HeatingInputError(
            "CO₂ split requires a bounded billing period (valid_to is required)"
        )
    period_days = days_between(billing_period.valid_from, billing_period.valid_to)
    reference_days = _reference_year_days(billing_period.valid_from)
    if period_days > reference_days:
        raise HeatingInputError(
            "CO₂-Aufteilung nicht möglich: Der Abrechnungszeitraum "
            f"({billing_period.valid_from.isoformat()} bis "
            f"{billing_period.valid_to.isoformat()}, {period_days} Tage) ist länger als ein Jahr "
            f"({reference_days} Tage). § 5 Abs. 1 Satz 4 CO2KostAufG kürzt die "
            "Einstufungstabelle nur bei einem Abrechnungszeitraum von unter einem Jahr; für "
            "längere Zeiträume gibt es keine gesetzliche Grundlage für eine Streckung der "
            "Tabelle. Bitte den Abrechnungszeitraum auf höchstens zwölf Monate begrenzen "
            "(§ 556 Abs. 3 Satz 1 BGB)."
        )
    factor = Decimal(period_days) / Decimal(reference_days)
    return _PeriodBasis(
        period_days=period_days,
        reference_year_days=reference_days,
        factor=min(_ONE, factor),
    )


def _select_step(
    intensity_kg_per_sqm: Decimal, table: Co2Table, period_factor: Decimal
) -> tuple[int, Co2Step]:
    """The one place the Einstufung is decided — the percent and the band both
    read off this single walk, so they can never disagree."""
    for index, step in enumerate(table):
        if (
            step.max_intensity_exclusive is None
            or intensity_kg_per_sqm < step.max_intensity_exclusive * period_factor
        ):
            return index, step
    raise HeatingInputError(
        f"CO₂ table has no step for intensity {intensity_kg_per_sqm} (missing open-ended step)"
    )


def landlord_share_percent_for_intensity(
    intensity_kg_per_sqm: Decimal, table: Co2Table, period_factor: Decimal = _ONE
) -> int:
    """Selects the step whose (exclusive) upper bound the intensity falls under.

    Every finite bound is shortened by `period_factor` (§ 5 Abs. 1 S. 4). The
    open-ended top step has no bound and is therefore never scaled — a building
    already in it stays in it.
    """
    return _select_step(intensity_kg_per_sqm, table, period_factor)[1].landlord_share_percent


def split_co2_cost(
    total_co2_kg: Decimal,
    co2_cost: Cents,
    heated_area_sqm: Decimal,
    table: Co2Table,
    rechtsstand: str,
    billing_period: Period,
) -> Co2Result:
    if heated_area_sqm <= 0:
        raise HeatingInputError("CO₂ split requires a positive heated area")
    basis = _period_basis_for(billing_period)
    factor = basis.factor
    # The period figure, deliberately not annualised: the statute shortens the
    # table, and this is the value § 7 Abs. 3 requires to be disclosed.
    intensity = total_co2_kg / heated_area_sqm
    index, step = _select_step(intensity, table, factor)
    landlord_percent = step.landlord_share_percent
    # The bounds the intensity was *actually* compared against, i.e. already
    # shortened. A renderer that scaled them itself would be a second
    # implementation of § 5 Abs. 1 S. 4, and the two would drift.
    previous_bound = table[index - 1].max_intensity_exclusive if index > 0 else None
    landlord_amount, renter_amount = distribute_cents(
        co2_cost, [landlord_percent, 100 - landlord_percent]
    )
    return Co2Result(
        intensity_kg_per_sqm=intensity,
        period_factor=factor,
        landlord_share_percent=landlord_percent,
        landlord_amount=landlord_amount,
        renter_amount=renter_amount,
        rechtsstand=rechtsstand,
        total_co2_kg=total_co2_kg,
        heated_area_sqm=heated_area_sqm,
        co2_cost=co2_cost,
        band_min_inclusive=None if previous_bound is None else previous_bound * factor,
        band_max_exclusive=(
            None if step.max_intensity_exclusive is None else step.max_intensity_exclusive * factor
        ),
        period_days=basis.period_days,
        reference_year_days=basis.reference_year_days,
    )
