"""Versioned Page-05 guard data resolved by callers before engine evaluation.

The structures here deliberately do not import the guard engine.  Application code
resolves a version, maps these immutable values into the engine's typed bundles, and
keeps external providers behind adapters.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .store import ResolvedRule, RuleSet, RuleVersion, get_rule

PAGE_05_SOURCE = "berkay-work/Spec-Seiten/05 · Wächter Fristen 3a95fd42073181038246e579777508f9.md"
REGISTER_SOURCE = "berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv"


@dataclass(frozen=True, slots=True)
class Page05Evidence:
    source: str
    register_row: str
    legal_basis: str
    rechtsstand: str
    verification_status: str


@dataclass(frozen=True, slots=True)
class Page05ProductionBlocker:
    code: str
    description: str


@dataclass(frozen=True, slots=True)
class Page05RuleConflict:
    code: str
    description: str
    production_blocking: bool
    applies_to_media: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Page05G1GuardRules:
    evidence: tuple[Page05Evidence, ...]
    unresolved_conflicts: tuple[Page05RuleConflict, ...]


@dataclass(frozen=True, slots=True)
class Page05G1Rules:
    w1: Page05G1GuardRules
    w2: Page05G1GuardRules
    w4: Page05G1GuardRules


@dataclass(frozen=True, slots=True)
class Page05PaymentArrearsRules:
    evidence: tuple[Page05Evidence, ...]
    production_blockers: tuple[Page05ProductionBlocker, ...]
    warning_3a_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class Page05ComparativeRentRules:
    evidence: tuple[Page05Evidence, ...]
    production_blockers: tuple[Page05ProductionBlocker, ...]
    normal_cap_rate: Decimal
    tight_market_cap_rate: Decimal
    declaration_wait_months: int
    effective_wait_months: int
    consent_months: int
    effective_after_request_months: int
    action_months_after_consent_deadline: int
    warning_full_check_de: str
    warning_cap_only_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class Page05GraduatedRentRules:
    evidence: tuple[Page05Evidence, ...]
    production_blockers: tuple[Page05ProductionBlocker, ...]
    minimum_interval_months: int
    warning_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class Page05IndexRentRules:
    evidence: tuple[Page05Evidence, ...]
    production_blockers: tuple[Page05ProductionBlocker, ...]
    minimum_interval_months: int
    rebasing_warning_de: str
    warning_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class Page05VacancyRules:
    evidence: tuple[Page05Evidence, ...]
    production_blockers: tuple[Page05ProductionBlocker, ...]
    threshold_days: int
    rent_period_days: int
    warning_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class Page05M9Rules:
    payment_arrears: Page05PaymentArrearsRules
    comparative_rent: Page05ComparativeRentRules
    graduated_rent: Page05GraduatedRentRules
    index_rent: Page05IndexRentRules
    vacancy: Page05VacancyRules


def _evidence(rows: str, legal_basis: str) -> tuple[Page05Evidence, ...]:
    return (
        Page05Evidence(
            source=PAGE_05_SOURCE,
            register_row="Page 05",
            legal_basis=legal_basis,
            rechtsstand="07/2026",
            verification_status="verify-before-production",
        ),
        Page05Evidence(
            source=REGISTER_SOURCE,
            register_row=rows,
            legal_basis=legal_basis,
            rechtsstand="07/2026",
            verification_status="verify-before-production",
        ),
    )


def _blocker(code: str, description: str) -> Page05ProductionBlocker:
    return Page05ProductionBlocker(code=code, description=description)


PAGE_05_G1_RULES = RuleSet(
    key="page05.g1.guards",
    versions=(
        RuleVersion(
            valid_from=date(2026, 8, 1),
            source=REGISTER_SOURCE,
            value=Page05G1Rules(
                w1=Page05G1GuardRules(
                    evidence=(
                        Page05Evidence(
                            source=REGISTER_SOURCE,
                            register_row="26",
                            legal_basis="§ 556 Abs. 3 S. 2–3 BGB",
                            rechtsstand="07/2026",
                            verification_status="geprüft",
                        ),
                        Page05Evidence(
                            source=REGISTER_SOURCE,
                            register_row="126",
                            legal_basis="§§ 187, 188 BGB; KONVENTION-D1/D4/D5",
                            rechtsstand="07/2026",
                            verification_status="verify-before-production",
                        ),
                    ),
                    unresolved_conflicts=(
                        Page05RuleConflict(
                            code="W1-D4-OBJECTION-END",
                            description=(
                                "Same-numbered day after 12 months versus month-end reading is "
                                "unresolved."
                            ),
                            production_blocking=True,
                        ),
                    ),
                ),
                w2=Page05G1GuardRules(
                    evidence=(
                        Page05Evidence(
                            source=REGISTER_SOURCE,
                            register_row="128",
                            legal_basis="§ 34 Abs. 2 MessEV; supersedes KONVENTION-D2",
                            rechtsstand="08/2026",
                            verification_status="geprüft",
                        ),
                        Page05Evidence(
                            source=REGISTER_SOURCE,
                            register_row="129",
                            legal_basis="MessEV Anlage 7 Nr. 5.5.1/5.5.2 und 7.1/7.2",
                            rechtsstand="08/2026",
                            verification_status="geprüft",
                        ),
                    ),
                    unresolved_conflicts=(
                        Page05RuleConflict(
                            code="W2-RETROFIT-TRANSITION",
                            description=(
                                "The Dritte MessEV-ÄndV unified the period at six years from "
                                "04.11.2021. That it also covers devices whose five-year period "
                                "was still running rests on provider communication; no transition "
                                "clause was found in the ordinance text."
                            ),
                            production_blocking=False,
                            applies_to_media=(
                                "warm_water",
                                "heat_meter",
                                "heat_exchanger_hot_water",
                            ),
                        ),
                    ),
                ),
                w4=Page05G1GuardRules(
                    evidence=(
                        Page05Evidence(
                            source=REGISTER_SOURCE,
                            register_row="4",
                            legal_basis="§ 6a Abs. 1 Nr. 2 HeizkostenV",
                            rechtsstand="07/2026",
                            verification_status="geprüft",
                        ),
                        Page05Evidence(
                            source=REGISTER_SOURCE,
                            register_row="117",
                            legal_basis="KONVENTION-D3; month-end due date",
                            rechtsstand="10/2023",
                            verification_status="verify-before-production",
                        ),
                        Page05Evidence(
                            source=REGISTER_SOURCE,
                            register_row="30",
                            legal_basis="§ 5 Abs. 2 HeizkostenV",
                            rechtsstand="07/2026",
                            verification_status="geprüft",
                        ),
                    ),
                    unresolved_conflicts=(
                        Page05RuleConflict(
                            code="W4-YEAR-ROUND-OR-HEATING-SEASON",
                            description=(
                                "Year-round cadence versus heating-season-only cadence is "
                                "unresolved."
                            ),
                            production_blocking=True,
                        ),
                    ),
                ),
            ),
        ),
    ),
)


PAGE_05_M9_RULES = RuleSet(
    key="page05.m9.guards",
    versions=(
        RuleVersion(
            valid_from=date(2026, 7, 1),
            source=f"{PAGE_05_SOURCE}; {REGISTER_SOURCE}",
            value=Page05M9Rules(
                payment_arrears=Page05PaymentArrearsRules(
                    evidence=_evidence("121,124,125,127", "§§ 543 Abs. 2 Nr. 3, 569 Abs. 3 BGB"),
                    production_blockers=(
                        _blocker(
                            "W3-VERIFY-BEFORE-PRODUCTION",
                            "Primary-source and legal verification is required.",
                        ),
                        _blocker(
                            "W3-WARNING-COPY-INCOMPLETE",
                            "Page 05 supplies exact warning copy only for stage 3a.",
                        ),
                        _blocker(
                            "PUSH-CLIENT-TOKEN-BOUNDARY-MISSING",
                            "Push remains unavailable until M10 supplies a client/token boundary.",
                        ),
                    ),
                    warning_3a_de=(
                        "Der Mietrückstand von {renter_label} beträgt {arrears} € und übersteigt "
                        "eine Monatsmiete bei zwei aufeinanderfolgenden offenen Terminen — die "
                        "Schwelle für eine fristlose Kündigung wegen Zahlungsverzugs (§ 543 Abs. "
                        "2 Nr. 3a BGB) ist erreicht. Hinweis: Eine Schonfristzahlung (§ 569 Abs. "
                        "3 Nr. 2 BGB) kann die Kündigung heilen."
                    ),
                    channels_by_stage={
                        "info": ("in_app",),
                        "3a": ("email",),
                        "3b": ("push",),
                    },
                    resolution_event="payment_received",
                ),
                comparative_rent=Page05ComparativeRentRules(
                    evidence=_evidence("116,119,120,122,123,126,132", "§§ 558, 558b BGB"),
                    production_blockers=(
                        _blocker(
                            "W5-VERIFY-BEFORE-PRODUCTION",
                            "Tenancy-law values and calendar reading require verification.",
                        ),
                        _blocker(
                            "W5-TIGHT-MARKET-LIST-MISSING",
                            "No state regulation list is supplied; the caller must classify it.",
                        ),
                        _blocker(
                            "W5-COMPARATIVE-RENT-PROVIDER-MISSING",
                            "Comparative rent remains a nullable manual input in V1.",
                        ),
                    ),
                    normal_cap_rate=Decimal("0.20"),
                    tight_market_cap_rate=Decimal("0.15"),
                    declaration_wait_months=12,
                    effective_wait_months=15,
                    consent_months=2,
                    effective_after_request_months=3,
                    action_months_after_consent_deadline=3,
                    warning_full_check_de=(
                        "Sie können die Miete für {unit_label} um bis zu {maximum_increase} € auf "
                        "{maximum_new_rent} € erhöhen (§ 558 BGB). Begrenzt durch "
                        "{limiting_rule}."
                    ),
                    warning_cap_only_de=(
                        "Die Kappungsgrenze erlaubt für {unit_label} bis zu {maximum_new_rent} € "
                        "(+{maximum_increase} €). Prüfen Sie zusätzlich selbst die ortsübliche "
                        "Vergleichsmiete — die Erhöhung nach § 558 darf sie nicht übersteigen."
                    ),
                    channels_by_stage={
                        "opportunity": ("in_app",),
                        "action_deadline": ("in_app", "email"),
                    },
                    resolution_event="rent_increase_consented",
                ),
                graduated_rent=Page05GraduatedRentRules(
                    evidence=_evidence("130", "§ 557a Abs. 1–2 BGB"),
                    production_blockers=(
                        _blocker(
                            "W6-VERIFY-BEFORE-PRODUCTION",
                            "The tenancy-law row requires primary-source/legal verification.",
                        ),
                    ),
                    minimum_interval_months=12,
                    warning_de=(
                        "Neue Mietstaffel für {unit_label} ab {step_effective_on}: {amount} €."
                    ),
                    channels_by_stage={"adjustment_due": ("in_app",)},
                    resolution_event="target_rent_updated",
                ),
                index_rent=Page05IndexRentRules(
                    evidence=_evidence("131,132,133", "§ 557b BGB; KONVENTION-VPI"),
                    production_blockers=(
                        _blocker(
                            "W7-VERIFY-BEFORE-PRODUCTION",
                            "The tenancy-law values require primary-source/legal verification.",
                        ),
                        _blocker(
                            "W7-PROPORTIONAL-METHOD-UNCERTAIN",
                            "The proportional VPI method is a non-production-approved convention.",
                        ),
                        _blocker(
                            "W7-REAL-DESTatis-PROVIDER-MISSING",
                            "The snapshot is test/demo data; no real GENESIS provider is selected.",
                        ),
                    ),
                    minimum_interval_months=12,
                    rebasing_warning_de="Index umrechnen (Umbasierung)",
                    warning_de=(
                        "VPI von {base_index} auf {new_index} (+{delta_percent} %) → mögliche "
                        "neue Miete {new_rent} € (+{increase} €)."
                    ),
                    channels_by_stage={"opportunity": ("in_app",)},
                    resolution_event="index_adjustment_effective",
                ),
                vacancy=Page05VacancyRules(
                    evidence=_evidence("118", "KONVENTION-L1/L2; product heuristic"),
                    production_blockers=(
                        _blocker(
                            "W8-VERIFY-BEFORE-PRODUCTION",
                            "The threshold and lost-rent framing are a product heuristic.",
                        ),
                    ),
                    threshold_days=30,
                    rent_period_days=30,
                    warning_de=(
                        "{unit_label} steht seit {vacancy_days} Tagen leer — ca. {lost_rent} € "
                        "entgangene Miete."
                    ),
                    channels_by_stage={"vacancy": ("in_app",)},
                    resolution_event="active_tenancy_started",
                ),
            ),
        ),
    ),
)


def resolve_page05_m9_rules(as_of: date) -> ResolvedRule[Page05M9Rules]:
    """Resolve the Page-05 M9 bundle for an explicit law date."""

    return get_rule(PAGE_05_M9_RULES, as_of)


def resolve_page05_g1_rules(as_of: date) -> ResolvedRule[Page05G1Rules]:
    """Resolve approved W1/W2/W4 evidence and conflicts for an explicit date."""

    return get_rule(PAGE_05_G1_RULES, as_of)
