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

CONSUMPTION and MEA are deliberately not asserted here: `docs/08` records the
CONSUMPTION unit as an open gap (nothing carries `MeasurementUnit` into the
statement), and an invented unit is worse than a missing row.
"""

from decimal import Decimal

from lokara_domain import AllocationKey, Occupancy, cents, period
from lokara_nk_engine import (
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
EXPECTED_REFERENCE_TOTALS: dict[str, tuple[Decimal, str]] = {
    "cost-garbage": (Decimal(36_500), "m²·Tage"),
    "cost-water": (Decimal(1_638), "Personen·Tage"),
    "cost-antenna": (Decimal(1_095), "Einheiten·Tage"),
}
_DISPLAY_DIVISORS = {
    AllocationKey.AREA: Decimal(100),
    AllocationKey.PERSONS: Decimal(1),
    AllocationKey.UNITS: Decimal(1),
}


def build_multi_key_statement() -> StatementData:
    result = calculate_nk_statement(
        NkInput(
            billing_period=BILLING_PERIOD,
            units=_UNITS,
            occupancies=_OCCUPANCIES,
            costs=_COSTS,
            person_counts=_PERSON_COUNTS,
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
