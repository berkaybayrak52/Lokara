"""Meter value objects — shared by the meter adapter, the DB and the API.

They live in `domain` (not in the adapter) for the reason docs/04 gives for
every normalized value object: **manual entry, MDL import and radio self-read
must produce the same model**, and the persistence layer must be able to store
that model without depending on the adapter package.

Two orthogonal facts about a meter that are easy to conflate:

- ``MeterKind`` — *what medium* it measures (Wärme / Warmwasser / Kaltwasser).
- ``MeasurementUnit`` — *in which unit* it counts. A building's Wärmemengenzähler
  counts kWh, while the Heizkostenverteiler in each flat counts dimensionless
  HKV-Einheiten. A gas meter also measures ``HEAT`` but counts m³. Only the
  approved device-type facts distinguish those combinations, and only the kWh
  heat meter may serve as the § 9 HeizkostenV energy denominator.

``ReadingReason`` is the HeiWaKo *Ablesegrund*. It matters legally (a
Nutzerwechsel reading splits a period) and operationally: readings are
**create-only**, so a fix is a new row with ``CORRECTION`` — never an UPDATE.
"""

from enum import StrEnum


class MeterKind(StrEnum):
    HEAT = "HEAT"
    WARM_WATER = "WARM_WATER"
    COLD_WATER = "COLD_WATER"


class MeterDeviceType(StrEnum):
    """The concrete device, separate from medium and measurement unit."""

    HEAT_METER = "HEAT_METER"
    HEAT_COST_ALLOCATOR = "HEAT_COST_ALLOCATOR"
    WARM_WATER_METER = "WARM_WATER_METER"
    COLD_WATER_METER = "COLD_WATER_METER"
    GAS_METER = "GAS_METER"


class RemoteReadability(StrEnum):
    REMOTE_READABLE = "REMOTE_READABLE"
    NOT_REMOTE_READABLE = "NOT_REMOTE_READABLE"
    UNKNOWN = "UNKNOWN"


class CalibrationDataState(StrEnum):
    DATA_AVAILABLE = "DATA_AVAILABLE"
    MISSING_DATA = "MISSING_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class MeterLifecycleEventType(StrEnum):
    INSTALLED = "INSTALLED"
    REMOVED = "REMOVED"
    REPLACED = "REPLACED"
    VOID = "VOID"


class HeatingBillingMode(StrEnum):
    LOKARA = "LOKARA"
    EXTERNAL_PROVIDER = "EXTERNAL_PROVIDER"


class ExternalHeatingStatus(StrEnum):
    BEAUFTRAGT = "BEAUFTRAGT"
    DATEN_UEBERMITTELT = "DATEN_UEBERMITTELT"
    ABRECHNUNG_ERHALTEN = "ABRECHNUNG_ERHALTEN"
    GEPRUEFT = "GEPRUEFT"
    UEBERNOMMEN = "UEBERNOMMEN"


class HeatingCostCategory(StrEnum):
    FUEL_OR_HEAT_SUPPLY = "FUEL_OR_HEAT_SUPPLY"
    OPERATING_ELECTRICITY = "OPERATING_ELECTRICITY"
    MAINTENANCE = "MAINTENANCE"
    METERING_SERVICE = "METERING_SERVICE"
    OTHER_ALLOWED = "OTHER_ALLOWED"


class MeasurementUnit(StrEnum):
    KWH = "KWH"  # Wärmemengenzähler — the § 9 energy denominator
    CUBIC_METRE = "CUBIC_METRE"  # Wasserzähler or Erdgas volume meter
    HKV_UNITS = "HKV_UNITS"  # Heizkostenverteiler — dimensionless Einheiten


class ReadingReason(StrEnum):
    """Ablesegrund. CORRECTION is how an append-only log fixes a typo."""

    PERIODIC = "PERIODIC"  # Turnusablesung (period start/end)
    INTERIM = "INTERIM"  # Zwischenablesung
    TENANT_CHANGE = "TENANT_CHANGE"  # Nutzerwechselablesung
    DEVICE_CHANGE = "DEVICE_CHANGE"  # Gerätewechsel
    CORRECTION = "CORRECTION"  # supersedes an earlier reading of the same date


class ReadingSource(StrEnum):
    MANUAL = "MANUAL"
    MDL = "MDL"  # Messdienstleister (HeiWaKo exchange)
    RADIO = "RADIO"  # Funk-Selbstablesung


# Which unit each medium is counted in when it is *not* an HKV allocator.
# Cold/warm water are always m³. Heat may be kWh, gas m³ or HKV_UNITS, so it
# has no single default and must be resolved through the concrete device type.
CANONICAL_UNITS: dict[MeterKind, MeasurementUnit] = {
    MeterKind.WARM_WATER: MeasurementUnit.CUBIC_METRE,
    MeterKind.COLD_WATER: MeasurementUnit.CUBIC_METRE,
}


DEVICE_TYPE_FACTS: dict[MeterDeviceType, tuple[MeterKind, MeasurementUnit]] = {
    MeterDeviceType.HEAT_METER: (MeterKind.HEAT, MeasurementUnit.KWH),
    MeterDeviceType.HEAT_COST_ALLOCATOR: (MeterKind.HEAT, MeasurementUnit.HKV_UNITS),
    MeterDeviceType.WARM_WATER_METER: (MeterKind.WARM_WATER, MeasurementUnit.CUBIC_METRE),
    MeterDeviceType.COLD_WATER_METER: (MeterKind.COLD_WATER, MeasurementUnit.CUBIC_METRE),
    MeterDeviceType.GAS_METER: (MeterKind.HEAT, MeasurementUnit.CUBIC_METRE),
}
