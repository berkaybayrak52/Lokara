"""Phase D DoD demo: the canonical fixtures through the real engines into a PDF.

Composes exactly like the API will at M3: resolve rule values from the
rules-store for the as-of date, run both engines, format the results with the
statement template, render via headless Chromium.

Run: ``uv run lokara-pdf-demo`` → packages/pdf/output/nk-heating-statement-demo.pdf
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from lokara_domain import AllocationKey, Occupancy, cents, period
from lokara_heating_engine import (
    Co2Input,
    HeatingInput,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    WarmWaterInput,
    calculate_heating_statement,
)
from lokara_nk_engine import CostItem, NkInput, NkResult, UnitBasis, calculate_nk_statement
from lokara_rules_store import (
    CO2_SPLIT_TABLE,
    DEFAULT_CONSUMPTION_SHARE,
    DEGREE_DAY_TABLE,
    HEATING_SPLIT_BOUNDS,
    WARM_WATER_FORMULA,
    get_rule,
)

from .rechtsstand import rechtsstand_entry
from .render import render_html_to_pdf
from .statement import PartyKey, StatementData, statement_html

BILLING_PERIOD = period("2025-01-01", "2026-01-01")
AS_OF = date(2025, 12, 31)

# The canonical building (docs/03): A 50 m², B 30 m², C 20 m²; Renter 2 moves
# out of B on Jun 30 (exclusive Jul 1), B vacant for the rest of the year.
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
_NK_COSTS = (
    CostItem(
        cost_id="cost-garbage",
        label="Müllabfuhr",
        amount=cents(120000),
        key=AllocationKey.AREA,
    ),
)
PARTY_LABELS: dict[PartyKey, str] = {
    ("unit-a", "ten-a"): "Wohnung A — Anna Beispiel",
    ("unit-b", "ten-b"): "Wohnung B — Bernd Muster (Auszug 30.06.2025)",
    ("unit-b", None): "Wohnung B — Leerstand ab 01.07.2025 → Vermieter",
    ("unit-c", "ten-c"): "Wohnung C — Clara Vorlage",
}


def compute_nk() -> NkResult:
    return calculate_nk_statement(
        NkInput(
            billing_period=BILLING_PERIOD,
            units=_UNITS,
            occupancies=_OCCUPANCIES,
            costs=_NK_COSTS,
        )
    )


def compute_heating() -> tuple[HeatingResult, tuple[str, ...]]:
    """Runs the heating fixture with rules resolved from the store; returns the
    result plus one deduped Rechtsstand entry per rule version used — each
    naming its rule, as ``docs/08`` item 6 requires."""
    split_bounds = get_rule(HEATING_SPLIT_BOUNDS, AS_OF)
    warm_water = get_rule(WARM_WATER_FORMULA, AS_OF)
    degree_days = get_rule(DEGREE_DAY_TABLE, AS_OF)
    co2_table = get_rule(CO2_SPLIT_TABLE, AS_OF)

    result = calculate_heating_statement(
        HeatingInput(
            billing_period=BILLING_PERIOD,
            total_cost=cents(1_030_000),
            total_energy_kwh=Decimal(20000),
            units=(
                HeatingUnit(
                    "unit-a", 5000, heat_consumption=Decimal(600), ww_consumption_m3=Decimal(20)
                ),
                HeatingUnit(
                    "unit-b", 3000, heat_consumption=Decimal(250), ww_consumption_m3=Decimal(12)
                ),
                HeatingUnit(
                    "unit-c", 2000, heat_consumption=Decimal(150), ww_consumption_m3=Decimal(8)
                ),
            ),
            # Same occupancy timeline as the NK section: one coherent statement.
            # Unit B's annual consumption is apportioned Bernd/landlord by
            # degree-days (585/415 ‰ at the Jul 1 change), base costs by days.
            occupancies=_OCCUPANCIES,
            rules=HeatingRules(
                consumption_share=DEFAULT_CONSUMPTION_SHARE,
                split_bounds=split_bounds.value,
                warm_water_formula=warm_water.value,
                degree_days=degree_days.value,
                co2_table=co2_table.value,
                co2_rechtsstand=co2_table.rechtsstand,
            ),
            warm_water=WarmWaterInput(volume_m3=Decimal(40)),
            co2=Co2Input(total_co2_kg=Decimal(2000), co2_cost=cents(30000)),
        )
    )
    # Label + date per rule, in resolution order. The citations come from the
    # store's `source`; the degree-day table is the documented exception, see
    # `rechtsstand.py`.
    stamps = tuple(
        dict.fromkeys(
            (
                rechtsstand_entry(split_bounds),
                rechtsstand_entry(warm_water),
                rechtsstand_entry(degree_days),
                rechtsstand_entry(co2_table),
            )
        )
    )
    return result, stamps


def build_demo_statement() -> StatementData:
    heating_result, stamps = compute_heating()
    return StatementData(
        landlord_name="Demo Vermieter",
        building_label="Musterstraße 12, 60311 Frankfurt am Main",
        period_label="01.01.2025 – 31.12.2025",
        nk_result=compute_nk(),
        nk_costs=_NK_COSTS,
        party_labels=PARTY_LABELS,
        rechtsstaende=stamps,
        heating_result=heating_result,
    )


def main() -> None:
    html = statement_html(build_demo_statement())
    pdf = render_html_to_pdf(html)
    out_dir = Path(__file__).resolve().parents[2] / "output"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "nk-heating-statement-demo.pdf"
    out_file.write_bytes(pdf)
    print(f"PDF written: {out_file} ({len(pdf)} bytes)")
