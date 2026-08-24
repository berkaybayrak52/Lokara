"""Immutable inputs, caller-supplied rules, and results for the guard engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class GuardSourceIdentity:
    """Stable identity of the record a guard evaluates."""

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


@dataclass(frozen=True, slots=True)
class StatementDeadlineInput:
    source_identity: GuardSourceIdentity
    today: date
    period_end: date
    statement_delivered_on: date | None


@dataclass(frozen=True, slots=True)
class StatementDeadlineRuleBundle:
    evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
    months_after_period: int
    warnings_de: Mapping[str, str]
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class MeterCalibrationInput:
    source_identity: GuardSourceIdentity
    today: date
    calibration_date: date | None
    medium: str
    unit_label: str


@dataclass(frozen=True, slots=True)
class MeterCalibrationRuleBundle:
    evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
    years_by_medium: Mapping[str, int]
    medium_labels_de: Mapping[str, str]
    excluded_media: tuple[str, ...]
    expiry_month: int
    expiry_day: int
    warning_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class UviCadenceInput:
    source_identity: GuardSourceIdentity
    today: date
    remote_readable: bool
    last_uvi_sent_on: date | None
    start_month: date | None
    uvi_sent_in_current_month: bool
    unit_label: str


@dataclass(frozen=True, slots=True)
class UviCadenceRuleBundle:
    evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
    retrofit_deadline: date
    warning_de: str
    retrofit_warning_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class GuardResult:
    """Common guard result plus the bounded W1, W2, and W4 details."""

    guard_code: str
    source_identity: GuardSourceIdentity
    stage: str
    active: bool
    resolved: bool
    warning_de: str | None
    escalation_channels: tuple[str, ...]
    boundary_date: date | None
    resolution_event: str
    rule_evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
    production_blockers: tuple[str, ...]
    days_until_deadline: int | None = None
    renter_objection_deadline: date | None = None
    credit_remains_payable: bool = False
    validity_years: int | None = None
    months_until_expiry: int | None = None
    uvi_guard_active: bool = False
    retrofit_notice_active: bool = False
