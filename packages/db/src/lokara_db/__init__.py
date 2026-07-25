"""SQLAlchemy 2.0 models + Alembic migrations + RLS backstop.

Imported by apps/api only — client apps never touch the DB (docs/04).
"""

from .ids import new_id
from .models import (
    ACCOUNT_SCOPED_TABLES,
    Account,
    AccountShape,
    AllocationKeyAssignment,
    Base,
    Building,
    BuildingAssignment,
    CostEntry,
    HeatingCostEntry,
    Landlord,
    Membership,
    Meter,
    MeterReading,
    Person,
    Plan,
    Renter,
    Role,
    SelfUseKind,
    SelfUsePeriod,
    Statement,
    StatementStatus,
    Tenancy,
    TenancyParty,
    Unit,
)
from .session import account_scoped_session, create_db_engine
from .settings import DbSettings, sqlalchemy_url

__version__ = "0.1.0"

__all__ = [
    "ACCOUNT_SCOPED_TABLES",
    "Account",
    "AccountShape",
    "AllocationKeyAssignment",
    "Base",
    "Building",
    "BuildingAssignment",
    "CostEntry",
    "DbSettings",
    "HeatingCostEntry",
    "Landlord",
    "Membership",
    "Meter",
    "MeterReading",
    "Person",
    "Plan",
    "Renter",
    "Role",
    "SelfUseKind",
    "SelfUsePeriod",
    "Statement",
    "StatementStatus",
    "Tenancy",
    "TenancyParty",
    "Unit",
    "account_scoped_session",
    "create_db_engine",
    "new_id",
    "sqlalchemy_url",
]
