"""M6-C2 owner-scoped bank, receivable and Page-01 handoff endpoints (docs/15).

Deliberately thin. The matching decisions live in `packages/matching-engine` and
the normalization in `packages/adapters`; this module only moves rows across the
HTTP boundary and enforces who may do it. No scoring, ordering or settlement rule
is re-expressed here — a second copy of a legal rule is a second thing to get
wrong.

The Zahlungen screen, the confirmation flow and the job entrypoints are M6-C3.
"""

from datetime import date

from fastapi import APIRouter, HTTPException
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
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..authorization import require_owner
from ..deps import PathAccountSession

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
        renter_id = session.scalar(
            select(TenancyParty.renter_id).where(TenancyParty.tenancy_id == settlement.tenancy_id)
        )
        if renter_id is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Zum Mietverhältnis dieser Abrechnung ist kein Mieter hinterlegt; "
                    "die Forderung wird nicht erzeugt."
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

    known = set(
        session.scalars(
            select(BankTransaction.provider_transaction_id).where(
                BankTransaction.bank_account_id == bank_account_id
            )
        ).all()
    )

    imported = 0
    skipped = 0
    for normalized in StubBankGateway().list_transactions(
        bank_account_id, body.window_from, body.window_to
    ):
        if normalized.provider_transaction_id in known:
            skipped += 1
            continue
        session.add(
            BankTransaction(
                id=new_id(),
                account_id=account_id,
                bank_account_id=bank_account_id,
                provider_transaction_id=normalized.provider_transaction_id,
                amount_cents=normalized.amount_cents,
                bank_booking_date=normalized.bank_booking_date,
                finapi_booking_date=normalized.finapi_booking_date,
                value_date=normalized.value_date,
                counterpart_iban=normalized.counterpart_iban,
                counterpart_name=normalized.counterpart_name,
                purpose=normalized.purpose,
                end_to_end_reference=normalized.end_to_end_reference,
                counterpart_mandate_reference=normalized.counterpart_mandate_reference,
                bank_transaction_code=normalized.bank_transaction_code,
                provider_type=normalized.provider_type,
                is_potential_duplicate=normalized.is_potential_duplicate,
            )
        )
        known.add(normalized.provider_transaction_id)
        imported += 1
    session.flush()
    return ImportResultOut(imported=imported, skipped_as_duplicate=skipped)


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


__all__ = ["router"]


# `Tenancy` is imported for the mapper registry: TenancyParty's scoped FK targets
# it, and a partially-configured registry raises on first query in a process that
# imported only this module.
_ = Tenancy
