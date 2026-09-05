"""Pure, versioned Page-02 cost classification.

This module deliberately makes no database or HTTP decision.  A caller supplies
the confirmed contract facts and persists its resulting audit record.  Every
current Page-02 convention is marked ``verify_before_production`` so a draft
can be useful to its owner without becoming tenant/final output.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise

from lokara_domain import AllocationKey

from .store import ResolvedRule, RuleSet, RuleVersion, get_rule


@dataclass(frozen=True)
class CatalogueRule:
    cost_type: str
    label: str
    betrkv_number: str | None
    default_key: AllocationKey | None
    period_principle: str
    naming_required: bool = False
    special_rule: str = "none"
    typical_labour_percent: int | None = None
    allocable: bool = True
    verify_before_production: bool = True


@dataclass(frozen=True)
class ContractFacts:
    allocation_agreed: bool
    named_other_costs: frozenset[str] = field(default_factory=frozenset)
    mehrbelastung_clause: bool = False
    contractual_keys: dict[str, AllocationKey] = field(default_factory=dict)
    residential_use: bool = True


@dataclass(frozen=True)
class CataloguePosition:
    cost_type: str
    amount_cents: int
    receipt_date: date
    non_allocable_cents: int = 0
    labour_cents: int | None = None
    key_override: AllocationKey | None = None
    service_from: date | None = None
    service_to: date | None = None  # exclusive
    new_cost: bool = False
    evidence: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ClassificationResult:
    rule_id: str
    betrkv_number: str | None
    allocable_cents: int
    non_allocable_cents: int
    labour_cents: int | None
    key: AllocationKey | None
    key_source: str | None
    findings: tuple[str, ...]
    production_blocked: bool
    resolved_rule: ResolvedRule[CatalogueRule]


def _rule(
    cost_type: str,
    label: str,
    number: str,
    key: AllocationKey,
    principle: str,
    *,
    naming: bool = False,
    special: str = "none",
    labour: int | None = None,
) -> CatalogueRule:
    return CatalogueRule(cost_type, label, number, key, principle, naming, special, labour)


_ALLOCABLE: tuple[CatalogueRule, ...] = (
    _rule("grundsteuer", "Grundsteuer", "2 Nr. 1", AllocationKey.AREA, "payment"),
    _rule("wasserversorgung", "Wasserversorgung", "2 Nr. 2", AllocationKey.CONSUMPTION, "service"),
    _rule("entwaesserung", "Entwässerung", "2 Nr. 3", AllocationKey.CONSUMPTION, "service"),
    _rule("niederschlagswasser", "Niederschlagswasser", "2 Nr. 3", AllocationKey.AREA, "payment"),
    _rule(
        "trinkwasseruntersuchung",
        "Trinkwasseruntersuchung",
        "2 Nr. 17",
        AllocationKey.AREA,
        "payment",
        naming=True,
        special="trinkwasser_fallback",
    ),
    _rule("heizkosten", "Heizkosten", "2 Nr. 4a", AllocationKey.CONSUMPTION, "service"),
    _rule(
        "wartung_heizung",
        "Wartung Heizungsanlage",
        "2 Nr. 4a",
        AllocationKey.CONSUMPTION,
        "service",
        labour=60,
    ),
    _rule(
        "brennstoffversorgung",
        "Brennstoffversorgungsanlage",
        "2 Nr. 4b",
        AllocationKey.CONSUMPTION,
        "service",
    ),
    _rule(
        "waermelieferung",
        "Wärmelieferung (Contracting)",
        "2 Nr. 4c",
        AllocationKey.CONSUMPTION,
        "service",
    ),
    _rule(
        "etagenheizung_wartung",
        "Reinigung/Wartung Etagenheizung",
        "2 Nr. 4d",
        AllocationKey.DIRECT,
        "payment",
        labour=70,
    ),
    _rule("warmwasser", "Warmwasser", "2 Nr. 5a", AllocationKey.CONSUMPTION, "service"),
    _rule(
        "verbundene_anlagen",
        "Verbundene Heizungs-/WW-Anlage",
        "2 Nr. 6",
        AllocationKey.CONSUMPTION,
        "service",
    ),
    _rule(
        "aufzug",
        "Aufzug",
        "2 Nr. 7",
        AllocationKey.UNITS,
        "payment",
        special="lift_ground_floor",
        labour=40,
    ),
    _rule("strassenreinigung", "Straßenreinigung", "2 Nr. 8", AllocationKey.AREA, "payment"),
    _rule("winterdienst", "Winterdienst", "2 Nr. 8", AllocationKey.AREA, "payment", labour=60),
    _rule("muellbeseitigung", "Müllbeseitigung", "2 Nr. 8", AllocationKey.PERSONS, "payment"),
    _rule(
        "gebaeudereinigung", "Gebäudereinigung", "2 Nr. 9", AllocationKey.AREA, "payment", labour=83
    ),
    _rule(
        "ungezieferbekaempfung",
        "Ungezieferbekämpfung",
        "2 Nr. 9",
        AllocationKey.AREA,
        "payment",
        special="preventive_pest_only",
        labour=70,
    ),
    _rule(
        "gartenpflege",
        "Gartenpflege",
        "2 Nr. 10",
        AllocationKey.AREA,
        "payment",
        special="garden_access",
        labour=83,
    ),
    _rule(
        "allgemeinstrom", "Allgemeinstrom / Beleuchtung", "2 Nr. 11", AllocationKey.AREA, "payment"
    ),
    _rule(
        "schornsteinreinigung",
        "Schornsteinreinigung",
        "2 Nr. 12",
        AllocationKey.UNITS,
        "payment",
        special="chimney_duplicate",
        labour=79,
    ),
    _rule(
        "versicherung",
        "Sach- und Haftpflichtversicherung",
        "2 Nr. 13",
        AllocationKey.AREA,
        "payment",
    ),
    _rule(
        "hauswart",
        "Hauswart",
        "2 Nr. 14",
        AllocationKey.AREA,
        "payment",
        special="caretaker_split",
        labour=80,
    ),
    _rule(
        "gemeinschaftsantenne",
        "Gemeinschafts-Antennenanlage",
        "2 Nr. 15a",
        AllocationKey.UNITS,
        "payment",
        special="cable_cutoff_new_installation",
    ),
    _rule(
        "breitband_verteilanlage",
        "Breitband-Verteilanlage",
        "2 Nr. 15b",
        AllocationKey.UNITS,
        "payment",
        special="cable_cutoff_new_installation",
    ),
    _rule(
        "glasfaser_bereitstellung",
        "Glasfaser-Bereitstellungsentgelt",
        "2 Nr. 15c",
        AllocationKey.UNITS,
        "payment",
        special="fibre_cap",
    ),
    _rule(
        "waeschepflege",
        "Einrichtungen für die Wäschepflege",
        "2 Nr. 16",
        AllocationKey.UNITS,
        "payment",
    ),
    _rule(
        "dachrinnenreinigung",
        "Dachrinnenreinigung",
        "2 Nr. 17",
        AllocationKey.AREA,
        "payment",
        naming=True,
        labour=80,
    ),
    _rule(
        "rauchwarnmelder_wartung",
        "Wartung Rauchwarnmelder",
        "2 Nr. 17",
        AllocationKey.UNITS,
        "payment",
        naming=True,
        special="smoke_detector_rent",
        labour=63,
    ),
    _rule(
        "lueftungsanlage_wartung",
        "Wartung Lüftungsanlage",
        "2 Nr. 17",
        AllocationKey.AREA,
        "payment",
        naming=True,
        labour=70,
    ),
    _rule(
        "elektropruefung",
        "Prüfung der Elektroanlage (DGUV V3)",
        "2 Nr. 17",
        AllocationKey.AREA,
        "payment",
        naming=True,
        special="inspection_without_defect_remediation",
        labour=80,
    ),
    _rule(
        "sonstige",
        "Sonstige Betriebskosten (frei benannt)",
        "2 Nr. 17",
        AllocationKey.AREA,
        "payment",
        naming=True,
    ),
)
_NON_ALLOCABLE = (
    "verwaltungskosten",
    "instandhaltung",
    "erneuerung",
    "schoenheitsreparaturen",
    "instandhaltungsruecklage",
    "bankgebuehren",
    "mietausfallwagnis",
    "rechtsverfolgung",
    "abrechnungserstellung",
    "kabel_altentgelt",
    "antenne_neuanlage",
)
CATALOGUE: dict[str, RuleSet[CatalogueRule]] = {
    row.cost_type: RuleSet(row.cost_type, (RuleVersion(date(1900, 1, 1), "BetrKV / Page 02", row),))
    for row in _ALLOCABLE
} | {
    name: RuleSet(
        name,
        (
            RuleVersion(
                date(1900, 1, 1),
                "§ 1 Abs. 2 BetrKV / Page 02",
                CatalogueRule(
                    name, name.replace("_", " ").title(), None, None, "payment", allocable=False
                ),
            ),
        ),
    )
    for name in _NON_ALLOCABLE
}


def resolve_rule(cost_type: str, as_of: date) -> ResolvedRule[CatalogueRule]:
    # Unknown types take the named Nr.17 route; this preserves a user decision
    # instead of making an OCR/free-text guess legally effective.
    return get_rule(CATALOGUE.get(cost_type, CATALOGUE["sonstige"]), as_of)


def list_catalogue(as_of: date) -> tuple[CatalogueRule, ...]:
    """Return the server-owned catalogue as it applies on one date.

    Clients may display these facts, but they never reconstruct or hard-code
    the legal catalogue themselves.
    """
    return tuple(resolve_rule(cost_type, as_of).value for cost_type in sorted(CATALOGUE))


def classify_position(position: CataloguePosition, contract: ContractFacts) -> ClassificationResult:
    # Credits are valid, but their declared non-allocable component still
    # cannot reverse past their absolute source amount.
    limit = abs(position.amount_cents) if position.amount_cents < 0 else position.amount_cents
    if position.non_allocable_cents < 0 or position.non_allocable_cents > limit:
        raise ValueError("non_allocable_cents must be between zero and the source amount")
    as_of = position.service_to or position.receipt_date
    resolved_rule = resolve_rule(position.cost_type, as_of)
    rule = resolved_rule.value
    source_allocable = position.amount_cents - position.non_allocable_cents
    if position.labour_cents is not None and not 0 <= position.labour_cents <= abs(
        source_allocable
    ):
        raise ValueError("labour_cents must be between zero and the allocable amount")
    findings: list[str] = ["verify-before-production"] if rule.verify_before_production else []
    if not rule.allocable:
        return ClassificationResult(
            rule.cost_type,
            rule.betrkv_number,
            0,
            position.amount_cents,
            None,
            None,
            None,
            tuple(findings),
            rule.verify_before_production,
            resolved_rule,
        )
    if not contract.allocation_agreed:
        return ClassificationResult(
            rule.cost_type,
            rule.betrkv_number,
            0,
            position.amount_cents,
            None,
            None,
            None,
            tuple([*findings, "umlagevereinbarung-fehlt"]),
            True,
            resolved_rule,
        )
    if not contract.residential_use:
        return ClassificationResult(
            rule.cost_type,
            rule.betrkv_number,
            0,
            position.amount_cents,
            None,
            None,
            None,
            tuple([*findings, "gewerbliche-nutzung-blockiert-v1"]),
            True,
            resolved_rule,
        )
    number = rule.betrkv_number
    if rule.naming_required and rule.cost_type not in contract.named_other_costs:
        if rule.special_rule == "trinkwasser_fallback":
            number = "2 Nr. 2"
            findings.append("trinkwasser-nr17-fallback")
        else:
            return ClassificationResult(
                rule.cost_type,
                number,
                0,
                position.amount_cents,
                None,
                None,
                None,
                tuple([*findings, "nr17-nicht-benannt"]),
                True,
                resolved_rule,
            )
    if position.new_cost and not contract.mehrbelastung_clause:
        return ClassificationResult(
            rule.cost_type,
            number,
            0,
            position.amount_cents,
            None,
            None,
            None,
            tuple([*findings, "mehrbelastungsklausel-fehlt"]),
            True,
            resolved_rule,
        )
    key, key_source = _select_key(position, contract, rule)
    labour = position.labour_cents
    if labour is None and rule.typical_labour_percent is not None:
        labour = int(
            (Decimal(abs(source_allocable)) * rule.typical_labour_percent / 100).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
        )
        findings.append("lohnanteil-vorgeschlagen")
    if rule.special_rule != "none":
        findings.append(f"sonderregel-{rule.special_rule}")
    return ClassificationResult(
        rule.cost_type,
        number,
        source_allocable,
        position.non_allocable_cents,
        labour,
        key,
        key_source,
        tuple(findings),
        rule.verify_before_production,
        resolved_rule,
    )


def _select_key(
    position: CataloguePosition, contract: ContractFacts, rule: CatalogueRule
) -> tuple[AllocationKey, str]:
    if position.key_override is not None:
        return position.key_override, "override"
    if rule.cost_type in contract.contractual_keys:
        return contract.contractual_keys[rule.cost_type], "contract"
    assert rule.default_key is not None
    return rule.default_key, "catalogue"


def split_position_at_rule_boundaries(
    position: CataloguePosition, boundaries: tuple[date, ...]
) -> tuple[CataloguePosition, ...]:
    """Split a service-period amount per actual day, half-up to cents.

    The last slice takes the residual so the original cents always reconcile.
    A receipt-date position has no service interval and intentionally remains one
    position: there is no invented service evidence to split.
    """
    if position.service_from is None or position.service_to is None:
        return (position,)
    if position.service_to <= position.service_from:
        raise ValueError("service_to must be after service_from")
    cuts = (
        position.service_from,
        *sorted(b for b in boundaries if position.service_from < b < position.service_to),
        position.service_to,
    )
    total_days = (position.service_to - position.service_from).days
    remaining = position.amount_cents
    result: list[CataloguePosition] = []
    for index, (start, end) in enumerate(pairwise(cuts)):
        if index == len(cuts) - 2:
            amount = remaining
        else:
            amount = int(
                (Decimal(position.amount_cents) * (end - start).days / total_days).quantize(
                    Decimal(1), rounding=ROUND_HALF_UP
                )
            )
            remaining -= amount
        result.append(
            CataloguePosition(
                position.cost_type,
                amount,
                position.receipt_date,
                service_from=start,
                service_to=end,
                key_override=position.key_override,
                evidence=position.evidence,
            )
        )
    return tuple(result)
