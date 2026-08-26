"""M6-C3b: the three scheduled job entrypoints (`docs/15` § 5.6).

Three properties hold for every function here, and each is load-bearing:

* **`now`/`today` are inputs.** Nothing reads the clock. A deadline that depends on
  when the worker happened to wake is not reproducible evidence, and `docs/12` § 3
  states the same rule for guards.
* **One account per run.** Each function takes an explicit `account_id` and runs on
  an already RLS-scoped session. `account` is scoped by its own id, so no
  cross-account enumeration exists — and none is added: `app_bootstrap_contexts`
  stays the only pre-context read (`CLAUDE.md` § 3.3). The caller supplies the ids.
* **Only sync writes.** `expire_bank_consents` and `watch_deadlines` are reports.
  "Cleanup" stops the pull; it never deletes a `bank_transaction`, which is
  append-only under § 147 AO.

The watcher deliberately applies no `docs/12` guard rule, threshold, warning copy or
escalation. W1–W8 and fixtures `12-F01`–`12-F24` belong to the guard-foundation
slice; restating one of them here would create a second, unversioned copy of a legal
rule.

No worker is installed. `StubScheduler` in `lokara_adapters` decides what is due;
this module decides what a due job does (`docs/01` D7).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum, StrEnum
from hashlib import sha256
from typing import Final, cast

from lokara_adapters import (
    BankGateway,
    DeliveryStatus,
    EmailAttachment,
    EmailGateway,
    OutgoingEmail,
)
from lokara_db import (
    BankAccount,
    BankTransaction,
    Building,
    DeliveryScheduleVersion,
    EmailAttempt,
    EmailDeliveryStatusEvent,
    GuardEvaluation,
    GuardReminder,
    GuardResolutionEvent,
    Landlord,
    Receivable,
    RecipientSuppressionEvent,
    Renter,
    RenterDeliveryArtifact,
    Statement,
    StatementArchive,
    StatementStatus,
    Tenancy,
    TenancyParty,
    Unit,
    UviRun,
    new_id,
)
from lokara_rules_store.page01_statement import PAGE_01_STATEMENT_RULES
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .bank_sync import ConsentExpiredError, import_transactions, require_aware
from .deps import job_account_session
from .matching_service import MatchingConflictError, MatchingNotFoundError, run_match
from .statement_service import (
    STATEMENT_AUTHORITY_ENVELOPE_INCOMPLETE,
    statement_authority_envelope_is_complete,
)

#: PSD2 RTS Art. 10 (Delegated Regulation (EU) 2018/389, as amended) caps how long
#: an AIS consent may stand before the renter re-authenticates. The authoritative
#: `Rechtsstand-Register.csv` carries **no** consent/PSD2/SCA/AIS row, so this is a
#: Lokara `Konvention`, `verify-before-production`, `Rechtsstand 08/2026`, resting on
#: an unverified primary source. Nothing defaults an expiry from it: the pull reads
#: only the stored `consent_expires_at`, and this value is a ceiling check alone.
AIS_CONSENT_MAX_DAYS: Final = 180

_SETTLED = "settled"

#: The two provider outcomes that end delivery to an address (`docs/12` § 6). They are
#: also the `reason` values `RecipientSuppressionEvent` accepts, and the database
#: trigger that derives one from the other uses the same pair.
_NEGATIVE_DELIVERY_STATUSES: Final = frozenset({"BOUNCED", "COMPLAINED"})


@dataclass(frozen=True)
class JobRefusal:
    """One transaction the matching service refused, and why.

    A refusal is evidence, not a failure to hide: `docs/15` § 5.2's missing
    tie-break and § 5.3's unresolvable return both surface here rather than being
    resolved by an invented rule.
    """

    bank_transaction_id: str
    reason: str


@dataclass(frozen=True)
class BankAccountSyncResult:
    """What one bank account's sync did.

    `skipped_reason` is `None`, `consent_missing` or `consent_expired`; a skipped
    account pulled nothing at all, so every count below it is zero.
    """

    bank_account_id: str
    skipped_reason: str | None
    imported: int
    skipped_as_duplicate: int
    auto_matched: int
    needs_review: int
    unmatched: int
    deduped: int
    reversed_payments: int
    settled: int
    refused: tuple[JobRefusal, ...]


@dataclass(frozen=True)
class SyncResult:
    account_id: str
    bank_accounts: tuple[BankAccountSyncResult, ...]


@dataclass(frozen=True)
class ConsentFinding:
    """`state` is `missing`, `expired` or `exceeds_max_window`.

    The third is a ceiling check against the flagged 180-day convention: a provider
    that hands back a longer validity than PSD2 permits is reported, never trimmed.
    """

    bank_account_id: str
    display_name: str
    state: str
    expires_at: datetime | None


@dataclass(frozen=True)
class OverdueReceivable:
    """A fact, not a warning. No § 543 stage, threshold or German copy is applied."""

    receivable_id: str
    renter_id: str
    period: str
    due_date: date
    days_overdue: int
    open_cents: int


@dataclass(frozen=True)
class DeadlineWatchResult:
    account_id: str
    overdue_receivables: tuple[OverdueReceivable, ...]
    consent_findings: tuple[ConsentFinding, ...]


def _bank_accounts(session: Session, account_id: str) -> Sequence[BankAccount]:
    # RLS already scopes this; the explicit predicate is the app-logic half that
    # CLAUDE.md rule 3 requires independently of the database backstop.
    return session.scalars(
        select(BankAccount).where(BankAccount.account_id == account_id).order_by(BankAccount.id)
    ).all()


@dataclass(frozen=True)
class _ImportPhase:
    """What one bank account's pull produced, before anything is matched."""

    skipped_reason: str | None
    imported: int
    skipped_as_duplicate: int
    transaction_ids: tuple[str, ...]


@dataclass
class _Tally:
    auto_matched: int = 0
    needs_review: int = 0
    unmatched: int = 0
    deduped: int = 0
    reversed_payments: int = 0
    settled: int = 0
    refused: list[JobRefusal] = field(default_factory=list)


# Migration 0021 makes the three reconciliation constraints DEFERRABLE INITIALLY
# DEFERRED, because a settlement inserts its ledger entry before its allocations and
# is only consistent once both are in. Under C3a that was harmless: one request was
# one `run_match` was one transaction, so the check ran at the same COMMIT. A job
# matches many transactions in one transaction, and a deferred violation would
# surface at the outer COMMIT and abort every import and settlement in the run.
# Forcing the check inside each SAVEPOINT puts the failure back where the run can
# bound it. Exactly these three constraints are deferrable, so `ALL` names them and
# nothing else, and the reset restores their declared state for the next transaction.
_ALL_IMMEDIATE = text("SET CONSTRAINTS ALL IMMEDIATE")
_ALL_DEFERRED = text("SET CONSTRAINTS ALL DEFERRED")


