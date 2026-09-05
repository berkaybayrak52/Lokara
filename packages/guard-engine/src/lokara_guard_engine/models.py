"""Immutable inputs, caller-supplied rules, and results for the guard engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


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
    legacy_years_by_medium: Mapping[str, int]
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
class PaymentDueEntry:
    due_date: date
    amount_cents: int


@dataclass(frozen=True, slots=True)
class PaymentEntry:
    payment_date: date
    amount_cents: int


@dataclass(frozen=True, slots=True)
class PaymentArrearsInput:
    source_identity: GuardSourceIdentity
    today: date
    gross_monthly_rent_cents: int
    due_entries: tuple[PaymentDueEntry, ...]
    payments: tuple[PaymentEntry, ...]
    renter_label: str


@dataclass(frozen=True, slots=True)
class PaymentArrearsRuleBundle:
    evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
    warning_3a_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class ComparativeRentIncreaseInput:
    source_identity: GuardSourceIdentity
    today: date
    net_cold_rent_cents: int
    base_rent_3y_cents: int
    last_increase_effective_on: date
    comparative_rent_cents: int | None
    tight_market: bool
    request_received_on: date | None
    unit_label: str


@dataclass(frozen=True, slots=True)
class ComparativeRentIncreaseRuleBundle:
    evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
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
class GraduatedRentStep:
    effective_on: date
    amount_cents: int


@dataclass(frozen=True, slots=True)
class GraduatedRentInput:
    source_identity: GuardSourceIdentity
    today: date
    schedule: tuple[GraduatedRentStep, ...]
    current_target_rent_cents: int
    unit_label: str


@dataclass(frozen=True, slots=True)
class GraduatedRentRuleBundle:
    evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
    minimum_interval_months: int
    warning_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class VpiSnapshot:
    value: Decimal
    basis_year: int
    reference_month: date
    status: str
    source: str
    captured_at: datetime


@dataclass(frozen=True, slots=True)
class IndexRentInput:
    source_identity: GuardSourceIdentity
    today: date
    net_cold_rent_cents: int
    base_index: VpiSnapshot
    new_index: VpiSnapshot
    last_adjustment_on: date


@dataclass(frozen=True, slots=True)
class IndexRentRuleBundle:
    evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
    minimum_interval_months: int
    rebasing_warning_de: str
    warning_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class VacancyInput:
    source_identity: GuardSourceIdentity
    today: date
    last_tenancy_ended_on: date
    active_tenancy: bool
    target_rent_cents: int
    unit_label: str


@dataclass(frozen=True, slots=True)
class VacancyRuleBundle:
    evidence: tuple[RuleEvidence, ...]
    unresolved_conflicts: tuple[RuleConflict, ...]
    threshold_days: int
    rent_period_days: int
    warning_de: str
    channels_by_stage: Mapping[str, tuple[str, ...]]
    resolution_event: str


@dataclass(frozen=True, slots=True)
class PaymentArrearsResult:
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
    arrears_cents: int
    consecutive_open_dates: int
    threshold_3a_cents: int
    threshold_3b_cents: int
    triggers_3a: bool
    triggers_3b: bool


@dataclass(frozen=True, slots=True)
class ComparativeRentIncreaseResult:
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
    cap_rate: Decimal
    cap_ceiling_cents: int
    maximum_new_rent_cents: int
    maximum_increase_cents: int
    mode: str
    limiting_rule: str
    legality_confirmed: bool
    earliest_declaration_on: date
    earliest_effective_on: date
    consent_deadline: date | None
    effective_on: date | None
    action_deadline: date | None


@dataclass(frozen=True, slots=True)
class GraduatedRentResult:
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
    valid: bool
    validation_errors: tuple[str, ...]
    active_step_cents: int | None
    adjustment_due: bool


@dataclass(frozen=True, slots=True)
class IndexRentResult:
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
    base_index: VpiSnapshot
    new_index: VpiSnapshot
    elapsed_months: int
    factor: Decimal | None
    new_rent_cents: int | None
    increase_cents: int | None
    delta_percent_display: Decimal | None


@dataclass(frozen=True, slots=True)
class VacancyResult:
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
    vacancy_days: int | None
    lost_rent_cents: int | None


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
