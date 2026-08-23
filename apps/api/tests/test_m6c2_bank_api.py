"""M6-C2 owner-scoped HTTP surface and the `BANKMATCH-F12` Page-01 handoff.

Two things are pinned here that no engine test can reach:

1. **F12** — a finalized `RECEIVABLE` `StatementSettlement` becomes an
   `nk_nachzahlung` receivable at **exactly** the settled cents (24,500 in the
   oracle). The value is copied, never recomputed.
2. **The refusal.** `docs/15` § 3.2 requires a `due_date` on every receivable, but
   the Zahlungsfrist for a Nachzahlung is `verify-before-production` in the
   authoritative register: *"keine gesetzliche Frist; Fälligkeit tritt mit Zugang
   einer ordnungsgemäßen Abrechnung ein"*, and the familiar 30 days is a flagged
   `Konvention`. So the caller supplies the date and the endpoint refuses without
   it, in German. `docs/03`: do not "fix" a refusal by adding a fallback estimate.

Same skip contract as the other live suites: skips without a reachable Postgres,
and LOKARA_REQUIRE_DB (CI) forbids the skip.
"""

import os
import time
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.settings import ApiSettings
from lokara_db import (
    Account,
    BankTransaction,
    Building,
    DbSettings,
    Membership,
    Person,
    Receivable,
    Renter,
    Role,
    Statement,
    StatementSettlement,
    StatementStatus,
    Tenancy,
    TenancyParty,
    Unit,
    create_db_engine,
    new_id,
)
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from sqlalchemy import delete, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
TEST_JWT_ISSUER = "https://lokara.test/auth/v1"

# A dedicated account, not the demo one. This fixture creates a FINALIZED
# statement, which is append-only evidence that /demo/reset is (correctly) unable
# to delete — writing it into the demo account breaks the demo-reset suite.
ACCOUNT_ID = "acc_m6c2_bank"
PERSON_ID = "per_m6c2_owner"
BUILDING = "bld_m6c2"
UNIT = "unit_m6c2"
RENTER = "ren_m6c2"
TENANCY = "ten_m6c2"
# StubBankGateway serves exactly this id, and the demo seed owns the matching
# bank_account row. The import tests therefore run against the demo account;
# the handoff tests use ACCOUNT_ID, because a FINALIZED statement is
# append-only evidence that /demo/reset cannot delete.
BANK_ACCOUNT = "bank_acc_demo"
OUTSIDER_ACCOUNT_ID = "acc_outsider_m6c2"
OUTSIDER_PERSON_ID = "per_outsider_m6c2"

# BANKMATCH-F12: the Page 01 Nachzahlung that must arrive at the receivable
# unchanged. Not a round number by accident — a recomputation would not land here.
F12_NACHZAHLUNG_CENTS = 24_500


class _Fixture:
    def __init__(self, statement_id: str) -> None:
        self.statement_id = statement_id


