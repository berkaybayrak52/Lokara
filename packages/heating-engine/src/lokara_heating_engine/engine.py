"""Heating + CO₂ statement calculation (M2).

Pipeline (every split via largest-remainder, so each stage reconciles):
1. CO₂ landlord share (CO2KostAufG 10-step) is deducted from the total first.
2. § 9 HeizkostenV: warm-water energy is separated from the billable cost.
3. §§ 7/8: each pot splits into base (fixed) and consumption portions.
4. Base portions allocate by day-weighted area (derived vacancy → landlord);
   consumption portions by measured values — degree-days apportion a unit's
   single reading across occupant changes (warm water/base by days instead).
5. § 9a: missing readings are estimated per m²; > 25 % missing area → the
   consumption portion falls back to the area key.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lokara_domain import (
    Cents,
    Segment,
    build_unit_segments,
    cents,
    distribute_cents,
)

from .co2 import split_co2_cost
from .degree_days import degree_day_weight
from .inputs import (
    Co2Result,
    HeatingInput,
    HeatingInputError,
    HeatingLine,
    HeatingResult,
    HeatingUnit,
)

_ZERO = cents(0)


@dataclass(frozen=True)
class _Party:
    unit_id: str
    tenancy_id: str | None
    days: int
    base_weight: Decimal
    degree_day_promille: Decimal


def calculate_heating_statement(heating_input: HeatingInput) -> HeatingResult:
    _validate(heating_input)
    window_from, window_to = (
        heating_input.billing_period.valid_from,
        heating_input.billing_period.valid_to,
    )
    assert window_to is not None  # _validate guarantees a bounded period

    parties = _build_parties(heating_input, window_from, window_to)
    party_count = len(parties)
    base_weights = [p.base_weight for p in parties]

    co2_result, billable = _apply_co2(heating_input)

    ww_pot, heating_pot = _separate_warm_water(heating_input, billable, window_from, window_to)

    share = heating_input.rules.consumption_share
    heat_base_pot, heat_cons_pot = distribute_cents(heating_pot, [1 - share, share])
    heat_base = distribute_cents(heat_base_pot, base_weights)

    heat_values, heat_estimated, heat_fallback = _resolve_readings(
        heating_input.units, [u.heat_consumption for u in heating_input.units]
    )
    if heat_fallback:
        heat_cons = distribute_cents(heat_cons_pot, base_weights)
    else:
        heat_cons = distribute_cents(
            heat_cons_pot, _consumption_weights(parties, heat_values, by_degree_days=True)
        )

    ww_estimated: tuple[str, ...] = ()
    ww_fallback = False
    if heating_input.warm_water is not None:
        ww_base_pot, ww_cons_pot = distribute_cents(ww_pot, [1 - share, share])
        ww_base = distribute_cents(ww_base_pot, base_weights)
        ww_values, ww_estimated, ww_fallback = _resolve_readings(
            heating_input.units, [u.ww_consumption_m3 for u in heating_input.units]
        )
        if ww_fallback:
            ww_cons = distribute_cents(ww_cons_pot, base_weights)
        else:
            ww_cons = distribute_cents(
                ww_cons_pot, _consumption_weights(parties, ww_values, by_degree_days=False)
            )
    else:
        ww_base = [_ZERO] * party_count
        ww_cons = [_ZERO] * party_count

    lines = tuple(
        HeatingLine(
            unit_id=party.unit_id,
            tenancy_id=party.tenancy_id,
            heating_base=hb,
            heating_consumption=hc,
            ww_base=wb,
            ww_consumption=wc,
            total=cents(int(hb) + int(hc) + int(wb) + int(wc)),
        )
        for party, hb, hc, wb, wc in zip(
            parties, heat_base, heat_cons, ww_base, ww_cons, strict=True
        )
    )

    landlord_co2 = int(co2_result.landlord_amount) if co2_result is not None else 0
    total = cents(sum(int(line.total) for line in lines) + landlord_co2)
    assert total == heating_input.total_cost  # reconciliation — never ship without it

    estimated = tuple(
        u.unit_id
        for u in heating_input.units
        if u.unit_id in set(heat_estimated) | set(ww_estimated)
    )
    return HeatingResult(
        lines=lines,
        co2=co2_result,
        estimated_unit_ids=estimated,
        consumption_fallback_to_area=heat_fallback or ww_fallback,
        total=total,
    )


def _validate(heating_input: HeatingInput) -> None:
    if heating_input.billing_period.valid_to is None:
        raise HeatingInputError("Billing period must be bounded (valid_to is required)")
    if not heating_input.units:
        raise HeatingInputError("At least one unit is required")
    bounds = heating_input.rules.split_bounds
    share = heating_input.rules.consumption_share
    if not (bounds.min_consumption_share <= share <= bounds.max_consumption_share):
        raise HeatingInputError(
            f"Consumption share {share} outside § 7 HeizkostenV bounds "
            f"[{bounds.min_consumption_share}, {bounds.max_consumption_share}]"
        )
    if heating_input.co2 is not None and (
        heating_input.rules.co2_table is None or heating_input.rules.co2_rechtsstand is None
    ):
        raise HeatingInputError(
            "CO₂ input given but rules carry no CO₂ table/Rechtsstand (CO2KostAufG)"
        )


def _build_parties(
    heating_input: HeatingInput, window_from: date, window_to: date
) -> list[_Party]:
    """Units in input order; within a unit renter parties chronological
    (consecutive same-tenancy segments merged), then one aggregated landlord
    party — the same deterministic ordering as the NK engine."""
    table = heating_input.rules.degree_days
    parties: list[_Party] = []
    for unit in heating_input.units:
        segments = build_unit_segments(
            unit.unit_id, heating_input.occupancies, window_from, window_to
        )
        unit_parties: list[_Party] = []
        landlord_segments: list[Segment] = []
        for segment in segments:
            if segment.tenancy_id is None:
                landlord_segments.append(segment)
                continue
            promille = degree_day_weight(segment.start, segment.days, table)
            last = unit_parties[-1] if unit_parties else None
            if last is not None and last.tenancy_id == segment.tenancy_id:
                unit_parties[-1] = _Party(
                    unit_id=unit.unit_id,
                    tenancy_id=segment.tenancy_id,
                    days=last.days + segment.days,
                    base_weight=last.base_weight + Decimal(unit.area_sqm_x100 * segment.days),
                    degree_day_promille=last.degree_day_promille + promille,
                )
            else:
                unit_parties.append(
                    _Party(
                        unit_id=unit.unit_id,
                        tenancy_id=segment.tenancy_id,
                        days=segment.days,
                        base_weight=Decimal(unit.area_sqm_x100 * segment.days),
                        degree_day_promille=promille,
                    )
                )
        if landlord_segments:
            days = sum(s.days for s in landlord_segments)
            promille = sum(
                (degree_day_weight(s.start, s.days, table) for s in landlord_segments),
                Decimal(0),
            )
            unit_parties.append(
                _Party(
                    unit_id=unit.unit_id,
                    tenancy_id=None,
                    days=days,
                    base_weight=Decimal(unit.area_sqm_x100 * days),
                    degree_day_promille=promille,
                )
            )
        parties.extend(unit_parties)
    return parties


def _apply_co2(heating_input: HeatingInput) -> tuple[Co2Result | None, Cents]:
    if heating_input.co2 is None:
        return None, heating_input.total_cost
    table = heating_input.rules.co2_table
    rechtsstand = heating_input.rules.co2_rechtsstand
    assert table is not None and rechtsstand is not None  # _validate guarantees
    heated_area_sqm = Decimal(sum(u.area_sqm_x100 for u in heating_input.units)) / 100
    co2_result = split_co2_cost(
        total_co2_kg=heating_input.co2.total_co2_kg,
        co2_cost=heating_input.co2.co2_cost,
        heated_area_sqm=heated_area_sqm,
        table=table,
        rechtsstand=rechtsstand,
    )
    billable = cents(int(heating_input.total_cost) - int(co2_result.landlord_amount))
    return co2_result, billable


def _separate_warm_water(
    heating_input: HeatingInput, billable: Cents, window_from: date, window_to: date
) -> tuple[Cents, Cents]:
    """§ 9: returns (ww_pot, heating_pot)."""
    if heating_input.warm_water is None:
        return _ZERO, billable
    formula = heating_input.rules.warm_water_formula
    if heating_input.warm_water.volume_m3 is not None:
        q_ww = formula.energy_kwh_for_volume(heating_input.warm_water.volume_m3)
    else:
        # § 9 Abs. 2 fallback: kWh per m² living area per year, pro-rated.
        area_sqm = Decimal(sum(u.area_sqm_x100 for u in heating_input.units)) / 100
        days = Decimal((window_to - window_from).days)
        q_ww = formula.area_fallback_kwh_per_sqm_year * area_sqm * days / Decimal(365)
    if q_ww <= 0 or q_ww >= heating_input.total_energy_kwh:
        raise HeatingInputError(
            f"Warm-water energy {q_ww} kWh must lie inside (0, total energy "
            f"{heating_input.total_energy_kwh} kWh)"
        )
    ww_pot, heating_pot = distribute_cents(
        billable, [q_ww, heating_input.total_energy_kwh - q_ww]
    )
    return ww_pot, heating_pot


def _resolve_readings(
    units: tuple[HeatingUnit, ...], values: list[Decimal | None]
) -> tuple[dict[str, Decimal], tuple[str, ...], bool]:
    """§ 9a: estimates missing readings from the measured units' per-m² average.
    Returns (value per unit, estimated unit ids, fallback-to-area flag)."""
    total_area = sum(u.area_sqm_x100 for u in units)
    missing_area = sum(u.area_sqm_x100 for u, v in zip(units, values, strict=True) if v is None)
    if missing_area * 4 > total_area:  # strictly more than 25 %
        return {}, (), True

    resolved: dict[str, Decimal] = {}
    estimated: list[str] = []
    measured_sum = sum(
        (v for v in values if v is not None),
        Decimal(0),
    )
    measured_area = total_area - missing_area
    for unit, value in zip(units, values, strict=True):
        if value is not None:
            resolved[unit.unit_id] = value
        else:
            resolved[unit.unit_id] = measured_sum * Decimal(unit.area_sqm_x100) / Decimal(
                measured_area
            )
            estimated.append(unit.unit_id)
    return resolved, tuple(estimated), False


def _consumption_weights(
    parties: list[_Party], values: dict[str, Decimal], *, by_degree_days: bool
) -> list[Decimal]:
    """Splits each unit's single reading across its parties: heating by
    degree-days (weather-dependent), warm water by days."""
    unit_parties: dict[str, list[_Party]] = {}
    for party in parties:
        unit_parties.setdefault(party.unit_id, []).append(party)

    weights: list[Decimal] = []
    for party in parties:
        value = values[party.unit_id]
        siblings = unit_parties[party.unit_id]
        if len(siblings) == 1:
            weights.append(value)
            continue
        if by_degree_days:
            own = party.degree_day_promille
            total = sum((p.degree_day_promille for p in siblings), Decimal(0))
        else:
            own = Decimal(party.days)
            total = Decimal(sum(p.days for p in siblings))
        weights.append(value * own / total)
    return weights
