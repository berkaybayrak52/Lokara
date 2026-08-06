"""Gate: every allocation key on the statement prints its own reference total.

Spec: `docs/08` → "Reference totals (Gesamtbemessung) — one per allocation key".

BGH formal minimum #2/#3 is a *calculation*, not a result: `600,00 €` and a
tenant's own `18.250 m²·Tage` prove nothing without the denominator the engine
divided by. `600 = 1200 × 18.250 / 36.500` is only checkable once `36.500` is on
the page.

The denominator is **per key**, and the keys carry different units — AREA is
m²·Tage, PERSONS is Personen·Tage, UNITS is Einheiten·Tage. So the fixture below
deliberately carries three keys: a renderer that emits one global figure (correct
only for a single-key statement, which is all today's demo happens to be) cannot
pass this file.

De-scaling canary (`docs/03`): the AREA denominator prints `36.500`, never
`3.650.000`. Integer-vs-integer tests stay green through that bug, so the
scaled form is asserted **absent**, not just the de-scaled form present.

**CONSUMPTION is asserted here since 06.08.2026.** It used to be excluded
because `docs/08` recorded its unit as an open gap — `ConsumptionValue` carried
a bare value and nothing carried `MeasurementUnit` into the statement, so the
only honest options were an invented unit or no row. That gap is closed by
`docs/08` → **"`MeasurementUnit` travels with the value — the plumbing decision
(slice 5)"**: the unit rides on `ConsumptionValue` and is surfaced on
`NkResult.consumption_unit`, so the renderer reads the unit the engine divided
in rather than being told one alongside the result. A cost whose rows carry no
unit still prints **no** reference total — the conservative branch is kept, not
removed, and it is asserted below too.

MEA remains out of this fixture: it needs `mea_x10000` on every unit and tests
a divisor, not a unit.
"""

from decimal import Decimal

from lokara_domain import AllocationKey, MeasurementUnit, Occupancy, cents, period
from lokara_nk_engine import (
    ConsumptionValue,
    CostItem,
    NkInput,
    PersonCountPeriod,
    UnitBasis,
    calculate_nk_statement,
)
from lokara_pdf import PartyKey, StatementData, format_number_de, statement_html

# The canonical docs/03 building — A 50 m², B 30 m², C 20 m²; Renter 2 moves out
# of B on Jun 30 (exclusive Jul 1), B vacant for the rest of 2025 (365 days).
BILLING_PERIOD = period("2025-01-01", "2026-01-01")

_UNITS = (
    UnitBasis(unit_id="unit-a", area_sqm_x100=5000),
    UnitBasis(unit_id="unit-b", area_sqm_x100=3000),
    UnitBasis(unit_id="unit-c", area_sqm_x100=2000),
)
_OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)
_PERSON_COUNTS = (
    PersonCountPeriod(tenancy_id="ten-a", count=2, period=period("2025-01-01")),
    PersonCountPeriod(tenancy_id="ten-b", count=3, period=period("2024-08-01", "2025-07-01")),
    PersonCountPeriod(tenancy_id="ten-c", count=1, period=period("2023-01-01")),
)
_COSTS = (
    CostItem(
        cost_id="cost-garbage",
        label="Müllabfuhr",
        amount=cents(120_000),
        key=AllocationKey.AREA,
    ),
    CostItem(
        cost_id="cost-water",
        label="Wasser/Abwasser",
        amount=cents(90_000),
        key=AllocationKey.PERSONS,
    ),
    CostItem(
        cost_id="cost-antenna",
        label="Gemeinschaftsantenne",
        amount=cents(36_000),
        key=AllocationKey.UNITS,
    ),
    CostItem(
        cost_id="cost-warm-water",
        label="Warmwasser",
        amount=cents(48_000),
        key=AllocationKey.CONSUMPTION,
    ),
)
# Period-resolved by the meter adapter upstream — no day weighting (`docs/08`,
# the reference-totals table). The unit rides on the row that carries the value:
# that is the whole point of slice 5, and a side channel would let the two
# disagree. 20 + 6 + 6 + 8 = 40 m³, the demo building's warm-water volume; unit
# B's vacancy draws water too, so the landlord party has a row of its own.
# `measurement_unit=None` is the branch `docs/08` keeps: a building that records
# no Maßeinheit prints no reference total rather than a guessed one.
_CONSUMPTION_ROWS: tuple[tuple[str, str | None, Decimal], ...] = (
    ("unit-a", "ten-a", Decimal(20)),
    ("unit-b", "ten-b", Decimal(6)),
    ("unit-b", None, Decimal(6)),
    ("unit-c", "ten-c", Decimal(8)),
)


