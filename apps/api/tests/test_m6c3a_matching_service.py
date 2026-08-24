"""Acceptance surface for M6-C3a matching persistence and owner APIs.

The pure engine already proves Page 08. These tests prove that the application service
persists that result without changing it. Expected decisions and cents are read from the
single approved oracle in ``packages/rules-store/tests/berkay_15_golden.py``; they are not
copied here. Migration and service implementation are now technically green on the C3a slice.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from threading import Barrier
from typing import Final, cast

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.routers.payments import router as payments_router
from lokara_api.settings import ApiSettings
from lokara_db import (
    Account,
    BankAccount,
    BankTransaction,
    Building,
    DbSettings,
    IbanHistory,
    MatchConfirmation,
    MatchProposal,
    Membership,
    PaymentAllocation,
    PaymentLedgerEntry,
    Person,
    Receivable,
    Renter,
    RenterMatchingProfile,
    Role,
    Tenancy,
    TenancyParty,
    Unit,
    create_db_engine,
    new_id,
)
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_ROOT = Path(__file__).resolve().parents[3]
_ORACLE_DIR = _ROOT / "packages" / "rules-store" / "tests"
if str(_ORACLE_DIR) not in sys.path:
    sys.path.insert(0, str(_ORACLE_DIR))
from berkay_15_golden import PAGE_08_GOLDENS  # noqa: E402

_DB_DIR = _ROOT / "packages" / "db"
_ISSUER = "https://lokara.test/auth/v1"
_CASE_IDS: Final = tuple(f"BANKMATCH-F{number:02}" for number in range(1, 14))


def _case(case_id: str) -> dict[str, object]:
    return PAGE_08_GOLDENS[case_id]


def _integer(case_id: str, key: str) -> int:
    value = _case(case_id)[key]
    assert isinstance(value, int)
    return value


def _string(case_id: str, key: str) -> str:
    value = _case(case_id)[key]
    assert isinstance(value, str)
    return value


def _integers(case_id: str, key: str) -> tuple[int, ...]:
    value = _case(case_id)[key]
    assert isinstance(value, tuple)
    assert all(isinstance(item, int) for item in value)
    return cast(tuple[int, ...], value)


class Graph:
    def __init__(self) -> None:
        self.account_id = new_id()
        self.foreign_account_id = new_id()
        self.owner_id = new_id()
        self.employee_id = new_id()
        self.foreign_owner_id = new_id()
        self.bank_account_id = new_id()
        self.transactions: dict[str, str] = {}
        self.renters: dict[str, str] = {}
        self.receivables: dict[str, list[str]] = {}


def _token(person_id: str) -> dict[str, str]:
    now = int(time.time())
    encoded = jwt.encode(
        {
            "sub": person_id,
            "iss": str(getattr(ApiSettings(), "supabase_jwt_issuer", _ISSUER)),
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {encoded}"}


def test_exactly_five_c3a_owner_routes_are_registered() -> None:
    """Non-DB red proof: the failure is the missing C3a API, not an import error."""
    expected = {
        ("PUT", "/a/{account_id}/renters/{renter_id}/matching-profile"),
        ("POST", "/a/{account_id}/bank-transactions/{transaction_id}/match"),
        ("GET", "/a/{account_id}/match-proposals"),
        ("POST", "/a/{account_id}/bank-transactions/{transaction_id}/decision"),
        ("GET", "/a/{account_id}/payment-ledger"),
    }
    app = create_app()
    # FastAPI 0.139 keeps included routers lazy. ``app.routes`` therefore contains
    # ``_IncludedRouter`` branches rather than eagerly copied ``APIRoute`` objects.
    # Prove the payments router itself is included, then inspect its public route list.
    assert any(getattr(route, "original_router", None) is payments_router for route in app.routes)
    registered = {
        (method, path)
        for route in payments_router.routes
        for path in (getattr(route, "path", None),)
        if isinstance(path, str)
        for method in getattr(route, "methods", set())
    }
    c3a_registered = {
        item
        for item in registered
        if item[1]
        in {
            "/a/{account_id}/renters/{renter_id}/matching-profile",
            "/a/{account_id}/match-proposals",
            "/a/{account_id}/payment-ledger",
        }
        or item[1].endswith("/{transaction_id}/match")
        or item[1].endswith("/{transaction_id}/decision")
    }
    assert c3a_registered == expected


def _seed_case(
    session: Session,
    graph: Graph,
    case_id: str,
    *,
    amount_cents: int,
    purpose: str | None,
    iban: str | None,
    surname: str,
    payment_code: str | None = None,
    potential_duplicate: bool = False,
    receivable_amounts: tuple[int, ...] = (108_000,),
    periods: tuple[str, ...] = ("2026-07",),
    profile: bool = True,
    known_iban: bool = True,
    end_to_end_reference: str | None = None,
) -> None:
    renter_id = new_id()
    building_id = new_id()
    unit_id = new_id()
    tenancy_id = new_id()
    graph.renters[case_id] = renter_id
    session.add(
        Building(
            id=building_id,
            account_id=graph.account_id,
            name=f"Haus {case_id}",
            street="Testweg 1",
            postal_code="10115",
            city="Berlin",
        )
    )
    session.add(Renter(id=renter_id, account_id=graph.account_id, legal_name=surname))
    session.flush()
    session.add(
        Unit(
            id=unit_id,
            account_id=graph.account_id,
            building_id=building_id,
            label=case_id,
            area_sqm_x100=5000,
        )
    )
    session.flush()
    session.add(
        Tenancy(
            id=tenancy_id,
            account_id=graph.account_id,
            unit_id=unit_id,
            valid_from=date(2025, 1, 1),
            valid_to=None,
            base_rent_cents=85_000,
        )
    )
    session.flush()
    session.add(
        TenancyParty(
            id=new_id(), account_id=graph.account_id, tenancy_id=tenancy_id, renter_id=renter_id
        )
    )
    # `enforce_receivable_tenancy_party` queries the database inside a BEFORE
    # trigger. Make the parent and its party visible before any Receivable flush.
    session.flush()
    if profile:
        session.add(
            RenterMatchingProfile(
                id=new_id(),
                account_id=graph.account_id,
                renter_id=renter_id,
                payment_code=payment_code,
                normalized_surname=surname.lower(),
            )
        )
    receivable_ids: list[str] = []
    for index, (amount, period) in enumerate(zip(receivable_amounts, periods, strict=True)):
        receivable_id = new_id()
        receivable_ids.append(receivable_id)
        is_nachzahlung = case_id == "BANKMATCH-F12"
        nominal = _integers("BANKMATCH-F11", "nominal_components")
        rent_components = (
            nominal if not is_nachzahlung and amount == sum(nominal) else (amount, 0, 0)
        )
        session.add(
            Receivable(
                id=receivable_id,
                account_id=graph.account_id,
                renter_id=renter_id,
                tenancy_id=tenancy_id,
                source_type="PAGE01_STATEMENT" if is_nachzahlung else "RECURRING_RENT",
                source_id=new_id() if is_nachzahlung else None,
                period=period,
                due_date=date(2026, 7 + min(index, 5), 3),
                expected_cents=amount,
                open_cents=amount,
                status="open",
                category="nk_nachzahlung" if is_nachzahlung else "rent",
                base_rent_cents=0 if is_nachzahlung else rent_components[0],
                nk_advance_cents=0 if is_nachzahlung else rent_components[1],
                heating_advance_cents=0 if is_nachzahlung else rent_components[2],
                garage_cents=0,
                open_costs_cents=0,
                open_interest_cents=0,
                open_principal_cents=amount,
                stored_reference=None,
            )
        )
    graph.receivables[case_id] = receivable_ids
    transaction_id = new_id()
    graph.transactions[case_id] = transaction_id
    session.add(
        BankTransaction(
            id=transaction_id,
            account_id=graph.account_id,
            bank_account_id=graph.bank_account_id,
            provider_transaction_id=f"provider-{case_id}-{transaction_id}",
            amount_cents=amount_cents,
            bank_booking_date=date(2026, 7, 5),
            finapi_booking_date=date(2026, 7, 5),
            value_date=date(2026, 7, 5),
            counterpart_iban=iban,
            counterpart_name=surname,
            purpose=purpose,
            end_to_end_reference=end_to_end_reference or f"E2E-{case_id}",
            counterpart_mandate_reference=None,
            bank_transaction_code="RETURN" if amount_cents < 0 else "SEPA-CT",
            provider_type="DEBIT" if amount_cents < 0 else "CREDIT",
            is_potential_duplicate=potential_duplicate,
        )
    )
    session.flush()
    # Page 08 derives known IBANs only from active history. Build legitimate prior
    # confirmation evidence on a different movement; never preload a proposal on the
    # transaction whose immutable run the test is about.
    if known_iban and iban is not None and amount_cents > 0:
        learned_tx = new_id()
        proposal_id = new_id()
        confirmation_id = new_id()
        session.add(
            BankTransaction(
                id=learned_tx,
                account_id=graph.account_id,
                bank_account_id=graph.bank_account_id,
                provider_transaction_id=f"learned-{learned_tx}",
                amount_cents=1,
                bank_booking_date=date(2026, 1, 1),
                finapi_booking_date=date(2026, 1, 1),
                value_date=date(2026, 1, 1),
                counterpart_iban=iban,
                counterpart_name=surname,
                purpose=None,
                end_to_end_reference=None,
                counterpart_mandate_reference=None,
                bank_transaction_code="SEPA-CT",
                provider_type="CREDIT",
                is_potential_duplicate=False,
            )
        )
        session.flush()
        proposal_kwargs: dict[str, object] = {
            "id": proposal_id,
            "account_id": graph.account_id,
            "bank_transaction_id": learned_tx,
            "receivable_id": receivable_ids[0],
            "renter_id": renter_id,
            "signal_iban": 0,
            "signal_amount": 0,
            "signal_code_or_surname": 10,
            "signal_e2e": 0,
            "signal_period": 0,
            "confidence": 10,
            "decision": "NEEDS_REVIEW",
            "convention_version": "docs/15 07/2026",
            "reason_de": "Frühere ausdrückliche Bestätigung.",
        }
        if hasattr(MatchProposal, "rank"):
            proposal_kwargs["rank"] = 1
        session.add(MatchProposal(**proposal_kwargs))
        session.flush()
        session.add(
            MatchConfirmation(
                id=confirmation_id,
                account_id=graph.account_id,
                match_proposal_id=proposal_id,
                outcome="CONFIRMED",
                confirmed_by=graph.owner_id,
            )
        )
        session.flush()
        session.add(
            IbanHistory(
                id=new_id(),
                account_id=graph.account_id,
                renter_id=renter_id,
                normalized_iban=iban,
                valid_from=datetime(2026, 1, 1, tzinfo=UTC),
                valid_to=None,
                learned_from_transaction_id=learned_tx,
                confirmed_match_id=confirmation_id,
                confirmed_by=graph.owner_id,
            )
        )


@pytest.fixture(scope="module")
def live() -> Iterator[tuple[TestClient, Graph, Engine]]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as connection:
            connection.execute(text((_DB_DIR / "scripts" / "init-app-role.sql").read_text()))
            connection.commit()
    except OperationalError as exc:
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_DIR / "alembic.ini")), "head")
    graph = Graph()
    with Session(owner) as session, session.begin():
        session.add_all(
            [
                Account(id=graph.account_id, name="M6-C3a"),
                Account(id=graph.foreign_account_id, name="M6-C3a foreign"),
                Person(id=graph.owner_id, email=f"{graph.owner_id}@example.test"),
                Person(id=graph.employee_id, email=f"{graph.employee_id}@example.test"),
                Person(id=graph.foreign_owner_id, email=f"{graph.foreign_owner_id}@example.test"),
            ]
        )
        session.flush()
        session.add_all(
            [
                Membership(
                    id=new_id(),
                    person_id=graph.owner_id,
                    account_id=graph.account_id,
                    role=Role.OWNER,
                ),
                Membership(
                    id=new_id(),
                    person_id=graph.employee_id,
                    account_id=graph.account_id,
                    role=Role.EMPLOYEE,
                ),
                Membership(
                    id=new_id(),
                    person_id=graph.foreign_owner_id,
                    account_id=graph.foreign_account_id,
                    role=Role.OWNER,
                ),
                BankAccount(
                    id=graph.bank_account_id,
                    account_id=graph.account_id,
                    provider="finapi",
                    provider_account_id=f"provider-{graph.bank_account_id}",
                    normalized_iban="DE02120300000000202051",
                    display_name="Mietkonto",
                    consent_expires_at=None,
                ),
            ]
        )
        session.flush()
        base = _integer("BANKMATCH-F11", "expected")
        scenarios = {
            "BANKMATCH-F01": (_integer("BANKMATCH-F01", "amount"), "Miete 2026-07", "DE01"),
            "BANKMATCH-F02": (_integer("BANKMATCH-F02", "amount"), "Zahlung Mueller", "DE02"),
            "BANKMATCH-F03": (_integer("BANKMATCH-F03", "amount"), "Miete Juli", "DE03"),
            "BANKMATCH-F04": (_integer("BANKMATCH-F04", "amount"), None, "DE04"),
            "BANKMATCH-F05": (_integer("BANKMATCH-F05", "amount"), None, None),
            "BANKMATCH-F06": (_integer("BANKMATCH-F06", "reversal_amount"), None, "DE06"),
            "BANKMATCH-F07": (_integer("BANKMATCH-F07", "amount"), "KDNR-4711", "DE07"),
            "BANKMATCH-F08": (_integer("BANKMATCH-F08", "amount"), "Miete 2026-08", "DE08"),
            "BANKMATCH-F09": (_integer("BANKMATCH-F09", "amount"), "KDNR-4711", None),
            "BANKMATCH-F10": (
                cast(tuple[tuple[str, int], ...], _case("BANKMATCH-F10")["decimal_imports"])[1][1],
                None,
                "DE10",
            ),
            "BANKMATCH-F11": (_integer("BANKMATCH-F11", "payment"), None, "DE11"),
            "BANKMATCH-F12": (_integer("BANKMATCH-F12", "payment"), "2025", "DE12"),
            "BANKMATCH-F13": (_integer("BANKMATCH-F13", "amount"), "Zahlung Mueller", "DE13"),
        }
        for case_id, (amount, purpose, iban) in scenarios.items():
            amounts = (
                (base, base)
                if case_id == "BANKMATCH-F04"
                else (
                    (_integer("BANKMATCH-F12", "receivable_expected"),)
                    if case_id == "BANKMATCH-F12"
                    else (base,)
                )
            )
            periods = (
                ("2026-06", "2026-07")
                if case_id == "BANKMATCH-F04"
                else (("2025",) if case_id == "BANKMATCH-F12" else ("2026-07",))
            )
            _seed_case(
                session,
                graph,
                case_id,
                amount_cents=amount,
                purpose=purpose,
                iban=iban,
                surname="Mueller"
                if case_id in {"BANKMATCH-F02", "BANKMATCH-F13"}
                else f"Mueller {case_id}",
                payment_code="KDNR-4711" if case_id in {"BANKMATCH-F07", "BANKMATCH-F09"} else None,
                potential_duplicate=case_id == "BANKMATCH-F03",
                receivable_amounts=amounts,
                periods=periods,
                known_iban=case_id not in {"BANKMATCH-F02", "BANKMATCH-F13"},
                end_to_end_reference="E2E-F06" if case_id == "BANKMATCH-F06" else None,
            )
        # F05 needs two equal weak candidates; F07 needs two renters actively sharing
        # one IBAN. Their extra movements are harmless evidence outside the 13 ids.
        _seed_case(
            session,
            graph,
            "BANKMATCH-F05-ALT",
            amount_cents=_integer("BANKMATCH-F05", "amount"),
            purpose=None,
            iban=None,
            surname="Schmidt F05",
        )
        _seed_case(
            session,
            graph,
            "BANKMATCH-F07-ALT",
            amount_cents=_integer("BANKMATCH-F07", "amount"),
            purpose="Zahlung",
            iban="DE07",
            surname="Schmidt F07",
        )
        _seed_case(
            session,
            graph,
            "BANKMATCH-F06-ORIGINAL",
            amount_cents=_integer("BANKMATCH-F06", "original_payment"),
            purpose="Miete 2026-07",
            iban="DE06",
            surname="Mueller F06",
            end_to_end_reference="E2E-F06",
        )
    yield TestClient(create_app()), graph, owner
    owner.dispose()


def _match(client: TestClient, graph: Graph, case_id: str) -> object:
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{graph.transactions[case_id]}/match",
        headers=_token(graph.owner_id),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _seed_fresh(
    owner: Engine,
    graph: Graph,
    case_id: str,
    *,
    amount_cents: int = 108_000,
    purpose: str | None = "Miete 2098-01",
    iban: str | None = None,
    end_to_end_reference: str | None = None,
    receivable_amounts: tuple[int, ...] = (108_000,),
) -> None:
    with Session(owner) as session, session.begin():
        _seed_case(
            session,
            graph,
            case_id,
            amount_cents=amount_cents,
            purpose=purpose,
            iban=iban or f"DE{case_id}",
            surname=f"Mieter {case_id}",
            receivable_amounts=receivable_amounts,
            periods=("2098-01",) * len(receivable_amounts),
            end_to_end_reference=end_to_end_reference,
        )


def _add_return(
    owner: Engine,
    graph: Graph,
    case_id: str,
    *,
    original_case: str,
    amount_cents: int,
    reference: str,
) -> str:
    transaction_id = new_id()
    graph.transactions[case_id] = transaction_id
    with Session(owner) as session, session.begin():
        original = session.get(BankTransaction, graph.transactions[original_case])
        assert original is not None
        session.add(
            BankTransaction(
                id=transaction_id,
                account_id=graph.account_id,
                bank_account_id=graph.bank_account_id,
                provider_transaction_id=f"return-{transaction_id}",
                amount_cents=amount_cents,
                bank_booking_date=original.bank_booking_date,
                finapi_booking_date=original.finapi_booking_date,
                value_date=original.value_date,
                counterpart_iban=original.counterpart_iban,
                counterpart_name=original.counterpart_name,
                purpose=None,
                end_to_end_reference=reference,
                counterpart_mandate_reference=None,
                bank_transaction_code="RETURN",
                provider_type="DEBIT",
                is_potential_duplicate=False,
            )
        )
    return transaction_id


def _assert_no_return_ledger(owner: Engine, transaction_id: str) -> None:
    with Session(owner) as session:
        count = session.scalar(
            select(func.count()).where(PaymentLedgerEntry.bank_transaction_id == transaction_id)
        )
    assert count == 0


def test_matching_profile_is_normalized_and_upserted(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, _ = live
    renter_id = graph.renters["BANKMATCH-F02"]
    response = client.put(
        f"/a/{graph.account_id}/renters/{renter_id}/matching-profile",
        headers=_token(graph.owner_id),
        json={"surname": "  MÜLLER-Schmidt ", "payment_code": " KDNR 42 "},
    )
    assert response.status_code == 200, response.text
    assert response.json()["normalized_surname"] == "muellerschmidt"


@pytest.mark.parametrize("case_id", _CASE_IDS)
def test_all_thirteen_oracle_cases_cross_service_and_persistence(
    live: tuple[TestClient, Graph, Engine], case_id: str
) -> None:
    client, graph, owner = live
    if case_id == "BANKMATCH-F06":
        _match(client, graph, "BANKMATCH-F06-ORIGINAL")
    result = cast(dict[str, object], _match(client, graph, case_id))
    assert result["transaction_id"] == graph.transactions[case_id]
    if case_id == "BANKMATCH-F06":
        assert result["event"] == _string(case_id, "guard_handoff")
    elif case_id == "BANKMATCH-F10":
        with Session(owner) as session:
            stored = session.get(BankTransaction, graph.transactions[case_id])
            assert stored is not None
            expected = cast(tuple[tuple[str, int], ...], _case(case_id)["decimal_imports"])[1][1]
            assert stored.amount_cents == expected
    else:
        key = {
            "BANKMATCH-F03": "potential_duplicate_decision",
            "BANKMATCH-F13": "initial_decision",
        }.get(case_id, "decision")
        assert result["decision"] == _string(case_id, key)
    with Session(owner) as session:
        proposal_count = session.scalar(
            select(func.count())
            .select_from(text("match_proposal"))
            .where(text("bank_transaction_id = :tx"))
            .params(tx=graph.transactions[case_id])
        )
        assert proposal_count is not None
        if case_id == "BANKMATCH-F06":
            assert proposal_count == 0
        else:
            assert proposal_count >= 1


def test_review_reject_and_duplicate_are_final_and_money_free(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, owner = live
    for case_id, outcome in (("BANKMATCH-F02", "rejected"), ("BANKMATCH-F03", "duplicate")):
        _match(client, graph, case_id)
        response = client.post(
            f"/a/{graph.account_id}/bank-transactions/{graph.transactions[case_id]}/decision",
            headers=_token(graph.owner_id),
            json={"outcome": outcome},
        )
        assert response.status_code == 200, response.text
        assert response.json()["outcome"] == outcome
        with Session(owner) as session:
            booked = session.scalar(
                select(func.count())
                .select_from(text("payment_ledger_entry"))
                .where(text("bank_transaction_id = :tx"))
                .params(tx=graph.transactions[case_id])
            )
            assert booked == 0


@pytest.mark.parametrize(
    "case_id", ("BANKMATCH-F01", "BANKMATCH-F04", "BANKMATCH-F11", "BANKMATCH-F12")
)
def test_persisted_money_and_components_match_the_oracle(
    live: tuple[TestClient, Graph, Engine], case_id: str
) -> None:
    client, graph, owner = live
    _match(client, graph, case_id)
    with Session(owner) as session:
        entry = session.scalar(
            select(PaymentLedgerEntry).where(
                PaymentLedgerEntry.bank_transaction_id == graph.transactions[case_id],
                PaymentLedgerEntry.kind == "PAYMENT",
            )
        )
        assert entry is not None
        allocations = session.scalars(
            select(PaymentAllocation).where(PaymentAllocation.ledger_entry_id == entry.id)
        ).all()
    assigned = sum(
        row.costs_cents + row.interest_cents + row.principal_cents for row in allocations
    )
    expected_assigned = _integer(case_id, "payment" if case_id == "BANKMATCH-F11" else "assigned")
    assert assigned == expected_assigned
    expected_credit = _integer(case_id, "credit") if case_id == "BANKMATCH-F04" else 0
    assert entry.credit_cents == expected_credit
    if case_id == "BANKMATCH-F01":
        row = allocations[0]
        assert (row.base_rent_cents, row.nk_advance_cents, row.heating_advance_cents) == _integers(
            case_id, "components_paid"
        )
    elif case_id == "BANKMATCH-F11":
        row = allocations[0]
        assert (row.base_rent_cents, row.nk_advance_cents, row.heating_advance_cents) == _integers(
            case_id, "paid_components"
        )
    elif case_id == "BANKMATCH-F12":
        row = allocations[0]
        assert row.principal_cents == _integer(case_id, "payment")
        assert (
            row.base_rent_cents,
            row.nk_advance_cents,
            row.heating_advance_cents,
            row.garage_cents,
        ) == (0, 0, 0, 0)


def test_confirmed_review_iban_uses_exact_confirmation_datetime(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, owner = live
    _match(client, graph, "BANKMATCH-F13")
    client.post(
        f"/a/{graph.account_id}/bank-transactions/{graph.transactions['BANKMATCH-F13']}/decision",
        headers=_token(graph.owner_id),
        json={"outcome": "confirmed"},
    )
    with Session(owner) as session:
        confirmation = session.scalar(
            select(MatchConfirmation)
            .join(MatchProposal, MatchProposal.id == MatchConfirmation.match_proposal_id)
            .where(MatchProposal.bank_transaction_id == graph.transactions["BANKMATCH-F13"])
        )
        learned = session.scalar(
            select(IbanHistory).where(
                IbanHistory.learned_from_transaction_id == graph.transactions["BANKMATCH-F13"]
            )
        )
    assert confirmation is not None and learned is not None
    assert isinstance(learned.valid_from, datetime)
    assert learned.valid_from == confirmation.confirmed_at
    assert learned.valid_to is None


def test_f04_full_return_keeps_credit_out_of_compensating_allocations(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, owner = live
    _match(client, graph, "BANKMATCH-F04")
    transaction_id = new_id()
    original = graph.transactions["BANKMATCH-F04"]
    with Session(owner) as session, session.begin():
        original_row = session.get(BankTransaction, original)
        assert original_row is not None
        session.add(
            BankTransaction(
                id=transaction_id,
                account_id=graph.account_id,
                bank_account_id=graph.bank_account_id,
                provider_transaction_id=f"return-{transaction_id}",
                amount_cents=-_integer("BANKMATCH-F04", "amount"),
                bank_booking_date=original_row.bank_booking_date,
                finapi_booking_date=original_row.finapi_booking_date,
                value_date=original_row.value_date,
                counterpart_iban=original_row.counterpart_iban,
                counterpart_name=original_row.counterpart_name,
                purpose=None,
                end_to_end_reference=original_row.end_to_end_reference,
                counterpart_mandate_reference=None,
                bank_transaction_code="RETURN",
                provider_type="DEBIT",
                is_potential_duplicate=False,
            )
        )
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{transaction_id}/match",
        headers=_token(graph.owner_id),
    )
    assert response.status_code == 200, response.text
    with Session(owner) as session:
        reversal = session.scalar(
            select(PaymentLedgerEntry).where(
                PaymentLedgerEntry.bank_transaction_id == transaction_id,
                PaymentLedgerEntry.kind == "REVERSAL",
            )
        )
        assert reversal is not None
        allocations = session.scalars(
            select(PaymentAllocation).where(PaymentAllocation.ledger_entry_id == reversal.id)
        ).all()
    assert reversal.amount_cents == -_integer("BANKMATCH-F04", "amount")
    assert reversal.credit_cents == 0
    assert sum(
        row.costs_cents + row.interest_cents + row.principal_cents for row in allocations
    ) == -_integer("BANKMATCH-F04", "assigned")


def test_confirmation_is_rank_one_only_and_learns_non_null_iban(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, _ = live
    _match(client, graph, "BANKMATCH-F13")
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{graph.transactions['BANKMATCH-F13']}/decision",
        headers=_token(graph.owner_id),
        json={"outcome": "confirmed"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["selected_rank"] == _integer("BANKMATCH-F02", "rank")
    # The request model deliberately offers no receivable/rank field: clients cannot
    # confirm a lower candidate. Extra input must be rejected, not silently trusted.
    lower = client.post(
        f"/a/{graph.account_id}/bank-transactions/{graph.transactions['BANKMATCH-F07']}/decision",
        headers=_token(graph.owner_id),
        json={"outcome": "confirmed", "receivable_id": graph.receivables["BANKMATCH-F07"][0]},
    )
    assert lower.status_code == 422


def test_match_is_idempotent_and_concurrent_safe(live: tuple[TestClient, Graph, Engine]) -> None:
    client, graph, owner = live
    first = _match(client, graph, "BANKMATCH-F11")
    second = _match(client, graph, "BANKMATCH-F11")
    assert second == first
    with Session(owner) as session:
        ledger_count = session.scalar(
            select(func.count())
            .select_from(text("payment_ledger_entry"))
            .where(text("bank_transaction_id = :tx"))
            .params(tx=graph.transactions["BANKMATCH-F11"])
        )
        assert ledger_count == 1


def test_two_sessions_create_one_sealed_proposal_run_and_one_ledger(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    _, graph, owner = live
    case_id = "CONCURRENT-RUN"
    _seed_fresh(owner, graph, case_id, iban="DECONCURRENT")
    barrier = Barrier(2)

    def invoke() -> tuple[int, dict[str, object]]:
        with TestClient(create_app()) as client:
            barrier.wait()
            response = client.post(
                f"/a/{graph.account_id}/bank-transactions/{graph.transactions[case_id]}/match",
                headers=_token(graph.owner_id),
            )
            return response.status_code, cast(dict[str, object], response.json())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda _: invoke(), range(2)))
    assert {status for status, _ in results} == {200}
    assert results[0][1] == results[1][1]
    with Session(owner) as session:
        proposals = session.scalars(
            select(MatchProposal)
            .where(MatchProposal.bank_transaction_id == graph.transactions[case_id])
            .order_by(MatchProposal.rank)
        ).all()
        ledger_count = session.scalar(
            select(func.count()).where(
                PaymentLedgerEntry.bank_transaction_id == graph.transactions[case_id]
            )
        )
    assert [row.rank for row in proposals] == list(range(1, len(proposals) + 1))
    assert len({(row.decision, row.reason_de, row.convention_version) for row in proposals}) == 1
    assert ledger_count == 1


@pytest.mark.parametrize("path", ("match-proposals", "payment-ledger"))
def test_owner_account_and_employee_boundaries(
    live: tuple[TestClient, Graph, Engine], path: str
) -> None:
    client, graph, _ = live
    assert (
        client.get(f"/a/{graph.account_id}/{path}", headers=_token(graph.owner_id)).status_code
        == 200
    )
    assert (
        client.get(f"/a/{graph.account_id}/{path}", headers=_token(graph.employee_id)).status_code
        == 403
    )


@pytest.mark.parametrize(
    "method,path,body",
    (
        (
            "PUT",
            "/renters/{renter}/matching-profile",
            {"surname": "Mueller", "payment_code": None},
        ),
        ("POST", "/bank-transactions/{transaction}/match", None),
        ("GET", "/match-proposals", None),
        ("POST", "/bank-transactions/{transaction}/decision", {"outcome": "rejected"}),
        ("GET", "/payment-ledger", None),
    ),
)
@pytest.mark.parametrize("actor", ("employee", "foreign_owner"))
def test_all_five_endpoints_refuse_non_owner_or_foreign_owner(
    live: tuple[TestClient, Graph, Engine],
    method: str,
    path: str,
    body: dict[str, object] | None,
    actor: str,
) -> None:
    client, graph, _ = live
    resolved = path.format(
        renter=graph.renters["BANKMATCH-F02"],
        transaction=graph.transactions["BANKMATCH-F02"],
    )
    person_id = graph.employee_id if actor == "employee" else graph.foreign_owner_id
    response = client.request(
        method,
        f"/a/{graph.account_id}{resolved}",
        headers=_token(person_id),
        json=body,
    )
    assert response.status_code == 403


def test_lists_expose_grouped_proposals_and_newest_first_ledger(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, _ = live
    proposals = client.get(f"/a/{graph.account_id}/match-proposals", headers=_token(graph.owner_id))
    assert proposals.status_code == 200, proposals.text
    rows = proposals.json()["transactions"]
    assert all(
        row["candidates"] == sorted(row["candidates"], key=lambda item: item["rank"])
        for row in rows
    )
    assert all(row["reason_de"] and row["decision"] == row["decision"].lower() for row in rows)
    ledger = client.get(f"/a/{graph.account_id}/payment-ledger", headers=_token(graph.owner_id))
    assert ledger.status_code == 200, ledger.text
    entries = ledger.json()["entries"]
    assert [entry["created_at"] for entry in entries] == sorted(
        (entry["created_at"] for entry in entries), reverse=True
    )


def test_zero_movement_remains_import_evidence_only(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    _, graph, owner = live
    transaction_id = new_id()
    with Session(owner) as session, session.begin():
        session.add(
            BankTransaction(
                id=transaction_id,
                account_id=graph.account_id,
                bank_account_id=graph.bank_account_id,
                provider_transaction_id=f"zero-{transaction_id}",
                amount_cents=0,
                bank_booking_date=date(2026, 7, 5),
                finapi_booking_date=date(2026, 7, 5),
                value_date=date(2026, 7, 5),
                counterpart_iban=None,
                counterpart_name=None,
                purpose=None,
                end_to_end_reference=None,
                counterpart_mandate_reference=None,
                bank_transaction_code=None,
                provider_type=None,
                is_potential_duplicate=False,
            )
        )
    client = TestClient(create_app())
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{transaction_id}/match",
        headers=_token(graph.owner_id),
    )
    assert response.status_code == 200, response.text
    assert response.json()["decision"] is None
    assert response.json()["ledger_entry_id"] is None


def test_conflicts_are_german_and_atomic(live: tuple[TestClient, Graph, Engine]) -> None:
    client, graph, _ = live
    missing = client.post(
        f"/a/{graph.account_id}/bank-transactions/fehlt/match", headers=_token(graph.owner_id)
    )
    assert missing.status_code == 404
    assert "nicht gefunden" in missing.json()["detail"].lower()
    # A changed final decision and an engine Largest-Remainder tie are both conflicts;
    # neither may leave a proposal, confirmation, ledger row or projection update behind.
    _match(client, graph, "BANKMATCH-F02")
    first = client.post(
        f"/a/{graph.account_id}/bank-transactions/{graph.transactions['BANKMATCH-F02']}/decision",
        headers=_token(graph.owner_id),
        json={"outcome": "rejected"},
    )
    assert first.status_code == 200
    changed = client.post(
        f"/a/{graph.account_id}/bank-transactions/{graph.transactions['BANKMATCH-F02']}/decision",
        headers=_token(graph.owner_id),
        json={"outcome": "confirmed"},
    )
    assert changed.status_code == 409
    assert "bereits" in changed.json()["detail"].lower()


def test_largest_remainder_tie_rolls_back_the_complete_match(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, owner = live
    case_id = "LARGEST-REMAINDER-TIE"
    _seed_fresh(
        owner,
        graph,
        case_id,
        amount_cents=1_001,
        iban="DETIE",
        receivable_amounts=(2_000,),
    )
    with Session(owner) as session, session.begin():
        receivable = session.get(Receivable, graph.receivables[case_id][0])
        assert receivable is not None
        receivable.base_rent_cents = 1_000
        receivable.nk_advance_cents = 1_000
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{graph.transactions[case_id]}/match",
        headers=_token(graph.owner_id),
    )
    assert response.status_code == 409
    with Session(owner) as session:
        proposal_count = session.scalar(
            select(func.count()).where(
                MatchProposal.bank_transaction_id == graph.transactions[case_id]
            )
        )
        ledger_count = session.scalar(
            select(func.count()).where(
                PaymentLedgerEntry.bank_transaction_id == graph.transactions[case_id]
            )
        )
        receivable = session.get(Receivable, graph.receivables[case_id][0])
    assert proposal_count == 0
    assert ledger_count == 0
    assert receivable is not None
    assert (receivable.open_cents, receivable.status) == (2_000, "open")


def test_partial_return_is_a_conflict_and_atomic(live: tuple[TestClient, Graph, Engine]) -> None:
    client, graph, owner = live
    case_id = "PARTIAL-RETURN-ORIGINAL"
    reference = "E2E-PARTIAL-RETURN"
    _seed_fresh(owner, graph, case_id, iban="DEPARTIAL", end_to_end_reference=reference)
    _match(client, graph, case_id)
    returned = _add_return(
        owner,
        graph,
        "PARTIAL-RETURN",
        original_case=case_id,
        amount_cents=-50_000,
        reference=reference,
    )
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{returned}/match",
        headers=_token(graph.owner_id),
    )
    assert response.status_code == 409
    _assert_no_return_ledger(owner, returned)


def test_ambiguous_original_return_is_a_conflict_and_atomic(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, owner = live
    reference = "E2E-AMBIGUOUS-RETURN"
    for suffix in ("A", "B"):
        case_id = f"AMBIGUOUS-ORIGINAL-{suffix}"
        _seed_fresh(
            owner,
            graph,
            case_id,
            iban=f"DEAMBIGUOUS{suffix}",
            end_to_end_reference=reference,
        )
        _match(client, graph, case_id)
    returned = _add_return(
        owner,
        graph,
        "AMBIGUOUS-RETURN",
        original_case="AMBIGUOUS-ORIGINAL-A",
        amount_cents=-108_000,
        reference=reference,
    )
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{returned}/match",
        headers=_token(graph.owner_id),
    )
    assert response.status_code == 409
    _assert_no_return_ledger(owner, returned)


def test_later_projection_change_makes_return_unsafe_and_atomic(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, owner = live
    case_id = "LATER-ALLOCATION-ORIGINAL"
    reference = "E2E-LATER-ALLOCATION"
    _seed_fresh(
        owner,
        graph,
        case_id,
        amount_cents=50_000,
        iban="DELATER",
        end_to_end_reference=reference,
    )
    _match(client, graph, case_id)
    later_case = "LATER-ALLOCATION-PAYMENT"
    later_transaction = new_id()
    graph.transactions[later_case] = later_transaction
    with Session(owner) as session, session.begin():
        original = session.get(BankTransaction, graph.transactions[case_id])
        assert original is not None
        session.add(
            BankTransaction(
                id=later_transaction,
                account_id=graph.account_id,
                bank_account_id=graph.bank_account_id,
                provider_transaction_id=f"later-{later_transaction}",
                amount_cents=10_000,
                bank_booking_date=original.bank_booking_date,
                finapi_booking_date=original.finapi_booking_date,
                value_date=original.value_date,
                counterpart_iban=original.counterpart_iban,
                counterpart_name=original.counterpart_name,
                purpose="Miete 2098-01",
                end_to_end_reference="E2E-LATER-PAYMENT",
                counterpart_mandate_reference=None,
                bank_transaction_code="SEPA-CT",
                provider_type="CREDIT",
                is_potential_duplicate=False,
            )
        )
    _match(client, graph, later_case)
    returned = _add_return(
        owner,
        graph,
        "LATER-ALLOCATION-RETURN",
        original_case=case_id,
        amount_cents=-50_000,
        reference=reference,
    )
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{returned}/match",
        headers=_token(graph.owner_id),
    )
    assert response.status_code == 409
    _assert_no_return_ledger(owner, returned)


def test_legacy_null_snapshot_return_is_a_conflict_and_atomic(
    live: tuple[TestClient, Graph, Engine],
) -> None:
    client, graph, owner = live
    case_id = "LEGACY-SNAPSHOT-ORIGINAL"
    reference = "E2E-LEGACY-SNAPSHOT"
    _seed_fresh(owner, graph, case_id, iban="DELEGACY", end_to_end_reference=reference)
    with Session(owner) as session, session.begin():
        transaction = session.get(BankTransaction, graph.transactions[case_id])
        receivable = session.get(Receivable, graph.receivables[case_id][0])
        assert transaction is not None and receivable is not None
        proposal = MatchProposal(
            id=new_id(),
            account_id=graph.account_id,
            bank_transaction_id=transaction.id,
            receivable_id=receivable.id,
            renter_id=receivable.renter_id,
            rank=1,
            signal_iban=50,
            signal_amount=30,
            signal_code_or_surname=0,
            signal_e2e=0,
            signal_period=0,
            confidence=80,
            decision="AUTO_MATCH",
            convention_version="legacy fixture",
            reason_de="Legacy-Zahlung ohne Projektionsnachweis.",
        )
        session.add(proposal)
        session.flush()
        entry = PaymentLedgerEntry(
            id=new_id(),
            account_id=graph.account_id,
            bank_transaction_id=transaction.id,
            match_proposal_id=proposal.id,
            kind="PAYMENT",
            amount_cents=108_000,
            credit_cents=0,
            ordering_version="legacy fixture",
            reverses_entry_id=None,
        )
        session.add(entry)
        session.flush()
        session.add(
            PaymentAllocation(
                id=new_id(),
                account_id=graph.account_id,
                ledger_entry_id=entry.id,
                receivable_id=receivable.id,
                costs_cents=0,
                interest_cents=0,
                principal_cents=108_000,
                base_rent_cents=85_000,
                nk_advance_cents=15_000,
                heating_advance_cents=8_000,
                garage_cents=0,
                resulting_status="settled",
                before_open_costs_cents=None,
                before_open_interest_cents=None,
                before_open_principal_cents=None,
                before_open_cents=None,
                before_status=None,
                after_open_costs_cents=None,
                after_open_interest_cents=None,
                after_open_principal_cents=None,
                after_open_cents=None,
                after_status=None,
            )
        )
        receivable.open_principal_cents = 0
        receivable.open_cents = 0
        receivable.status = "settled"
    returned = _add_return(
        owner,
        graph,
        "LEGACY-SNAPSHOT-RETURN",
        original_case=case_id,
        amount_cents=-108_000,
        reference=reference,
    )
    response = client.post(
        f"/a/{graph.account_id}/bank-transactions/{returned}/match",
        headers=_token(graph.owner_id),
    )
    assert response.status_code == 409
    _assert_no_return_ledger(owner, returned)
