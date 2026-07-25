"""Meter value objects — shared by the meter adapter, the DB and the API.

They live in `domain` (not in the adapter) for the reason docs/04 gives for
every normalized value object: **manual entry, MDL import and radio self-read
must produce the same model**, and the persistence layer must be able to store
that model without depending on the adapter package.

Two orthogonal facts about a meter that are easy to conflate:

- ``MeterKind`` — *what medium* it measures (Wärme / Warmwasser / Kaltwasser).
- ``MeasurementUnit`` — *in which unit* it counts. A building's Wärmemengenzähler
  counts kWh, while the Heizkostenverteiler in each flat counts dimensionless
  HKV-Einheiten. Both are ``HEAT``; only the unit tells them apart, and only the
  kWh one may serve as the § 9 HeizkostenV energy denominator.

``ReadingReason`` is the HeiWaKo *Ablesegrund*. It matters legally (a
Nutzerwechsel reading splits a period) and operationally: readings are
**create-only**, so a fix is a new row with ``CORRECTION`` — never an UPDATE.
"""

from enum import StrEnum


class MeterKind(StrEnum):
    HEAT = "HEAT"
    WARM_WATER = "WARM_WATER"
    COLD_WATER = "COLD_WATER"


class MeasurementUnit(StrEnum):
    KWH = "KWH"  # Wärmemengenzähler — the § 9 energy denominator
    CUBIC_METRE = "CUBIC_METRE"  # Wasserzähler
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
# Cold/warm water are always m³; heat is kWh at the building meter and
# HKV_UNITS at the flat allocators, so it has no single default.
CANONICAL_UNITS: dict[MeterKind, MeasurementUnit] = {
    MeterKind.WARM_WATER: MeasurementUnit.CUBIC_METRE,
    MeterKind.COLD_WATER: MeasurementUnit.CUBIC_METRE,
}
