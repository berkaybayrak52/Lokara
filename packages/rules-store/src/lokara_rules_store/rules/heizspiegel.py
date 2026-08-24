"""K13 — versioned Heizspiegel rows for the UVI Block D2 comparison.

The co2online table includes heating and warm water. Callers receive the
vintage-valid middle value together with the vintage-specific deduction and
must pass that resolved input into the pure UVI engine. The rules store never
selects the newest vintage independently of the UVI month.

All values remain ``verify-before-production``. In particular, the heat-pump
deduction is the Lokara convention ``24 / JAZ 3`` and is not a confirmed
co2online kWh value. Every future vintage must be imported as new immutable
data and revalidated before it can be used.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Final

from lokara_domain import RuleEvidence
from lokara_uvi_engine import ResolvedHeizspiegelRow

from ..store import RuleSet, RuleVersion, get_rule


@dataclass(frozen=True, slots=True)
class HeizspiegelRow:
    """One source row, including the original heat-plus-warm-water bands."""

    size_class: str
    energy_source: str
    low_kwh_m2a: int
    middle_kwh_m2a: int
    high_kwh_m2a: int
    too_high_from_kwh_m2a: int


@dataclass(frozen=True, slots=True)
class HeizspiegelVintage:
    """Immutable source table and method metadata for one publication vintage."""

    vintage: str
    billing_year: int
    source_as_of: str
    source_row_identity: str
    attribution_de: str
    rows: tuple[HeizspiegelRow, ...]
    warm_water_deductions_kwh_m2a: MappingProxyType[str, int]
    heat_pump_deduction_status: str


HEIZSPIEGEL_2025_ROWS: Final[tuple[HeizspiegelRow, ...]] = (
    HeizspiegelRow("80-150", "Erdgas", 62, 121, 207, 208),
    HeizspiegelRow("80-150", "Heizoel", 100, 165, 263, 264),
    HeizspiegelRow("80-150", "Fernwaerme", 38, 89, 191, 192),
    HeizspiegelRow("80-150", "Waermepumpe", 20, 36, 82, 83),
    HeizspiegelRow("80-150", "Holzpellets", 74, 148, 249, 250),
    HeizspiegelRow("150-250", "Erdgas", 64, 116, 187, 188),
    HeizspiegelRow("150-250", "Heizoel", 92, 142, 220, 221),
    HeizspiegelRow("150-250", "Fernwaerme", 41, 94, 169, 170),
    HeizspiegelRow("150-250", "Waermepumpe", 18, 33, 77, 78),
    HeizspiegelRow("150-250", "Holzpellets", 72, 126, 219, 220),
    HeizspiegelRow("250-500", "Erdgas", 61, 114, 185, 186),
    HeizspiegelRow("250-500", "Heizoel", 78, 123, 197, 198),
    HeizspiegelRow("250-500", "Fernwaerme", 36, 112, 203, 204),
    HeizspiegelRow("250-500", "Waermepumpe", 17, 30, 69, 70),
    HeizspiegelRow("250-500", "Holzpellets", 60, 113, 196, 197),
    HeizspiegelRow("ueber-500", "Erdgas", 59, 115, 177, 178),
    HeizspiegelRow("ueber-500", "Heizoel", 68, 127, 198, 199),
    HeizspiegelRow("ueber-500", "Fernwaerme", 46, 87, 144, 145),
)

WARM_WATER_DEDUCTIONS_2025: Final[MappingProxyType[str, int]] = MappingProxyType(
    {
        "Erdgas": 24,
        "Heizoel": 24,
        "Fernwaerme": 24,
        "Holzpellets": 24,
        "Waermepumpe": 8,
    }
)

HEIZSPIEGEL_ATTRIBUTION_DE: Final = "Quelle: co2online gGmbH (Heizspiegel)"
OVER_500_FALLBACK_LABEL_DE: Final = (
    "Vergleichswert der Größenklasse 250–500 m²; für über 500 m² liegt für diesen "
    "Energieträger noch kein Wert vor"
)

_OVER_500_FALLBACKS: Final[MappingProxyType[str, str]] = MappingProxyType(
    {"Waermepumpe": "250-500", "Holzpellets": "250-500"}
)


def validate_heizspiegel_import(
    rows: tuple[HeizspiegelRow, ...],
    warm_water_deductions_kwh_m2a: MappingProxyType[str, int],
) -> None:
    """Reject an import if any resolved middle value is not positive heat-only."""

    for row in rows:
        deduction = warm_water_deductions_kwh_m2a.get(row.energy_source)
        if deduction is None:
            raise ValueError(f"missing warm-water deduction for {row.energy_source}")
        if row.middle_kwh_m2a - deduction <= 0:
            raise ValueError(
                "middle value minus warm-water deduction must be positive for "
                f"{row.energy_source}/{row.size_class}"
            )


validate_heizspiegel_import(HEIZSPIEGEL_2025_ROWS, WARM_WATER_DEDUCTIONS_2025)

_HEIZSPIEGEL_2025: Final = HeizspiegelVintage(
    vintage="Heizspiegel 2025",
    billing_year=2024,
    source_as_of="09/2025",
    source_row_identity="HEIZSPIEGEL_2025_ROWS",
    attribution_de=HEIZSPIEGEL_ATTRIBUTION_DE,
    rows=HEIZSPIEGEL_2025_ROWS,
    warm_water_deductions_kwh_m2a=WARM_WATER_DEDUCTIONS_2025,
    heat_pump_deduction_status="verify-before-production_convention",
)

HEIZSPIEGEL_RULES: Final[RuleSet[HeizspiegelVintage]] = RuleSet(
    key="uvi.heizspiegel",
    versions=(
        RuleVersion(
            valid_from=date(2025, 10, 1),
            source=HEIZSPIEGEL_ATTRIBUTION_DE,
            value=_HEIZSPIEGEL_2025,
        ),
    ),
)


def resolve_heizspiegel_row(
    rule_set: RuleSet[HeizspiegelVintage],
    *,
    as_of: date,
    energy_source: str,
    requested_size_class: str,
) -> ResolvedHeizspiegelRow:
    """Resolve the exact vintage valid at ``as_of`` into the UVI input type."""

    resolved_rule = get_rule(rule_set, as_of)
    vintage = resolved_rule.value
    actual_size_class = requested_size_class
    fallback_label_de: str | None = None
    if requested_size_class == "ueber-500" and energy_source in _OVER_500_FALLBACKS:
        actual_size_class = _OVER_500_FALLBACKS[energy_source]
        fallback_label_de = OVER_500_FALLBACK_LABEL_DE

    row = next(
        (
            candidate
            for candidate in vintage.rows
            if candidate.energy_source == energy_source
            and candidate.size_class == actual_size_class
        ),
        None,
    )
    if row is None:
        raise ValueError(f"no Heizspiegel row for {energy_source}/{requested_size_class}")

    deduction = vintage.warm_water_deductions_kwh_m2a.get(energy_source)
    if deduction is None:
        raise ValueError(f"missing warm-water deduction for {energy_source}")

    deduction_basis = "co2online method; verify for every Heizspiegel vintage"
    if energy_source == "Waermepumpe":
        deduction_basis = "Lokara convention: 24 / JAZ 3; co2online confirmation outstanding"

    evidence = (
        RuleEvidence(
            source=vintage.attribution_de,
            register_row=vintage.source_row_identity,
            legal_basis="§ 6a HeizkostenV; normed building-level comparison",
            rechtsstand=vintage.source_as_of,
            verification_status="verify-before-production",
        ),
        RuleEvidence(
            source=vintage.attribution_de,
            register_row="HEIZSPIEGEL_D2_CONTRACT",
            legal_basis=deduction_basis,
            rechtsstand=vintage.source_as_of,
            verification_status="verify-before-production",
        ),
        RuleEvidence(
            source=resolved_rule.source,
            register_row=vintage.source_row_identity,
            legal_basis="RuleVersion effective date selected by UVI month",
            rechtsstand=resolved_rule.rechtsstand,
            verification_status="verify-before-production",
        ),
    )

    return ResolvedHeizspiegelRow(
        energy_source=energy_source,
        requested_size_class=requested_size_class,
        actual_size_class=actual_size_class,
        heizspiegel_mittel_kwh_m2a=Decimal(row.middle_kwh_m2a),
        warm_water_deduction_kwh_m2a=Decimal(deduction),
        heizspiegel_vintage=(
            f"{vintage.vintage.removeprefix('Heizspiegel ')}/billing-year-{vintage.billing_year}"
        ),
        fallback_label_de=fallback_label_de,
        evidence=evidence,
    )
