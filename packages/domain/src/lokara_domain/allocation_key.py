"""Allocation keys (Umlageschlüssel) — mirrors the DB enum (docs/02)."""

import enum


class AllocationKey(enum.Enum):
    AREA = "AREA"  # Fläche
    PERSONS = "PERSONS"  # Personen
    CONSUMPTION = "CONSUMPTION"  # Verbrauch (metered)
    UNITS = "UNITS"  # Einheiten
    DIRECT = "DIRECT"  # Direktzuordnung — cost to exactly one unit/tenancy
    MEA = "MEA"  # Miteigentumsanteil (WEG)
