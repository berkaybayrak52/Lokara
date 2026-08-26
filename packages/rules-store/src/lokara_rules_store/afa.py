"""Versioned AfA inputs transcribed from the approved Page-03 specification."""

from dataclasses import dataclass
from datetime import date

from .store import RuleSet, RuleVersion, get_rule


@dataclass(frozen=True)
class AfaRates:
    """Statutory rates and the § 6 Abs. 1 Nr. 1a limit. These four are `geprüft`."""

    residential_after_2022_bp: int
    residential_1925_through_2022_bp: int
    residential_before_1925_bp: int
    near_acquisition_cost_limit_bp: int
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
                verification_flag="geprüft",
            ),
        ),
    ),
)


@dataclass(frozen=True)
class AfaDisagioConvention:
    """The 5% market limit is administrative practice, not statute.

    It used to ride inside the `geprüft` ``AfaRates`` record, which stamped
    lawyer-checked status onto a value the authoritative register flags
    ``verify-before-production`` / ``Konvention`` (row ``10-K14 — Marktüblichkeit des
    Disagios``). CLAUDE.md § 4 forbids presenting a flagged convention as settled law,
    so it carries its own record and its own flag.
    """

    market_limit_bp: int
    verification_flag: str
    production_blocked: bool


AFA_DISAGIO_CONVENTION: RuleSet[AfaDisagioConvention] = RuleSet(
    key="afa.disagio.market_limit",
    versions=(
        RuleVersion(
            # When the practice applies, not when it was checked. Those are two axes:
            # the register's Rechtsstand 07/2026 records the verification date, while
            # `valid_from` must cover every supported tax year — it is aligned with
            # AFA_RATES so a 2023-2025 record resolves the same way the rates do.
            valid_from=date(2023, 1, 1),
            source=(
                "Verwaltungspraxis zu § 11 Abs. 2 S. 4 EStG — nicht im Gesetz; "
                "register 10-K14 — Marktüblichkeit des Disagios"
            ),
            value=AfaDisagioConvention(
                market_limit_bp=500,
                verification_flag="verify-before-production",
                production_blocked=True,
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
    disagio = get_rule(AFA_DISAGIO_CONVENTION, as_of)
    value = rates.value
    return ResolvedAfaRuleBundle(
        linear_rates_bp=(
            (None, 1924, value.residential_before_1925_bp),
            (1925, 2022, value.residential_1925_through_2022_bp),
            (2023, None, value.residential_after_2022_bp),
        ),
        guard_rate_bp=value.near_acquisition_cost_limit_bp,
        market_disagio_limit_bp=disagio.value.market_limit_bp,
        source_evidence=tuple(sorted({rates.source, disagio.source, "docs/10-afa.md@07/2026"})),
        # docs/10 § 2 and every Page-03 register row carry 07/2026. The old
        # `docs/10-afa.md@08/2026` evidence literal disagreed with the `rechtsstand` in
        # the same record, so one stored AfA snapshot claimed two law dates.
        rechtsstand="07/2026",
        # Derived, not asserted: unblocking now requires every contributing record to be
        # unblocked and checked, instead of a literal `True` that no record could move.
        # `AFA_CONVENTIONS` is deliberately not resolved here — its `valid_from` is the
        # 07/2026 verification date rather than a date the conventions apply from, so
        # resolving it at a tax-year end raises RuleNotFoundError. Recorded as an open
        # M7 limit; fixing it means deciding what those conventions are valid *from*.
        production_blocked=(
            disagio.value.production_blocked or value.verification_flag != "geprüft"
        ),
    )


__all__ = [
    "AFA_CONVENTIONS",
    "AFA_DISAGIO_CONVENTION",
    "AFA_RATES",
    "AfaConventionProfile",
    "AfaDisagioConvention",
    "AfaRates",
    "ResolvedAfaRuleBundle",
    "resolve_afa_rule_bundle",
]
