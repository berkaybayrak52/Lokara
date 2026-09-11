"""GET /me — the Person's relationships, from which the left nav is derived.

The nav is navigation only (docs/04): every request re-authorizes
independently, so this endpoint never grants anything — it just lists what
exists. No membership is not an error here (the dashboard offers "Demo-Szenario
laden" in that case), so this returns an empty list instead of 403.
"""

from fastapi import APIRouter, HTTPException

from ..auth import RequireAuth
from ..deps import resolve_bootstrap_subject
from ..schemas import MeAccount, MeRenterContext, MeResponse

router = APIRouter()


@router.get("/me")
def me(auth: RequireAuth) -> MeResponse:
    rows = resolve_bootstrap_subject(auth)
    if not rows:
        raise HTTPException(status_code=401, detail="Authenticated subject has no Person")

    accounts: list[MeAccount] = []
    renter_contexts: list[MeRenterContext] = []
    for row in rows:
        if row.context_kind == "RENTER_TENANCY":
            if row.tenancy_id is None:
                raise HTTPException(status_code=500, detail="Invalid bootstrap renter context")
            renter_contexts.append(MeRenterContext(tenancy_id=row.tenancy_id))
            continue
        if row.context_kind == "SUBJECT":
            continue
        if row.context_kind != "MEMBERSHIP":
            raise HTTPException(status_code=500, detail="Invalid bootstrap context kind")
        account_id = row.account_id
        account_name = row.account_name
        account_shape = row.account_shape
        membership_role = row.membership_role
        if account_id is None:
            continue
        if account_name is None or account_shape is None or membership_role is None:
            raise HTTPException(status_code=500, detail="Invalid bootstrap account context")
        accounts.append(
            MeAccount(
                id=account_id,
                name=account_name,
                role=membership_role.value,
                shape=account_shape.value,
            )
        )
    return MeResponse(
        person_id=rows[0].person_id,
        email=rows[0].email,
        accounts=accounts,
        renter_contexts=renter_contexts,
    )
