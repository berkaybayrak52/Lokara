"""Versioned AfA inputs transcribed from the approved Page-03 specification."""

from dataclasses import dataclass
from datetime import date

from .store import RuleSet, RuleVersion, get_rule


@dataclass(frozen=True)
class AfaRates:
    residential_after_2022_bp: int
    residential_1925_through_2022_bp: int
    residential_before_1925_bp: int
    near_acquisition_cost_limit_bp: int
    market_disagio_limit_bp: int
    verification_flag: str


AFA_RATES: RuleSet[AfaRates] = RuleSet(
    key="afa.rates",
    versions=(
        RuleVersion(
            valid_from=date(2023, 1, 1),
            source=("§ 7 Abs. 4 S. 1 Nr. 2 lit. a-c EStG; § 6 Abs. 1 Nr. 1a EStG"),
            value=AfaRates(
                residential_after_2022_bp=300,
                residential_1925_through_2022_bp=200,
                residential_before_1925_bp=250,
                near_acquisition_cost_limit_bp=1_500,
                market_disagio_limit_bp=500,
                verification_flag="geprüft",
            ),
        ),
    ),
)


@dataclass(frozen=True)
class AfaConventionProfile:
    first_year_month_granularity: bool
    letting_change_started_month_counts: bool
    later_cost_basis_from_year_start: bool
    verification_flag: str
    production_blocked: bool


AFA_CONVENTIONS: RuleSet[AfaConventionProfile] = RuleSet(
    key="afa.conventions.page03",
    versions=(
        RuleVersion(
            valid_from=date(2026, 7, 1),
            source="docs/10-afa.md 10-K08 through 10-K12",
            value=AfaConventionProfile(
                first_year_month_granularity=True,
                letting_change_started_month_counts=True,
                later_cost_basis_from_year_start=True,
                verification_flag="verify-before-production",
                production_blocked=True,
            ),
        ),
    ),
)


@dataclass(frozen=True)
class ResolvedAfaRuleBundle:
    """Pure-engine inputs after the caller resolves the versioned rule data."""

    linear_rates_bp: tuple[tuple[int | None, int | None, int], ...]
    guard_rate_bp: int
    market_disagio_limit_bp: int
    source_evidence: tuple[str, ...]
    rechtsstand: str
    production_blocked: bool


def resolve_afa_rule_bundle(as_of: date) -> ResolvedAfaRuleBundle:
    rates = get_rule(AFA_RATES, as_of)
    value = rates.value
    return ResolvedAfaRuleBundle(
        linear_rates_bp=(
            (None, 1924, value.residential_before_1925_bp),
            (1925, 2022, value.residential_1925_through_2022_bp),
            (2023, None, value.residential_after_2022_bp),
        ),
        guard_rate_bp=value.near_acquisition_cost_limit_bp,
        market_disagio_limit_bp=value.market_disagio_limit_bp,
        source_evidence=tuple(sorted((rates.source, "docs/10-afa.md@08/2026"))),
        rechtsstand="07/2026",
        production_blocked=True,
    )


__all__ = [
    "AFA_CONVENTIONS",
    "AFA_RATES",
    "AfaConventionProfile",
    "AfaRates",
    "ResolvedAfaRuleBundle",
    "resolve_afa_rule_bundle",
]
