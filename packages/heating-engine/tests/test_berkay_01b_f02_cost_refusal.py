"""`01b-F02` — missing supplier CO₂ cost is refused without choosing a factor.

Source: original Page 01b E1/F02 as corrected by approved `docs/03` § 7 item 5. Transcription:
`docs/03-nk-heating-engines.md` §§ 0, 3, 4 H2, 6 E1 and 7 no. 5.
Rechtsstand 08/2026.

The Erdgas mass fallback values are resolved by the authoritative CSV. This
executable contract deliberately supplies the mass and omits only the supplier's
euro amount, so no emission factor is needed or permitted to decide the result:
missing supplier CO₂ cost remains a hard refusal and is never derived.
"""

from decimal import Decimal
from typing import cast

import pytest
from lokara_domain import (
    Cents,
    Co2Step,
    Co2Table,
    DegreeDayTable,
    HeatingSplitBounds,
    Occupancy,
    WarmWaterFormula,
    cents,
    period,
)
from lokara_heating_engine import (
    Co2Input,
    HeatingInput,
    HeatingInputError,
    HeatingRules,
    HeatingUnit,
    calculate_heating_statement,
)

CO2_TABLE: Co2Table = (
    Co2Step(Decimal(12), 0),
    Co2Step(Decimal(17), 10),
    Co2Step(Decimal(22), 20),
    Co2Step(Decimal(27), 30),
    Co2Step(Decimal(32), 40),
    Co2Step(Decimal(37), 50),
    Co2Step(Decimal(42), 60),
    Co2Step(Decimal(47), 70),
    Co2Step(Decimal(52), 80),
    Co2Step(None, 95),
)
RULES = HeatingRules(
    consumption_share=Decimal("0.7"),
    split_bounds=HeatingSplitBounds(Decimal("0.5"), Decimal("0.7")),
    warm_water_formula=WarmWaterFormula(Decimal("2.5"), Decimal(60), Decimal(10), Decimal(32)),
    degree_days=DegreeDayTable(
        tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 133, 133, 134, 300, 800, 1200, 1600)
    ),
    co2_table=CO2_TABLE,
    co2_rechtsstand="Rechtsstand 01/2023",
)


def test_berkay_01b_f02_missing_supplier_cost_is_a_hard_refusal() -> None:
    missing_cost = Co2Input(
        total_co2_kg=Decimal(4000),
        co2_cost=cast(Cents, None),
        emission_factor=None,
    )
    assert missing_cost.emission_factor is None

    with pytest.raises(
        HeatingInputError,
        match=r"CO₂-Kosten.*Lieferant|Lieferant.*CO₂-Kosten",
    ):
        calculate_heating_statement(
            HeatingInput(
                billing_period=period("2025-01-01", "2026-01-01"),
                total_cost=cents(300_000),
                total_energy_kwh=Decimal(20_000),
                units=(HeatingUnit("WE-01", 10_000, Decimal(1000)),),
                occupancies=(Occupancy("WE-01", "Muster", period("2025-01-01")),),
                rules=RULES,
                co2=missing_cost,
            )
        )