def _match_one(session: Session, transaction: BankTransaction, tally: _Tally) -> None:
    """Match one transaction inside its own SAVEPOINT, and count what happened."""
    savepoint = session.begin_nested()
    try:
        result = run_match(session, transaction.id)
        session.execute(_ALL_IMMEDIATE)
        session.execute(_ALL_DEFERRED)
    except (MatchingConflictError, MatchingNotFoundError, IntegrityError) as error:
        savepoint.rollback()
        tally.refused.append(JobRefusal(bank_transaction_id=transaction.id, reason=str(error)))
        return
    savepoint.commit()

    decision = result.get("decision")
    if decision == "auto_match":
        tally.auto_matched += 1
    elif decision == "needs_review":
        tally.needs_review += 1
    elif decision == "unmatched":
        tally.unmatched += 1
    elif decision == "deduped":
        tally.deduped += 1
    if result.get("event") is not None:
        tally.reversed_payments += 1
    if result.get("ledger_entry_id") is not None:
        tally.settled += 1


def _import_phase(
    session: Session,
    *,
    account_id: str,
    bank_account_id: str,
    window_from: date,
    window_to: date,
    gateway: BankGateway,
    now: datetime,
) -> _ImportPhase:
    try:
        outcome = import_transactions(
            session,
            account_id=account_id,
            bank_account_id=bank_account_id,
            window_from=window_from,
            window_to=window_to,
            gateway=gateway,
            now=now,
        )
    except ConsentExpiredError as error:
        return _ImportPhase(
            skipped_reason=error.reason,
            imported=0,
            skipped_as_duplicate=0,
            transaction_ids=(),
        )
    return _ImportPhase(
        skipped_reason=None,
        imported=outcome.imported,
        skipped_as_duplicate=outcome.skipped_as_duplicate,
        transaction_ids=outcome.imported_transaction_ids,
    )


def sync_bank_transactions(
    session: Session,
    *,
    account_id: str,
    window_from: date,
    window_to: date,
    gateway: BankGateway,
    now: datetime,
) -> SyncResult:
    """Pull every connected bank account of one account, then match what arrived.

    Matching runs here on purpose: `docs/15` § 4 defines `AUTO_MATCH` as the
    automatic channel, so a scheduled sync settles it. `NEEDS_REVIEW` still moves no
    money before a human confirmation, which is the property the whole contract
    rests on.

    Import and matching are two phases, not one loop per bank account. `docs/15`
    § 5.1 settles a renter's receivables FIFO across *all* of their payments, and a
    renter's rent and their garage may arrive on two different accounts — so
    matching one bank account to completion before opening the next would order
    settlement by `bank_account_id` and only then by the date the bank booked.
    """
    require_aware(now, "now")
    phases = {
        bank_account.id: _import_phase(
            session,
            account_id=account_id,
            bank_account_id=bank_account.id,
            window_from=window_from,
            window_to=window_to,
            gateway=gateway,
            now=now,
        )
        for bank_account in _bank_accounts(session, account_id)
    }

    imported_ids = [
        transaction_id for phase in phases.values() for transaction_id in phase.transaction_ids
    ]
    tallies = {bank_account_id: _Tally() for bank_account_id in phases}
    for transaction in session.scalars(
        select(BankTransaction)
        .where(
            BankTransaction.account_id == account_id,
            BankTransaction.id.in_(imported_ids),
        )
        .order_by(BankTransaction.bank_booking_date, BankTransaction.provider_transaction_id)
    ).all():
        _match_one(session, transaction, tallies[transaction.bank_account_id])

    return SyncResult(
        account_id=account_id,
        bank_accounts=tuple(
            BankAccountSyncResult(
                bank_account_id=bank_account_id,
                skipped_reason=phases[bank_account_id].skipped_reason,
                imported=phases[bank_account_id].imported,
                skipped_as_duplicate=phases[bank_account_id].skipped_as_duplicate,
                auto_matched=tallies[bank_account_id].auto_matched,
                needs_review=tallies[bank_account_id].needs_review,
                unmatched=tallies[bank_account_id].unmatched,
                deduped=tallies[bank_account_id].deduped,
                reversed_payments=tallies[bank_account_id].reversed_payments,
                settled=tallies[bank_account_id].settled,
                refused=tuple(tallies[bank_account_id].refused),
            )
            for bank_account_id in sorted(phases)
        ),
    )


def expire_bank_consents(
    session: Session, *, account_id: str, now: datetime
) -> tuple[ConsentFinding, ...]:
    """Report the bank accounts that may no longer be pulled. Writes nothing.

    Reconsent is a landlord action through the provider, so the job's whole job is
    to name the accounts. It deletes no evidence and revokes nothing itself; the
    pull is already blocked by the same stored expiry in `bank_sync`.
    """
    require_aware(now, "now")
    ceiling = now + timedelta(days=AIS_CONSENT_MAX_DAYS)
    findings: list[ConsentFinding] = []
    for bank_account in _bank_accounts(session, account_id):
        expires_at = bank_account.consent_expires_at
        if expires_at is None:
            state = "missing"
        elif expires_at <= now:
            state = "expired"
        elif expires_at > ceiling:
            state = "exceeds_max_window"
        else:
            continue
        findings.append(
            ConsentFinding(
                bank_account_id=bank_account.id,
                display_name=bank_account.display_name,
                state=state,
                expires_at=expires_at,
            )
        )
    return tuple(findings)


def watch_deadlines(
    session: Session, *, account_id: str, today: date, now: datetime
) -> DeadlineWatchResult:
    """Report the M6-owned deadline facts. Writes nothing.

    An overdue receivable is stated as days and cents. It carries no § 543 stage, no
    threshold comparison and no warning text — those are `docs/12` W3, and they ship
    with the guard engine, versioned, not as a copy made here.
    """
    require_aware(now, "now")
    rows = session.scalars(
        select(Receivable)
        .where(
            Receivable.account_id == account_id,
            Receivable.status != _SETTLED,
            Receivable.due_date < today,
        )
        .order_by(Receivable.due_date, Receivable.id)
    ).all()
    return DeadlineWatchResult(
        account_id=account_id,
        overdue_receivables=tuple(
            OverdueReceivable(
                receivable_id=row.id,
                renter_id=row.renter_id,
                period=row.period,
                due_date=row.due_date,
                days_overdue=(today - row.due_date).days,
                open_cents=row.open_cents,
            )
            for row in rows
        ),
        consent_findings=expire_bank_consents(session, account_id=account_id, now=now),
    )


# ── M9: guards, reminders and opt-in renter delivery. ──


