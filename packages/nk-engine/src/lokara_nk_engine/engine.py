"""Day-weighted NK allocation over an Abrechnungszeitraum.

Weights are built from the temporal rows (never scalars); any day a unit is
not RENTED stays in the denominator as vacancy/self-use. Renter lines round
half-up individually; the one unweighted owner residual reconciles each cost.

Line ordering is part of the contract: units in input order; within a unit,
renter segments chronological, then one aggregated landlord line. Ordering is
deterministic because largest-remainder ties break toward the lowest index.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise

from lokara_domain import (
    ZERO_CENTS,
    AllocationKey,
    MeasurementUnit,
    Occupancy,
    OccupancyOverlapError,
    Period,
    Segment,
    build_unit_segments,
    cents,
    distribute_cents_owner_residual,
    overlap_days,
)

from .inputs import (
    BillingWindowTooLongError,
    ConsumptionValue,
    CostItem,
    NkInput,
    NkInputError,
    NkResult,
    ShareLine,
    TenancyIneligibilityPeriod,
    UnitBasis,
)


@dataclass(frozen=True)
class _Party:
    unit_id: str | None
    tenancy_id: str | None
    weight: Decimal


def calculate_nk_statement(nk_input: NkInput) -> NkResult:
    window_from, window_to = _billing_window(nk_input)
    _validate_ineligibility_periods(nk_input.ineligible_tenancy_periods)
    consumption_unit = _resolve_consumption_unit(nk_input.consumptions)

    lines: list[ShareLine] = []
    for cost in nk_input.costs:
        parties = _parties_for_cost(cost, nk_input, window_from, window_to)
        renter_parties = [party for party in parties if party.tenancy_id is not None]
        owner_weight = sum(
            (party.weight for party in parties if party.tenancy_id is None), Decimal(0)
        )
        weights = [party.weight for party in renter_parties]
        if not weights or sum(weights, Decimal(0)) + owner_weight == 0:
            # 08-F12 / docs/08: "A zero consumption denominator gives renters 0
            # and leaves the cost with the owner; it never silently changes to
            # an area key." Refusing the cost was wrong in both directions: it
            # blocked a statement that Page 01 says must render, and the only
            # alternative a caller had was to re-key it. Every recorded party
            # keeps its rendered 0,00 EUR line and the pot goes to the owner.
            lines.extend(
                ShareLine(
                    cost_id=cost.cost_id,
                    unit_id=party.unit_id,
                    tenancy_id=party.tenancy_id,
                    weight=party.weight,
                    amount=ZERO_CENTS,
                )
                for party in renter_parties
            )
            lines.append(
                ShareLine(
                    cost_id=cost.cost_id,
                    unit_id=None,
                    tenancy_id=None,
                    weight=owner_weight,
                    amount=cost.amount,
                )
            )
            continue
        amounts, owner_amount = distribute_cents_owner_residual(
            cost.amount, weights, owner_weight=owner_weight
        )
        lines.extend(
            ShareLine(
                cost_id=cost.cost_id,
                unit_id=party.unit_id,
                tenancy_id=party.tenancy_id,
                weight=party.weight,
                amount=amount,
            )
            for party, amount in zip(renter_parties, amounts, strict=True)
        )
        lines.append(
            ShareLine(
                cost_id=cost.cost_id,
                unit_id=None,
                tenancy_id=None,
                weight=owner_weight,
                amount=owner_amount,
            )
        )
        assert sum(a for a in amounts) + owner_amount == cost.amount  # reconciliation, per cost

    total = cents(sum(int(line.amount) for line in lines))
    return NkResult(lines=tuple(lines), total=total, consumption_unit=consumption_unit)


def _resolve_consumption_unit(
    consumptions: tuple[ConsumptionValue, ...],
) -> MeasurementUnit | None:
    """The Maßeinheit every CONSUMPTION Bemessung is counted in (docs/08 rule 2).

    All parties supplying a value for the key must agree: the reference total is
    a **sum**, and `600 kWh + 250 m³` is not a quantity, so two distinct units
    are an input error rather than a display problem — never a silent pick,
    never a majority vote. Any row without a unit makes the key unit-less and
    the reference total is withheld (rule 3); NK has no estimation branch, so
    every row is a supplied value and every one of them must declare its unit.
    """
    declared = {row.measurement_unit for row in consumptions if row.measurement_unit is not None}
    if len(declared) > 1:
        raise NkInputError(
            "CONSUMPTION key mixes measurement units "
            f"({', '.join(sorted(u.value for u in declared))}); a Gesamtbemessung is a sum "
            "and units that cannot be summed cannot be a checkable denominator"
        )
    if not consumptions or any(row.measurement_unit is None for row in consumptions):
        return None
    return declared.pop()


def _billing_window(nk_input: NkInput) -> tuple[date, date]:
    if nk_input.billing_period.valid_to is None:
        raise NkInputError("Billing period must be bounded (valid_to is required)")
    window_from = nk_input.billing_period.valid_from
    window_to = nk_input.billing_period.valid_to
    # docs/02 § 5 step 1 and docs/08 "Period boundary": more than 12 months
    # hard-blocks BEFORE an engine run or render. It lives here, in the window
    # precondition, rather than in the per-cost loop: an over-long period is
    # wrong even for a statement that happens to carry no costs at all.
    #
    # Day-exact and calendar-based, never 365: an Abrechnungszeitraum is bounded
    # by the same day of the month twelve months on, so a leap year keeps its
    # actual 366 days (08-F20) and no special money rule appears anywhere.
    maximum_to = _twelve_months_after(window_from)
    if window_to > maximum_to:
        raise BillingWindowTooLongError(window_from, window_to, maximum_to)
    return window_from, window_to


def _twelve_months_after(day: date) -> date:
    """The same calendar day one year on, clamped for 29 February."""
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        # 29.02. in a leap year has no counterpart in the following year.
        return day.replace(year=day.year + 1, month=3, day=1)


def _parties_for_cost(
    cost: CostItem, nk_input: NkInput, window_from: date, window_to: date
) -> list[_Party]:
    match cost.key:
        case AllocationKey.AREA | AllocationKey.UNITS | AllocationKey.MEA:
            return _unit_value_parties(cost, nk_input, window_from, window_to)
        case AllocationKey.PERSONS:
            return _persons_parties(cost, nk_input, window_from, window_to)
        case AllocationKey.CONSUMPTION:
            return _consumption_parties(cost, nk_input)
        case AllocationKey.DIRECT:
            return _direct_parties(cost, nk_input, window_from, window_to)


def _unit_key_value(cost: CostItem, unit: UnitBasis) -> int:
    match cost.key:
        case AllocationKey.AREA:
            return unit.area_sqm_x100
        case AllocationKey.UNITS:
            return 1
        case AllocationKey.MEA:
            if unit.mea_x10000 is None:
                raise NkInputError(
                    f"Cost {cost.cost_id}: unit {unit.unit_id} has no MEA share for the MEA key"
                )
            return unit.mea_x10000
        case _:
            raise NkInputError(f"Cost {cost.cost_id}: {cost.key} is not a per-unit key")


def _unit_value_parties(
    cost: CostItem, nk_input: NkInput, window_from: date, window_to: date
) -> list[_Party]:
    parties: list[_Party] = []
    for unit in nk_input.units:
        key_value = _unit_key_value(cost, unit)
        try:
            segments = build_unit_segments(
                unit.unit_id, nk_input.occupancies, window_from, window_to
            )
        except OccupancyOverlapError as overlap:
            # The timeline builder is key-agnostic, so it measures in
            # Einheiten·Tage. Only here is the applied key known, so this is
            # where docs/08 "Reference totals" de-scaling happens — once.
            raise overlap.rescaled(_display_key_value(cost, key_value)) from overlap
        parties.extend(
            _segment_parties(
                unit.unit_id,
                segments,
                key_value,
                nk_input.ineligible_tenancy_periods,
                cost.cost_id,
            )
        )
    return parties


def _display_key_value(cost: CostItem, key_value: int) -> Decimal:
    """The unit's key value in the key's printed unit (docs/08 "Reference totals").

    `36.500 m²·Tage` must never render as `3.650.000`, so the fixed-point scale
    comes off before the figure reaches a human. UNITS is already a count.
    """
    divisor = _KEY_DISPLAY_DIVISORS.get(cost.key)
    return Decimal(key_value) if divisor is None else Decimal(key_value) / divisor


_KEY_DISPLAY_DIVISORS: dict[AllocationKey, Decimal] = {
    AllocationKey.AREA: Decimal(100),
    AllocationKey.MEA: Decimal(10000),
}


def _segment_parties(
    unit_id: str,
    segments: tuple[Segment, ...],
    key_value: int,
    ineligible_periods: tuple[TenancyIneligibilityPeriod, ...] = (),
    cost_id: str | None = None,
) -> list[_Party]:
    """Renter lines chronological (consecutive same-tenancy segments merged),
    then one aggregated landlord line for the unit's vacancy/self-use days."""
    parties: list[_Party] = []
    landlord_days = 0
    for segment in segments:
        if segment.tenancy_id is None:
            landlord_days += segment.days
            continue
        ineligible_days = _ineligible_days(segment.tenancy_id, segment, ineligible_periods, cost_id)
        eligible_days = segment.days - ineligible_days
        # The renter remains a printed party even where every day is
        # ineligible.  Their ordinary days enter the owner denominator below.
        weight = Decimal(key_value * eligible_days)
        last = parties[-1] if parties else None
        if last is not None and last.tenancy_id == segment.tenancy_id:
            parties[-1] = _Party(unit_id, segment.tenancy_id, last.weight + weight)
        else:
            parties.append(_Party(unit_id, segment.tenancy_id, weight))
        landlord_days += ineligible_days
    if landlord_days > 0:
        parties.append(_Party(unit_id, None, Decimal(key_value * landlord_days)))
    return parties