def consumptions(
    *, unit: MeasurementUnit | None = MeasurementUnit.CUBIC_METRE
) -> tuple[ConsumptionValue, ...]:
    """Built lazily on purpose: while `measurement_unit` does not exist yet this
    file must still *collect*, so the pre-existing AREA/PERSONS/UNITS assertions
    fail one by one with their own message instead of the whole module erroring
    out at import time."""
    return tuple(
        ConsumptionValue(unit_id=unit_id, tenancy_id=tenancy_id, value=value, measurement_unit=unit)
        for unit_id, tenancy_id, value in _CONSUMPTION_ROWS
    )


_PARTY_LABELS: dict[PartyKey, str] = {
    ("unit-a", "ten-a"): "Wohnung A — Anna Beispiel",
    ("unit-b", "ten-b"): "Wohnung B — Bernd Muster (Auszug 30.06.2025)",
    ("unit-b", None): "Wohnung B — Leerstand ab 01.07.2025 → Vermieter",
    ("unit-c", "ten-c"): "Wohnung C — Clara Vorlage",
}

# docs/08 table: Σ engine weights ÷ the key's de-scale divisor, with the key's
# own unit. Hand-computed here; the engine agreement is asserted separately so a
# fixture drift never masquerades as a renderer bug.
#   AREA    50·365 + 30·181 + 30·184 + 20·365 = 18.250+5.430+5.520+7.300 = 36.500
#   PERSONS  2·365 +  3·181 +           1·365 =    730+  543+        365 =  1.638
#   UNITS    1·365 +  1·181 +  1·184 +  1·365 =    365+  181+  184+   365 = 1.095
#   CONSUMPTION 20 + 6 + 6 + 8 = 40, no day weighting, unit off the meter
EXPECTED_REFERENCE_TOTALS: dict[str, tuple[Decimal, str]] = {
    "cost-garbage": (Decimal(36_500), "m²·Tage"),
    "cost-water": (Decimal(1_638), "Personen·Tage"),
    "cost-antenna": (Decimal(1_095), "Einheiten·Tage"),
    "cost-warm-water": (Decimal(40), "m³"),
}
_DISPLAY_DIVISORS = {
    AllocationKey.AREA: Decimal(100),
    AllocationKey.PERSONS: Decimal(1),
    AllocationKey.UNITS: Decimal(1),
    AllocationKey.CONSUMPTION: Decimal(1),
}


def build_multi_key_statement(
    *, consumption_unit: MeasurementUnit | None = MeasurementUnit.CUBIC_METRE
) -> StatementData:
    result = calculate_nk_statement(
        NkInput(
            billing_period=BILLING_PERIOD,
            units=_UNITS,
            occupancies=_OCCUPANCIES,
            costs=_COSTS,
            person_counts=_PERSON_COUNTS,
            consumptions=consumptions(unit=consumption_unit),
        )
    )
    return StatementData(
        landlord_name="Demo Vermieter",
        building_label="Musterstraße 12, 60311 Frankfurt am Main",
        period_label="01.01.2025 – 31.12.2025",
        nk_result=result,
        nk_costs=_COSTS,
        party_labels=_PARTY_LABELS,
        rechtsstaende=("Rechtsstand 01/2025",),
        heating_result=None,
    )


def _plain(html: str) -> str:
    """NBSP/narrow-NBSP are a formatting choice, not part of the spec."""
    return html.replace("\xa0", " ").replace("\u202f", " ")


