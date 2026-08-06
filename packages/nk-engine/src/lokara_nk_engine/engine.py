"""Day-weighted NK allocation over an Abrechnungszeitraum.

Weights are built from the temporal rows (never scalars); any day a unit is
not RENTED lands on the landlord side (vacancy/self-use); largest-remainder
rounding reconciles every cost to the input to the cent.

Line ordering is part of the contract: units in input order; within a unit,
renter segments chronological, then one aggregated landlord line. Ordering is
deterministic because largest-remainder ties break toward the lowest index.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lokara_domain import (
    AllocationKey,
    MeasurementUnit,
    Occupancy,
    Segment,
    build_unit_segments,
    cents,
    distribute_cents,
    overlap_days,
)

from .inputs import (
    ConsumptionValue,
    CostItem,
    NkInput,
    NkInputError,
    NkResult,
    ShareLine,
    UnitBasis,
)


@dataclass(frozen=True)
class _Party:
    unit_id: str | None
    tenancy_id: str | None
    weight: Decimal


def calculate_nk_statement(nk_input: NkInput) -> NkResult:
    window_from, window_to = _billing_window(nk_input)
    consumption_unit = _resolve_consumption_unit(nk_input.consumptions)

    lines: list[ShareLine] = []
    for cost in nk_input.costs:
        parties = _parties_for_cost(cost, nk_input, window_from, window_to)
        weights = [p.weight for p in parties]
        if not weights or sum(weights) == 0:
            raise NkInputError(f"Cost {cost.cost_id}: no positive allocation weights")
        amounts = distribute_cents(cost.amount, weights)
        lines.extend(
            ShareLine(
                cost_id=cost.cost_id,
                unit_id=party.unit_id,
                tenancy_id=party.tenancy_id,
                weight=party.weight,
                amount=amount,
            )
            for party, amount in zip(parties, amounts, strict=True)
        )
        assert sum(a for a in amounts) == cost.amount  # reconciliation, per cost

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
    return nk_input.billing_period.valid_from, nk_input.billing_period.valid_to


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
        segments = build_unit_segments(unit.unit_id, nk_input.occupancies, window_from, window_to)
        key_value = _unit_key_value(cost, unit)
        parties.extend(_segment_parties(unit.unit_id, segments, key_value))
    return parties


def _segment_parties(unit_id: str, segments: tuple[Segment, ...], key_value: int) -> list[_Party]:
    """Renter lines chronological (consecutive same-tenancy segments merged),
    then one aggregated landlord line for the unit's vacancy/self-use days."""
    parties: list[_Party] = []
    landlord_days = 0
    for segment in segments:
        if segment.tenancy_id is None:
            landlord_days += segment.days
            continue
        weight = Decimal(key_value * segment.days)
        last = parties[-1] if parties else None
        if last is not None and last.tenancy_id == segment.tenancy_id:
            parties[-1] = _Party(unit_id, segment.tenancy_id, last.weight + weight)
        else:
            parties.append(_Party(unit_id, segment.tenancy_id, weight))
    if landlord_days > 0:
        parties.append(_Party(unit_id, None, Decimal(key_value * landlord_days)))
    return [p for p in parties if p.weight > 0]


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
        if row.tenancy_id not in unit_by_tenancy:
            raise NkInputError(
                f"Cost {cost.cost_id}: person count references unknown tenancy {row.tenancy_id}"
            )
        parties.append(
            _Party(unit_by_tenancy[row.tenancy_id], row.tenancy_id, Decimal(row.count * days))
        )
    return parties


def _consumption_parties(cost: CostItem, nk_input: NkInput) -> list[_Party]:
    if not nk_input.consumptions:
        raise NkInputError(f"Cost {cost.cost_id}: CONSUMPTION key requires consumption values")
    return [
        _Party(row.unit_id, row.tenancy_id, row.value)
        for row in nk_input.consumptions
        if row.value > 0
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
        return _segment_parties(cost.direct_unit_id, segments, key_value=1)
    raise NkInputError(f"Cost {cost.cost_id}: DIRECT requires a target unit or tenancy")


def _unit_by_tenancy(occupancies: tuple[Occupancy, ...]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for occupancy in occupancies:
        if occupancy.tenancy_id is not None and occupancy.tenancy_id not in mapping:
            mapping[occupancy.tenancy_id] = occupancy.unit_id
    return mapping
