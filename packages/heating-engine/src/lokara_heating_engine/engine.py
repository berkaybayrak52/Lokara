"""Heating + CO₂ statement calculation (M2).

Pipeline (every split reconciles to its input by construction):
1. CO₂ landlord share (CO2KostAufG 10-step) is deducted from the total first.
2. § 9 HeizkostenV: warm-water energy is separated from the billable cost.
3. §§ 7/8: each pot splits into base (fixed) and consumption portions.
4. Base portions allocate by day-weighted area (derived vacancy → landlord);
   consumption portions by measured values — degree-days apportion a unit's
   single reading across occupant changes (warm water/base by days instead).
5. § 9a: missing readings are estimated per m²; > 25 % missing area → the
   consumption portion falls back to the area key.

**Rounding (R1/R5/K9, `docs/03` § 9.1).** A pot split into two complementary
parts names its rounded side by the formula and gives the rest to the
complement: `grund = round_half_up(pot × p)`, `verbrauch = pot - grund`. A
Blockbetrag allocated across parties gives every renter its own
`round_half_up` and puts the `Verteilungsrest` on the **Liegenschafts-Residuum**
— one Eigentümerzeile per Liegenschaft, the same line in all four blocks
(§ 1.3 Frage 3), so one line explains every ±ct of the statement:

    eigentuemerCent[block] = blockbetragCent[block] - Σ mieteranteilCent[block]

That line is **not a party**. It is never derived from occupancy and never
computed from a weight; the vacancy's Fiktivbelegung (D0) enters the
**denominator** and nowhere else, which is what makes the residual come out at
the vacancy share rather than at zero. It exists in every building, including a
fully let one, where it is the pure line-wise Rundungsdifferenz and typically
**-0,01 € per block** — negative because `round_half_up` biases the renter
shares upward. Model: `docs/02` → *"The Eigentümeranteil is a residual line, not
a party"*; engine wiring and the two conventions it superseded: `docs/03` § 9.2.

Rechtsnatur: the approved fixed model rule in `docs/03` § 9.2 and original Page
01 D12, so the destination of the Verteilungsrest carries no
`verify-before-production` flag. K9 keeps its flag
for what remains of it, the `round_half_up` direction; no output may present
that as a norm.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lokara_domain import (
    Cents,
    MeasurementUnit,
    Segment,
    build_unit_segments,
    cents,
    co2_grams_from_energy,
    distribute_cents_half_up,
    distribute_cents_owner_residual,
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
    OwnerResidual,
    OwnerResidualOrigin,
    WarmWaterSeparation,
)

_ZERO = cents(0)
# A two-element pot split is written `a = round_half_up(pot × q)`, `b = pot - a`:
# the formula names its rounded side, and the residual sits on the *complement*,
# which is index 1 in every such call here (`docs/03` § 9.1 sites #1, #5, #9).
# Not a party index and never an owner bucket — see § 9.2.
_COMPLEMENT = 1


def _heated_area_sqm(units: tuple[HeatingUnit, ...]) -> Decimal:
    """The building's heated area. One source: § 7 Abs. 3 CO2KostAufG and § 9
    Abs. 2's Ersatzwert must never disclose two different areas for one
    building."""
    return Decimal(sum(u.area_sqm_x100 for u in units)) / 100


@dataclass(frozen=True)
class _Party:
    unit_id: str
    tenancy_id: str | None
    days: int
    base_weight: Decimal
    degree_day_promille: Decimal


@dataclass(frozen=True)
class _Block:
    """One Blockbetrag, allocated: the renter rows, block (a) per empty unit,
    and the Eigentümerzeile's figure for that block."""

    renters: list[Cents]
    # (a) — the empty/self-used units' *separately computed* shares, aligned
    # with `_Split.owner_indexes`. Never an output on the Gesamtübersicht.
    origins: list[Cents]
    owner: Cents