def test_fixture_denominators_match_the_engine() -> None:
    """Self-check: the hand-computed goldens are what the engine actually divides
    by, so a red assertion below means the renderer, never the fixture."""
    result = build_multi_key_statement().nk_result

    for cost in _COSTS:
        weight_sum = sum(
            (line.weight for line in result.lines if line.cost_id == cost.cost_id),
            Decimal(0),
        )
        expected, _unit = EXPECTED_REFERENCE_TOTALS[cost.cost_id]
        assert weight_sum / _DISPLAY_DIVISORS[cost.key] == expected, cost.cost_id

    # And the allocation itself still reconciles to the cent (docs/03).
    for cost in _COSTS:
        share_sum = sum(int(line.amount) for line in result.lines if line.cost_id == cost.cost_id)
        assert share_sum == int(cost.amount), cost.cost_id
    assert int(result.total) == sum(int(c.amount) for c in _COSTS)


def test_each_allocation_key_prints_its_own_reference_total() -> None:
    """docs/08: one Gesamtbemessung per key, each with its own unit."""
    html = _plain(statement_html(build_multi_key_statement()))

    for cost_id, (value, unit) in EXPECTED_REFERENCE_TOTALS.items():
        expected = f"Gesamtbemessung: {format_number_de(value)} {unit}"
        assert expected in html, f"{cost_id}: missing reference total {expected!r}"


def test_reference_totals_are_per_key_not_one_global_figure() -> None:
    """A single figure is right only for a single-key statement. Three costs,
    three keys → three reference totals."""
    html = _plain(statement_html(build_multi_key_statement()))

    assert html.count("Gesamtbemessung") == len(_COSTS)


def test_reference_totals_are_de_scaled() -> None:
    """docs/03 de-scaling canary: 36.500, never 3.650.000. Engine-integer tests
    stay green through this bug — only rendered text catches it."""
    html = _plain(statement_html(build_multi_key_statement()))

    assert "36.500" in html
    assert "3.650.000" not in html  # Σ AREA weights, ×100 fixed point, leaked
    assert "1.825.000" not in html  # unit A's AREA weight, likewise
    # A metered value's DB scale is ×1000 (`value_x1000`, `packages/db` →
    # `MeterReading`), so the leak form of `40 m³` is `40.000` and of a party's
    # `20 m³` is `20.000`. Scoped to this fixture, where no legitimate figure is
    # in the tens of thousands — the same canary is deliberately *not* page-wide
    # in `scripts/assert_statement_pdf.py`, because 40.000,00 € is a plausible
    # heating invoice on a larger building.
    assert "40.000" not in html
    assert "20.000" not in html


def test_the_consumption_total_carries_the_unit_the_engine_divided_in() -> None:
    """`docs/08` → "`MeasurementUnit` travels with the value", rules 1 and 6.

    The figure alone is not the disclosure: `40` between `36.500 m²·Tage` and
    `1.638 Personen·Tage` invites the renter to assume a unit, and the candidate
    units differ by orders of magnitude in what they mean. The compact spelling
    is what a numeric cell takes."""
    data = build_multi_key_statement()
    html = _plain(statement_html(data))

    assert data.nk_result.consumption_unit is MeasurementUnit.CUBIC_METRE
    assert "Gesamtbemessung: 40 m³" in html
    # The key label names the unit too, so the denominator is not the only place
    # the renter meets it (`docs/08`: the NK label names the *unit*, never a
    # device — outside the heating column `m³` is a Kalt- or a Warmwasserzähler).
    assert "Verbrauch (m³)" in html


def test_a_consumption_cost_without_a_recorded_unit_prints_no_reference_total() -> None:
    """`docs/08` rule 3: absence propagates, and the conservative branch is kept.

    A guessed unit on a Verbrauchsabrechnung is a defect that reaches a tenant,
    so a cost whose rows carry no unit prints no denominator at all — and the
    other three keys are unaffected, which is what makes this a per-key rule."""
    data = build_multi_key_statement(consumption_unit=None)
    html = _plain(statement_html(data))

    assert data.nk_result.consumption_unit is None
    assert html.count("Gesamtbemessung") == len(_COSTS) - 1
    assert "Gesamtbemessung: 40" not in html
    assert "Verbrauch (m³)" not in html
    # …and the cost is still on the page with its key named (BGH minimum #2).
    assert "Warmwasser" in html
    assert "Umlageschlüssel: Verbrauch" in html
