"""Versioned legal rules/config store.

Never hardcode a legal rule (CLAUDE.md): AfA rates, HKVO ratios, the CO₂
10-step table, Anlage-V line numbers etc. are DATA with an "as-of law date".
Engines receive a resolved rule as a parameter and stamp `Rechtsstand MM/JJJJ`
into every legal output.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RuleVersion[T]:
    # The date this version of the rule became law ("Rechtsstand").
    valid_from: date
    # Citation, e.g. "§ 7 Abs. 1 HeizkostenV".
    source: str
    value: T
    # Optional end of validity (exclusive). Open-ended if None.
    valid_to: date | None = None


@dataclass(frozen=True)
class RuleSet[T]:
    key: str
    versions: tuple[RuleVersion[T], ...]


@dataclass(frozen=True)
class ResolvedRule[T]:
    key: str
    value: T
    source: str
    # e.g. "Rechtsstand 12/2023" — must be shown in every legal output.
    rechtsstand: str


class RuleNotFoundError(LookupError):
    def __init__(self, key: str, as_of: date) -> None:
        super().__init__(f'No version of rule "{key}" is valid as of {as_of.isoformat()}')


def format_rechtsstand(as_of: date) -> str:
    return f"Rechtsstand {as_of.month:02d}/{as_of.year}"


def get_rule[T](rule_set: RuleSet[T], as_of: date) -> ResolvedRule[T]:
    """Resolves the version of a rule valid as of ``as_of``: the latest
    ``valid_from <= as_of`` whose ``valid_to`` (if any) is still open at ``as_of``.
    """
    applicable = [
        v
        for v in rule_set.versions
        if v.valid_from <= as_of and (v.valid_to is None or as_of < v.valid_to)
    ]
    if not applicable:
        raise RuleNotFoundError(rule_set.key, as_of)
    match = max(applicable, key=lambda v: v.valid_from)
    return ResolvedRule(
        key=rule_set.key,
        value=match.value,
        source=match.source,
        rechtsstand=format_rechtsstand(match.valid_from),
    )