@dataclass(frozen=True)
class _Split:
    """Which of the engine's internal parties are Mietverhältnisse and which are
    the empty/self-used segments the Eigentümerzeile aggregates.

    Both index into the same `parties` list, because a consumption weight is
    apportioned across *all* of a unit's segments and only then split — the
    landlord segment is a denominator entry, never a row.
    """

    renter_indexes: list[int]
    owner_indexes: list[int]


def _split_parties(parties: list[_Party]) -> _Split:
    return _Split(
        renter_indexes=[i for i, p in enumerate(parties) if p.tenancy_id is not None],
        owner_indexes=[i for i, p in enumerate(parties) if p.tenancy_id is None],
    )


def _allocate_to_parties(pot: Cents, weights: list[Decimal], split: _Split) -> _Block:
    """R1/R5 with the Liegenschafts-Residuum: every renter gets its own
    `round_half_up` against a denominator that includes the owner's Bemessung,
    and the Eigentümerzeile gets `pot - Σ Mieteranteile`.

    `sum(renters) + owner == pot` holds by construction, in every composition —
    including a fully let one, where the residual is the pure line-wise
    Rundungsdifferenz. There is no second allocation method and no branch:
    § 1.3 Frage 3 rejected the largest-remainder fallback outright.
    """
    renter_weights = [weights[i] for i in split.renter_indexes]
    owner_weights = [weights[i] for i in split.owner_indexes]
    renters, owner = distribute_cents_owner_residual(
        pot, renter_weights, owner_weight=sum(owner_weights, Decimal(0))
    )
    # Block (a): each empty unit's **own** `round_half_up` against the same full
    # denominator — what the Leerstandsaufstellung itemises for Anlage V, and
    # what D12 forbids as the *printed* figure. The same primitive with the roles
    # exchanged (R1 is symmetric); the rest it returns is the renters' and is
    # discarded, because (a) and the printed residual are two routes to one
    # quantity and their difference is block (c).
    origins, _ = distribute_cents_owner_residual(
        pot, owner_weights, owner_weight=sum(renter_weights, Decimal(0))
    )
    return _Block(renters=renters, origins=origins, owner=owner)


def _zero_block(split: _Split) -> _Block:
    """No warm-water column exists at all — every figure in it is `0`, the
    Eigentümerzeile's included. Not a § 9a Abs. 2 fallback, and the statement
    must not claim one happened."""
    return _Block(
        renters=[_ZERO] * len(split.renter_indexes),
        origins=[_ZERO] * len(split.owner_indexes),
        owner=_ZERO,
    )


def _reconcile_all_area_blocks_to_single_allocation(
    billable: Cents,
    base_weights: list[Decimal],
    split: _Split,
    blocks: tuple[_Block, _Block, _Block, _Block],
) -> tuple[_Block, _Block, _Block, _Block]:
    """Make area-only renter totals follow one allocation of the full amount.

    When every non-zero block uses the same m²-days key, allocating each block
    separately can round a renter once per block. § 9a Abs. 2 instead fixes the
    renter total from one allocation of the full billable amount. The final
    non-zero block carries the cent reconciliation so every block still sums to
    its disclosed pot and the owner remains the structural residual.
    """
    target = _allocate_to_parties(billable, base_weights, split)
    current_totals = [
        sum(int(block.renters[index]) for block in blocks)
        for index in range(len(split.renter_indexes))
    ]
    deltas = [
        int(expected) - current
        for expected, current in zip(target.renters, current_totals, strict=True)
    ]
    if not any(deltas):
        return blocks

    reconcile_index = next(
        (
            index
            for index in range(len(blocks) - 1, -1, -1)
            if int(blocks[index].owner) + sum(int(value) for value in blocks[index].renters) != 0
        ),
        len(blocks) - 1,
    )
    reconciled = blocks[reconcile_index]
    replacement = _Block(
        renters=[
            cents(int(value) + delta)
            for value, delta in zip(reconciled.renters, deltas, strict=True)
        ],
        origins=reconciled.origins,
        owner=cents(int(reconciled.owner) - sum(deltas)),
    )
    result = list(blocks)
    result[reconcile_index] = replacement
    return result[0], result[1], result[2], result[3]


