"""M5 role and building authorization on top of account RLS.

RLS isolates accounts.  This module supplies the narrower relationship check
inside an account: an employee may only reach buildings assigned to their live
membership.  Keep it explicit at each resource boundary so an id-only route
cannot accidentally bypass the building relationship.
"""

from dataclasses import dataclass

from fastapi import HTTPException
from lokara_db import Building, Role
from sqlalchemy import select

from .deps import PathAccountSession


@dataclass(frozen=True)
class PortalScope:
    role: Role
    building_ids: frozenset[str]
    membership_id: str


def _scope(session: PathAccountSession) -> PortalScope:
    scope = session.info.get("portal_scope")
    if not isinstance(scope, PortalScope):
        raise RuntimeError("portal authorization scope is missing")
    return scope


def require_building(session: PathAccountSession, building_id: str) -> Building:
    """Return a visible active building, otherwise use the anti-enumeration 404."""
    scope = _scope(session)
    if scope.role is Role.EMPLOYEE and building_id not in scope.building_ids:
        raise HTTPException(status_code=404, detail="Building not found")
    building = session.scalar(
        select(Building).where(Building.id == building_id, Building.archived_at.is_(None))
    )
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


def require_resource_building(session: PathAccountSession, building_id: str) -> None:
    """Check an id-only resource after its owning building has been resolved."""
    require_building(session, building_id)


def visible_building_ids(session: PathAccountSession) -> frozenset[str] | None:
    """``None`` means an owner and therefore no additional building filter."""
    scope = _scope(session)
    return None if scope.role is Role.OWNER else scope.building_ids


def default_building_id(session: PathAccountSession) -> str | None:
    """Resolve an account-level route for an employee without guessing a building."""
    scope = _scope(session)
    if scope.role is Role.OWNER:
        return None
    if not scope.building_ids:
        raise HTTPException(status_code=404, detail="No assigned building found")
    if len(scope.building_ids) > 1:
        raise HTTPException(status_code=422, detail="Bitte ein Objekt auswählen.")
    return next(iter(scope.building_ids))


def require_owner(session: PathAccountSession) -> None:
    if _scope(session).role is not Role.OWNER:
        raise HTTPException(status_code=403, detail="Only owners may create buildings")