class ScheduledDeliveryKind(StrEnum):
    """The only two renter-document schedules approved for M9."""

    ANNUAL_STATEMENT = "ANNUAL_STATEMENT"
    UVI = "UVI"


class DeliveryBlockReason(StrEnum):
    """A no-send result which must remain visible to the caller."""

    SCHEDULE_DISABLED = "SCHEDULE_DISABLED"
    MISSING_EMAIL = "MISSING_EMAIL"
    RECIPIENT_SUPPRESSED = "RECIPIENT_SUPPRESSED"
    PRODUCTION_BLOCKED = "PRODUCTION_BLOCKED"
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    HASH_MISMATCH = "HASH_MISMATCH"
    MISSING_PROVIDER = "MISSING_PROVIDER"
    INVALID_SENDER = "INVALID_SENDER"
    IDEMPOTENCY_UNAVAILABLE = "IDEMPOTENCY_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class LegalDeliveryConfirmation:
    """Owner evidence of legal delivery; provider status is deliberately absent."""

    delivered_on: date
    evidence_reference: str


@dataclass(frozen=True, slots=True)
class GuardEvaluationOccurrence:
    """One already-normalized pure-engine evaluation to persist.

    The scheduler owns neither legal input discovery nor rule resolution.  Its caller
    supplies all three exact snapshots plus the stable occurrence identity.  This
    keeps this application boundary generic across W1--W8 and prevents it from
    copying engine rules.
    """

    guard_code: str
    occurrence_key: str
    subject_type: str
    subject_id: str
    building_id: str
    input_snapshot: Mapping[str, object]
    result_snapshot: Mapping[str, object]
    rule_snapshot: Mapping[str, object]
    unit_id: str | None = None
    tenancy_id: str | None = None
    renter_id: str | None = None
    reminder_channels: tuple[str, ...] = ()
    production_blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GuardEvaluationJobResult:
    account_id: str
    evaluated_occurrences: int
    existing_occurrences: int
    created_reminders: int
    push_available: bool
    production_blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReminderBlock:
    reminder_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ReminderDispatchResult:
    account_id: str
    queued: int
    already_dispatched: int
    blocked: tuple[ReminderBlock, ...]
    push_unavailable: bool


@dataclass(frozen=True, slots=True)
class RenterDeliveryRequest:
    """One due schedule occurrence for one renter and one frozen artifact.

    A caller must create one item per recipient.  Recipient lookup remains server
    side through ``renter_id``; no email address from a worker is trusted.
    """

    building_id: str
    renter_id: str
    delivery_kind: ScheduledDeliveryKind
    occurrence_key: str
    subject_de: str
    html_body_de: str
    from_name: str
    sender_address: str
    schedule_version_id: str | None = None
    artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class BlockedRenterDelivery:
    renter_id: str
    occurrence_key: str
    reason: DeliveryBlockReason
    detail: str


@dataclass(frozen=True, slots=True)
class RenterDeliveryJobResult:
    account_id: str
    scheduled: int
    queued: int
    already_processed: int
    blocked: tuple[BlockedRenterDelivery, ...]
    provider_delivered: int
    legally_confirmed: int


@dataclass(frozen=True, slots=True)
class ArtifactFreezeResult:
    artifact: RenterDeliveryArtifact | None
    created: bool
    blocked_reason: DeliveryBlockReason | None
    detail: str | None


def derive_uvi_production_blockers(run: object) -> tuple[str, ...]:
    """Read production eligibility only from the bound immutable UVI result."""

    results = getattr(run, "results", None)
    if not isinstance(results, Mapping):
        return ("UVI-RUN-RESULTS-MISSING",)
    blockers: list[str] = []
    rule_evidence = results.get("rule_evidence")
    if isinstance(rule_evidence, (list, tuple)):
        for evidence in rule_evidence:
            if not isinstance(evidence, Mapping):
                continue
            status = str(evidence.get("verification_status", "")).strip().lower()
            if status and status not in {"geprüft", "verified", "approved"}:
                marker = str(
                    evidence.get("code")
                    or evidence.get("source")
                    or evidence.get("legal_basis")
                    or "UVI-RULE-EVIDENCE"
                )
                blockers.append(f"{marker}: {status}")
    reduction_risks = results.get("reduction_risks")
    if isinstance(reduction_risks, (list, tuple)):
        for risk in reduction_risks:
            if not isinstance(risk, Mapping):
                continue
            status = str(risk.get("status", "")).strip().lower()
            if status and status not in {"geprüft", "verified", "approved", "closed"}:
                marker = str(risk.get("code") or "UVI-REDUCTION-RISK")
                blockers.append(f"{marker}: {status}")
    raw_blockers = results.get("production_blockers")
    if isinstance(raw_blockers, (list, tuple)):
        blockers.extend(str(item) for item in raw_blockers if str(item).strip())
    conflicts = results.get("unresolved_conflicts")
    if isinstance(conflicts, (list, tuple)):
        for conflict in conflicts:
            if isinstance(conflict, Mapping) and conflict.get("production_blocking") is not False:
                code = str(conflict.get("code", "UVI-UNRESOLVED-CONFLICT"))
                description = str(conflict.get("description", "")).strip()
                blockers.append(f"{code}: {description}" if description else code)
    if results.get("production_blocked") is True and not blockers:
        blockers.append("UVI-PRODUCTION-BLOCKED")
    return tuple(blockers)


def derive_statement_production_blockers(snapshot: object) -> list[object]:
    """Collect every production/legal warning frozen by the real M6-B envelope."""

    if not isinstance(snapshot, Mapping):
        return ["STATEMENT-FINALIZED-SNAPSHOT-MISSING"]
    explicit = snapshot.get("production_blockers")
    incomplete: list[object] = (
        []
        if statement_authority_envelope_is_complete(
            explicit, snapshot.get("statement_rule_evidence")
        )
        else [STATEMENT_AUTHORITY_ENVELOPE_INCOMPLETE]
    )
    published_blockers: list[str] = []
    statement_rule_evidence = snapshot.get("statement_rule_evidence")
    for version in PAGE_01_STATEMENT_RULES.versions:
        published_evidence = [asdict(row) for row in version.value.evidence]
        if statement_rule_evidence != published_evidence:
            continue
        published_blockers = [
            f"{row.name}: {row.verification_status}"
            for row in version.value.evidence
            if row.verification_status.strip().lower()
            not in {"", "geprüft", "verified", "approved", "closed"}
        ]
        break
    if isinstance(explicit, list):
        rest = [item for item in explicit if item != STATEMENT_AUTHORITY_ENVELOPE_INCOMPLETE]
        return incomplete + rest + [item for item in published_blockers if item not in rest]

    found: list[object] = [*incomplete, *published_blockers]

    def visit(value: object, path: str) -> None:
        if isinstance(value, Mapping):
            nested = value.get("production_blockers")
            if isinstance(nested, (list, tuple)):
                found.extend(nested)
            for status_key in ("verification_status", "legal_status", "status"):
                status = value.get(status_key)
                if isinstance(status, str) and status.strip().lower() not in {
                    "",
                    "geprüft",
                    "verified",
                    "approved",
                    "closed",
                }:
                    marker = (
                        value.get("code") or value.get("source") or value.get("legal_basis") or path
                    )
                    found.append(f"{marker}: {status}")
            if value.get("production_blocked") is True and not nested:
                found.append(f"STATEMENT-PRODUCTION-BLOCKED:{path}")
            for key, item in value.items():
                if key != "production_blockers":
                    visit(item, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, str) and any(
            marker in value.lower() for marker in ("verify-before-production", "unsicher")
        ):
            found.append(value)

    visit(snapshot, "finalized_snapshot")
    return list(dict.fromkeys(str(item) for item in found))


