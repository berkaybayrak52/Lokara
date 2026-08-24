"""Shared immutable provenance value objects for pure engines."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Stable identity of a source record."""

    source_type: str
    source_id: str


@dataclass(frozen=True, slots=True)
class RuleEvidence:
    """Legal or conventional evidence supplied with a rule bundle."""

    source: str
    register_row: str
    legal_basis: str
    rechtsstand: str
    verification_status: str


@dataclass(frozen=True, slots=True)
class RuleConflict:
    """An unresolved rule conflict that must remain visible to callers."""

    code: str
    description: str
    production_blocking: bool
    applies_to_media: tuple[str, ...] | None = None