def calculate_heating_statement(heating_input: HeatingInput) -> HeatingResult:
    _validate(heating_input)
    window_from, window_to = (
        heating_input.billing_period.valid_from,
        heating_input.billing_period.valid_to,
    )
    assert window_to is not None  # _validate guarantees a bounded period

    parties = _build_parties(heating_input, window_from, window_to)
    base_weights = [p.base_weight for p in parties]
    split = _split_parties(parties)

    co2_result, billable = _apply_co2(heating_input)

    ww_pot, heating_pot, separation = _separate_warm_water(
        heating_input, billable, window_from, window_to
    )

    share = heating_input.rules.consumption_share
    # Site #1 — H4: `grundHz = round_half_up(kostenHz × p)`, the consumption pot
    # is the complement, so the sum is exact. No owner bucket here: the residual
    # holder is the other *pot*, not a party.
    heat_base_pot, heat_cons_pot = distribute_cents_half_up(
        heating_pot, [1 - share, share], residual_index=_COMPLEMENT
    )
    heat_base = _allocate_to_parties(heat_base_pot, base_weights, split)

    heat_values, heat_estimated, heat_fallback = _resolve_readings(
        heating_input.units, [u.heat_consumption for u in heating_input.units]
    )
    # `None` = no consumption Bemessung was applied to this column, so none may
    # be disclosed; otherwise these are the exact weights that were allocated by.
    heat_weights: list[Decimal] | None = None
    if heat_fallback:
        # Site #3 — § 9a Abs. 2 replaces the *key*, never the rounding rule.
        heat_cons = _allocate_to_parties(heat_cons_pot, base_weights, split)
    else:
        # Site #4.
        heat_weights = _consumption_weights(parties, heat_values, by_degree_days=True)
        heat_cons = _allocate_to_parties(heat_cons_pot, heat_weights, split)
    # The unit follows the weights it labels: `None` under § 9a Abs. 2 means the
    # consumption key was *replaced*, so there is no Bemessung to put a unit on.
    heat_unit = None if heat_fallback else _resolve_heat_unit(heating_input.units)

    ww_estimated: tuple[str, ...] = ()
    ww_fallback = False
    ww_weights: list[Decimal] | None = None
    if heating_input.warm_water is not None:
        # Site #5 — H4's second line pair; residual on the complement pot.
        ww_base_pot, ww_cons_pot = distribute_cents_half_up(
            ww_pot, [1 - share, share], residual_index=_COMPLEMENT
        )
        # Site #6.
        ww_base = _allocate_to_parties(ww_base_pot, base_weights, split)
        ww_values, ww_estimated, ww_fallback = _resolve_readings(
            heating_input.units, [u.ww_consumption_m3 for u in heating_input.units]
        )
        if ww_fallback:
            # Site #7 — as #3.
            ww_cons = _allocate_to_parties(ww_cons_pot, base_weights, split)
        else:
            # Site #8.
            ww_weights = _consumption_weights(parties, ww_values, by_degree_days=False)
            ww_cons = _allocate_to_parties(ww_cons_pot, ww_weights, split)
    else:
        # No warm-water column exists at all — that is not a § 9a Abs. 2
        # fallback, and the statement must not claim one happened.
        ww_base_pot, ww_cons_pot = _ZERO, _ZERO
        ww_base = _zero_block(split)
        ww_cons = _zero_block(split)

    if heat_fallback and (heating_input.warm_water is None or ww_fallback):
        heat_base, heat_cons, ww_base, ww_cons = _reconcile_all_area_blocks_to_single_allocation(
            billable,
            base_weights,
            split,
            (heat_base, heat_cons, ww_base, ww_cons),
        )

    unit_days, unit_promille = _unit_totals(parties)
    lines = tuple(
        HeatingLine(
            unit_id=parties[index].unit_id,
            tenancy_id=parties[index].tenancy_id,
            heating_base=hb,
            heating_consumption=hc,
            ww_base=wb,
            ww_consumption=wc,
            total=cents(int(hb) + int(hc) + int(wb) + int(wc)),
            days=parties[index].days,
            unit_total_days=unit_days[parties[index].unit_id],
            base_weight_sqm_days_x100=parties[index].base_weight,
            heat_consumption_weight=None if heat_weights is None else heat_weights[index],
            ww_consumption_weight_m3=None if ww_weights is None else ww_weights[index],
            degree_day_promille=parties[index].degree_day_promille,
            unit_degree_day_promille_total=unit_promille[parties[index].unit_id],
        )
        for index, hb, hc, wb, wc in zip(
            split.renter_indexes,
            heat_base.renters,
            heat_cons.renters,
            ww_base.renters,
            ww_cons.renters,
            strict=True,
        )
    )
    owner_residual = _owner_residual(
        parties,
        split,
        (heat_base, heat_cons, ww_base, ww_cons),
        heat_weights,
        ww_weights,
        unit_days,
        unit_promille,
    )

    landlord_co2 = int(co2_result.landlord_amount) if co2_result is not None else 0
    # `Σ Mieteranteile + Eigentümeranteil (+ CO₂-Vermieteranteil) == Gesamtkosten`
    # — § 1.1, and the residual is *inside* that sum, never an exception to it.
    total = cents(sum(int(line.total) for line in lines) + int(owner_residual.total) + landlord_co2)
    assert total == heating_input.total_cost  # reconciliation — never ship without it

    estimated = tuple(
        u.unit_id
        for u in heating_input.units
        if u.unit_id in set(heat_estimated) | set(ww_estimated)
    )
    return HeatingResult(
        lines=lines,
        owner_residual=owner_residual,
        co2=co2_result,
        estimated_unit_ids=estimated,
        consumption_fallback_to_area=heat_fallback or ww_fallback,
        heat_fallback_to_area=heat_fallback,
        ww_fallback_to_area=ww_fallback,
        total=total,
        billable_cost=billable,
        heating_pot=heating_pot,
        ww_pot=ww_pot,
        heat_base_pot=heat_base_pot,
        heat_cons_pot=heat_cons_pot,
        ww_base_pot=ww_base_pot,
        ww_cons_pot=ww_cons_pot,
        applied_consumption_share=share,
        split_bounds=heating_input.rules.split_bounds,
        warm_water_separation=separation,
        heat_consumption_unit=heat_unit,
    )