def freeze_renter_delivery_artifact(
    session: Session,
    *,
    account_id: str,
    source_kind: ScheduledDeliveryKind,
    source_id: str,
    renter_id: str,
    occurrence_key: str,
    now: datetime,
) -> ArtifactFreezeResult:
    """Freeze exact server-owned source bytes for one renter, idempotently."""

    require_aware(now, "now")
    existing = session.scalar(
        select(RenterDeliveryArtifact).where(
            RenterDeliveryArtifact.account_id == account_id,
            RenterDeliveryArtifact.renter_id == renter_id,
            RenterDeliveryArtifact.artifact_kind == source_kind.value,
            RenterDeliveryArtifact.occurrence_key == occurrence_key,
        )
    )
    if existing is not None:
        expected_source = (
            existing.statement_archive_id
            if source_kind is ScheduledDeliveryKind.ANNUAL_STATEMENT
            else existing.uvi_run_id
        )
        if expected_source != source_id:
            return ArtifactFreezeResult(
                None,
                False,
                DeliveryBlockReason.PRODUCTION_BLOCKED,
                "Die vorhandene Zustellfassung ist an eine andere Quelle gebunden.",
            )
        return ArtifactFreezeResult(existing, False, None, None)

    if source_kind is ScheduledDeliveryKind.UVI:
        run = session.scalar(
            select(UviRun).where(UviRun.account_id == account_id, UviRun.id == source_id)
        )
        detail = (
            "Die gebundene UVI-Auswertung fehlt."
            if run is None
            else "Für die UVI liegen keine unveränderlichen Dokumentbytes vor."
        )
        return ArtifactFreezeResult(
            artifact=None,
            created=False,
            blocked_reason=DeliveryBlockReason.MISSING_ARTIFACT,
            detail=detail,
        )

    archive = session.scalar(
        select(StatementArchive).where(
            StatementArchive.account_id == account_id,
            StatementArchive.id == source_id,
            StatementArchive.audience == "TENANT",
            StatementArchive.tenancy_id.is_not(None),
        )
    )
    if archive is None or archive.tenancy_id is None:
        return ArtifactFreezeResult(
            None, False, DeliveryBlockReason.MISSING_ARTIFACT, "Mieterarchiv fehlt."
        )
    if sha256(archive.content_bytes).hexdigest() != archive.sha256:
        return ArtifactFreezeResult(
            None,
            False,
            DeliveryBlockReason.HASH_MISMATCH,
            "Der Archiv-Hash stimmt nicht mit den exakten Bytes überein.",
        )
    statement = session.scalar(
        select(Statement).where(
            Statement.account_id == account_id,
            Statement.id == archive.statement_id,
        )
    )
    tenancy = session.scalar(
        select(Tenancy).where(
            Tenancy.account_id == account_id,
            Tenancy.id == archive.tenancy_id,
        )
    )
    if statement is None or tenancy is None:
        return ArtifactFreezeResult(
            None, False, DeliveryBlockReason.MISSING_ARTIFACT, "Abrechnungskontext fehlt."
        )
    if getattr(statement, "status", StatementStatus.FINALIZED) is not StatementStatus.FINALIZED:
        return ArtifactFreezeResult(
            None,
            False,
            DeliveryBlockReason.PRODUCTION_BLOCKED,
            "Nur eine finalisierte Abrechnung darf eingefroren werden.",
        )
    unit = session.scalar(
        select(Unit).where(Unit.account_id == account_id, Unit.id == tenancy.unit_id)
    )
    if unit is None or unit.building_id != statement.building_id:
        return ArtifactFreezeResult(
            None, False, DeliveryBlockReason.PRODUCTION_BLOCKED, "Objektbezug ist ungültig."
        )
    party = session.scalar(
        select(TenancyParty).where(
            TenancyParty.account_id == account_id,
            TenancyParty.tenancy_id == tenancy.id,
            TenancyParty.renter_id == renter_id,
        )
    )
    if party is None:
        return ArtifactFreezeResult(
            None, False, DeliveryBlockReason.PRODUCTION_BLOCKED, "Mieterbezug ist ungültig."
        )
    blockers = derive_statement_production_blockers(statement.finalized_snapshot)
    artifact = RenterDeliveryArtifact(
        id=new_id(),
        account_id=account_id,
        building_id=statement.building_id,
        unit_id=unit.id,
        tenancy_id=tenancy.id,
        renter_id=renter_id,
        artifact_kind=source_kind.value,
        occurrence_key=occurrence_key,
        statement_archive_id=archive.id,
        uvi_run_id=None,
        content_bytes=archive.content_bytes,
        sha256=archive.sha256,
        mime_type=archive.mime_type,
        filename=archive.filename,
        production_blockers_snapshot=blockers,
        generated_at=now,
    )
    session.add(artifact)
    session.flush()
    return ArtifactFreezeResult(artifact, True, None, None)


