"""CO2KostAufG 10-step split of the CO₂ cost portion of heating cost.

The Anlage's bounds are per **year** (`kg CO2/m2/a`), so a billing period that is
not a year is classified against an **annualised** intensity (H2). § 5 Abs. 1
S. 3 then requires that intensity to be rounded to one decimal before the step
lookup (R8):

    spezifisch = (co2Gramm / 1e6) / gesamtflaecheM2
    if nTage not in (365, 366): spezifisch ×= 365 / nTage  # H2
    spezifisch = round_half_up(spezifisch, 1 Nachkommastelle)
    step = lookup10(spezifisch)          # against the UNSHORTENED Anlage table

The rounded value is both classified and carried for disclosure. `ROUND_HALF_UP`
is Lokara's explicit tie convention; neither the statute nor Berkay specifies a
tie mode. Source: `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` § 6;
`docs/03-nk-heating-engines.md` R8. Rechtsstand 08/2026.

⚠️ **Do not "fix" this back to shortening the table.** The § 5 Abs. 1 S. 4
reading (scale every finite bound by days/reference-year, leave the intensity as
the period figure) was implemented here before, is quoted verbatim and argued at
length in `docs/03-nk-heating-engines.md`, and is marked **SUPERSEDED** there
rather than deleted so that nobody re-derives it. Both readings select the *same
step* — `i × 365/d < b` ⇔ `i < b × d/365` — so no Einstufung and no euro move on
selection. They differ in the figure that is **printed**, and the printed figure
is what § 7 Abs. 3 CO2KostAufG is about: the old reading printed a 275-day
figure under a `kg CO₂/m²/a` header, against a band (20,34–24,11) that appears
in no statute annex. H2 prints an annualised figure against the statute's own
bounds (27–32), which is the pair a tenant can check against the published
Anlage. Spec: `docs/03` → "Seite 01b … (3) CO₂ short billing period".

Periods longer than twelve months are refused, not annualised downward — a
validation error inherited from Seite 01 (E6/E24), so annualisation never sees
one. The unchanged statutory step table has Rechtsstand 01/2023.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from lokara_domain import (
    Cents,
    Co2Step,
    Co2Table,
    Period,
    days_between,
    distribute_cents_half_up,
)

from .inputs import Co2Result, HeatingInputError

_ONE = Decimal(1)
# The renters' side of the two-way § 7 split is the complement of the landlord's
# rounded deduction, so it holds the leftover cent. Index 1, and the order of the
# pair is load-bearing: reordering it would silently invert the direction at an
# exact half cent (`docs/03` § 9.3).
_RENTER_SIDE = 1
# H2's divisor is a flat 365, and it triggers on `nTage ∉ {365, 366}` — Berkay's
# rule as written, *not* the anchored reference year the superseded convention
# used. A 366-day non-calendar period is therefore left un-annualised; recorded
# as an open convention in `docs/03` § 7 no. 8, not decided here.
_ANNUALISATION_DIVISOR_DAYS = 365
_FULL_YEAR_DAY_COUNTS = frozenset({365, 366})
_S3_QUANTUM = Decimal("0.1")


@dataclass(frozen=True)
class _PeriodBasis:
    """The period's length, the divisor H2 annualises by, and the resulting
    factor. `Co2Result` carries all three because the factor alone cannot be
    un-divided back into the days the disclosure copy needs."""

    period_days: int
    reference_year_days: int
    annualisation_factor: Decimal


def _reference_year_days(start: date) -> int:
    """Days in [start, same calendar date one year later).

    Used **only** to decide whether the period exceeds a year, not to annualise:
    anchoring on the period's own `valid_from` is what keeps a full leap year at
    366 of 366 rather than 366 of 365, so a leap year is not treated as longer
    than a year. A 29 Feb start rolls to 1 Mar (docs/03).
    """
    try:
        end = start.replace(year=start.year + 1)
    except ValueError:  # 29 Feb has no counterpart in the following year
        end = date(start.year + 1, 3, 1)
    return days_between(start, end)


def annualisation_factor_for(billing_period: Period) -> Decimal:
    """`365 / days(billing_period)`, or exactly 1 for a full year — exact, never float."""
    return _period_basis_for(billing_period).annualisation_factor


def _period_basis_for(billing_period: Period) -> _PeriodBasis:
    """The annualisation factor and the day counts behind it, computed together.

    Raises for a period longer than a year (E24): S. 4 addresses periods *under*
    a year and for Wohnraum a longer Abrechnungszeitraum is not lawful at all
    (§ 556 Abs. 3 S. 1 BGB). Annualising downward would enlarge nothing but
    would shrink the intensity, push the building into a **lower** Stufe and
    shift cost onto the renter — inventing a legal number in the one direction
    the 3 % Kürzungsrecht punishes (docs/03 → "Why a period > 12 months is
    refused rather than scaled").
    """
    if billing_period.valid_to is None:
        raise HeatingInputError(
            "CO₂ split requires a bounded billing period (valid_to is required)"
        )
    period_days = days_between(billing_period.valid_from, billing_period.valid_to)
    if period_days > _reference_year_days(billing_period.valid_from):
        raise HeatingInputError(
            "CO₂-Aufteilung nicht möglich: Der Abrechnungszeitraum "
            f"({billing_period.valid_from.isoformat()} bis "
            f"{billing_period.valid_to.isoformat()}, {period_days} Tage) ist länger als ein Jahr. "
            "Die Einstufungstabelle der Anlage zum CO2KostAufG gilt je Jahr "
            "(kg CO₂/m²/Jahr); für einen längeren Zeitraum gibt es keine gesetzliche Grundlage, "
            "den spezifischen Wert umzurechnen. Bitte den Abrechnungszeitraum auf höchstens "
            "zwölf Monate begrenzen (§ 556 Abs. 3 Satz 1 BGB)."
        )
    factor = (
        _ONE
        if period_days in _FULL_YEAR_DAY_COUNTS
        else Decimal(_ANNUALISATION_DIVISOR_DAYS) / Decimal(period_days)
    )
    return _PeriodBasis(
        period_days=period_days,
        # What was divided by, echoed rather than re-derived — the disclosure
        # prints "(275 von 365 Tagen)" and 1,327… cannot be un-divided into it.
        reference_year_days=_ANNUALISATION_DIVISOR_DAYS,
        annualisation_factor=factor,
    )


def _select_step(intensity_kg_per_sqm: Decimal, table: Co2Table) -> tuple[Decimal, int, Co2Step]:
    """Round under S. 3, then select the step from the unchanged Anlage table.

    The input must already be annualised under H2. Returning the quantized value
    with the step keeps classification and disclosure on the same figure.
    """
    rounded_intensity = intensity_kg_per_sqm.quantize(_S3_QUANTUM, rounding=ROUND_HALF_UP)
    for index, step in enumerate(table):
        if (
            step.max_intensity_exclusive is None
            or rounded_intensity < step.max_intensity_exclusive
        ):
            return rounded_intensity, index, step
    raise HeatingInputError(
        f"CO₂ table has no step for intensity {rounded_intensity} (missing open-ended step)"
    )


def landlord_share_percent_for_intensity(intensity_kg_per_sqm: Decimal, table: Co2Table) -> int:
    """Selects the step whose (exclusive) upper bound the annualised intensity
    falls under. Intervals are left-closed, right-open: exactly 12,00 is step 2,
    exactly 52,00 is the open-ended top step.

    This helper applies § 5 Abs. 1 S. 3 itself: it rounds the annualised value
    to one decimal with Lokara's `ROUND_HALF_UP` convention before selection.
    """
    return _select_step(intensity_kg_per_sqm, table)[2].landlord_share_percent


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
    # Annualised (H2), because the Anlage's column header reads
    # "… pro Quadratmeter Wohnfläche **und Jahr**". The quotient is recomputed
    # rather than multiplied by the stored factor (R2).
    intensity = total_co2_kg / heated_area_sqm
    if basis.period_days not in _FULL_YEAR_DAY_COUNTS:
        intensity = intensity * Decimal(_ANNUALISATION_DIVISOR_DAYS) / Decimal(basis.period_days)
    # R8: raw → annualise above → round to one decimal → classify. The same
    # rounded Decimal is carried in the result for the statement.
    intensity, index, step = _select_step(intensity, table)
    landlord_percent = step.landlord_share_percent
    previous_bound = table[index - 1].max_intensity_exclusive if index > 0 else None
    # R6 + H2: the *statutory percentage* is what gets `round_half_up`, and H2
    # makes the landlord's **deduction** the rounded quantity
    # (`co2AbzugVermieterCent = round_half_up(co2Cent × vermieterAnteil/100)`,
    # then `umlagefaehigCent = gesamtCent - co2Abzug`). This is a two-way split
    # by a statutory percentage, **not** an allocation across parties: there is
    # no owner bucket here, only the complement the formula names (`docs/03`
    # § 9.3). At an exact half cent the deduction therefore rounds **up**, i.e.
    # the landlord bears the cent — worth knowing before anyone "corrects" it.
    landlord_amount, renter_amount = distribute_cents_half_up(
        co2_cost, [landlord_percent, 100 - landlord_percent], residual_index=_RENTER_SIDE
    )
    return Co2Result(
        intensity_kg_per_sqm=intensity,
        annualisation_factor=basis.annualisation_factor,
        landlord_share_percent=landlord_percent,
        landlord_amount=landlord_amount,
        renter_amount=renter_amount,
        rechtsstand=rechtsstand,
        total_co2_kg=total_co2_kg,
        heated_area_sqm=heated_area_sqm,
        co2_cost=co2_cost,
        band_min_inclusive=previous_bound,
        band_max_exclusive=step.max_intensity_exclusive,
        period_days=basis.period_days,
        reference_year_days=basis.reference_year_days,
    )