def _persons_parties(
    cost: CostItem, nk_input: NkInput, window_from: date, window_to: date
) -> list[_Party]:
    if not nk_input.person_counts:
        raise NkInputError(f"Cost {cost.cost_id}: PERSONS key requires person_counts")
    unit_by_tenancy = _unit_by_tenancy(nk_input.occupancies)
    parties: list[_Party] = []
    for row in nk_input.person_counts:
        days = overlap_days(row.period, window_from, window_to)
        if days == 0:
            continue
        if row.tenancy_id is None:
            # D0 Fiktivbelegung (docs/02 § 5, Page 01 § 4 D0): the fictional
            # occupancy of what stood empty. It is added to the denominator
            # BEFORE any share is formed, and it lands on the landlord side —
            # a weight, never a party, never a Renter. The count itself was
            # derived by the caller; the engine only weights it by days.
            parties.append(_Party(row.unit_id, None, Decimal(row.count * days)))
            continue
        if row.tenancy_id not in unit_by_tenancy:
            raise NkInputError(
                f"Cost {cost.cost_id}: person count references unknown tenancy {row.tenancy_id}"
            )
        ineligible_days = _ineligible_days_for_period(
            row.tenancy_id,
            row.period,
            window_from,
            window_to,
            nk_input.ineligible_tenancy_periods,
            cost.cost_id,
        )
        parties.append(
            _Party(
                unit_by_tenancy[row.tenancy_id],
                row.tenancy_id,
                Decimal(row.count * (days - ineligible_days)),
            )
        )
        if ineligible_days:
            parties.append(
                _Party(unit_by_tenancy[row.tenancy_id], None, Decimal(row.count * ineligible_days))
            )
    return parties


