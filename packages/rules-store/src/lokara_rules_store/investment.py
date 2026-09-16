"""Versioned Page-07 investment rules for the pure investment engine."""

from dataclasses import dataclass
from datetime import date

from .store import RuleSet, RuleVersion, get_rule


@dataclass(frozen=True)
class InvestmentRuleBundle:
    """Complete server-owned input bundle for one investment calculation."""

    default_building_share_bp: int
    default_afa_rate_bp: int
    default_marginal_tax_bp: int
    interest_sensitivity_offsets_bp: tuple[int, ...]
    repayment_sensitivity_steps_bp: tuple[int, ...]
    dscr_amber_hundredths: int
    dscr_green_hundredths: int
    cashflow_amber_cents: int
    cashflow_green_cents: int
    source_evidence: tuple[str, ...]
    rechtsstand: str
    production_blocked: bool


INVESTMENT_RULE_BUNDLES: RuleSet[InvestmentRuleBundle] = RuleSet(
    key="investment.page07.bundle",
    versions=(
        RuleVersion(
            valid_from=date(2026, 7, 1),
            source="docs/14-investment-kpis.md § 4.8; Page 07; Rechtsstand 07/2026",
            value=InvestmentRuleBundle(
                default_building_share_bp=7_500,
                default_afa_rate_bp=200,
                default_marginal_tax_bp=4_200,
                interest_sensitivity_offsets_bp=(-100, -50, 0, 50, 100),
                repayment_sensitivity_steps_bp=(100, 200, 300, 400),
                dscr_amber_hundredths=100,
                dscr_green_hundredths=120,
                cashflow_amber_cents=0,
                cashflow_green_cents=5_000,
                source_evidence=("docs/14-investment-kpis.md@07/2026",),
                rechtsstand="07/2026",
                production_blocked=True,
            ),
        ),
    ),
)


def resolve_investment_rule_bundle(as_of: date) -> InvestmentRuleBundle:
    """Resolve the frozen Page-07 bundle that applies on ``as_of``."""

    return get_rule(INVESTMENT_RULE_BUNDLES, as_of).value


__all__ = [
    "INVESTMENT_RULE_BUNDLES",
    "InvestmentRuleBundle",
    "resolve_investment_rule_bundle",
]
