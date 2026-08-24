"""Pure, deterministic evaluators for Page-05 guards W1, W2, and W4."""

from __future__ import annotations

import calendar
from datetime import date

from .models import (
    GuardResult,
    GuardSourceIdentity,
    MeterCalibrationInput,
    MeterCalibrationRuleBundle,
    RuleConflict,
    RuleEvidence,
    StatementDeadlineInput,
    StatementDeadlineRuleBundle,
    UviCadenceInput,
    UviCadenceRuleBundle,
)


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _month_end(value: date) -> date:
    return date(value.year, value.month, calendar.monthrange(value.year, value.month)[1])


def _blocking_conflict_codes(conflicts: tuple[RuleConflict, ...]) -> tuple[str, ...]:
    return tuple(conflict.code for conflict in conflicts if conflict.production_blocking)


def _meter_conflicts(conflicts: tuple[RuleConflict, ...], medium: str) -> tuple[RuleConflict, ...]:
    return tuple(
        conflict
        for conflict in conflicts
        if conflict.applies_to_media is None or medium in conflict.applies_to_media
    )


def _result(
    *,
    guard_code: str,
    source_identity: GuardSourceIdentity,
    stage: str,
    active: bool,
    resolved: bool,
    warning_de: str | None,
    escalation_channels: tuple[str, ...],
    boundary_date: date | None,
    resolution_event: str,
    rule_evidence: tuple[RuleEvidence, ...],
    unresolved_conflicts: tuple[RuleConflict, ...],
    production_blockers: tuple[str, ...],
    validity_years: int | None = None,
    months_until_expiry: int | None = None,
    uvi_guard_active: bool = False,
    retrofit_notice_active: bool = False,
) -> GuardResult:
    return GuardResult(
        guard_code=guard_code,
        source_identity=source_identity,
        stage=stage,
        active=active,
        resolved=resolved,
        warning_de=warning_de,
        escalation_channels=escalation_channels,
        boundary_date=boundary_date,
        resolution_event=resolution_event,
        rule_evidence=rule_evidence,
        unresolved_conflicts=unresolved_conflicts,
        production_blockers=production_blockers,
        validity_years=validity_years,
        months_until_expiry=months_until_expiry,
        uvi_guard_active=uvi_guard_active,
        retrofit_notice_active=retrofit_notice_active,
    )


def evaluate_statement_deadline(
    input_: StatementDeadlineInput, rules: StatementDeadlineRuleBundle
) -> GuardResult:
    """Evaluate the W1 landlord statement deadline without reading ambient state."""

    boundary = _add_months(input_.period_end, rules.months_after_period)
    days = (boundary - input_.today).days
    delivered_on_time = (
        input_.statement_delivered_on is not None and input_.statement_delivered_on <= boundary
    )
    objection_deadline = (
        _add_months(input_.statement_delivered_on, 12)
        if input_.statement_delivered_on is not None
        else None
    )

    if delivered_on_time:
        stage = "resolved"
        active = False
        resolved = True
    elif days < 0:
        stage = "expired"
        active = True
        resolved = False
    elif days == 0:
        stage = "last_day"
        active = True
        resolved = False
    elif days == 30:
        stage = "reminder_30_days"
        active = True
        resolved = False
    elif days == 90:
        stage = "reminder_90_days"
        active = True
        resolved = False
    else:
        stage = "none"
        active = False
        resolved = False

    warning_template = rules.warnings_de.get(stage)
    warning = (
        warning_template.format(
            year=input_.period_end.year,
            boundary_date=boundary.strftime("%d.%m.%Y"),
        )
        if warning_template is not None
        else None
    )
    blockers = list(_blocking_conflict_codes(rules.unresolved_conflicts))
    if active and stage in {"reminder_90_days", "last_day"} and warning is None:
        blockers.append(f"missing_warning_copy:{stage}")

    return GuardResult(
        guard_code="W1",
        source_identity=input_.source_identity,
        stage=stage,
        active=active,
        resolved=resolved,
        warning_de=warning,
        escalation_channels=rules.channels_by_stage.get(stage, ()),
        boundary_date=boundary,
        resolution_event=rules.resolution_event,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
        production_blockers=tuple(blockers),
        days_until_deadline=days,
        renter_objection_deadline=objection_deadline,
        credit_remains_payable=stage == "expired",
    )