def _json_value(value: object) -> object:
    """Turn normalized values into an immutable JSON-compatible snapshot."""

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _json_value(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _json_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    raise TypeError(f"Cannot snapshot normalized value {type(value).__name__}")


def _json_object(value: Mapping[str, object]) -> dict[str, object]:
    return cast(dict[str, object], _json_value(value))


def _normalized_channel(channel: str) -> str:
    return channel.strip().upper()


def run_daily_guard_evaluations(
    session: Session,
    *,
    account_id: str,
    today: date,
    now: datetime,
    occurrences: Sequence[GuardEvaluationOccurrence] = (),
) -> GuardEvaluationJobResult:
    """Persist caller-resolved W1--W8 results and their idempotent reminders.

    ``today`` is intentionally present even though the pure evaluator has already
    consumed it: it is recorded with each input snapshot and makes the job boundary
    impossible to call with an implicit day.  The caller supplies occurrences for
    exactly one already RLS-scoped account; this function never discovers accounts.
    """

    require_aware(now, "now")
    evaluated = 0
    existing = 0
    reminders = 0
    blockers: set[str] = set()

    for occurrence in occurrences:
        blockers.update(occurrence.production_blockers)
        evaluation = session.scalar(
            select(GuardEvaluation).where(
                GuardEvaluation.account_id == account_id,
                GuardEvaluation.guard_code == occurrence.guard_code,
                GuardEvaluation.occurrence_key == occurrence.occurrence_key,
            )
        )
        if evaluation is None:
            input_snapshot = _json_object(occurrence.input_snapshot)
            input_snapshot.setdefault("today", today.isoformat())
            evaluation = GuardEvaluation(
                id=new_id(),
                account_id=account_id,
                guard_code=occurrence.guard_code,
                subject_type=occurrence.subject_type,
                subject_id=occurrence.subject_id,
                building_id=occurrence.building_id,
                unit_id=occurrence.unit_id,
                tenancy_id=occurrence.tenancy_id,
                renter_id=occurrence.renter_id,
                occurrence_key=occurrence.occurrence_key,
                input_snapshot=input_snapshot,
                result_snapshot=_json_object(occurrence.result_snapshot),
                rule_snapshot=_json_object(occurrence.rule_snapshot),
                evaluated_at=now,
            )
            session.add(evaluation)
            session.flush()
            evaluated += 1
        else:
            existing += 1

        result_active = occurrence.result_snapshot.get("active") is True
        result_resolved = occurrence.result_snapshot.get("resolved") is True
        if not result_active or result_resolved:
            continue
        for raw_channel in occurrence.reminder_channels:
            channel = _normalized_channel(raw_channel)
            if channel == "PUSH":
                blockers.add("PUSH-CLIENT-TOKEN-BOUNDARY-MISSING")
                continue
            if channel not in {"EMAIL", "IN_APP"}:
                blockers.add(f"UNSUPPORTED-REMINDER-CHANNEL:{raw_channel}")
                continue
            idempotency_key = f"guard:{occurrence.occurrence_key}:{channel.lower()}"
            reminder = session.scalar(
                select(GuardReminder).where(
                    GuardReminder.account_id == account_id,
                    GuardReminder.idempotency_key == idempotency_key,
                )
            )
            if reminder is not None:
                continue
            session.add(
                GuardReminder(
                    id=new_id(),
                    account_id=account_id,
                    guard_evaluation_id=evaluation.id,
                    occurrence_key=occurrence.occurrence_key,
                    channel=channel,
                    due_at=now,
                    idempotency_key=idempotency_key,
                    payload_snapshot={
                        "guard_code": occurrence.guard_code,
                        "subject_type": occurrence.subject_type,
                        "subject_id": occurrence.subject_id,
                        "warning_de": _json_value(occurrence.result_snapshot.get("warning_de")),
                    },
                )
            )
            session.flush()
            reminders += 1

    return GuardEvaluationJobResult(
        account_id=account_id,
        evaluated_occurrences=evaluated,
        existing_occurrences=existing,
        created_reminders=reminders,
        push_available=False,
        production_blockers=tuple(sorted(blockers)),
    )


def dispatch_guard_reminders(
    session: Session,
    *,
    account_id: str,
    today: date,
    now: datetime,
) -> ReminderDispatchResult:
    """Expose due reminder occurrences without inventing a worker/provider state.

    ``GuardReminder`` is itself the immutable idempotent dispatch occurrence.  M9
    has no separate reminder provider-attempt ledger, so this job reports stored
    in-app/e-mail occurrences as queued and keeps push visibly blocked.  It performs
    no hidden network I/O and mutates no evidence.
    """

    del today  # Required explicit clock; reminder due times are timestamp-exact.
    require_aware(now, "now")
    due = session.scalars(
        select(GuardReminder)
        .where(
            GuardReminder.account_id == account_id,
            GuardReminder.due_at <= now,
        )
        .order_by(GuardReminder.due_at, GuardReminder.id)
    ).all()
    blocked = tuple(
        ReminderBlock(
            reminder_id=reminder.id,
            reason=(
                "Push ist bis zur M10-Client/Token-Grenze nicht verfügbar."
                if reminder.channel == "PUSH"
                else "Ein Anbieter für die Erinnerungszustellung ist nicht verfügbar."
            ),
        )
        for reminder in due
    )
    return ReminderDispatchResult(
        account_id=account_id,
        queued=0,
        already_dispatched=0,
        blocked=blocked,
        push_unavailable=True,
    )


def _latest_schedule(
    session: Session, *, account_id: str, request: RenterDeliveryRequest, today: date
) -> DeliveryScheduleVersion | None:
    statement = (
        select(DeliveryScheduleVersion)
        .where(
            DeliveryScheduleVersion.account_id == account_id,
            DeliveryScheduleVersion.building_id == request.building_id,
            DeliveryScheduleVersion.delivery_kind == request.delivery_kind.value,
            DeliveryScheduleVersion.valid_from <= today,
        )
        .order_by(DeliveryScheduleVersion.version.desc())
        .limit(1)
    )
    latest = session.scalar(statement)
    if request.schedule_version_id is not None and (
        latest is None or latest.id != request.schedule_version_id
    ):
        return None
    return latest


def _artifact(
    session: Session, *, account_id: str, request: RenterDeliveryRequest
) -> RenterDeliveryArtifact | None:
    statement = select(RenterDeliveryArtifact).where(
        RenterDeliveryArtifact.account_id == account_id,
        RenterDeliveryArtifact.building_id == request.building_id,
        RenterDeliveryArtifact.renter_id == request.renter_id,
        RenterDeliveryArtifact.artifact_kind == request.delivery_kind.value,
        RenterDeliveryArtifact.occurrence_key == request.occurrence_key,
    )
    if request.artifact_id is not None:
        statement = statement.where(RenterDeliveryArtifact.id == request.artifact_id)
    return session.scalar(statement)


def _blocked_delivery(
    request: RenterDeliveryRequest, reason: DeliveryBlockReason, detail: str
) -> BlockedRenterDelivery:
    return BlockedRenterDelivery(
        renter_id=request.renter_id,
        occurrence_key=request.occurrence_key,
        reason=reason,
        detail=detail,
    )


def _legal_confirmation_exists(
    session: Session, *, account_id: str, artifact: RenterDeliveryArtifact
) -> bool:
    if not all(
        hasattr(artifact, field)
        for field in (
            "building_id",
            "unit_id",
            "tenancy_id",
            "renter_id",
            "occurrence_key",
        )
    ):
        return False
    events = session.scalars(
        select(GuardResolutionEvent)
        .join(
            GuardEvaluation,
            GuardEvaluation.id == GuardResolutionEvent.guard_evaluation_id,
        )
        .where(
            GuardResolutionEvent.account_id == account_id,
            GuardResolutionEvent.renter_delivery_artifact_id == artifact.id,
            GuardEvaluation.account_id == account_id,
            GuardEvaluation.guard_code == "W1",
            GuardEvaluation.building_id == artifact.building_id,
            GuardEvaluation.unit_id == artifact.unit_id,
            GuardEvaluation.tenancy_id == artifact.tenancy_id,
            GuardEvaluation.renter_id == artifact.renter_id,
            GuardEvaluation.occurrence_key == artifact.occurrence_key,
            GuardResolutionEvent.event_type.in_(
                (
                    "statement_sent",
                    "statement_delivery_evidence_late",
                    "statement_sent_correction",
                    "statement_delivery_evidence_late_correction",
                )
            ),
        )
    ).all()
    return any(
        isinstance(event.event_snapshot.get("delivered_on"), str)
        and bool(event.evidence_reference.strip())
        for event in events
    )


def dispatch_renter_artifact(
    session: Session,
    *,
    account_id: str,
    today: date,
    now: datetime,
    request: RenterDeliveryRequest,
    gateway: EmailGateway | None,
) -> RenterDeliveryJobResult:
    """Dispatch one artifact using a provider-enforced idempotency replay key."""

    require_aware(now, "now")
    del today
    renter = session.scalar(
        select(Renter).where(
            Renter.account_id == account_id,
            Renter.id == request.renter_id,
        )
    )

    def blocked(reason: DeliveryBlockReason, detail: str) -> RenterDeliveryJobResult:
        return RenterDeliveryJobResult(
            account_id=account_id,
            scheduled=1,
            queued=0,
            already_processed=0,
            blocked=(_blocked_delivery(request, reason, detail),),
            provider_delivered=0,
            legally_confirmed=0,
        )

    if renter is None or renter.email is None or not renter.email.strip():
        return blocked(
            DeliveryBlockReason.MISSING_EMAIL,
            "Für diesen Mieter ist keine E-Mail-Adresse hinterlegt.",
        )
    recipient = renter.email.strip().lower()

    suppression = session.scalar(
        select(RecipientSuppressionEvent.id).where(
            RecipientSuppressionEvent.account_id == account_id,
            RecipientSuppressionEvent.normalized_recipient == recipient,
            RecipientSuppressionEvent.reason.in_(("BOUNCED", "COMPLAINED")),
        )
    )
    if suppression is not None:
        return blocked(
            DeliveryBlockReason.RECIPIENT_SUPPRESSED,
            "Die Adresse ist nach Rückläufer oder Beschwerde gesperrt.",
        )

    # The suppression row is written by a database trigger on the provider status
    # event, so in the ordinary path the read above already covers this. It is not
    # the authority, though: the append-only status history is. A bounce or a
    # complaint that never produced its suppression row -- an event replayed into an
    # older schema, a row removed by hand -- must still stop the next occurrence,
    # so the history is consulted directly rather than trusted through its
    # projection.
    negative_history = [
        str(status)
        for status in session.scalars(
            select(EmailDeliveryStatusEvent.status)
            .join(EmailAttempt, EmailAttempt.id == EmailDeliveryStatusEvent.email_attempt_id)
            .where(
                EmailDeliveryStatusEvent.account_id == account_id,
                EmailAttempt.account_id == account_id,
                EmailAttempt.normalized_recipient == recipient,
                EmailDeliveryStatusEvent.status.in_(_NEGATIVE_DELIVERY_STATUSES),
            )
        ).all()
        if str(status) in _NEGATIVE_DELIVERY_STATUSES
    ]
    if negative_history:
        return blocked(
            DeliveryBlockReason.RECIPIENT_SUPPRESSED,
            "Die Adresse ist nach Rückläufer oder Beschwerde gesperrt.",
        )

    artifact = _artifact(session, account_id=account_id, request=request)
    if artifact is None:
        return blocked(
            DeliveryBlockReason.MISSING_ARTIFACT,
            "Das eingefrorene Zustelldokument fehlt.",
        )
    if sha256(artifact.content_bytes).hexdigest() != artifact.sha256:
        return blocked(
            DeliveryBlockReason.HASH_MISMATCH,
            "Der SHA-256-Wert stimmt nicht mit den exakten Dokumentbytes überein.",
        )

    blocker_snapshot = tuple(
        str(item) for item in getattr(artifact, "production_blockers_snapshot", ())
    )
    if request.delivery_kind is ScheduledDeliveryKind.ANNUAL_STATEMENT and (
        artifact.production_blocked or blocker_snapshot
    ):
        return blocked(
            DeliveryBlockReason.PRODUCTION_BLOCKED,
            "; ".join(blocker_snapshot)
            if blocker_snapshot
            else "Dokument ist nicht produktionsfreigegeben.",
        )

    # ORM artifacts must remain bound to exactly one immutable source. Lightweight
    # port tests intentionally use a smaller stand-in and therefore have no binding
    # attributes to resolve.
    if hasattr(artifact, "statement_archive_id"):
        source_id = (
            artifact.statement_archive_id
            if request.delivery_kind is ScheduledDeliveryKind.ANNUAL_STATEMENT
            else artifact.uvi_run_id
        )
        if source_id is None:
            return blocked(
                DeliveryBlockReason.PRODUCTION_BLOCKED,
                "Das Zustelldokument ist nicht an seine unveränderliche Quelle gebunden.",
            )
        if request.delivery_kind is ScheduledDeliveryKind.ANNUAL_STATEMENT:
            statement_source = session.scalar(
                select(StatementArchive)
                .join(Statement, Statement.id == StatementArchive.statement_id)
                .where(
                    StatementArchive.account_id == account_id,
                    StatementArchive.id == source_id,
                    StatementArchive.tenancy_id == artifact.tenancy_id,
                    Statement.account_id == account_id,
                    Statement.building_id == artifact.building_id,
                )
            )
            source_exists = (
                statement_source is not None
                and statement_source.content_bytes == artifact.content_bytes
                and statement_source.sha256 == artifact.sha256
            )
        else:
            uvi_source = session.scalar(
                select(UviRun).where(
                    UviRun.account_id == account_id,
                    UviRun.id == source_id,
                    UviRun.tenancy_id == artifact.tenancy_id,
                    UviRun.unit_id == artifact.unit_id,
                )
            )
            source_exists = uvi_source is not None
            uvi_blockers = () if uvi_source is None else derive_uvi_production_blockers(uvi_source)
            all_uvi_blockers = tuple(dict.fromkeys((*blocker_snapshot, *uvi_blockers)))
            if all_uvi_blockers:
                return blocked(
                    DeliveryBlockReason.PRODUCTION_BLOCKED,
                    "; ".join(all_uvi_blockers),
                )
        if not source_exists:
            return blocked(
                DeliveryBlockReason.PRODUCTION_BLOCKED,
                "Die gebundene unveränderliche Dokumentquelle fehlt.",
            )

    sender = request.sender_address.strip().lower()
    if not sender.endswith("@lokara.de"):
        return blocked(
            DeliveryBlockReason.INVALID_SENDER,
            "Die Absenderadresse muss die konfigurierte Lokara-Domain verwenden.",
        )
    if gateway is None:
        return blocked(
            DeliveryBlockReason.MISSING_PROVIDER,
            "Es ist kein E-Mail-Anbieter konfiguriert.",
        )
    if not gateway.provider_idempotency_enforced:
        return blocked(
            DeliveryBlockReason.IDEMPOTENCY_UNAVAILABLE,
            "Der Anbieter garantiert keine Wiederholungssicherheit für den Idempotenzschlüssel.",
        )

    idempotency_key = (
        f"delivery:{request.delivery_kind.value.lower()}:{request.occurrence_key}:"
        f"{request.renter_id}"
    )
    attempt = session.scalar(
        select(EmailAttempt).where(
            EmailAttempt.account_id == account_id,
            EmailAttempt.idempotency_key == idempotency_key,
        )
    )
    if attempt is not None:
        provider_statuses = session.scalars(
            select(EmailDeliveryStatusEvent.status).where(
                EmailDeliveryStatusEvent.account_id == account_id,
                EmailDeliveryStatusEvent.email_attempt_id == attempt.id,
            )
        ).all()
        delivered = DeliveryStatus.DELIVERED.value in provider_statuses
        confirmed = _legal_confirmation_exists(session, account_id=account_id, artifact=artifact)
        return RenterDeliveryJobResult(
            account_id=account_id,
            scheduled=1,
            queued=0,
            already_processed=1,
            blocked=(),
            provider_delivered=int(delivered),
            legally_confirmed=int(confirmed),
        )

    attachment = EmailAttachment(
        filename=artifact.filename,
        mime_type=artifact.mime_type,
        content_bytes=artifact.content_bytes,
        sha256=artifact.sha256,
    )
    email = OutgoingEmail(
        to=recipient,
        from_name=request.from_name,
        subject=request.subject_de,
        html_body=request.html_body_de,
        attachments=(attachment,),
        idempotency_key=idempotency_key,
    )
    attempt = EmailAttempt(
        id=new_id(),
        account_id=account_id,
        renter_delivery_artifact_id=artifact.id,
        renter_id=request.renter_id,
        normalized_recipient=recipient,
        sender_address=sender,
        from_name=request.from_name,
        idempotency_key=idempotency_key,
        provider_message_id=None,
        message_snapshot={
            "delivery_kind": request.delivery_kind.value,
            "occurrence_key": request.occurrence_key,
            "subject_de": request.subject_de,
            "artifact_sha256": artifact.sha256,
            "artifact_filename": artifact.filename,
            "claim_state": "CLAIMED_BEFORE_PROVIDER_SEND",
        },
        attempted_at=now,
    )
    session.add(attempt)
    # This flush is staged local evidence, not a crash-safe send claim. Safety
    # across a provider-success/local-rollback window comes from replaying the
    # same provider-enforced idempotency key above.
    session.flush()
    receipt = gateway.send(email)
    session.add(
        EmailDeliveryStatusEvent(
            id=new_id(),
            account_id=account_id,
            email_attempt_id=attempt.id,
            status=receipt.status.value,
            occurred_at=receipt.accepted_at,
            provider_reference=receipt.message_id,
            event_snapshot={"provider_status": receipt.status.value},
        )
    )
    # A bounce or a complaint suppresses the address, but this path does not write
    # that row: `append_recipient_suppression_from_status_m9` derives it from the
    # status event above. Writing it here as well inserted the same
    # (account, recipient, reason, attempt) tuple a second time, which the
    # deduplication trigger skips by returning NULL -- and an ORM insert the database
    # silently skips is a `FlushError`, so every synchronous BOUNCED/COMPLAINED
    # receipt crashed the job. The derivation has one owner, and it is the trigger.
    session.flush()
    confirmed = _legal_confirmation_exists(session, account_id=account_id, artifact=artifact)

    return RenterDeliveryJobResult(
        account_id=account_id,
        scheduled=1,
        queued=int(receipt.status == DeliveryStatus.QUEUED),
        already_processed=0,
        blocked=(),
        provider_delivered=int(receipt.status == DeliveryStatus.DELIVERED),
        legally_confirmed=int(confirmed),
    )


def schedule_renter_deliveries(
    session: Session,
    *,
    account_id: str,
    today: date,
    now: datetime,
    gateway: EmailGateway | None = None,
) -> RenterDeliveryJobResult:
    """Freeze and dispatch source-bound documents under current opt-in schedules."""

    require_aware(now, "now")
    versions = session.scalars(
        select(DeliveryScheduleVersion)
        .where(
            DeliveryScheduleVersion.account_id == account_id,
            DeliveryScheduleVersion.valid_from <= today,
        )
        .order_by(
            DeliveryScheduleVersion.building_id,
            DeliveryScheduleVersion.delivery_kind,
            DeliveryScheduleVersion.version.desc(),
        )
    ).all()
    current: dict[tuple[str, str], DeliveryScheduleVersion] = {}
    for version in versions:
        current.setdefault((version.building_id, version.delivery_kind), version)

    results: list[RenterDeliveryJobResult] = []
    blocked_rows: list[BlockedRenterDelivery] = []
    for version in current.values():
        if not version.enabled:
            continue
        if version.delivery_kind == ScheduledDeliveryKind.UVI.value:
            blocked_rows.append(
                BlockedRenterDelivery(
                    renter_id="",
                    occurrence_key=f"schedule:{version.id}",
                    reason=DeliveryBlockReason.MISSING_ARTIFACT,
                    detail="Für UVI liegen keine unveränderlichen Dokumentbytes vor.",
                )
            )
            continue
        building = session.scalar(
            select(Building).where(
                Building.account_id == account_id,
                Building.id == version.building_id,
            )
        )
        landlord = (
            None
            if building is None or building.landlord_id is None
            else session.scalar(
                select(Landlord).where(
                    Landlord.account_id == account_id,
                    Landlord.id == building.landlord_id,
                )
            )
        )
        if landlord is None or not landlord.legal_name.strip():
            blocked_rows.append(
                BlockedRenterDelivery(
                    renter_id="",
                    occurrence_key=f"schedule:{version.id}",
                    reason=DeliveryBlockReason.PRODUCTION_BLOCKED,
                    detail="Der Vermieter-Absendername fehlt.",
                )
            )
            continue
        snapshot = version.schedule_snapshot
        archive_id = snapshot.get("statement_archive_id")
        statement_id = snapshot.get("statement_id")
        occurrence_key = snapshot.get("occurrence_key")
        period = snapshot.get("statement_period")
        valid_binding = (
            isinstance(archive_id, str)
            and bool(archive_id.strip())
            and isinstance(statement_id, str)
            and bool(statement_id.strip())
            and isinstance(occurrence_key, str)
            and bool(occurrence_key.strip())
            and isinstance(period, dict)
            and isinstance(period.get("period_start"), str)
            and isinstance(period.get("period_end"), str)
        )
        if not valid_binding:
            blocked_rows.append(
                BlockedRenterDelivery(
                    renter_id="",
                    occurrence_key=f"schedule:{version.id}",
                    reason=DeliveryBlockReason.MISSING_ARTIFACT,
                    detail=(
                        "Der Zustellplan bindet keine eindeutige Abrechnung, "
                        "Abrechnungsperiode und Fälligkeit."
                    ),
                )
            )
            continue
        assert isinstance(archive_id, str)
        assert isinstance(statement_id, str)
        assert isinstance(occurrence_key, str)
        assert isinstance(period, dict)
        try:
            period_start = date.fromisoformat(cast(str, period["period_start"]))
            period_end = date.fromisoformat(cast(str, period["period_end"]))
        except (KeyError, TypeError, ValueError):
            blocked_rows.append(
                BlockedRenterDelivery(
                    renter_id="",
                    occurrence_key=occurrence_key,
                    reason=DeliveryBlockReason.MISSING_ARTIFACT,
                    detail="Die gebundene Abrechnungsperiode ist ungültig.",
                )
            )
            continue
        if period_end < period_start:
            blocked_rows.append(
                BlockedRenterDelivery(
                    renter_id="",
                    occurrence_key=occurrence_key,
                    reason=DeliveryBlockReason.MISSING_ARTIFACT,
                    detail="Die gebundene Abrechnungsperiode ist ungültig.",
                )
            )
            continue
        # Select only the immutable archive named by the schedule.  Filtering
        # the returned rows again keeps deterministic test doubles honest and
        # prevents an adapter/session bug from widening this to archive history.
        archive = next(
            (
                row
                for row in session.scalars(
                    select(StatementArchive).where(
                        StatementArchive.account_id == account_id,
                        StatementArchive.id == archive_id,
                        StatementArchive.audience == "TENANT",
                    )
                ).all()
                if row.id == archive_id
            ),
            None,
        )
        if archive is None or archive.statement_id != statement_id or archive.tenancy_id is None:
            blocked_rows.append(
                BlockedRenterDelivery(
                    renter_id="",
                    occurrence_key=occurrence_key,
                    reason=DeliveryBlockReason.MISSING_ARTIFACT,
                    detail="Die im Zustellplan gebundene Abrechnung fehlt oder passt nicht.",
                )
            )
            continue
        canonical_occurrence = f"annual-statement:{statement_id}:{archive.id}:{archive.tenancy_id}"
        statement = session.scalar(
            select(Statement).where(
                Statement.account_id == account_id,
                Statement.id == statement_id,
            )
        )
        statement_binding_matches = statement is None or (
            statement.building_id == version.building_id
            and statement.period_start == period_start
            and statement.period_end == period_end
        )
        if occurrence_key != canonical_occurrence or not statement_binding_matches:
            blocked_rows.append(
                BlockedRenterDelivery(
                    renter_id="",
                    occurrence_key=occurrence_key,
                    reason=DeliveryBlockReason.PRODUCTION_BLOCKED,
                    detail=(
                        "Die Abrechnung, Periode oder Fälligkeitskennung des "
                        "Zustellplans stimmt nicht mit der eingefrorenen Quelle überein."
                    ),
                )
            )
            continue
        renter_ids = list(
            session.scalars(
                select(TenancyParty.renter_id).where(
                    TenancyParty.account_id == account_id,
                    TenancyParty.tenancy_id == archive.tenancy_id,
                )
            ).all()
        )
        candidates = renter_ids or [""]
        for renter_id in candidates:
            frozen = freeze_renter_delivery_artifact(
                session,
                account_id=account_id,
                source_kind=ScheduledDeliveryKind.ANNUAL_STATEMENT,
                source_id=archive.id,
                renter_id=renter_id,
                occurrence_key=occurrence_key,
                now=now,
            )
            if frozen.artifact is None:
                blocked_rows.append(
                    BlockedRenterDelivery(
                        renter_id=renter_id,
                        occurrence_key=occurrence_key,
                        reason=frozen.blocked_reason or DeliveryBlockReason.MISSING_ARTIFACT,
                        detail=(
                            frozen.detail or "Zustelldokument konnte nicht eingefroren werden."
                        ),
                    )
                )
                continue
            artifact = frozen.artifact
            request = RenterDeliveryRequest(
                building_id=artifact.building_id,
                renter_id=artifact.renter_id,
                delivery_kind=ScheduledDeliveryKind.ANNUAL_STATEMENT,
                occurrence_key=artifact.occurrence_key,
                subject_de="Ihre Betriebskostenabrechnung",
                html_body_de="Das angeforderte Dokument finden Sie im Anhang.",
                from_name=landlord.legal_name,
                sender_address="zustellung@lokara.de",
                schedule_version_id=version.id,
                artifact_id=artifact.id,
            )
            results.append(
                dispatch_renter_artifact(
                    session,
                    account_id=account_id,
                    today=today,
                    now=now,
                    request=request,
                    gateway=gateway,
                )
            )
    return RenterDeliveryJobResult(
        account_id=account_id,
        scheduled=sum(item.scheduled for item in results),
        queued=sum(item.queued for item in results),
        already_processed=sum(item.already_processed for item in results),
        blocked=tuple(blocked_rows) + tuple(block for item in results for block in item.blocked),
        provider_delivered=sum(item.provider_delivered for item in results),
        legally_confirmed=sum(item.legally_confirmed for item in results),
    )


def run_for_accounts[T](
    engine: Engine, account_ids: Sequence[str], job: Callable[[Session, str], T]
) -> tuple[T, ...]:
    """Run one job once per account id, each in its own RLS-scoped transaction.

    The ids come from the caller. A scheduler that wanted to discover them would
    need a second pre-context read, and `CLAUDE.md` § 3.3 allows exactly one —
    `docs/15` § 5.6 records that gap as open rather than closing it here.

    The session comes from `deps.job_account_session` rather than
    `account_scoped_session` directly: `scripts/check_pre_context_reads.py` keeps
    every RLS session boundary in `deps.py`, and a job is not an exception to that.
    """
    results: list[T] = []
    for account_id in account_ids:
        with job_account_session(engine, account_id) as session:
            results.append(job(session, account_id))
    return tuple(results)
