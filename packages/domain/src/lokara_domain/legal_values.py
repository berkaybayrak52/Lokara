"""Shapes of legal rule values.

These are normalized value objects only — the actual legal numbers live in the
versioned rules store (lokara-rules-store) with as-of law dates, never in code
(CLAUDE.md). Engines depend only on this package, so the shapes are defined
here and resolved rule values are passed to engines as parameters.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class HeatingSplitBounds:
    """§ 7 Abs. 1 HeizkostenV: allowed consumption-based share of heating cost."""

    min_consumption_share: Decimal
    max_consumption_share: Decimal


@dataclass(frozen=True)
class Co2Step:
    """One step of the CO2KostAufG 10-step model.

    max_intensity_exclusive is the step's upper bound in kg CO₂/m²/year
    (exclusive); None marks the open-ended last step.
    """

    max_intensity_exclusive: Decimal | None
    landlord_share_percent: int


Co2Table = tuple[Co2Step, ...]


@dataclass(frozen=True)
class DegreeDayTable:
    """Monthly degree-day (Gradtagszahlen) weights, Jan..Dec, in **Zehntelpromille**;
    sums to 10 000.

    The unit is in the field name because the table itself forces it: VDI 2067
    Blatt 1, Ausgabe 12/1983, Tabelle 22 puts Jun/Jul/Aug at 13,3 / 13,3 / 13,4 ‰
    — 400/3 split three ways, which no integer promille can represent (K3,
    `docs/03-nk-heating-engines.md` → "Seite 01b … (2) K3").

    Display value = stored / 10. Never store the ‰ integer: the superseded
    promille table summed to 1000 and would otherwise be constructible here in
    silence, at a tenth of its intended weight.
    """

    tenth_promille_by_month: tuple[int, int, int, int, int, int, int, int, int, int, int, int]

    def __post_init__(self) -> None:
        if sum(self.tenth_promille_by_month) != 10_000:
            raise ValueError("DegreeDayTable tenth-promille values must sum to 10 000")


@dataclass(frozen=True)
class WarmWaterFormula:
    """§ 9 Abs. 2 HeizkostenV constants for separating warm-water energy."""

    factor_kwh_per_m3_kelvin: Decimal
    hot_temp_c: Decimal
    cold_temp_c: Decimal
    # Fallback when the warm-water volume is not measured: kWh per m² living
    # area per year.
    area_fallback_kwh_per_sqm_year: Decimal

    def energy_kwh_for_volume(self, volume_m3: Decimal) -> Decimal:
        return self.factor_kwh_per_m3_kelvin * volume_m3 * (self.hot_temp_c - self.cold_temp_c)