def _sum_weights(
    weights: list[Decimal] | None, indexes: list[int], *, empty_is_none: bool
) -> Decimal | None:
    """The Bemessung the Eigentümerzeile prints, aggregated over the empty units.

    Two distinct reasons for `None`, and both must stay `None` rather than `0`
    (`docs/08` § 2). Either **no consumption Bemessung was applied to that
    column at all** (§ 9a Abs. 2, or no central warm water — `weights is None`,
    exactly as on every `HeatingLine`), or **nothing stood empty and nothing was
    self-used**, in which case the column is empty rather than zero: a printed
    `0` would imply an allocation base of zero instead of none.
    """
    if weights is None or (empty_is_none and not indexes):
        return None
    return sum((weights[index] for index in indexes), Decimal(0))


def _owner_residual(
    parties: list[_Party],
    split: _Split,
    blocks: tuple[_Block, _Block, _Block, _Block],
    heat_weights: list[Decimal] | None,
    ww_weights: list[Decimal] | None,
    unit_days: dict[str, int],
    unit_promille: dict[str, Decimal],
) -> OwnerResidual:
    """The one Eigentümerzeile, and block (a) underneath it.

    `origins` are the empty/self-used units' *separately computed* shares, kept
    because the landlord needs the vacancy share per object for Anlage V (§ 1.4
    — *"Aggregation im Display, Herkunft in den Daten."*). What the statement
    prints is the residual; `rounding_difference` is the difference, block (c),
    and it belongs to no unit.
    """
    heat_base, heat_cons, ww_base, ww_cons = blocks
    origins = tuple(
        OwnerResidualOrigin(
            unit_id=parties[index].unit_id,
            heating_base=hb,
            heating_consumption=hc,
            ww_base=wb,
            ww_consumption=wc,
            total=cents(int(hb) + int(hc) + int(wb) + int(wc)),
            days=parties[index].days,
            unit_total_days=unit_days[parties[index].unit_id],
            base_weight_sqm_days_x100=parties[index].base_weight,
            heat_consumption_weight=None if heat_weights is None else heat_weights[index],
            ww_consumption_weight_m3=None if ww_weights is None else ww_weights[index],
            degree_day_promille=parties[index].degree_day_promille,
            unit_degree_day_promille_total=unit_promille[parties[index].unit_id],
        )
        for index, hb, hc, wb, wc in zip(
            split.owner_indexes,
            heat_base.origins,
            heat_cons.origins,
            ww_base.origins,
            ww_cons.origins,
            strict=True,
        )
    )
    total = cents(
        int(heat_base.owner) + int(heat_cons.owner) + int(ww_base.owner) + int(ww_cons.owner)
    )
    base_weights = [p.base_weight for p in parties]
    return OwnerResidual(
        heating_base=heat_base.owner,
        heating_consumption=heat_cons.owner,
        ww_base=ww_base.owner,
        ww_consumption=ww_cons.owner,
        total=total,
        origins=origins,
        # (c) = Eigentümeranteil (Residuum) - Σ (a). Zero with exactly one empty
        # unit, because the residual column then already *is* that unit's (a)
        # figure; non-zero as soon as (a) is itemised across more than one.
        rounding_difference=cents(int(total) - sum(int(origin.total) for origin in origins)),
        base_weight_sqm_days_x100=_sum_weights(
            base_weights, split.owner_indexes, empty_is_none=True
        ),
        heat_consumption_weight=_sum_weights(heat_weights, split.owner_indexes, empty_is_none=True),
        ww_consumption_weight_m3=_sum_weights(ww_weights, split.owner_indexes, empty_is_none=True),
    )


