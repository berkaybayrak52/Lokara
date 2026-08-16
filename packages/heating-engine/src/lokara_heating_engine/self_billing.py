"""Pure normalized capabilities for the Page 01b self-billing path."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from lokara_domain import Cents, cents, distribute_cents_half_up

from .inputs import HeatingInputError

CostPositionKind = Literal[
    "fuel",
    "district_heat",
    "operating_electricity",
    "maintenance",
    "measurement",
    "equipment",
    "other",
]
WarmWaterCostMethod = Literal[
    "measured_energy",
    "volume_formula",
    "area_fallback",
    "not_connected",
]

_COST_POSITION_KINDS = frozenset(
    {
        "fuel",
        "district_heat",
        "operating_electricity",
        "maintenance",
        "measurement",
        "equipment",
        "other",
    }
)
_COMPLEMENT = 1
_ONE_CENT = Decimal(1)
_THREE_DECIMALS = Decimal("0.001")
_TWO_DECIMALS = Decimal("0.01")
_ZERO = cents(0)


@dataclass(frozen=True)
class HeatingCostPosition:
    kind: CostPositionKind
    amount: Cents


@dataclass(frozen=True)
class DistrictHeatDisclosure:
    energy_mix: str
    greenhouse_gas_g_per_kwh: Decimal
    primary_energy_factor: Decimal
    taxes: Cents


@dataclass(frozen=True)
class PlantCostAggregation:
    positions: tuple[HeatingCostPosition, ...]
    total_cost: Cents
    district_heat_disclosure: DistrictHeatDisclosure | None


@dataclass(frozen=True)
class CapabilityWarning:
    code: str
    blocking: bool
    dismissible: bool


@dataclass(frozen=True)
class InvoiceAllocation:
    invoice_days: int
    overlap_days: int
    allocated_amount: Cents
    coverage_ratio: Decimal
    coverage_percent: Decimal
    missing_days: int
    warning: CapabilityWarning | None


@dataclass(frozen=True)
class OilPurchase:
    litres: Decimal
    cost: Cents


@dataclass(frozen=True)
class OilStockInput:
    opening_litres: Decimal
    opening_cost: Cents
    purchases: tuple[OilPurchase, ...]
    closing_litres: Decimal


@dataclass(frozen=True)
class OilConsumptionResult:
    available_litres: Decimal
    available_cost: Cents
    consumed_litres: Decimal
    weighted_cost_per_litre: Decimal
    fuel_cost: Cents
    closing_stock_cost: Cents
    energy_kwh: Decimal
    co2_grams: int
    co2_cost: None = None


@dataclass(frozen=True)
class WarmWaterCostSeparation:
    method: WarmWaterCostMethod
    q_ww_kwh: Decimal
    warm_water_cost: Cents
    heating_cost: Cents
    warnings: tuple[CapabilityWarning, ...]


@dataclass(frozen=True)
class HeatingCostBlocks:
    heating_base: Cents
    heating_consumption: Cents
    warm_water_base: Cents
    warm_water_consumption: Cents
    total: Cents


@dataclass(frozen=True)
class OwnerBurdenPreview:
    current_owner_total: Cents
    proposed_owner_total: Cents
    change: Cents
    increases_owner_burden: bool
    show_before_save: bool


def _require_cents(value: Cents, *, field: str, non_negative: bool = True) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HeatingInputError(f"{field} muss als ganze Centzahl angegeben sein")
    if non_negative and value < 0:
        raise HeatingInputError(f"{field} darf nicht negativ sein")


def _require_decimal(
    value: Decimal, *, field: str, positive: bool = False, non_negative: bool = True
) -> None:
    if not value.is_finite():
        raise HeatingInputError(f"{field} muss endlich sein")
    if positive and value <= 0:
        raise HeatingInputError(f"{field} muss größer als null sein")
    if non_negative and value < 0:
        raise HeatingInputError(f"{field} darf nicht negativ sein")


def _round_cents(value: Decimal) -> Cents:
    return cents(int(value.quantize(_ONE_CENT, rounding=ROUND_HALF_UP)))


def aggregate_plant_cost_positions(
    *,
    positions: tuple[HeatingCostPosition, ...],
    district_heat_disclosure: DistrictHeatDisclosure | None,
) -> PlantCostAggregation:
    if not positions:
        raise HeatingInputError("Mindestens eine Kostenposition ist erforderlich")
    has_district_heat = False
    for position in positions:
        if position.kind not in _COST_POSITION_KINDS:
            raise HeatingInputError(f"Unbekannte Heizkostenposition: {position.kind}")
        _require_cents(position.amount, field=f"Betrag der Position {position.kind}")
        has_district_heat = has_district_heat or position.kind == "district_heat"
    if has_district_heat and district_heat_disclosure is None:
        raise HeatingInputError("Pflichtangaben des Fernwärmeversorgers fehlen")
    if not has_district_heat and district_heat_disclosure is not None:
        raise HeatingInputError("Fernwärmeangaben sind ohne Fernwärmeposition nicht zulässig")
    if district_heat_disclosure is not None:
        if not district_heat_disclosure.energy_mix:
            raise HeatingInputError("Energiemix des Fernwärmeversorgers fehlt")
        _require_decimal(
            district_heat_disclosure.greenhouse_gas_g_per_kwh,
            field="Treibhausgasemissionen des Fernwärmeversorgers",
        )
        _require_decimal(
            district_heat_disclosure.primary_energy_factor,
            field="Primärenergiefaktor des Fernwärmeversorgers",
        )
        _require_cents(district_heat_disclosure.taxes, field="Fernwärmesteuern")
    return PlantCostAggregation(
        positions=positions,
        total_cost=cents(sum(int(position.amount) for position in positions)),
        district_heat_disclosure=district_heat_disclosure,
    )


def allocate_invoice_to_billing_period(
    *,
    amount: Cents,
    invoice_from: date,
    invoice_to: date,
    billing_from: date,
    billing_to: date,
) -> InvoiceAllocation:
    _require_cents(amount, field="Rechnungsbetrag")
    if invoice_to < invoice_from:
        raise HeatingInputError("Rechnungsende liegt vor dem Rechnungsbeginn")
    if billing_to < billing_from:
        raise HeatingInputError("Abrechnungsende liegt vor dem Abrechnungsbeginn")

    invoice_days = (invoice_to - invoice_from).days + 1
    billing_days = (billing_to - billing_from).days + 1
    overlap_from = max(invoice_from, billing_from)
    overlap_to = min(invoice_to, billing_to)
    overlap_days = max(0, (overlap_to - overlap_from).days + 1)
    allocated_amount = _round_cents(Decimal(amount) * Decimal(overlap_days) / Decimal(invoice_days))
    coverage_ratio = Decimal(overlap_days) / Decimal(billing_days)
    missing_days = billing_days - overlap_days
    warning = (
        None
        if missing_days == 0
        else CapabilityWarning(
            code="invoice_period_incomplete",
            blocking=False,
            dismissible=False,
        )
    )
    return InvoiceAllocation(
        invoice_days=invoice_days,
        overlap_days=overlap_days,
        allocated_amount=allocated_amount,
        coverage_ratio=coverage_ratio,
        coverage_percent=(coverage_ratio * Decimal(100)).quantize(
            _TWO_DECIMALS, rounding=ROUND_HALF_UP
        ),
        missing_days=missing_days,
        warning=warning,
    )


def calculate_oil_consumption(
    *,
    stock: OilStockInput,
    heating_value_kwh_per_litre: Decimal,
    emission_factor_kg_per_kwh: Decimal,
) -> OilConsumptionResult:
    _require_decimal(stock.opening_litres, field="Heizöl-Anfangsbestand")
    _require_cents(stock.opening_cost, field="Wert des Heizöl-Anfangsbestands")
    for purchase in stock.purchases:
        _require_decimal(purchase.litres, field="Heizöl-Zukauf", positive=True)
        _require_cents(purchase.cost, field="Heizöl-Zukaufskosten")
    _require_decimal(stock.closing_litres, field="Heizöl-Endbestand")
    _require_decimal(
        heating_value_kwh_per_litre,
        field="Heizwert je Liter",
        positive=True,
    )
    _require_decimal(
        emission_factor_kg_per_kwh,
        field="Emissionsfaktor",
    )

    available_litres = stock.opening_litres + sum(
        (purchase.litres for purchase in stock.purchases), Decimal(0)
    )
    if available_litres <= 0:
        raise HeatingInputError("Der verfügbare Heizölbestand muss größer als null sein")
    if stock.closing_litres > available_litres:
        raise HeatingInputError("Heizöl-Endbestand übersteigt den verfügbaren Bestand")
    available_cost = cents(
        int(stock.opening_cost) + sum(int(purchase.cost) for purchase in stock.purchases)
    )
    consumed_litres = available_litres - stock.closing_litres
    weighted_cost_per_litre = Decimal(available_cost) / available_litres
    fuel_cost = _round_cents(weighted_cost_per_litre * consumed_litres)
    closing_stock_cost = cents(int(available_cost) - int(fuel_cost))
    energy_kwh = consumed_litres * heating_value_kwh_per_litre
    co2_grams = int(
        (energy_kwh * emission_factor_kg_per_kwh * Decimal(1000)).quantize(
            _ONE_CENT, rounding=ROUND_HALF_UP
        )
    )
    return OilConsumptionResult(
        available_litres=available_litres,
        available_cost=available_cost,
        consumed_litres=consumed_litres,
        weighted_cost_per_litre=weighted_cost_per_litre,
        fuel_cost=fuel_cost,
        closing_stock_cost=closing_stock_cost,
        energy_kwh=energy_kwh,
        co2_grams=co2_grams,
    )


def separate_warm_water_costs(
    *,
    connected_plant: bool,
    billable_cost: Cents,
    total_energy_kwh: Decimal,
    measured_ww_energy_kwh: Decimal | None,
    central_ww_volume_m3: Decimal | None,
    hot_water_temperature_c: Decimal,
    heated_area_sqm: Decimal,
    volume_factor: Decimal,
    cold_water_temperature_c: Decimal,
    area_fallback_kwh_per_sqm: Decimal,
) -> WarmWaterCostSeparation:
    _require_cents(billable_cost, field="Umlagefähige Kosten")
    if not connected_plant:
        return WarmWaterCostSeparation(
            method="not_connected",
            q_ww_kwh=Decimal("0.000"),
            warm_water_cost=_ZERO,
            heating_cost=billable_cost,
            warnings=(),
        )

    _require_decimal(total_energy_kwh, field="Gesamtenergie", positive=True)
    warnings: tuple[CapabilityWarning, ...] = ()
    method: WarmWaterCostMethod
    if measured_ww_energy_kwh is not None:
        _require_decimal(
            measured_ww_energy_kwh,
            field="Gemessene Warmwasserenergie",
            positive=True,
        )
        q_ww_kwh = measured_ww_energy_kwh
        method = "measured_energy"
    elif central_ww_volume_m3 is not None:
        _require_decimal(
            central_ww_volume_m3,
            field="Zentrales Warmwasservolumen",
            positive=True,
        )
        _require_decimal(volume_factor, field="Warmwasserfaktor", positive=True)
        if not hot_water_temperature_c.is_finite() or not cold_water_temperature_c.is_finite():
            raise HeatingInputError("Warmwassertemperaturen müssen endlich sein")
        if hot_water_temperature_c <= cold_water_temperature_c:
            raise HeatingInputError(
                "Warmwassertemperatur muss über der Kaltwassertemperatur liegen"
            )
        q_ww_kwh = (
            volume_factor
            * central_ww_volume_m3
            * (hot_water_temperature_c - cold_water_temperature_c)
        )
        method = "volume_formula"
    else:
        _require_decimal(heated_area_sqm, field="Beheizte Fläche", positive=True)
        _require_decimal(
            area_fallback_kwh_per_sqm,
            field="Warmwasser-Ersatzwert je Quadratmeter",
            positive=True,
        )
        q_ww_kwh = area_fallback_kwh_per_sqm * heated_area_sqm
        method = "area_fallback"
        warnings = (
            CapabilityWarning(
                code="ww_area_fallback",
                blocking=False,
                dismissible=False,
            ),
        )
    q_ww_kwh = q_ww_kwh.quantize(_THREE_DECIMALS, rounding=ROUND_HALF_UP)
    if q_ww_kwh >= total_energy_kwh:
        raise HeatingInputError("Warmwasserenergie muss unter der Gesamtenergie liegen")
    warm_water_cost, heating_cost = distribute_cents_half_up(
        billable_cost,
        [q_ww_kwh, total_energy_kwh - q_ww_kwh],
        residual_index=_COMPLEMENT,
    )
    return WarmWaterCostSeparation(
        method=method,
        q_ww_kwh=q_ww_kwh,
        warm_water_cost=warm_water_cost,
        heating_cost=heating_cost,
        warnings=warnings,
    )


def form_heating_cost_blocks(
    *,
    heating_cost: Cents,
    warm_water_cost: Cents,
    base_share_percent: Decimal | int,
) -> HeatingCostBlocks:
    _require_cents(heating_cost, field="Heizkosten")
    _require_cents(warm_water_cost, field="Warmwasserkosten")
    share = (
        base_share_percent
        if isinstance(base_share_percent, Decimal)
        else Decimal(base_share_percent)
    )
    if not share.is_finite() or not Decimal(30) <= share <= Decimal(50):
        raise HeatingInputError("Grundkostenanteil muss zwischen 30 und 50 Prozent liegen")
    heating_base, heating_consumption = distribute_cents_half_up(
        heating_cost,
        [share, Decimal(100) - share],
        residual_index=_COMPLEMENT,
    )
    warm_water_base, warm_water_consumption = distribute_cents_half_up(
        warm_water_cost,
        [share, Decimal(100) - share],
        residual_index=_COMPLEMENT,
    )
    return HeatingCostBlocks(
        heating_base=heating_base,
        heating_consumption=heating_consumption,
        warm_water_base=warm_water_base,
        warm_water_consumption=warm_water_consumption,
        total=cents(int(heating_cost) + int(warm_water_cost)),
    )


def calculate_owner_burden_preview(
    *, current_owner_total: Cents, proposed_owner_total: Cents
) -> OwnerBurdenPreview:
    _require_cents(current_owner_total, field="Aktueller Eigentümeranteil", non_negative=False)
    _require_cents(
        proposed_owner_total,
        field="Vorgeschlagener Eigentümeranteil",
        non_negative=False,
    )
    change = cents(int(proposed_owner_total) - int(current_owner_total))
    return OwnerBurdenPreview(
        current_owner_total=current_owner_total,
        proposed_owner_total=proposed_owner_total,
        change=change,
        increases_owner_burden=change > 0,
        show_before_save=True,
    )
