"""Normalized heating-engine inputs/outputs.

Plain frozen dataclasses; every legal ratio/table arrives as a resolved rule
value (lokara-domain shapes) — the engine never hardcodes a legal number.

The result shapes carry, besides the money, every intermediate the statement's
legally required disclosure has to show: the pots of the §§ 7/8/9 vertical
split, the per-party Bemessungen of the horizontal one, which § 9 branch ran
with which operands, and the § 7 Abs. 3 CO2KostAufG Berechnungsgrundlagen.
Contract: `docs/08-statement-document.md` → "The carried-intermediates contract
(slice 3)". Two rules hold throughout:

* **Every disclosure field is required.** A default lets a caller build a result
  that silently omits a legally required figure, and the omission surfaces as a
  blank on a tenant's statement instead of as a `TypeError` in CI.
* **`None` means "not applied", never "not carried".** Where a branch did not
  run its operands are `None`, so a template printing the wrong branch prints
  `None` loudly rather than a plausible wrong formula.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from lokara_domain import (
    Cents,
    Co2Table,
    DegreeDayTable,
    EmissionFactor,
    EnergyReference,
    HeatingSplitBounds,
    MeasurementUnit,
    Occupancy,
    Period,
    WarmWaterFormula,
)


@dataclass(frozen=True)
class HeatingUnit:
    unit_id: str
    area_sqm_x100: int
    # Measured heating consumption (heat-meter units). None → §9a estimation.
    heat_consumption: Decimal | None
    # Measured warm-water volume (m³). None → §9a estimation (if WW exists).
    ww_consumption_m3: Decimal | None = None
    # The Maßeinheit `heat_consumption` is counted in, carried on the row that
    # carries the value (docs/08 rule 1). `MeterKind.HEAT` covers both a
    # Wärmemengenzähler counting kWh and a Heizkostenverteiler counting
    # dimensionless Einheiten, so the unit is not derivable from the kind.
    #
    # Defaulting to `None` is a deliberate exception to this module's
    # "every disclosure field is required" rule: an absent unit is not silently
    # dropped, it propagates to the printed disclosure "ohne Maßeinheit — nicht
    # ausgewiesen". A unit may declare its device without supplying a reading —
    # the § 9a estimate is then in the measured units' unit — but a *conflicting*
    # declaration is still an input error.
    heat_consumption_unit: MeasurementUnit | None = None


@dataclass(frozen=True)
class WarmWaterInput:
    """Central warm water exists. volume_m3=None → § 9 Abs. 2 area fallback."""

    volume_m3: Decimal | None


@dataclass(frozen=True)
class Co2Input:
    """§ 3 CO2KostAufG: what the supplier stated, and the K4 fallback if it did not.

    `total_co2_kg` is the Brennstoffemissionen the supplier is obliged to state
    (§ 3 Abs. 1 Nr. 1) — the normal path, and the one the demo runs. `None` means
    the obligation was breached (E1); then and **only** then is
    `emission_factor` read, and it must carry the same Bezugsgröße as
    `HeatingInput.energy_reference`. Supplying both is refused rather than
    ignored: a silently ignored factor is how a wrong one survives in the data
    until the day a supplier stops stating the mass (`docs/03` § 9.5).
    """

    total_co2_kg: Decimal | None
    co2_cost: Cents | None
    # K4 fallback (`nur Fallback`, `Konvention` / verify-before-production,
    # Rechtsstand 07/2026). Carries its own Ho/Hu reference — that is what makes
    # a mismatch checkable at all instead of a comment next to a number.
    emission_factor: EmissionFactor | None = None


@dataclass(frozen=True)
class HeatingRules:
    """Resolved rule values (from lokara-rules-store, as of the law date)."""

    consumption_share: Decimal
    split_bounds: HeatingSplitBounds
    warm_water_formula: WarmWaterFormula
    degree_days: DegreeDayTable
    co2_table: Co2Table | None = None
    co2_rechtsstand: str | None = None


@dataclass(frozen=True)
class HeatingInput:
    billing_period: Period
    # Total cost of the heating system incl. warm-water generation.
    total_cost: Cents
    # Fuel energy content over the period (kWh) — denominator for § 9.
    total_energy_kwh: Decimal
    units: tuple[HeatingUnit, ...]
    occupancies: tuple[Occupancy, ...]
    rules: HeatingRules
    warm_water: WarmWaterInput | None = None
    co2: Co2Input | None = None
    # The Bezugsgröße of `total_energy_kwh` — Brennwert (Ho), as a German gas
    # invoice bills, or Heizwert (Hu), which § 3 Abs. 1 Nr. 3 CO2KostAufG's
    # factor refers to. Read **only** on the K4 mass fallback; where the supplier
    # stated the mass the question does not arise and this may stay `None`.
    # It is never defaulted: defaulting to Hu on an Ho invoice is the silent 11 %
    # error the whole no-conversion design exists to stop (`docs/03` § 9.5).
    energy_reference: EnergyReference | None = None


@dataclass(frozen=True)
class WarmWaterSeparation:
    """§ 9 HeizkostenV — which branch separated the warm-water energy, and with
    which operands. The two branches print different text, so the result has to
    say which one ran; the wrong one must be unprintable rather than plausible.

    In `MEASURED` the four fallback operands are `None`; in `AREA_FALLBACK` the
    four measured ones are.
    """

    method: Literal["MEASURED", "AREA_FALLBACK"]
    # § 9 Abs. 2 — the separated warm-water energy, the result of the formula.
    q_ww_kwh: Decimal
    # The denominator the copy prints ("… von 20.000 kWh Gesamtenergie").
    total_energy_kwh: Decimal
    # MEASURED operands — the resolved rule values, never template literals.
    volume_m3: Decimal | None
    factor_kwh_per_m3_kelvin: Decimal | None
    hot_temp_c: Decimal | None
    cold_temp_c: Decimal | None
    # AREA_FALLBACK operands (§ 9 Abs. 2 Ersatzwert).
    area_fallback_kwh_per_sqm_year: Decimal | None
    heated_area_sqm: Decimal | None
    period_days: int | None
    # The divisor the engine actually used — a flat 365, deliberately *not* the
    # anchored reference year the CO₂ factor uses. The result echoes what was
    # divided by; harmonising the two moves a euro figure (docs/08, gaps).
    reference_year_days: int | None


@dataclass(frozen=True)
class HeatingLine:
    """One **Mietverhältnis**'s share, plus the Bemessung that produced it in
    each column.

    ``tenancy_id`` is `None` on no line the engine emits: since 14.08.2026 the
    Eigentümeranteil is not a party but `HeatingResult.owner_residual`
    (`docs/02` → *"The Eigentümeranteil is a residual line, not a party"*). The
    field keeps its optional type because the NK engine's `PartyKey` vocabulary
    is shared with it and still carries a landlord party until Seite 02 lands in
    `docs/09`.
    """

    unit_id: str
    tenancy_id: str | None
    heating_base: Cents
    heating_consumption: Cents
    ww_base: Cents
    ww_consumption: Cents
    total: Cents
    # § 9b Abs. 3 Zeitanteile: this party's days, and the per-unit sum they are
    # a share of (the applied denominator — not the billing period's length).
    days: int
    unit_total_days: int
    # §§ 7 Abs. 1 / 8 Abs. 1 Fläche·Tage Bemessung. **×100 fixed point** (the
    # scale is in the name on purpose): ÷ 100 gives the printed m²·Tage.
    base_weight_sqm_days_x100: Decimal
    # The consumption Bemessung applied to the heating pot. `None` iff the
    # heating column fell back to the area key (§ 9a Abs. 2) — then no
    # consumption figure was applied and none may be shown.
    heat_consumption_weight: Decimal | None
    # The warm-water Bemessung in m³ (unscaled). `None` iff there is no central
    # warm water or that column fell back to the area key.
    ww_consumption_weight_m3: Decimal | None
    # § 9b Abs. 2 Gradtagszahlen: this party's promille and the per-unit total.
    # Never print the promille bare — over a partial billing period a unit's
    # parties sum to less than 1.000 and "585 ‰" alone would read as wrong.
    degree_day_promille: Decimal
    unit_degree_day_promille_total: Decimal


@dataclass(frozen=True)
class Co2Result:
    # kg CO₂/m²/**Jahr** — annualised (H2), which is what the Anlage's column
    # header asks for, then rounded to one decimal under § 5 Abs. 1 S. 3 (R8).
    # This is the value used for classification and disclosure; the raw value
    # remains reproducible from the carried mass, area and period-day fields.
    intensity_kg_per_sqm: Decimal
    # H2: `365 / nTage`, which is **>= 1** for a short period and exactly 1 when
    # nTage is 365 or 366. Deliberately not called `period_factor`: that name
    # belonged to the superseded bound-shortening factor, which was <= 1, and an
    # inverted meaning behind an old name is how a renderer silently prints the
    # wrong band.
    annualisation_factor: Decimal
    landlord_share_percent: int
    landlord_amount: Cents
    renter_amount: Cents
    # e.g. "Rechtsstand 01/2023" — must appear on the statement.
    rechtsstand: str
    # § 7 Abs. 3 Berechnungsgrundlagen — the two operands the intensity is
    # reproducible from, and the amount being split. This object discharges
    # § 7 Abs. 3 on its own, which is why the area is repeated here.
    total_co2_kg: Decimal
    heated_area_sqm: Decimal
    co2_cost: Cents
    # The Einstufung as the band actually compared against — the Anlage's own,
    # unscaled bounds, i.e. the pair a tenant can look up in the published annex.
    # `Co2Step` carries no ordinal, so a step *number* would be invented.
    # `None` lower = the first step ("unter 12"); `None` upper = the open-ended
    # top step.
    band_min_inclusive: Decimal | None
    band_max_exclusive: Decimal | None
    # The two day counts behind `annualisation_factor` — "(275 von 365 Tagen)"
    # is required copy and 1,327272… cannot be un-divided back into it.
    period_days: int
    # The divisor H2 actually applied: a flat 365, never the anchored reference
    # year (which is used only to refuse a period longer than a year). The
    # result echoes what was divided by; the flat divisor is a convention
    # recorded in `docs/03` § 7 no. 8.
    reference_year_days: int


@dataclass(frozen=True)
class OwnerResidualOrigin:
    """Block (a) of the Leerstandsaufstellung: one empty/self-used unit's own
    share of each block, computed **for the annex** — its own `round_half_up`
    against the full denominator, *not* a slice of the residual.

    Never printed on the Gesamtübersicht: the printed Eigentümeranteil is the
    residual, and the two differ by the line-wise rounding (his `08-F21`:
    17.536 computed separately, 17.531 as a residual). Kept because the landlord
    needs the vacancy share **per object** for Anlage V (§ 9 EStG) and because
    § 9b Abs. 3 (Block C — Nutzerwechsel) still has to disclose the vacancy
    segment's Zeitanteil even though its money row is gone.

    Spec: `docs/08-statement-document.md` → "Die Eigentümerzeile" §§ 5-6.
    """

    unit_id: str
    heating_base: Cents
    heating_consumption: Cents
    ww_base: Cents
    ww_consumption: Cents
    total: Cents
    # The Bemessungen Block C still has to disclose for the vacancy segment, in
    # the same shapes and with the same `None` semantics as `HeatingLine`.
    days: int
    unit_total_days: int
    base_weight_sqm_days_x100: Decimal
    heat_consumption_weight: Decimal | None
    ww_consumption_weight_m3: Decimal | None
    degree_day_promille: Decimal
    unit_degree_day_promille_total: Decimal


@dataclass(frozen=True)
class OwnerResidual:
    """The one Eigentümerzeile per Liegenschaft (Seite 01 **D12**).

        eigentuemerCent[block] = blockbetragCent[block] - Σ mieteranteilCent[block]

    For heating that is one line across **all four blocks** (§ 1.3 Frage 3). It
    always exists — including at `0,00 €`, including in a fully-let building —
    and it may be negative, because `round_half_up` biases the renter shares
    upward and the residual absorbs the overshoot.

    **Carries no quota, by shape rather than by discipline:** there is no
    percentage field, so a renderer cannot print one. § 1.3 Frage 2: *"Eine
    gedruckte Quote würde eine Verteilungsbasis suggerieren, die es nicht gibt —
    der Betrag ist ein Rest, keine Quote."*
    """

    heating_base: Cents
    heating_consumption: Cents
    ww_base: Cents
    ww_consumption: Cents
    total: Cents
    # (a) — one entry per empty/self-used unit, in the engine's unit order.
    # Empty tuple in a fully-let building; the row still renders.
    origins: tuple[OwnerResidualOrigin, ...]
    # (c) = total - Σ origins.total. Belongs to no unit. In a fully-let building
    # the whole line is block (c).
    rounding_difference: Cents
    # The Fiktivbelegung (D0) printed in the Bemessung column, aggregated over
    # `origins`. `None` — not 0 — when there is no vacancy and no self-use: the
    # column then stays empty, and `None` is what makes "empty" unprintable as a
    # zero. Also `None` where the column's key was replaced under § 9a Abs. 2,
    # exactly as on `HeatingLine`.
    base_weight_sqm_days_x100: Decimal | None
    heat_consumption_weight: Decimal | None
    ww_consumption_weight_m3: Decimal | None


@dataclass(frozen=True)
class HeatingResult:
    # Mietverhältnisse only — the Eigentümer is not a party, so there is no
    # party slot an owner share could be written into (`docs/02`).
    lines: tuple[HeatingLine, ...]
    # Required, never `None`: an `OwnerResidual | None` would re-create the
    # branch § 1.3 Frage 1 removes, and the first renderer to write
    # `if result.owner_residual:` would silently drop a `0,00 €` row.
    owner_residual: OwnerResidual
    co2: Co2Result | None
    # Units whose missing readings were estimated per § 9a.
    estimated_unit_ids: tuple[str, ...]
    # True when > 25 % of the area lacked readings and the consumption
    # portion was allocated by the fixed (area) key instead (§ 9a Abs. 2).
    # Kept as heat-or-warm-water; the per-column flags below are what a
    # statement needs, because Block B states an Umlageschlüssel per column.
    consumption_fallback_to_area: bool
    heat_fallback_to_area: bool
    ww_fallback_to_area: bool
    total: Cents
    # The §§ 7/8/9 vertical split, top to bottom. `total` minus the landlord's
    # CO₂ share; equals `total` when there is no CO₂ split.
    billable_cost: Cents
    heating_pot: Cents
    ww_pot: Cents
    heat_base_pot: Cents
    heat_cons_pot: Cents
    ww_base_pot: Cents
    ww_cons_pot: Cents
    # § 7 Abs. 1 HeizkostenV — two distinct facts the page states separately:
    # what was applied, and what the law permits.
    applied_consumption_share: Decimal
    split_bounds: HeatingSplitBounds
    # `None` exactly when there is no central warm water.
    warm_water_separation: WarmWaterSeparation | None
    # The Maßeinheit of the `heat_consumption_weight` Bemessungen — the label on
    # the Gesamtbemessung the renter checks the denominator by. `None` when the
    # heating column fell back to the area key (§ 9a Abs. 2 — no consumption
    # Bemessung was applied, exactly as `heat_consumption_weight` is `None`
    # there) or when any supplied value carried no unit; the statement then
    # withholds the unit rather than guessing one (docs/08 rules 2–4).
    heat_consumption_unit: MeasurementUnit | None


class HeatingInputError(ValueError):
    pass