def _consumption_parties(cost: CostItem, nk_input: NkInput) -> list[_Party]:
    if not nk_input.consumptions:
        raise NkInputError(f"Cost {cost.cost_id}: CONSUMPTION key requires consumption values")
    # A recorded zero is a reading, not a missing row. docs/08: "Every cost line
    # receives engine output" — a renter whose meter read 0 gets a rendered
    # 0,00 EUR share, never a row the document layer has to invent (08-F12).
    # Meter values have no sub-period in the current normalized input.  A
    # confirmed ineligible period therefore conservatively withholds that
    # tenancy's recorded value for this cost; it is still retained as owner
    # denominator weight and yields the required zero renter line.
    return [
        _Party(
            row.unit_id,
            row.tenancy_id,
            Decimal(0)
            if row.tenancy_id is not None
            and any(
                p.tenancy_id == row.tenancy_id and (p.cost_id is None or p.cost_id == cost.cost_id)
                for p in nk_input.ineligible_tenancy_periods
            )
            else row.value,
        )
        for row in nk_input.consumptions
    ] + [
        _Party(row.unit_id, None, row.value)
        for row in nk_input.consumptions
        if row.tenancy_id is not None
        and any(
            p.tenancy_id == row.tenancy_id and (p.cost_id is None or p.cost_id == cost.cost_id)
            for p in nk_input.ineligible_tenancy_periods
        )
    ]


