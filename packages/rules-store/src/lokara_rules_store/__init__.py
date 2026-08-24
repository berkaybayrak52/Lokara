"""Versioned legal rules with as-of law dates.

Every legal ratio/table (HKVO split bounds, CO₂ 10-step table, degree-day
weights, warm-water formula) is data with a law date — resolved via
``get_rule(rule_set, as_of)`` and stamped ``Rechtsstand MM/JJJJ`` in output.
"""

from .afa import (
    AFA_CONVENTIONS,
    AFA_RATES,
    AfaConventionProfile,
    AfaRates,
    ResolvedAfaRuleBundle,
    resolve_afa_rule_bundle,
)
from .betrkv_catalogue import (
    CataloguePosition,
    ClassificationResult,
    ContractFacts,
    classify_position,
    resolve_rule,
)
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
from .tax_export import (
    ANLAGE_V_LAYOUTS,
    EXTF_PROFILES,
    VERIFIED_TEST_EXTF_PROFILES,
    AnlageVLayout,
    ExtfProfile,
    TaxCategoryMapping,
)

__version__ = "0.1.0"

__all__ = [
    "AFA_CONVENTIONS",
    "AFA_RATES",
    "ANLAGE_V_LAYOUTS",
    "CO2_FALLBACK_EMISSION_FACTORS",
    "CO2_SPLIT_TABLE",
    "DEFAULT_CONSUMPTION_SHARE",
    "DEGREE_DAY_TABLE",
    "EXTF_PROFILES",
    "HEATING_SPLIT_BOUNDS",
    "VERIFIED_TEST_EXTF_PROFILES",
    "WARM_WATER_FORMULA",
    "AfaConventionProfile",
    "AfaRates",
    "AnlageVLayout",
    "CataloguePosition",
    "ClassificationResult",
    "ContractFacts",
    "ExtfProfile",
    "ResolvedAfaRuleBundle",
    "ResolvedRule",
    "RuleNotFoundError",
    "RuleSet",
    "RuleVersion",
    "TaxCategoryMapping",
    "classify_position",
    "format_rechtsstand",
    "get_rule",
    "resolve_afa_rule_bundle",
    "resolve_rule",
]