def _resolve_heat_unit(units: tuple[HeatingUnit, ...]) -> MeasurementUnit | None:
    """The Maßeinheit of the heating-consumption Bemessungen (docs/08 rule 3).

    A unit with `heat_consumption=None` supplies **no measured value**: § 9a
    estimates it from the measured units, so its estimate is by construction in
    *their* unit and that row need not declare one. A unit that did supply a
    value and declares no Maßeinheit makes the key unit-less — the statement
    then withholds it rather than guessing. `_validate` has already rejected
    conflicting declarations, so at most one distinct unit reaches here.
    """
    if any(u.heat_consumption is not None and u.heat_consumption_unit is None for u in units):
        return None
    declared = {u.heat_consumption_unit for u in units if u.heat_consumption_unit is not None}
    return declared.pop() if declared else None


def _unit_totals(parties: list[_Party]) -> tuple[dict[str, int], dict[str, Decimal]]:
    """Per unit: the days and the Gradtagszahlen-promille its parties sum to —
    the denominators `_consumption_weights` apportions against. Disclosed
    alongside each party's own figure, because over a partial billing period a
    unit's parties sum to less than the full period and less than 1.000 ‰."""
    days: dict[str, int] = {}
    promille: dict[str, Decimal] = {}
    for party in parties:
        days[party.unit_id] = days.get(party.unit_id, 0) + party.days
        promille[party.unit_id] = (
            promille.get(party.unit_id, Decimal(0)) + party.degree_day_promille
        )
    return days, promille


