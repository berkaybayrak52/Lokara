"""Pure, deterministic evaluators for Page-05 guards W1, W2, and W4."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise

from .models import (
    ComparativeRentIncreaseInput,
    ComparativeRentIncreaseResult,
    ComparativeRentIncreaseRuleBundle,
    GraduatedRentInput,
    GraduatedRentResult,
    GraduatedRentRuleBundle,
    GuardResult,
    GuardSourceIdentity,
    IndexRentInput,
    IndexRentResult,
    IndexRentRuleBundle,
    MeterCalibrationInput,
    MeterCalibrationRuleBundle,
    PaymentArrearsInput,
    PaymentArrearsResult,
    PaymentArrearsRuleBundle,
    RuleConflict,
    RuleEvidence,
    StatementDeadlineInput,
    StatementDeadlineRuleBundle,
    UviCadenceInput,
    UviCadenceRuleBundle,
    VacancyInput,
    VacancyResult,
    VacancyRuleBundle,
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


def _round_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _format_euros(cents: int) -> str:
    euros = Decimal(cents) / Decimal(100)
    raw = f"{euros:,.2f}"
    return raw.replace(",", "_").replace(".", ",").replace("_", ".")


def _elapsed_months(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + end.month - start.month
    return months - (1 if end.day < start.day else 0)


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


def evaluate_payment_arrears(
    input_: PaymentArrearsInput, rules: PaymentArrearsRuleBundle
) -> PaymentArrearsResult:
    """Evaluate W3 after applying received payments to the oldest due entries."""

    if input_.gross_monthly_rent_cents <= 0:
        raise ValueError("gross_monthly_rent_cents must be positive")
    due_amounts = [
        entry.amount_cents
        for entry in sorted(input_.due_entries, key=lambda entry: entry.due_date)
        if entry.due_date <= input_.today
    ]
    if any(amount < 0 for amount in due_amounts):
        raise ValueError("due amounts must not be negative")
    received_payments = tuple(
        payment.amount_cents for payment in input_.payments if payment.payment_date <= input_.today
    )
    if any(amount < 0 for amount in received_payments):
        raise ValueError("payment amounts must not be negative")
    payments = sum(received_payments)
    remaining_payment = payments
    open_amounts: list[int] = []
    for amount in due_amounts:
        applied = min(amount, remaining_payment)
        open_amounts.append(amount - applied)
        remaining_payment -= applied

    arrears = sum(open_amounts)
    consecutive_open_dates = sum(amount > 0 for amount in open_amounts)
    threshold_3a = input_.gross_monthly_rent_cents
    threshold_3b = 2 * input_.gross_monthly_rent_cents
    triggers_3b = consecutive_open_dates > 2 and arrears >= threshold_3b
    triggers_3a = consecutive_open_dates >= 2 and arrears > threshold_3a
    if triggers_3b:
        stage = "3b"
    elif triggers_3a:
        stage = "3a"
    elif arrears > 0:
        stage = "info"
    else:
        stage = "resolved"

    warning = None
    if triggers_3a:
        warning = rules.warning_3a_de.format(
            renter_label=input_.renter_label,
            arrears=_format_euros(arrears),
        )
    return PaymentArrearsResult(
        guard_code="W3",
        source_identity=input_.source_identity,
        stage=stage,
        active=arrears > 0,
        resolved=arrears == 0,
        warning_de=warning,
        escalation_channels=rules.channels_by_stage.get(stage, ()),
        boundary_date=None,
        resolution_event=rules.resolution_event,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
        production_blockers=_blocking_conflict_codes(rules.unresolved_conflicts),
        arrears_cents=arrears,
        consecutive_open_dates=consecutive_open_dates,
        threshold_3a_cents=threshold_3a,
        threshold_3b_cents=threshold_3b,
        triggers_3a=triggers_3a,
        triggers_3b=triggers_3b,
    )


def evaluate_comparative_rent_increase(
    input_: ComparativeRentIncreaseInput, rules: ComparativeRentIncreaseRuleBundle
) -> ComparativeRentIncreaseResult:
    """Evaluate W5 with caller-supplied market classification and comparative rent."""

    rent_amounts = (
        input_.net_cold_rent_cents,
        input_.base_rent_3y_cents,
        *(item for item in (input_.comparative_rent_cents,) if item is not None),
    )
    if min(rent_amounts) < 0:
        raise ValueError("rent amounts must not be negative")
    cap_rate = rules.tight_market_cap_rate if input_.tight_market else rules.normal_cap_rate
    cap_ceiling = _round_cents(Decimal(input_.base_rent_3y_cents) * (Decimal(1) + cap_rate))
    if input_.comparative_rent_cents is None:
        maximum_new_rent = cap_ceiling
        mode = "cap_only"
        limiting_rule = "cap"
        legality_confirmed = False
        warning_template = rules.warning_cap_only_de
    else:
        maximum_new_rent = min(cap_ceiling, input_.comparative_rent_cents)
        mode = "full_check"
        limiting_rule = "comparative_rent" if input_.comparative_rent_cents < cap_ceiling else "cap"
        legality_confirmed = False
        warning_template = rules.warning_full_check_de
    maximum_increase = max(0, maximum_new_rent - input_.net_cold_rent_cents)
    earliest_declaration = _add_months(
        input_.last_increase_effective_on, rules.declaration_wait_months
    )
    earliest_effective = _add_months(input_.last_increase_effective_on, rules.effective_wait_months)
    active = input_.today >= earliest_declaration and maximum_increase > 0
    stage = (
        "opportunity" if active else ("no_increase" if maximum_increase == 0 else "waiting_period")
    )

    consent_deadline: date | None = None
    effective_on: date | None = None
    action_deadline: date | None = None
    if input_.request_received_on is not None:
        consent_deadline = _month_end(_add_months(input_.request_received_on, rules.consent_months))
        effective_month = _add_months(
            input_.request_received_on, rules.effective_after_request_months
        )
        effective_on = date(effective_month.year, effective_month.month, 1)
        action_deadline = _add_months(consent_deadline, rules.action_months_after_consent_deadline)

    warning = None
    if active:
        warning = warning_template.format(
            unit_label=input_.unit_label,
            maximum_increase=_format_euros(maximum_increase),
            maximum_new_rent=_format_euros(maximum_new_rent),
            limiting_rule=(
                "ortsübliche Vergleichsmiete"
                if limiting_rule == "comparative_rent"
                else "Kappungsgrenze"
            ),
        )
    return ComparativeRentIncreaseResult(
        guard_code="W5",
        source_identity=input_.source_identity,
        stage=stage,
        active=active,
        resolved=False,
        warning_de=warning,
        escalation_channels=rules.channels_by_stage.get(stage, ()),
        boundary_date=action_deadline or earliest_declaration,
        resolution_event=rules.resolution_event,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
        production_blockers=_blocking_conflict_codes(rules.unresolved_conflicts),
        cap_rate=cap_rate,
        cap_ceiling_cents=cap_ceiling,
        maximum_new_rent_cents=maximum_new_rent,
        maximum_increase_cents=maximum_increase,
        mode=mode,
        limiting_rule=limiting_rule,
        legality_confirmed=legality_confirmed,
        earliest_declaration_on=earliest_declaration,
        earliest_effective_on=earliest_effective,
        consent_deadline=consent_deadline,
        effective_on=effective_on,
        action_deadline=action_deadline,
    )


def evaluate_graduated_rent(
    input_: GraduatedRentInput, rules: GraduatedRentRuleBundle
) -> GraduatedRentResult:
    """Evaluate W6 and refuse schedules with intervals below the supplied minimum."""

    schedule = tuple(sorted(input_.schedule, key=lambda step: step.effective_on))
    invalid_interval = any(
        current.effective_on < _add_months(previous.effective_on, rules.minimum_interval_months)
        for previous, current in pairwise(schedule)
    )
    if invalid_interval:
        return GraduatedRentResult(
            guard_code="W6",
            source_identity=input_.source_identity,
            stage="invalid",
            active=False,
            resolved=False,
            warning_de=None,
            escalation_channels=(),
            boundary_date=None,
            resolution_event=rules.resolution_event,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            production_blockers=_blocking_conflict_codes(rules.unresolved_conflicts),
            valid=False,
            validation_errors=(f"schedule_interval_below_{rules.minimum_interval_months}_months",),
            active_step_cents=None,
            adjustment_due=False,
        )

    active_steps = tuple(step for step in schedule if step.effective_on <= input_.today)
    active_step = active_steps[-1] if active_steps else None
    adjustment_due = (
        active_step is not None and active_step.amount_cents != input_.current_target_rent_cents
    )
    stage = "adjustment_due" if adjustment_due else ("resolved" if active_step else "not_due")
    warning = (
        rules.warning_de.format(
            unit_label=input_.unit_label,
            step_effective_on=active_step.effective_on.strftime("%d.%m.%Y"),
            amount=_format_euros(active_step.amount_cents),
        )
        if adjustment_due and active_step is not None
        else None
    )
    return GraduatedRentResult(
        guard_code="W6",
        source_identity=input_.source_identity,
        stage=stage,
        active=adjustment_due,
        resolved=active_step is not None and not adjustment_due,
        warning_de=warning,
        escalation_channels=rules.channels_by_stage.get(stage, ()),
        boundary_date=active_step.effective_on if active_step is not None else None,
        resolution_event=rules.resolution_event,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
        production_blockers=_blocking_conflict_codes(rules.unresolved_conflicts),
        valid=True,
        validation_errors=(),
        active_step_cents=active_step.amount_cents if active_step is not None else None,
        adjustment_due=adjustment_due,
    )


def evaluate_index_rent(input_: IndexRentInput, rules: IndexRentRuleBundle) -> IndexRentResult:
    """Evaluate W7 from immutable VPI snapshots without provider access."""

    if input_.net_cold_rent_cents < 0:
        raise ValueError("net cold rent must not be negative")
    elapsed_months = _elapsed_months(input_.last_adjustment_on, input_.today)
    boundary = _add_months(input_.last_adjustment_on, rules.minimum_interval_months)
    blockers = list(_blocking_conflict_codes(rules.unresolved_conflicts))
    if input_.base_index.basis_year != input_.new_index.basis_year:
        blockers.append("basis_year_mismatch")
        return IndexRentResult(
            guard_code="W7",
            source_identity=input_.source_identity,
            stage="basis_year_mismatch",
            active=False,
            resolved=False,
            warning_de=rules.rebasing_warning_de,
            escalation_channels=(),
            boundary_date=boundary,
            resolution_event=rules.resolution_event,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            production_blockers=tuple(blockers),
            base_index=input_.base_index,
            new_index=input_.new_index,
            elapsed_months=elapsed_months,
            factor=None,
            new_rent_cents=None,
            increase_cents=None,
            delta_percent_display=None,
        )
    if input_.base_index.value <= 0:
        raise ValueError("base index must be positive")

    factor = input_.new_index.value / input_.base_index.value
    if input_.new_index.value <= input_.base_index.value:
        return IndexRentResult(
            guard_code="W7",
            source_identity=input_.source_identity,
            stage="no_increase",
            active=False,
            resolved=False,
            warning_de=None,
            escalation_channels=(),
            boundary_date=boundary,
            resolution_event=rules.resolution_event,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            production_blockers=tuple(blockers),
            base_index=input_.base_index,
            new_index=input_.new_index,
            elapsed_months=elapsed_months,
            factor=factor,
            new_rent_cents=None,
            increase_cents=0,
            delta_percent_display=None,
        )

    new_rent = _round_cents(Decimal(input_.net_cold_rent_cents) * factor)
    increase = new_rent - input_.net_cold_rent_cents
    delta_percent = ((factor - Decimal(1)) * Decimal(100)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    active = elapsed_months >= rules.minimum_interval_months
    stage = "opportunity" if active else "waiting_period"
    warning = (
        rules.warning_de.format(
            base_index=input_.base_index.value,
            new_index=input_.new_index.value,
            delta_percent=delta_percent,
            new_rent=_format_euros(new_rent),
            increase=_format_euros(increase),
        )
        if active
        else None
    )
    return IndexRentResult(
        guard_code="W7",
        source_identity=input_.source_identity,
        stage=stage,
        active=active,
        resolved=False,
        warning_de=warning,
        escalation_channels=rules.channels_by_stage.get(stage, ()),
        boundary_date=boundary,
        resolution_event=rules.resolution_event,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
        production_blockers=tuple(blockers),
        base_index=input_.base_index,
        new_index=input_.new_index,
        elapsed_months=elapsed_months,
        factor=factor,
        new_rent_cents=new_rent,
        increase_cents=increase,
        delta_percent_display=delta_percent,
    )


def evaluate_vacancy(input_: VacancyInput, rules: VacancyRuleBundle) -> VacancyResult:
    """Evaluate W8 while suppressing vacancy framing for an active tenancy."""

    if input_.target_rent_cents < 0:
        raise ValueError("target rent must not be negative")
    if rules.rent_period_days <= 0:
        raise ValueError("rent_period_days must be positive")
    blockers = _blocking_conflict_codes(rules.unresolved_conflicts)
    if input_.active_tenancy:
        return VacancyResult(
            guard_code="W8",
            source_identity=input_.source_identity,
            stage="active_tenancy",
            active=False,
            resolved=True,
            warning_de=None,
            escalation_channels=(),
            boundary_date=None,
            resolution_event=rules.resolution_event,
            rule_evidence=rules.evidence,
            unresolved_conflicts=rules.unresolved_conflicts,
            production_blockers=blockers,
            vacancy_days=None,
            lost_rent_cents=None,
        )
    vacancy_days = max(0, (input_.today - input_.last_tenancy_ended_on).days)
    lost_rent = _round_cents(
        Decimal(input_.target_rent_cents) * Decimal(vacancy_days) / Decimal(rules.rent_period_days)
    )
    active = vacancy_days > rules.threshold_days
    stage = "vacancy" if active else "within_threshold"
    warning = (
        rules.warning_de.format(
            unit_label=input_.unit_label,
            vacancy_days=vacancy_days,
            lost_rent=_format_euros(lost_rent),
        )
        if active
        else None
    )
    return VacancyResult(
        guard_code="W8",
        source_identity=input_.source_identity,
        stage=stage,
        active=active,
        resolved=False,
        warning_de=warning,
        escalation_channels=rules.channels_by_stage.get(stage, ()),
        boundary_date=input_.last_tenancy_ended_on + timedelta(days=rules.threshold_days),
        resolution_event=rules.resolution_event,
        rule_evidence=rules.evidence,
        unresolved_conflicts=rules.unresolved_conflicts,
        production_blockers=blockers,
        vacancy_days=vacancy_days,
        lost_rent_cents=lost_rent,
    )