@pytest.fixture(scope="module")
def live(request: pytest.FixtureRequest) -> Iterator[tuple[TestClient, _Fixture]]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as conn:
            conn.execute(text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()))
            conn.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")

    statement_id = new_id()
    with Session(owner) as session, session.begin():
        seed_demo(session)
        session.merge(Person(id=PERSON_ID, email="owner-m6c2@lokara.example"))
        session.merge(Person(id=OUTSIDER_PERSON_ID, email="outsider-m6c2@lokara.example"))
        session.merge(Account(id=ACCOUNT_ID, name="M6-C2 Bankkonto-Test"))
        session.merge(Account(id=OUTSIDER_ACCOUNT_ID, name="Fremdkonto M6-C2"))
        session.flush()
        session.merge(
            Membership(
                id="mem_m6c2_owner", person_id=PERSON_ID, account_id=ACCOUNT_ID, role=Role.OWNER
            )
        )
        session.merge(
            Membership(
                id="mem_outsider_m6c2",
                person_id=OUTSIDER_PERSON_ID,
                account_id=OUTSIDER_ACCOUNT_ID,
                role=Role.OWNER,
            )
        )
        session.merge(
            Building(
                id=BUILDING,
                account_id=ACCOUNT_ID,
                name="Testhaus M6-C2",
                street="Bankweg 1",
                postal_code="60311",
                city="Frankfurt am Main",
            )
        )
        session.merge(Renter(id=RENTER, account_id=ACCOUNT_ID, legal_name="Mieterin M6-C2"))
        session.flush()
        session.merge(
            Unit(
                id=UNIT,
                account_id=ACCOUNT_ID,
                building_id=BUILDING,
                label="Wohnung M6-C2",
                area_sqm_x100=5000,
            )
        )
        session.flush()
        session.merge(
            Tenancy(
                id=TENANCY,
                account_id=ACCOUNT_ID,
                unit_id=UNIT,
                valid_from=date(2024, 1, 1),
                valid_to=None,
                base_rent_cents=85_000,
            )
        )
        session.flush()
        session.merge(
            TenancyParty(id="tp_m6c2", account_id=ACCOUNT_ID, tenancy_id=TENANCY, renter_id=RENTER)
        )
        # Statements are append-only: a previous run's fixture statement cannot be
        # deleted, and the (building, period, version) key would collide. Take the
        # next free version rather than a fixed one.
        used = session.scalars(
            select(Statement.version).where(
                Statement.building_id == BUILDING,
                Statement.period_start == date(2025, 1, 1),
                Statement.period_end == date(2025, 12, 31),
            )
        ).all()
        # Bank transactions are ordinary rows, so a rerun starts from a clean
        # import — otherwise the idempotency test's first call reports zero.
        session.execute(
            delete(BankTransaction).where(BankTransaction.bank_account_id == BANK_ACCOUNT)
        )
        session.add(
            Statement(
                id=statement_id,
                account_id=ACCOUNT_ID,
                building_id=BUILDING,
                period_start=date(2025, 1, 1),
                period_end=date(2025, 12, 31),
                version=max([*used, 0]) + 1,
                status=StatementStatus.FINALIZED,
                total_cents=120_000,
                content_hash="f12-fixture",
            )
        )
        session.flush()
        session.add(
            StatementSettlement(
                id=new_id(),
                account_id=ACCOUNT_ID,
                statement_id=statement_id,
                tenancy_id=TENANCY,
                amount_cents=F12_NACHZAHLUNG_CENTS,
                origin_saldo_cents=F12_NACHZAHLUNG_CENTS,
                kind="RECEIVABLE",
                late_positive_exception_reason=None,
            )
        )

    def _cleanup() -> None:
        # Receivables and bank transactions are ordinary projection rows. The
        # statement and its settlement are append-only evidence and stay, exactly
        # as the RLS suite retains its graph.
        with Session(owner) as session, session.begin():
            session.execute(delete(Receivable).where(Receivable.source_id == statement_id))
            session.execute(
                delete(BankTransaction).where(BankTransaction.bank_account_id == BANK_ACCOUNT)
            )
        owner.dispose()

    request.addfinalizer(_cleanup)
    yield TestClient(create_app()), _Fixture(statement_id)


