"""Demo seed — the €1,200 scenario from lokara-arch.md §10 (port of prisma/seed.ts).

One building, three units (50/30/20 m²), Renter 2 moves out 30 Jun 2025
(valid_to exclusive → 2025-07-01). Idempotent: merge() on fixed ids.

Unlike the TS seed this also creates the OWNER Membership — the FastAPI
account_session dependency really checks it (403 without).

Runs as the owner role (DIRECT_URL); locally that's the docker superuser which
bypasses the FORCEd RLS. TODO(supabase): the Supabase owner is a non-superuser,
so there the seed must set the app.account_id context first.
"""

from datetime import date

from sqlalchemy.orm import Session

from .models import (
    Account,
    Building,
    Membership,
    Person,
    Renter,
    Role,
    Tenancy,
    TenancyParty,
    Unit,
)
from .session import create_db_engine
from .settings import DbSettings

DEMO_ACCOUNT_ID = "acc_demo_lokara"
DEMO_PERSON_ID = "per_demo_owner"

_UNITS = (
    ("unit_demo_a", "Wohnung A (EG links)", 5000),
    ("unit_demo_b", "Wohnung B (EG rechts)", 3000),
    ("unit_demo_c", "Wohnung C (1. OG)", 2000),
)
_RENTERS = (
    ("ren_demo_1", "Anna Beispiel"),
    ("ren_demo_2", "Bernd Muster"),
    ("ren_demo_3", "Clara Vorlage"),
)
_TENANCIES = (
    # (id, unit, renter, valid_from, valid_to_exclusive, base_rent, advance)
    ("ten_demo_a1", "unit_demo_a", "ren_demo_1", date(2023, 4, 1), None, 95000, 22000),
    ("ten_demo_b1", "unit_demo_b", "ren_demo_2", date(2021, 9, 1), date(2025, 7, 1), 68000, 15000),
    ("ten_demo_c1", "unit_demo_c", "ren_demo_3", date(2024, 1, 1), None, 52000, 11000),
)


def seed_demo(session: Session) -> None:
    session.merge(Person(id=DEMO_PERSON_ID, email="demo@lokara.example", name="Demo Vermieter"))
    session.merge(Account(id=DEMO_ACCOUNT_ID, name="Demo Konto"))
    session.merge(
        Membership(
            id="mem_demo_owner",
            person_id=DEMO_PERSON_ID,
            account_id=DEMO_ACCOUNT_ID,
            role=Role.OWNER,
        )
    )
    session.merge(
        Building(
            id="bld_demo_muster12",
            account_id=DEMO_ACCOUNT_ID,
            name="Musterstraße 12",
            street="Musterstraße 12",
            postal_code="60311",
            city="Frankfurt am Main",
        )
    )
    for unit_id, label, area in _UNITS:
        session.merge(
            Unit(
                id=unit_id,
                account_id=DEMO_ACCOUNT_ID,
                building_id="bld_demo_muster12",
                label=label,
                area_sqm_x100=area,
            )
        )
    for renter_id, legal_name in _RENTERS:
        session.merge(Renter(id=renter_id, account_id=DEMO_ACCOUNT_ID, legal_name=legal_name))
    for tenancy_id, unit_id, renter_id, valid_from, valid_to, rent, advance in _TENANCIES:
        session.merge(
            Tenancy(
                id=tenancy_id,
                account_id=DEMO_ACCOUNT_ID,
                unit_id=unit_id,
                valid_from=valid_from,
                valid_to=valid_to,
                base_rent_cents=rent,
                advance_payment_cents=advance,
            )
        )
        session.merge(
            TenancyParty(
                id=f"tp_{tenancy_id}",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                renter_id=renter_id,
            )
        )


def main() -> None:
    engine = create_db_engine(DbSettings().direct_url)
    with Session(engine) as session, session.begin():
        seed_demo(session)
    engine.dispose()
    print("Seed complete: demo account, building Musterstraße 12, 3 units, 3 tenancies.")


if __name__ == "__main__":
    main()
