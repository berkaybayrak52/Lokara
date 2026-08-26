"""Versioned legal rules with as-of law dates.

Every legal ratio/table (HKVO split bounds, CO₂ 10-step table, degree-day
weights, warm-water formula) is data with a law date — resolved via
``get_rule(rule_set, as_of)`` and stamped ``Rechtsstand MM/JJJJ`` in output.
"""

from .afa import (
    AFA_CONVENTIONS,
    AFA_DISAGIO_CONVENTION,
    AFA_RATES,
    AfaConventionProfile,
    AfaDisagioConvention,
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
from .page01_statement import (
    PAGE_01_STATEMENT_RULES,
    Page01StatementEvidence,
    Page01StatementRules,
    resolve_page01_statement_rules,
)
from .page05_guards import (
    PAGE_05_G1_RULES,
    PAGE_05_M9_RULES,
    Page05ComparativeRentRules,
    Page05Evidence,
    Page05G1GuardRules,
    Page05G1Rules,
    Page05GraduatedRentRules,
    Page05IndexRentRules,
    Page05M9Rules,
    Page05PaymentArrearsRules,
    Page05ProductionBlocker,
    Page05RuleConflict,
    Page05VacancyRules,
    resolve_page05_g1_rules,
    resolve_page05_m9_rules,
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
    "AFA_DISAGIO_CONVENTION",
    "AFA_RATES",
    "ANLAGE_V_LAYOUTS",
    "CO2_FALLBACK_EMISSION_FACTORS",
    "CO2_SPLIT_TABLE",
    "DEFAULT_CONSUMPTION_SHARE",
    "DEGREE_DAY_TABLE",
    "EXTF_PROFILES",
    "HEATING_SPLIT_BOUNDS",
    "PAGE_01_STATEMENT_RULES",
    "PAGE_05_G1_RULES",
    "PAGE_05_M9_RULES",
    "VERIFIED_TEST_EXTF_PROFILES",
    "WARM_WATER_FORMULA",
    "AfaConventionProfile",
    "AfaDisagioConvention",
    "AfaRates",
    "AnlageVLayout",
    "CataloguePosition",
    "ClassificationResult",
    "ContractFacts",
    "ExtfProfile",
    "Page01StatementEvidence",
    "Page01StatementRules",
    "Page05ComparativeRentRules",
    "Page05Evidence",
    "Page05G1GuardRules",
    "Page05G1Rules",
    "Page05GraduatedRentRules",
    "Page05IndexRentRules",
    "Page05M9Rules",
    "Page05PaymentArrearsRules",
    "Page05ProductionBlocker",
    "Page05RuleConflict",
    "Page05VacancyRules",
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
    "resolve_page01_statement_rules",
    "resolve_page05_g1_rules",
    "resolve_page05_m9_rules",
    "resolve_rule",
]
