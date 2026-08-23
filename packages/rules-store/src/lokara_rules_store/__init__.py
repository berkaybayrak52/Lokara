"""Versioned legal rules with as-of law dates.

Every legal ratio/table (HKVO split bounds, CO₂ 10-step table, degree-day
weights, warm-water formula) is data with a law date — resolved via
``get_rule(rule_set, as_of)`` and stamped ``Rechtsstand MM/JJJJ`` in output.
"""

from .rules import (
    CO2_FALLBACK_EMISSION_FACTORS,
    CO2_SPLIT_TABLE,
    DEFAULT_CONSUMPTION_SHARE,
    DEGREE_DAY_TABLE,
    HEATING_SPLIT_BOUNDS,
    WARM_WATER_FORMULA,
)
from .store import (
    ResolvedRule,
    RuleNotFoundError,
    RuleSet,
    RuleVersion,
    format_rechtsstand,
    get_rule,
)

__version__ = "0.1.0"

__all__ = [
    "CO2_FALLBACK_EMISSION_FACTORS",
    "CO2_SPLIT_TABLE",
    "DEFAULT_CONSUMPTION_SHARE",
    "DEGREE_DAY_TABLE",
    "HEATING_SPLIT_BOUNDS",
    "WARM_WATER_FORMULA",
    "ResolvedRule",
    "RuleNotFoundError",
    "RuleSet",
    "RuleVersion",
    "format_rechtsstand",
    "get_rule",
]
from .betrkv_catalogue import (
    CataloguePosition,
    ClassificationResult,
    ContractFacts,
    classify_position,
    resolve_rule,
)

__all__ = [
    "CataloguePosition",
    "ClassificationResult",
    "ContractFacts",
    "classify_position",
    "resolve_rule",
]