def _validate(heating_input: HeatingInput) -> None:
    if heating_input.billing_period.valid_to is None:
        raise HeatingInputError("Billing period must be bounded (valid_to is required)")
    if not heating_input.units:
        raise HeatingInputError("At least one unit is required")
    if heating_input.co2 is not None and heating_input.co2.co2_cost is None:
        raise HeatingInputError(
            "CO₂-Kosten des Lieferanten fehlen. Die Abrechnung wird nicht berechnet; "
            "bitte die CO₂-Kosten beim Lieferanten anfordern."
        )
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
    # One key, one unit (docs/08 rule 2). Checked over the **declarations**, so a
    # unit that declares a device without supplying a reading conflicts too: its
    # § 9a estimate would otherwise be labelled with another device's unit.
    # Checked here, before any branch runs — validation that depends on which
    # branch ran can be skipped by an unrelated data problem, and mixed units
    # stay an input error even when § 9a Abs. 2 replaces the key entirely.
    declared_units = {
        u.heat_consumption_unit for u in heating_input.units if u.heat_consumption_unit is not None
    }
    if len(declared_units) > 1:
        raise HeatingInputError(
            "Heating consumption key mixes measurement units "
            f"({', '.join(sorted(u.value for u in declared_units))}); a Gesamtbemessung is a sum "
            "and units that cannot be summed cannot be a checkable denominator"
        )


def _build_parties(heating_input: HeatingInput, window_from: date, window_to: date) -> list[_Party]:
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


def _resolve_co2_mass_kg(heating_input: HeatingInput) -> Decimal:
    """The Brennstoffemissionen the split runs on — stated, or K4-derived.

    The five cases of `docs/03` § 9.5, in the order they can be decided. There is
    **no conversion step** and none may be added: the factor declares its
    Bezugsgröße, `total_energy_kwh` declares the same one, and any other pairing
    is refused. A `× 0,903` correction is a step somebody forgets, or applies
    twice, and its absence is what makes the mismatch unrepresentable rather
    than merely checked for.
    """
    co2 = heating_input.co2
    assert co2 is not None  # only called on the CO₂ path
    factor = co2.emission_factor
    if co2.total_co2_kg is not None:
        if factor is not None:
            raise HeatingInputError(
                "CO₂-Berechnung nicht möglich: Es sind gleichzeitig die vom Lieferanten "
                "ausgewiesenen Brennstoffemissionen (§ 3 Abs. 1 Nr. 1 CO2KostAufG) und ein "
                "Emissionsfaktor hinterlegt. Der Faktor ist nur ein Ersatzwert für den Fall, "
                "dass die Emissionen nicht ausgewiesen sind; er wird nicht stillschweigend "
                "ignoriert. Bitte eine der beiden Angaben entfernen."
            )
        return co2.total_co2_kg
    if factor is None:
        raise HeatingInputError(
            "CO₂-Berechnung nicht möglich: Die Abrechnung des Lieferanten weist die "
            "Brennstoffemissionen nicht aus (Verstoß gegen § 3 Abs. 1 Nr. 1 CO2KostAufG) und "
            "es ist kein Emissionsfaktor als Ersatzwert hinterlegt. Die Emissionen werden "
            "nicht geschätzt. Bitte die Angabe beim Lieferanten anfordern oder einen "
            "Emissionsfaktor mit passender Bezugsgröße hinterlegen."
        )
    reference = heating_input.energy_reference
    if reference is None:
        raise HeatingInputError(
            "CO₂-Berechnung nicht möglich: Für die Energiemenge "
            f"({heating_input.total_energy_kwh} kWh) ist keine Bezugsgröße angegeben. Ohne "
            "die Angabe, ob es sich um Brennwert- (Ho) oder Heizwert-Kilowattstunden (Hu) "
            "handelt, kann der Emissionsfaktor nicht angewendet werden; eine Annahme wird "
            "bewusst nicht getroffen (§ 3 Abs. 1 Nr. 3 CO2KostAufG). Bitte die Bezugsgröße "
            "der Energiemenge erfassen."
        )
    # Raises `EnergyReferenceMismatchError` on a mismatch — deliberately **not**
    # caught and re-raised as a `HeatingInputError`: an API layer branches on the
    # type and a landlord reads the German text, and wrapping loses both.
    return Decimal(
        co2_grams_from_energy(heating_input.total_energy_kwh, reference, factor)
    ) / Decimal(1000)


