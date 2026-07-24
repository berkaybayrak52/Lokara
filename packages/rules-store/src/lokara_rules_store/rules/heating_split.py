"""§ 7 Abs. 1 HeizkostenV — base/consumption split of heating cost.

At least 50 % and at most 70 % of the cost must be allocated by measured
consumption; the remainder by a fixed key (living/heated area). 70/30 is the
common default; the chosen share is per-building configuration within these
bounds.
"""

from datetime import date
from decimal import Decimal

from lokara_domain import HeatingSplitBounds

from ..store import RuleSet, RuleVersion

DEFAULT_CONSUMPTION_SHARE = Decimal("0.7")

HEATING_SPLIT_BOUNDS: RuleSet[HeatingSplitBounds] = RuleSet(
    key="hkvo.heating-split-bounds",
    versions=(
        RuleVersion(
            valid_from=date(1989, 3, 1),
            source="§ 7 Abs. 1 HeizkostenV",
            value=HeatingSplitBounds(
                min_consumption_share=Decimal("0.5"),
                max_consumption_share=Decimal("0.7"),
            ),
        ),
    ),
)