def evaluate_meter_calibration(
    input_: MeterCalibrationInput, rules: MeterCalibrationRuleBundle
) -> GuardResult:
    """Evaluate W2 using only the caller's medium table and expiry convention."""

    if input_.medium in rules.excluded_media:
        return _result(
            guard_code="W2",
            source_identity=input_.source_identity,
            stage="excluded",
            active=False,
            resolved=False,
            warning_de=None,
            escalation_channels=(),
            boundary_date=None,
            resolution_event=rules.resolution_event,
            rule_evidence=rules.evidence,
            unresolved_conflicts=(),
            production_blockers=(),
        )

    try:
        validity_years = rules.years_by_medium[input_.medium]
        medium_label = rules.medium_labels_de[input_.medium]
    except KeyError as error:
        raise ValueError(f"unsupported meter medium: {input_.medium}") from error

    if input_.calibration_date is None:
        return _result(
            guard_code="W2",
            source_identity=input_.source_identity,
            stage="missing_calibration_date",
            active=True,
            resolved=False,
            warning_de="Eichdatum erfassen",
            escalation_channels=(),
            boundary_date=None,
            resolution_event=rules.resolution_event,
            rule_evidence=rules.evidence,
            unresolved_conflicts=(),
            production_blockers=(),
            validity_years=validity_years,
        )

    applicable_conflicts = _meter_conflicts(rules.unresolved_conflicts, input_.medium)
    blockers = _blocking_conflict_codes(applicable_conflicts)

    boundary = date(
        input_.calibration_date.year + validity_years,
        rules.expiry_month,
        rules.expiry_day,
    )
    months = (boundary.year - input_.today.year) * 12 + boundary.month - input_.today.month
    if months < 0:
        stage = "exceeded"
        active = True
    elif months == 0:
        stage = "expiry_month"
        active = True
    elif months <= 6:
        stage = "notice"
        active = True
    else:
        stage = "none"
        active = False

    warning = (
        rules.warning_de.format(
            medium_label=medium_label,
            unit_label=input_.unit_label,
            boundary_date=boundary.strftime("%d.%m.%Y"),
        )
        if active
        else None
    )
    return _result(
        guard_code="W2",
        source_identity=input_.source_identity,
        stage=stage,
        active=active,
        resolved=False,
        warning_de=warning,
        escalation_channels=rules.channels_by_stage.get(stage, ()),
        boundary_date=boundary,
        resolution_event=rules.resolution_event,
        rule_evidence=rules.evidence,
        unresolved_conflicts=applicable_conflicts,
        production_blockers=blockers,
        validity_years=validity_years,
        months_until_expiry=months,
    )


def evaluate_uvi_cadence(input_: UviCadenceInput, rules: UviCadenceRuleBundle) -> GuardResult:
    """Evaluate W4 cadence while refusing to invent post-retrofit behavior."""

    blockers = list(_blocking_conflict_codes(rules.unresolved_conflicts))
    if not input_.remote_readable:
        if input_.today <= rules.retrofit_deadline:
            return _result(
                guard_code="W4",
                source_identity=input_.source_identity,
                stage="retrofit_notice",
                active=True,
                resolved=False,
                warning_de=rules.retrofit_warning_de,
                escalation_channels=(),
                boundary_date=rules.retrofit_deadline,
                resolution_event=rules.resolution_event,
                rule_evidence=rules.evidence,
                unresolved_conflicts=rules.unresolved_conflicts,
                production_blockers=tuple(blockers),
                uvi_guard_active=False,
                retrofit_notice_active=True,
            )
        blockers.append("missing_post_retrofit_rule")
        return _result(
            guard_code="W4",
            source_identity=input_.source_identity,
            stage="source_missing",
            active=False,
            resolved=False,
            warning_de=None,
            escalation_channels=(),
            boundary_date=None,
            resolution_event=rules.resolution_event,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            production_blockers=tuple(blockers),
        )

    cadence_source = input_.last_uvi_sent_on or input_.start_month
    if cadence_source is None:
        blockers.append("missing_uvi_cadence_start")
        return _result(
            guard_code="W4",
            source_identity=input_.source_identity,
            stage="source_missing",
            active=False,
            resolved=False,
            warning_de=None,
            escalation_channels=(),
            boundary_date=None,
            resolution_event=rules.resolution_event,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            production_blockers=tuple(blockers),
            uvi_guard_active=True,
        )

    boundary = _month_end(_add_months(cadence_source, 1))
    if input_.uvi_sent_in_current_month:
        stage = "resolved"
        active = False
        resolved = True
    elif input_.today > boundary:
        stage = "overdue"
        active = True
        resolved = False
    elif input_.today == boundary:
        stage = "due"
        active = True
        resolved = False
    else:
        stage = "not_due"
        active = False
        resolved = False

    warning = (
        rules.warning_de.format(
            unit_label=input_.unit_label,
            month_label=boundary.strftime("%m/%Y"),
        )
        if active
        else None
    )
    return _result(
        guard_code="W4",
        source_identity=input_.source_identity,
        stage=stage,
        active=active,
        resolved=resolved,
        warning_de=warning,
        escalation_channels=rules.channels_by_stage.get(stage, ()),
        boundary_date=boundary,
        resolution_event=rules.resolution_event,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
        production_blockers=tuple(blockers),
        uvi_guard_active=True,
        retrofit_notice_active=False,
    )
