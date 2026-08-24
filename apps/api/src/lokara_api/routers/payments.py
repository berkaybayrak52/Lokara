"""Owner-scoped payment routes from M6-C2 and M6-C3a (docs/15).

M6-C2 supplies bank import/list, receivable list and Page-01 handoff routes. M6-C3a
adds matching-profile upsert, match execution, grouped proposals, final decisions
and the immutable payment-ledger list. The calculation lives in
`packages/matching-engine`, normalization in `packages/adapters`, and persistence
orchestration in `matching_service`; this router enforces the HTTP boundary and
owner authorization without copying those rules.

The C3b job entrypoints and C3c landlord Zahlungen screen remain future work.
"""

from datetime import UTC, date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from lokara_adapters import StubBankGateway
from lokara_db import (
    BankAccount,
    BankTransaction,
    Receivable,
    Statement,
    StatementSettlement,
    StatementStatus,
    Tenancy,
    TenancyParty,
    new_id,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

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