def _direct_parties(
    cost: CostItem, nk_input: NkInput, window_from: date, window_to: date
) -> list[_Party]:
    if cost.direct_tenancy_id is not None:
        unit_by_tenancy = _unit_by_tenancy(nk_input.occupancies)
        if cost.direct_tenancy_id not in unit_by_tenancy:
            raise NkInputError(
                f"Cost {cost.cost_id}: DIRECT target tenancy {cost.direct_tenancy_id} not found"
            )
        return [_Party(unit_by_tenancy[cost.direct_tenancy_id], cost.direct_tenancy_id, Decimal(1))]
    if cost.direct_unit_id is not None:
        if all(u.unit_id != cost.direct_unit_id for u in nk_input.units):
            raise NkInputError(
                f"Cost {cost.cost_id}: DIRECT target unit {cost.direct_unit_id} not found"
            )
        segments = build_unit_segments(
            cost.direct_unit_id, nk_input.occupancies, window_from, window_to
        )
        return _segment_parties(
            cost.direct_unit_id,
            segments,
            key_value=1,
            ineligible_periods=nk_input.ineligible_tenancy_periods,
            cost_id=cost.cost_id,
        )
    raise NkInputError(f"Cost {cost.cost_id}: DIRECT requires a target unit or tenancy")


def _unit_by_tenancy(occupancies: tuple[Occupancy, ...]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for occupancy in occupancies:
        if occupancy.tenancy_id is not None and occupancy.tenancy_id not in mapping:
            mapping[occupancy.tenancy_id] = occupancy.unit_id
    return mapping


def _ineligible_days(
    tenancy_id: str,
    segment: Segment,
    periods: tuple[TenancyIneligibilityPeriod, ...],
    cost_id: str | None,
) -> int:
    return sum(
        overlap_days(row.period, segment.start, segment.start + timedelta(days=segment.days))
        for row in periods
        if row.tenancy_id == tenancy_id and (row.cost_id is None or row.cost_id == cost_id)
    )


def _ineligible_days_for_period(
    tenancy_id: str,
    period: Period,
    window_from: date,
    window_to: date,
    periods: tuple[TenancyIneligibilityPeriod, ...],
    cost_id: str | None,
) -> int:
    start = max(period.valid_from, window_from)
    end = min(period.valid_to or window_to, window_to)
    if end <= start:
        return 0
    return sum(
        overlap_days(row.period, start, end)
        for row in periods
        if row.tenancy_id == tenancy_id and (row.cost_id is None or row.cost_id == cost_id)
    )


def _validate_ineligibility_periods(periods: tuple[TenancyIneligibilityPeriod, ...]) -> None:
    by_tenancy: dict[tuple[str, str | None], list[Period]] = {}
    for row in periods:
        if row.period.valid_to is None:
            raise NkInputError("Ineligible tenancy periods must be bounded")
        by_tenancy.setdefault((row.tenancy_id, row.cost_id), []).append(row.period)
    for (tenancy_id, _cost_id), tenancy_periods in by_tenancy.items():
        ordered = sorted(tenancy_periods, key=lambda period: period.valid_from)
        for earlier, later in pairwise(ordered):
            assert earlier.valid_to is not None
            if later.valid_from < earlier.valid_to:
                raise NkInputError(f"Ineligible tenancy periods overlap for {tenancy_id}")
