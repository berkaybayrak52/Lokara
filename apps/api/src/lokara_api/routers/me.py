"""GET /me — the Person's relationships, from which the left nav is derived.

The nav is navigation only (docs/04): every request re-authorizes
independently, so this endpoint never grants anything — it just lists what
exists. No membership is not an error here (the dashboard offers "Demo-Szenario
laden" in that case), so this returns an empty list instead of 403.
"""

from fastapi import APIRouter
from lokara_db import Account, Membership
from sqlalchemy import select

from ..auth import RequireAuth
from ..deps import raw_account_scoped_session
from ..schemas import MeAccount, MeResponse

router = APIRouter()


@router.get("/me")
def me(auth: RequireAuth) -> MeResponse:
    # TODO(M5): a person-scoped RLS policy will let this list *all* of the
    # person's accounts; until then RLS limits the view to the claimed account.
    accounts: list[MeAccount] = []
    with raw_account_scoped_session(auth.account_id) as session:
        rows = session.execute(
            select(Membership, Account)
            .join(Account, Membership.account_id == Account.id)
            .where(
                Membership.person_id == auth.person_id,
                Membership.revoked_at.is_(None),
            )
        ).all()
        for membership, account in rows:
            accounts.append(
                MeAccount(
                    id=account.id,
                    name=account.name,
                    role=membership.role.value,
                    shape=account.shape.value,
                )
            )
    return MeResponse(person_id=auth.person_id, accounts=accounts)