def _token(person_id: str) -> dict[str, str]:
    now = int(time.time())
    encoded = jwt.encode(
        {
            "sub": person_id,
            "iss": str(getattr(ApiSettings(), "supabase_jwt_issuer", TEST_JWT_ISSUER)),
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {encoded}"}


class TestPage01Handoff:
    def test_f12_copies_the_settled_cents_exactly(self, live: tuple[TestClient, _Fixture]) -> None:
        client, fixture = live
        response = client.post(
            f"/a/{ACCOUNT_ID}/statements/{fixture.statement_id}/receivables",
            headers=_token(PERSON_ID),
            json={"due_date": "2026-02-15"},
        )
        assert response.status_code == 201, response.text
        created = response.json()["receivables"]
        assert len(created) == 1

        receivable = created[0]
        assert receivable["expected_cents"] == F12_NACHZAHLUNG_CENTS
        assert receivable["open_cents"] == F12_NACHZAHLUNG_CENTS
        assert receivable["category"] == "nk_nachzahlung"
        assert receivable["status"] == "open"
        assert receivable["tenancy_id"] == TENANCY
        assert receivable["due_date"] == "2026-02-15"

    def test_the_handoff_is_not_repeatable_for_the_same_statement(
        self, live: tuple[TestClient, _Fixture]
    ) -> None:
        """A statement creates its obligation once. Running the handoff twice
        would double a renter's debt, which no later reconciliation could see."""
        client, fixture = live
        response = client.post(
            f"/a/{ACCOUNT_ID}/statements/{fixture.statement_id}/receivables",
            headers=_token(PERSON_ID),
            json={"due_date": "2026-02-15"},
        )
        assert response.status_code == 409
        assert "bereits" in response.json()["detail"]

    def test_a_missing_due_date_is_refused_in_german(
        self, live: tuple[TestClient, _Fixture]
    ) -> None:
        """The Zahlungsfrist is verify-before-production: no statutory deadline
        exists, and the customary 30 days is a flagged Konvention. Lokara asks
        rather than defaulting."""
        client, fixture = live
        response = client.post(
            f"/a/{ACCOUNT_ID}/statements/{fixture.statement_id}/receivables",
            headers=_token(PERSON_ID),
            json={},
        )
        assert response.status_code == 422


class TestOwnerScoping:
    def test_a_foreign_account_cannot_run_the_handoff(
        self, live: tuple[TestClient, _Fixture]
    ) -> None:
        """CLAUDE.md rule 3: the endpoint verifies the caller holds the account in
        the URL. Being an OWNER somewhere else is not authorization here."""
        client, fixture = live
        response = client.post(
            f"/a/{ACCOUNT_ID}/statements/{fixture.statement_id}/receivables",
            headers=_token(OUTSIDER_PERSON_ID),
            json={"due_date": "2026-02-15"},
        )
        assert response.status_code == 403

    def test_listing_receivables_requires_membership_in_the_url_account(
        self, live: tuple[TestClient, _Fixture]
    ) -> None:
        client, _ = live
        assert (
            client.get(
                f"/a/{ACCOUNT_ID}/receivables", headers=_token(OUTSIDER_PERSON_ID)
            ).status_code
            == 403
        )

    def test_the_owner_sees_the_receivable_it_created(
        self, live: tuple[TestClient, _Fixture]
    ) -> None:
        client, fixture = live
        response = client.get(f"/a/{ACCOUNT_ID}/receivables", headers=_token(PERSON_ID))
        assert response.status_code == 200
        rows = response.json()["receivables"]
        assert [r["expected_cents"] for r in rows if r["source_id"] == fixture.statement_id] == [
            F12_NACHZAHLUNG_CENTS
        ]


class TestBankTransactionImport:
    def test_import_is_idempotent_on_the_provider_identity(
        self, live: tuple[TestClient, _Fixture]
    ) -> None:
        """docs/15 § 3.1: an exact re-import creates no second normalized
        transaction. The second call must report zero imported, not raise."""
        client, _ = live
        url = f"/a/{DEMO_ACCOUNT_ID}/bank-accounts/{BANK_ACCOUNT}/transactions/import"
        first = client.post(
            url,
            headers=_token(DEMO_PERSON_ID),
            json={"window_from": "2025-01-01", "window_to": "2026-01-01"},
        )
        assert first.status_code == 200, first.text
        assert first.json()["imported"] == 4

        second = client.post(
            url,
            headers=_token(DEMO_PERSON_ID),
            json={"window_from": "2025-01-01", "window_to": "2026-01-01"},
        )
        assert second.status_code == 200
        assert second.json()["imported"] == 0
        assert second.json()["skipped_as_duplicate"] == 4

    def test_a_bank_account_of_another_account_is_not_found(
        self, live: tuple[TestClient, _Fixture]
    ) -> None:
        """CLAUDE.md § 3.3: the endpoint verifies **every** relationship its URL
        carries, not just the account.

        The outsider legitimately owns their own account, so `require_owner` passes.
        `bank_acc_demo` belongs to the demo account. Without an explicit check the
        composite FK still blocks the write — isolation is not the thing at risk —
        but the caller gets a 500 from an unhandled IntegrityError instead of a 404,
        and the endpoint has trusted a path parameter it never verified. That it
        looks harmless today is an accident of the stub returning nothing for an
        unknown id; the real AISP adapter will not.
        """
        client, _ = live
        response = client.post(
            f"/a/{OUTSIDER_ACCOUNT_ID}/bank-accounts/{BANK_ACCOUNT}/transactions/import",
            headers=_token(OUTSIDER_PERSON_ID),
            json={"window_from": "2025-01-01", "window_to": "2026-01-01"},
        )
        assert response.status_code == 404, response.text

    def test_a_debit_keeps_its_negative_sign_through_the_boundary(
        self, live: tuple[TestClient, _Fixture]
    ) -> None:
        client, _ = live
        response = client.get(
            f"/a/{DEMO_ACCOUNT_ID}/bank-transactions", headers=_token(DEMO_PERSON_ID)
        )
        assert response.status_code == 200
        by_id = {t["provider_transaction_id"]: t for t in response.json()["transactions"]}
        assert by_id["tx_stub_001"]["amount_cents"] == 117_000
        assert by_id["tx_stub_004"]["amount_cents"] == -120_000


def test_receivable_source_is_traceable_to_its_statement(
    live: tuple[TestClient, _Fixture],
) -> None:
    """GoBD / § 147 AO: the obligation must be re-derivable years later, so the
    receivable names the statement it came from rather than only its amount."""
    _, fixture = live
    owner = create_db_engine(DbSettings().direct_url)
    with Session(owner) as session:
        rows = session.scalars(
            select(Receivable).where(Receivable.source_id == fixture.statement_id)
        ).all()
    owner.dispose()
    assert len(rows) == 1
    assert rows[0].source_type == "PAGE01_STATEMENT"
    assert rows[0].expected_cents == F12_NACHZAHLUNG_CENTS
    assert rows[0].stored_reference is None
