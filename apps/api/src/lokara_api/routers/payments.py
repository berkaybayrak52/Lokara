"""Owner-scoped payment routes from M6-C2 and M6-C3a (docs/15).

M6-C2 supplies bank import/list, receivable list and Page-01 handoff routes. M6-C3a
adds matching-profile upsert, match execution, grouped proposals, final decisions
and the immutable payment-ledger list. The calculation lives in
`packages/matching-engine`, normalization in `packages/adapters`, and persistence
orchestration in `matching_service`; this router enforces the HTTP boundary and
owner authorization without copying those rules.

UI-07 adds the server-owned payment workspace and append-only ignore history on
top of those shipped M6 contracts. Source-blocked manual-payment and recurring-
receivable rules remain inactive.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from lokara_adapters import StubBankGateway
from lokara_db import (
    BankAccount,
    BankTransaction,
    BankTransactionClassificationEvent,
    Building,
    MatchConfirmation,
    MatchProposal,
    PaymentAllocation,
    PaymentLedgerEntry,
    Receivable,
    Renter,
    Statement,
    StatementSettlement,
    StatementStatus,
    Tenancy,
    TenancyParty,
    Unit,
    new_id,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select

from ..auth import AuthContext, require_auth
from ..authorization import require_owner
from ..bank_sync import ConsentExpiredError, import_transactions
from ..deps import PathAccountSession
from ..matching_service import (
    MatchingConflictError,
    MatchingNotFoundError,
    decide_match,
    list_ledger,
    list_proposals,
    run_match,
    upsert_matching_profile,
)

router = APIRouter(prefix="/a/{account_id}")

# docs/15 § 3.2: an nk_nachzahlung carries no rent, garage or advance component.
# See migration 0018 for why parking it in nk_advance_cents would be a defect.
_NO_COMPONENTS = {
    "base_rent_cents": 0,
    "nk_advance_cents": 0,
    "heating_advance_cents": 0,
    "garage_cents": 0,
}
_PAGE01_SOURCE = "PAGE01_STATEMENT"

# docs/15 § 5.6: a pull without a standing PSD2 consent is refused, not defaulted.
_CONSENT_DETAIL = {
    "consent_missing": (
        "Für dieses Bankkonto ist keine PSD2-Einwilligung hinterlegt. "
        "Bitte verbinden Sie das Konto erneut."
    ),
    "consent_expired": (
        "Die PSD2-Einwilligung für dieses Bankkonto ist abgelaufen. "
        "Bitte verbinden Sie das Konto erneut."
    ),
}


class HandoffIn(BaseModel):
    """`due_date` is required and has no default, on purpose.

    The Zahlungsfrist for a Nachzahlung is `verify-before-production` in the
    authoritative register: there is no statutory deadline — the claim falls due
    on receipt of a proper statement — and the customary 30 days is a flagged
    `Konvention`. Defaulting here would silently turn that convention into
    Lokara's answer on every statement. The landlord knows the date they granted;
    the API asks for it.
    """

    due_date: date


class ImportWindowIn(BaseModel):
    window_from: date
    window_to: date = Field(description="exclusive — the window is half-open")


class ReceivableOut(BaseModel):
    id: str
    renter_id: str
    tenancy_id: str
    source_type: str
    source_id: str | None
    period: str
    due_date: date
    expected_cents: int
    open_cents: int
    status: str
    category: str


class ReceivableListOut(BaseModel):
    receivables: list[ReceivableOut]


class BankTransactionOut(BaseModel):
    id: str
    bank_account_id: str
    provider_transaction_id: str
    amount_cents: int
    bank_booking_date: date
    counterpart_name: str | None
    purpose: str | None
    is_potential_duplicate: bool


class BankTransactionListOut(BaseModel):
    transactions: list[BankTransactionOut]


class ImportResultOut(BaseModel):
    imported: int
    skipped_as_duplicate: int


class MatchingProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surname: str = Field(min_length=1, max_length=200)
    payment_code: str | None = Field(default=None, max_length=200)


class MatchingDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["confirmed", "rejected", "duplicate"]


class ClassificationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["ignored", "restored"]
    reason: str | None = Field(default=None, max_length=200)


class BulkClassificationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_ids: list[str] = Field(min_length=1, max_length=50)
    action: Literal["ignored", "restored"]
    reason: str | None = Field(default=None, max_length=200)


class PaymentAccountOut(BaseModel):
    id: str
    display_name: str
    masked_iban: str
    provider_label: str
    consent_status: Literal["active", "expiring", "reconnect"]
    consent_expires_at: datetime | None
    last_sync_at: datetime | None
    sync_status: Literal["idle", "running", "failed"]


class PaymentAccountListOut(BaseModel):
    accounts: list[PaymentAccountOut]


class PaymentWorkspaceHistoryOut(BaseModel):
    kind: str
    label: str
    actor_person_id: str | None
    created_at: datetime


class PaymentWorkspaceRowOut(BaseModel):
    id: str
    bank_account_id: str
    account_label: str
    amount_cents: int
    direction: Literal["incoming", "outgoing"]
    booking_date: date
    value_date: date
    counterpart_name: str | None
    counterpart_iban_masked: str | None
    purpose: str | None
    source_label: str
    status: Literal["unassigned", "review", "assigned", "partial", "ignored"]
    status_label: str
    ignored: bool
    assignment_label: str | None
    receivable_id: str | None
    tenancy_id: str | None
    building_id: str | None
    building_name: str | None
    unit_label: str | None
    renter_name: str | None
    expected_cents: int | None
    open_cents: int | None
    confidence: int | None
    match_reason_de: str | None
    available_actions: list[str]
    history: list[PaymentWorkspaceHistoryOut]


class PaymentWorkspaceOut(BaseModel):
    rows: list[PaymentWorkspaceRowOut]
    next_cursor: str | None
    counts: dict[str, int]
    total: int


def _matching_http_error(error: Exception) -> HTTPException:
    if isinstance(error, MatchingNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    return HTTPException(status_code=409, detail=str(error))


def _receivable_out(row: Receivable) -> ReceivableOut:
    return ReceivableOut(
        id=row.id,
        renter_id=row.renter_id,
        tenancy_id=row.tenancy_id,
        source_type=row.source_type,
        source_id=row.source_id,
        period=row.period,
        due_date=row.due_date,
        expected_cents=row.expected_cents,
        open_cents=row.open_cents,
        status=row.status,
        category=row.category,
    )


@router.post("/statements/{statement_id}/receivables", status_code=201)
def create_receivables_from_statement(
    statement_id: str,
    body: HandoffIn,
    session: PathAccountSession,
) -> ReceivableListOut:
    """`BANKMATCH-F12`: a finalized RECEIVABLE Saldo becomes an open receivable.

    The cents are **copied** from the settlement, never recomputed. `F12`'s 24,500
    is not a round number by accident: a recomputation from the statement would
    have to redo the whole Page 01 allocation and could land a cent away, and the
    settlement is the immutable record of what the landlord finalized.

    Only a positive Saldo creates an obligation. A CREDIT_REFUND is the landlord's
    debt to the renter and is not a receivable; V1 records credit and never pays
    it out (`docs/15` § 9).
    """
    require_owner(session)

    statement = session.get(Statement, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Abrechnung nicht gefunden")
    if statement.status is not StatementStatus.FINALIZED:
        raise HTTPException(
            status_code=409,
            detail="Nur eine finalisierte Abrechnung erzeugt eine Forderung.",
        )

    already = session.scalar(
        select(Receivable.id).where(
            Receivable.source_type == _PAGE01_SOURCE,
            Receivable.source_id == statement_id,
        )
    )
    if already is not None:
        # Running the handoff twice would double a renter's debt, and no later
        # reconciliation could tell the second row from a genuine second claim.
        # `uq_receivable_source` (migration 0019) is what actually enforces this —
        # this check is only here to turn the race into a clean 409.
        raise HTTPException(
            status_code=409,
            detail="Für diese Abrechnung wurden bereits Forderungen erzeugt.",
        )

    settlements = session.scalars(
        select(StatementSettlement).where(
            StatementSettlement.statement_id == statement_id,
            StatementSettlement.kind == "RECEIVABLE",
        )
    ).all()

    period = f"{statement.period_end:%Y-%m}"
    created: list[Receivable] = []
    for settlement in settlements:
        # All parties, not the first one. `tenancy_party` is unique on
        # (tenancy_id, renter_id), so a couple on one Mietvertrag is two rows and
        # entirely normal. `Session.scalar()` would return one and discard the rest
        # with no error and no ORDER BY — the Nachzahlung would land on an arbitrary
        # spouse, and a payment from the other one would then find no receivable and
        # fall to Unmatched with nothing warning anyone.
        parties = session.scalars(
            select(TenancyParty.renter_id)
            .where(TenancyParty.tenancy_id == settlement.tenancy_id)
            .order_by(TenancyParty.renter_id)
        ).all()
        if len(parties) != 1:
            # Same refusal posture as the missing due date: docs/15 says nothing about
            # splitting one Nachzahlung across joint renters, so Lokara does not choose.
            raise HTTPException(
                status_code=409,
                detail=(
                    "Dieses Mietverhältnis hat keinen oder mehr als einen Mieter. "
                    "Die Aufteilung einer Nachzahlung auf mehrere Mieter ist nicht "
                    "festgelegt; die Forderung wird nicht erzeugt."
                ),
            )
        renter_id = parties[0]

        # A correction is a new statement id, so keying the guard above only on
        # statement_id let v2 of the same period bill this renter a second time for
        # the same Saldo. Scoped per tenancy, not per period: two tenancies in one
        # building period each legitimately get their own Nachzahlung. Superseding an
        # existing receivable needs a supersede path M6-C2 does not have, so this
        # refuses rather than guessing.
        if (
            session.scalar(
                select(Receivable.id).where(
                    Receivable.source_type == _PAGE01_SOURCE,
                    Receivable.category == "nk_nachzahlung",
                    Receivable.tenancy_id == settlement.tenancy_id,
                    Receivable.period == period,
                )
            )
            is not None
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Für dieses Mietverhältnis und diesen Abrechnungszeitraum besteht "
                    "bereits eine Nachzahlungsforderung. Eine Korrekturabrechnung "
                    "ersetzt sie nicht automatisch."
                ),
            )
        created.append(
            Receivable(
                id=new_id(),
                account_id=settlement.account_id,
                renter_id=renter_id,
                tenancy_id=settlement.tenancy_id,
                source_type=_PAGE01_SOURCE,
                source_id=statement_id,
                period=period,
                due_date=body.due_date,
                expected_cents=settlement.amount_cents,
                open_cents=settlement.amount_cents,
                status="open",
                category="nk_nachzahlung",
                open_costs_cents=0,
                open_interest_cents=0,
                open_principal_cents=settlement.amount_cents,
                stored_reference=None,
                **_NO_COMPONENTS,
            )
        )
    session.add_all(created)
    # account_scoped_session owns the transaction and commits on clean exit;
    # flushing is enough to surface a constraint violation as a 4xx here.
    session.flush()
    return ReceivableListOut(receivables=[_receivable_out(r) for r in created])


@router.get("/receivables")
def list_receivables(session: PathAccountSession) -> ReceivableListOut:
    require_owner(session)
    rows = session.scalars(select(Receivable).order_by(Receivable.due_date, Receivable.id)).all()
    return ReceivableListOut(receivables=[_receivable_out(r) for r in rows])


@router.post("/bank-accounts/{bank_account_id}/transactions/import")
def import_bank_transactions(
    account_id: str,
    bank_account_id: str,
    body: ImportWindowIn,
    session: PathAccountSession,
) -> ImportResultOut:
    """Pull normalized transactions from the AIS adapter into storage.

    An exact re-import is skipped rather than rejected (`docs/15` § 3.1): the same
    `provider_transaction_id` on the same bank account is the movement already
    processed, so it creates no second normalized row and no second ledger entry.
    That is distinct from `is_potential_duplicate`, which keeps its transaction and
    forces Review.

    The dedupe rule and the PSD2 consent precondition live in `bank_sync`, because
    M6-C3b's scheduled sync pulls through the same primitive; two copies of the
    `docs/15` § 3.1 identity rule could drift. A missing or expired
    `consent_expires_at` refuses the pull with 409 rather than assuming one.

    finAPI stays stubbed (`docs/01` D7). The gateway is constructed here rather
    than injected because there is exactly one implementation until the real AISP
    slice; that is where a port dependency belongs.
    """
    require_owner(session)

    # CLAUDE.md § 3.3: this URL carries two relationships, and both are verified.
    # `require_owner` covers the account; this covers the bank account. The lookup
    # runs under the RLS-scoped session, so a bank account belonging to another
    # account is simply not there.
    #
    # The composite (bank_account_id, account_id) FK from migration 0017 already
    # makes the cross-account row unrepresentable, so isolation never depended on
    # this check — but without it the caller gets a 500 from an unhandled
    # IntegrityError instead of a 404, and the endpoint has trusted a path
    # parameter it never verified. Relying on the stub returning nothing for an
    # unknown id is not a substitute: that is the stub's behaviour, not the port's.
    if session.get(BankAccount, bank_account_id) is None:
        raise HTTPException(status_code=404, detail="Bankkonto nicht gefunden")

    try:
        outcome = import_transactions(
            session,
            account_id=account_id,
            bank_account_id=bank_account_id,
            window_from=body.window_from,
            window_to=body.window_to,
            gateway=StubBankGateway(),
            now=datetime.now(UTC),
        )
    except ConsentExpiredError as error:
        raise HTTPException(status_code=409, detail=_CONSENT_DETAIL[error.reason]) from error
    return ImportResultOut(
        imported=outcome.imported, skipped_as_duplicate=outcome.skipped_as_duplicate
    )


@router.get("/bank-transactions")
def list_bank_transactions(session: PathAccountSession) -> BankTransactionListOut:
    require_owner(session)
    rows = session.scalars(
        select(BankTransaction).order_by(BankTransaction.bank_booking_date, BankTransaction.id)
    ).all()
    return BankTransactionListOut(
        transactions=[
            BankTransactionOut(
                id=r.id,
                bank_account_id=r.bank_account_id,
                provider_transaction_id=r.provider_transaction_id,
                amount_cents=r.amount_cents,
                bank_booking_date=r.bank_booking_date,
                counterpart_name=r.counterpart_name,
                purpose=r.purpose,
                is_potential_duplicate=r.is_potential_duplicate,
            )
            for r in rows
        ]
    )


def _masked_iban(value: str | None) -> str | None:
    if not value:
        return None
    compact = "".join(value.split())
    return f"•••• {compact[-4:]}" if len(compact) >= 4 else "••••"


@router.get("/payment-workspace/accounts")
def payment_workspace_accounts(session: PathAccountSession) -> PaymentAccountListOut:
    require_owner(session)
    now = datetime.now(UTC)
    accounts = session.scalars(select(BankAccount).order_by(BankAccount.display_name)).all()
    return PaymentAccountListOut(
        accounts=[
            PaymentAccountOut(
                id=row.id,
                display_name=row.display_name,
                masked_iban=_masked_iban(row.normalized_iban) or "••••",
                provider_label="Demo-Bank" if row.provider.endswith("stub") else row.provider,
                consent_status=(
                    "reconnect"
                    if row.consent_expires_at is None or row.consent_expires_at <= now
                    else "expiring"
                    if row.consent_expires_at <= now + timedelta(days=14)
                    else "active"
                ),
                consent_expires_at=row.consent_expires_at,
                # The current bank model has no persisted job-run projection.
                # Absence remains null/idle instead of a fabricated timestamp.
                last_sync_at=None,
                sync_status="idle",
            )
            for row in accounts
        ]
    )


def _workspace_rows(
    session: PathAccountSession,
    *,
    bank_account_id: str | None,
    direction: Literal["all", "incoming", "outgoing"],
    search: str | None,
    date_from: date,
    date_to: date,
) -> list[PaymentWorkspaceRowOut]:
    query = select(BankTransaction).where(
        BankTransaction.bank_booking_date >= date_from,
        BankTransaction.bank_booking_date <= date_to,
    )
    if bank_account_id is not None:
        query = query.where(BankTransaction.bank_account_id == bank_account_id)
    if direction == "incoming":
        query = query.where(BankTransaction.amount_cents >= 0)
    elif direction == "outgoing":
        query = query.where(BankTransaction.amount_cents < 0)
    if search:
        needle = f"%{search.strip()}%"
        query = query.where(
            or_(
                BankTransaction.counterpart_name.ilike(needle),
                BankTransaction.purpose.ilike(needle),
            )
        )
    transactions = session.scalars(
        query.order_by(BankTransaction.bank_booking_date.desc(), BankTransaction.id.desc())
    ).all()
    if not transactions:
        return []

    transaction_ids = [row.id for row in transactions]
    accounts = {
        row.id: row
        for row in session.scalars(
            select(BankAccount).where(
                BankAccount.id.in_({row.bank_account_id for row in transactions})
            )
        ).all()
    }
    proposals = session.scalars(
        select(MatchProposal)
        .where(MatchProposal.bank_transaction_id.in_(transaction_ids))
        .order_by(MatchProposal.bank_transaction_id, MatchProposal.rank)
    ).all()
    proposal_by_transaction: dict[str, MatchProposal] = {}
    for proposal_row in proposals:
        proposal_by_transaction.setdefault(proposal_row.bank_transaction_id, proposal_row)
    proposal_ids = [row.id for row in proposals]
    confirmations = {
        row.match_proposal_id: row
        for row in session.scalars(
            select(MatchConfirmation).where(MatchConfirmation.match_proposal_id.in_(proposal_ids))
        ).all()
    }
    ledger_rows = session.scalars(
        select(PaymentLedgerEntry).where(
            PaymentLedgerEntry.bank_transaction_id.in_(transaction_ids)
        )
    ).all()
    ledger_by_transaction = {row.bank_transaction_id: row for row in ledger_rows}
    ledger_ids = [row.id for row in ledger_rows]
    allocations = session.scalars(
        select(PaymentAllocation).where(PaymentAllocation.ledger_entry_id.in_(ledger_ids))
    ).all()
    allocation_by_ledger: dict[str, PaymentAllocation] = {}
    for allocation_row in allocations:
        allocation_by_ledger.setdefault(allocation_row.ledger_entry_id, allocation_row)

    receivable_ids = {row.receivable_id for row in proposals if row.receivable_id is not None} | {
        row.receivable_id for row in allocations
    }
    receivables = {
        row.id: row
        for row in session.scalars(
            select(Receivable).where(Receivable.id.in_(receivable_ids))
        ).all()
    }
    tenancy_ids = {row.tenancy_id for row in receivables.values()}
    tenancy_context = {
        tenancy.id: (tenancy, unit, building)
        for tenancy, unit, building in session.execute(
            select(Tenancy, Unit, Building)
            .join(Unit, and_(Unit.id == Tenancy.unit_id, Unit.account_id == Tenancy.account_id))
            .join(
                Building,
                and_(Building.id == Unit.building_id, Building.account_id == Unit.account_id),
            )
            .where(Tenancy.id.in_(tenancy_ids))
        ).all()
    }
    renter_ids = {row.renter_id for row in receivables.values()}
    renters = {
        row.id: row
        for row in session.scalars(select(Renter).where(Renter.id.in_(renter_ids))).all()
    }
    classification_rows = session.scalars(
        select(BankTransactionClassificationEvent)
        .where(BankTransactionClassificationEvent.bank_transaction_id.in_(transaction_ids))
        .order_by(
            BankTransactionClassificationEvent.created_at,
            BankTransactionClassificationEvent.id,
        )
    ).all()
    classification_by_transaction: dict[str, list[BankTransactionClassificationEvent]] = {}
    for event in classification_rows:
        classification_by_transaction.setdefault(event.bank_transaction_id, []).append(event)

    result: list[PaymentWorkspaceRowOut] = []
    for transaction in transactions:
        proposal = proposal_by_transaction.get(transaction.id)
        ledger = ledger_by_transaction.get(transaction.id)
        allocation = allocation_by_ledger.get(ledger.id) if ledger is not None else None
        receivable_id = (
            allocation.receivable_id
            if allocation is not None
            else proposal.receivable_id
            if proposal is not None
            else None
        )
        receivable = receivables.get(receivable_id) if receivable_id is not None else None
        events = classification_by_transaction.get(transaction.id, [])
        ignored = bool(events and events[-1].action == "IGNORED")
        if ignored:
            status = "ignored"
            status_label = "Ignoriert"
        elif ledger is not None and allocation is not None and allocation.after_status == "partial":
            status = "partial"
            status_label = "Teilweise"
        elif ledger is not None:
            status = "assigned"
            status_label = "Zugeordnet"
        elif proposal is not None and proposal.decision == "NEEDS_REVIEW":
            status = "review"
            status_label = "Prüfen"
        else:
            status = "unassigned"
            status_label = "Nicht zugeordnet"
        context = tenancy_context.get(receivable.tenancy_id) if receivable is not None else None
        renter = renters.get(receivable.renter_id) if receivable is not None else None
        account = accounts.get(transaction.bank_account_id)
        history = [
            PaymentWorkspaceHistoryOut(
                kind=event.action.lower(),
                label=(
                    f"Ignoriert · {event.reason}"
                    if event.action == "IGNORED" and event.reason
                    else "Ignoriert"
                    if event.action == "IGNORED"
                    else "Ignorieren aufgehoben"
                ),
                actor_person_id=event.actor_person_id,
                created_at=event.created_at,
            )
            for event in events
        ]
        if proposal is not None:
            confirmation = confirmations.get(proposal.id)
            history.insert(
                0,
                PaymentWorkspaceHistoryOut(
                    kind="matching",
                    label=(
                        f"Zuordnungsvorschlag · {proposal.reason_de}"
                        if proposal.reason_de
                        else "Zuordnungsvorschlag erstellt"
                    ),
                    actor_person_id=(confirmation.confirmed_by if confirmation else None),
                    created_at=proposal.created_at,
                ),
            )
        assignment_label = None
        if receivable is not None:
            assignment_label = " · ".join(
                part
                for part in (
                    renter.legal_name if renter is not None else None,
                    context[1].label if context is not None else None,
                    receivable.period,
                )
                if part
            )
        result.append(
            PaymentWorkspaceRowOut(
                id=transaction.id,
                bank_account_id=transaction.bank_account_id,
                account_label=account.display_name if account else "Bankkonto",
                amount_cents=transaction.amount_cents,
                direction="incoming" if transaction.amount_cents >= 0 else "outgoing",
                booking_date=transaction.bank_booking_date,
                value_date=transaction.value_date,
                counterpart_name=transaction.counterpart_name,
                counterpart_iban_masked=_masked_iban(transaction.counterpart_iban),
                purpose=transaction.purpose,
                source_label=(
                    "Demo-Bank" if account and account.provider.endswith("stub") else "Bank"
                ),
                status=status,  # type: ignore[arg-type]
                status_label=status_label,
                ignored=ignored,
                assignment_label=assignment_label,
                receivable_id=receivable.id if receivable else None,
                tenancy_id=receivable.tenancy_id if receivable else None,
                building_id=context[2].id if context else None,
                building_name=context[2].name if context else None,
                unit_label=context[1].label if context else None,
                renter_name=renter.legal_name if renter else None,
                expected_cents=receivable.expected_cents if receivable else None,
                open_cents=receivable.open_cents if receivable else None,
                confidence=proposal.confidence if proposal else None,
                match_reason_de=proposal.reason_de if proposal else None,
                available_actions=(
                    ["restore"] if ignored else [] if ledger is not None else ["ignore", "assign"]
                ),
                history=history,
            )
        )
    return result


@router.get("/payment-workspace/transactions")
def payment_workspace_transactions(
    session: PathAccountSession,
    cursor: Annotated[str | None, Query()] = None,
    status: Annotated[
        Literal["all", "unassigned", "review", "assigned", "partial", "ignored"], Query()
    ] = "all",
    bank_account_id: Annotated[str | None, Query()] = None,
    direction: Annotated[Literal["all", "incoming", "outgoing"], Query()] = "all",
    search: Annotated[str | None, Query(max_length=200)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
) -> PaymentWorkspaceOut:
    require_owner(session)
    today = date.today()
    rows = _workspace_rows(
        session,
        bank_account_id=bank_account_id,
        direction=direction,
        search=search,
        date_from=date_from or today - timedelta(days=100),
        date_to=date_to or today,
    )
    counts = {key: 0 for key in ("all", "unassigned", "review", "assigned", "partial", "ignored")}
    for row in rows:
        counts["all"] += 1
        counts[row.status] += 1
    filtered = rows if status == "all" else [row for row in rows if row.status == status]
    start = 0
    if cursor is not None:
        start = next((index + 1 for index, row in enumerate(filtered) if row.id == cursor), 0)
    page = filtered[start : start + limit]
    next_cursor = page[-1].id if start + limit < len(filtered) and page else None
    return PaymentWorkspaceOut(
        rows=page, next_cursor=next_cursor, counts=counts, total=len(filtered)
    )


@router.post("/bank-transactions/{transaction_id}/classification")
def classify_bank_transaction(
    transaction_id: str,
    body: ClassificationIn,
    session: PathAccountSession,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict[str, object]:
    require_owner(session)
    return _append_classification(
        session,
        transaction_id=transaction_id,
        action=body.action,
        reason=body.reason,
        actor_person_id=auth.person_id,
    )


def _append_classification(
    session: PathAccountSession,
    *,
    transaction_id: str,
    action: Literal["ignored", "restored"],
    reason: str | None,
    actor_person_id: str,
) -> dict[str, object]:
    transaction = session.get(BankTransaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Bankumsatz nicht gefunden")
    if (
        session.scalar(
            select(PaymentLedgerEntry.id).where(
                PaymentLedgerEntry.bank_transaction_id == transaction_id
            )
        )
        is not None
    ):
        raise HTTPException(
            status_code=409,
            detail="Ein bereits gebuchter Zahlungsnachweis kann nicht ignoriert werden.",
        )
    latest = session.scalar(
        select(BankTransactionClassificationEvent)
        .where(BankTransactionClassificationEvent.bank_transaction_id == transaction_id)
        .order_by(
            BankTransactionClassificationEvent.created_at.desc(),
            BankTransactionClassificationEvent.id.desc(),
        )
        .limit(1)
    )
    requested = "IGNORED" if action == "ignored" else "RESTORED"
    if latest is not None and latest.action == requested:
        raise HTTPException(status_code=409, detail="Diese Klassifizierung ist bereits aktiv.")
    if requested == "RESTORED" and (latest is None or latest.action != "IGNORED"):
        raise HTTPException(status_code=409, detail="Dieser Umsatz ist nicht ignoriert.")
    event = BankTransactionClassificationEvent(
        id=new_id(),
        account_id=transaction.account_id,
        bank_transaction_id=transaction.id,
        action=requested,
        reason=reason,
        actor_person_id=actor_person_id,
    )
    session.add(event)
    session.flush()
    return {"id": event.id, "transaction_id": transaction.id, "action": action}


@router.post("/bank-transactions/classification/bulk")
def bulk_classify_bank_transactions(
    body: BulkClassificationIn,
    session: PathAccountSession,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict[str, object]:
    require_owner(session)
    results: list[dict[str, object]] = []
    for transaction_id in dict.fromkeys(body.transaction_ids):
        try:
            result = _append_classification(
                session,
                transaction_id=transaction_id,
                action=body.action,
                reason=body.reason,
                actor_person_id=auth.person_id,
            )
        except HTTPException as error:
            results.append(
                {
                    "transaction_id": transaction_id,
                    "ok": False,
                    "detail": error.detail,
                }
            )
        else:
            results.append({**result, "ok": True, "detail": None})
    return {"results": results}


@router.put("/renters/{renter_id}/matching-profile")
def put_matching_profile(
    renter_id: str,
    body: MatchingProfileIn,
    session: PathAccountSession,
) -> dict[str, object]:
    require_owner(session)
    try:
        return upsert_matching_profile(session, renter_id, body.surname, body.payment_code)
    except (MatchingNotFoundError, MatchingConflictError) as error:
        raise _matching_http_error(error) from error


@router.post("/bank-transactions/{transaction_id}/match")
def match_bank_transaction(
    transaction_id: str,
    session: PathAccountSession,
) -> dict[str, object]:
    require_owner(session)
    try:
        return run_match(session, transaction_id)
    except (MatchingNotFoundError, MatchingConflictError) as error:
        raise _matching_http_error(error) from error


@router.get("/match-proposals")
def get_match_proposals(session: PathAccountSession) -> dict[str, object]:
    require_owner(session)
    return list_proposals(session)


@router.post("/bank-transactions/{transaction_id}/decision")
def decide_bank_transaction(
    transaction_id: str,
    body: MatchingDecisionIn,
    session: PathAccountSession,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict[str, object]:
    require_owner(session)
    try:
        return decide_match(session, transaction_id, body.outcome, auth.person_id)
    except (MatchingNotFoundError, MatchingConflictError) as error:
        raise _matching_http_error(error) from error


@router.get("/payment-ledger")
def get_payment_ledger(session: PathAccountSession) -> dict[str, object]:
    require_owner(session)
    return list_ledger(session)


__all__ = ["router"]


# `Tenancy` is imported for the mapper registry: TenancyParty's scoped FK targets
# it, and a partially-configured registry raises on first query in a process that
# imported only this module.
_ = Tenancy