def _apply_co2(heating_input: HeatingInput) -> tuple[Co2Result | None, Cents]:
    if heating_input.co2 is None:
        return None, heating_input.total_cost
    table = heating_input.rules.co2_table
    rechtsstand = heating_input.rules.co2_rechtsstand
    co2_cost = heating_input.co2.co2_cost
    assert table is not None and rechtsstand is not None  # _validate guarantees
    assert co2_cost is not None  # _validate refuses a missing supplier amount
    heated_area_sqm = _heated_area_sqm(heating_input.units)
    co2_result = split_co2_cost(
        total_co2_kg=_resolve_co2_mass_kg(heating_input),
        co2_cost=co2_cost,
        heated_area_sqm=heated_area_sqm,
        table=table,
        rechtsstand=rechtsstand,
        billing_period=heating_input.billing_period,
    )
    billable = cents(int(heating_input.total_cost) - int(co2_result.landlord_amount))
    return co2_result, billable


def _separate_warm_water(
    heating_input: HeatingInput, billable: Cents, window_from: date, window_to: date
) -> tuple[Cents, Cents, WarmWaterSeparation | None]:
    """§ 9: returns (ww_pot, heating_pot, the separation that produced them).

    The separation records the branch and its operands so the statement can
    reprint the formula that ran; the other branch's operands stay `None`.
    """
    if heating_input.warm_water is None:
        return _ZERO, billable, None
    formula = heating_input.rules.warm_water_formula
    total_energy = heating_input.total_energy_kwh
    if heating_input.warm_water.volume_m3 is not None:
        volume_m3 = heating_input.warm_water.volume_m3
        q_ww = formula.energy_kwh_for_volume(volume_m3)
        separation = WarmWaterSeparation(
            method="MEASURED",
            q_ww_kwh=q_ww,
            total_energy_kwh=total_energy,
            volume_m3=volume_m3,
            factor_kwh_per_m3_kelvin=formula.factor_kwh_per_m3_kelvin,
            hot_temp_c=formula.hot_temp_c,
            cold_temp_c=formula.cold_temp_c,
            area_fallback_kwh_per_sqm_year=None,
            heated_area_sqm=None,
            period_days=None,
            reference_year_days=None,
        )
    else:
        # § 9 Abs. 2 fallback: kWh per m² living area per year, pro-rated over a
        # flat 365 — the divisor is echoed, not harmonised with co2.py (docs/08).
        area_sqm = _heated_area_sqm(heating_input.units)
        period_days = (window_to - window_from).days
        days = Decimal(period_days)
        q_ww = formula.area_fallback_kwh_per_sqm_year * area_sqm * days / Decimal(365)
        separation = WarmWaterSeparation(
            method="AREA_FALLBACK",
            q_ww_kwh=q_ww,
            total_energy_kwh=total_energy,
            volume_m3=None,
            factor_kwh_per_m3_kelvin=None,
            hot_temp_c=None,
            cold_temp_c=None,
            area_fallback_kwh_per_sqm_year=formula.area_fallback_kwh_per_sqm_year,
            heated_area_sqm=area_sqm,
            period_days=period_days,
            reference_year_days=365,
        )
    if q_ww <= 0 or q_ww >= heating_input.total_energy_kwh:
        raise HeatingInputError(
            f"Warm-water energy {q_ww} kWh must lie inside (0, total energy "
            f"{heating_input.total_energy_kwh} kWh)"
        )
    # Site #9 — H3: `kostenWw = round_half_up(umlagefaehig × anteilWw)`,
    # `kostenHz = umlagefaehig - kostenWw` ("complement, so the sum is exact").
    # The residual sits on the heating pot, which is the complement here.
    ww_pot, heating_pot = distribute_cents_half_up(
        billable, [q_ww, heating_input.total_energy_kwh - q_ww], residual_index=_COMPLEMENT
    )
    return ww_pot, heating_pot, separation


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
            resolved[unit.unit_id] = (
                measured_sum * Decimal(unit.area_sqm_x100) / Decimal(measured_area)
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
