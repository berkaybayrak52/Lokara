"""CO2KostAufG 10-step model (Stufenmodell) for residential buildings.

The building's CO₂ intensity (kg CO₂ per m² per year) selects a step; the step
sets the landlord's percentage share of the CO₂ cost portion of heating cost.
Missing/incorrect split = the tenant's 3 % reduction right (§ 7 Abs. 4
CO2KostAufG) — correctness-critical, not cosmetic. In force since 2023-01-01.
"""

from datetime import date
from decimal import Decimal

from lokara_domain import Co2Step, Co2Table

from ..store import RuleSet, RuleVersion

_STEPS_2023: Co2Table = (
    Co2Step(max_intensity_exclusive=Decimal(12), landlord_share_percent=0),
    Co2Step(max_intensity_exclusive=Decimal(17), landlord_share_percent=10),
    Co2Step(max_intensity_exclusive=Decimal(22), landlord_share_percent=20),
    Co2Step(max_intensity_exclusive=Decimal(27), landlord_share_percent=30),
    Co2Step(max_intensity_exclusive=Decimal(32), landlord_share_percent=40),
    Co2Step(max_intensity_exclusive=Decimal(37), landlord_share_percent=50),
    Co2Step(max_intensity_exclusive=Decimal(42), landlord_share_percent=60),
    Co2Step(max_intensity_exclusive=Decimal(47), landlord_share_percent=70),
    Co2Step(max_intensity_exclusive=Decimal(52), landlord_share_percent=80),
    Co2Step(max_intensity_exclusive=None, landlord_share_percent=95),
)

CO2_SPLIT_TABLE: RuleSet[Co2Table] = RuleSet(
    key="co2kostaufg.stufenmodell",
    versions=(
        RuleVersion(
            valid_from=date(2023, 1, 1),
            source="§ 5 Abs. 1 i. V. m. Anlage CO2KostAufG",
            value=_STEPS_2023,
        ),
    ),
)
