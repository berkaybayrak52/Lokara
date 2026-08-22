"""Confirming a Messdienstleister statement over HTTP (`docs/03` H7, `docs/08` § 8).

Four things are being asserted here, and only the first is an ordinary create:

1. **The confirmation is stored exactly as the document read.** H7 — "validate
   and pass through; never recompute MDL amounts" — so the endpoint's job is to
   persist figures a human confirmed, not to derive them.
2. **A statement the engine cannot accept leaves no trace.** The control-sum
   check runs as a dry run *before* `session.add`, so a mistyped decimal is a
   422 and an empty table, not a row somebody has to notice and delete.
   `01b-F29` requires the block; the "no trace" half is what makes a retry
   safe.
3. **A correction appends.** `CLAUDE.md` § 3.2: a legally relevant record is
   never overwritten. The second confirmation of the same building period is
   `version + 1`, the first one stays readable, and `GET` lists both — an
   append-only record whose superseded versions are invisible is not auditable.
4. **The relationship in the URL is verified.** A member of another account gets
   403 for a building that exists and 403 for one that does not, with the same
   body, because "does this building exist" is itself an answer nobody outside
   the account is owed (`CLAUDE.md` § 3.3).

Plus one assertion that the confirmed row lands on the engine path the renderer
keys off: `packages/pdf/src/lokara_pdf/statement.py::_mdl_section` prints its
table only for `MDL_NET` / `MDL_GROSS`, so a row that resolves to anything else
is a silently blank section on a landlord's statement.

Same skip contract as the other live suites: skips without a reachable DB, but
LOKARA_REQUIRE_DB (set in CI) forbids the skip.
"""

import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.settings import ApiSettings
from lokara_api.statement_service import RULES_AS_OF, mdl_statement_input
from lokara_db import (
    Account,
    Building,
    DbSettings,
    MdlStatement,
    Membership,
    Person,
    Renter,
    Role,
    Tenancy,
    TenancyParty,
    Unit,
    create_db_engine,
)
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from lokara_domain import Period
from lokara_heating_engine import calculate_page01b_statement
from lokara_rules_store import CO2_SPLIT_TABLE, get_rule
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"

# This suite's own object, in the demo account. Never the demo building: a
# confirmed MDL statement *replaces* the §§ 7/8 self-billing run for its period
# (`statement_service._confirmed_mdl`), so writing one onto `bld_demo_muster12`
# would change what every other live suite computes.
BUILDING_ID = "bld_mdl_waermehaus"
UNIT_1, UNIT_2 = "unit_mdl_1", "unit_mdl_2"
TENANCY_1, TENANCY_2 = "ten_mdl_1", "ten_mdl_2"
RENTER_1, RENTER_2 = "ren_mdl_1", "ren_mdl_2"

# A tenancy of the SAME account in ANOTHER building. RLS cannot separate these
# two — only the endpoint's own check of the relationship in the URL can.
FOREIGN_BUILDING_TENANCY = "ten_demo_a1"

ISO_ACCOUNT_ID = "acc_iso_mdl"
ISO_PERSON_ID = "per_iso_mdl"

BASE = f"/a/{DEMO_ACCOUNT_ID}/buildings/{BUILDING_ID}/mdl-statements"

# One NET document: the landlord's CO₂ share was already deducted by the
# Messdienstleister, so positions + Eigentümerposition == confirmed total.
NET_BODY: dict[str, Any] = {
    "branch": "NET",
    "periodFrom": "2025-01-01",
    "periodTo": "2025-12-31",  # inclusive in the request, half-open in storage
    "confirmedTotalCents": 338_218,
    "ownerPositionCents": 3_285,
    "positions": [
        {"tenancyId": TENANCY_1, "amountCents": 201_784},
        {"tenancyId": TENANCY_2, "amountCents": 133_149},
    ],
    "sourceRef": "Techem-Abrechnung 2025, Beleg 4711",
}

# One GROSS document: still carrying the CO₂ cost, which the engine splits and
# then rescales the positions by. The CO₂ triple is transcribed from the
# document, never computed here.
GROSS_BODY: dict[str, Any] = {
    "branch": "GROSS",
    "periodFrom": "2025-01-01",
    "periodTo": "2025-12-31",
    "confirmedTotalCents": 350_600,
    "ownerPositionCents": 3_405,
    "positions": [
        {"tenancyId": TENANCY_1, "amountCents": 209_110},
        {"tenancyId": TENANCY_2, "amountCents": 138_085},
    ],
    "sourceRef": "Techem-Abrechnung 2025 (brutto), Beleg 4712",
    "co2KgX1000": 5_628_000,  # 5.628 kg
    "co2CostCents": 30_954,
    "heatedAreaSqmX100": 19_400,  # 194,00 m²
}

_ADDED_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("tenancy_party", (f"tp_{TENANCY_1}", f"tp_{TENANCY_2}")),
    ("tenancy", (TENANCY_1, TENANCY_2)),
    ("renter", (RENTER_1, RENTER_2)),
    ("unit", (UNIT_1, UNIT_2)),
    ("building", (BUILDING_ID,)),
)


def _owner_engine() -> Engine:
    return create_db_engine(DbSettings().direct_url)


def _drop_confirmations(session: Session) -> None:
    """Positions first — the composite FK to `mdl_statement` is real."""
    session.execute(
        text(
            "DELETE FROM mdl_statement_position WHERE mdl_statement_id IN "
            "(SELECT id FROM mdl_statement WHERE building_id = :b)"
        ),
        {"b": BUILDING_ID},
    )
    session.execute(text("DELETE FROM mdl_statement WHERE building_id = :b"), {"b": BUILDING_ID})


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    settings = DbSettings()
    try:
        owner = create_db_engine(settings.direct_url)
        with owner.connect() as conn:
            conn.execute(text((_DB_PACKAGE_DIR / "scripts" / "init-app-role.sql").read_text()))
            conn.commit()
    except OperationalError as exc:  # DB not running
        if os.environ.get("LOKARA_REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres unreachable (start it with `docker compose up -d`): {exc}")
    command.upgrade(Config(str(_DB_PACKAGE_DIR / "alembic.ini")), "head")
    with Session(owner) as session, session.begin():
        seed_demo(session)
        session.merge(Person(id=ISO_PERSON_ID, email="iso-mdl@lokara.example"))
        session.merge(Account(id=ISO_ACCOUNT_ID, name="Isolationskonto MDL"))
        session.merge(
            Membership(
                id="mem_iso_mdl",
                person_id=ISO_PERSON_ID,
                account_id=ISO_ACCOUNT_ID,
                role=Role.OWNER,
            )
        )
        _drop_confirmations(session)
        session.merge(
            Building(
                id=BUILDING_ID,
                account_id=DEMO_ACCOUNT_ID,
                name="Wärmehaus 7",
                street="Wärmeweg 7",
                postal_code="50667",
                city="Köln",
            )
        )
        for unit_id, label, area in ((UNIT_1, "WE 1 (MDL)", 9_000), (UNIT_2, "WE 2 (MDL)", 6_000)):
            session.merge(
                Unit(
                    id=unit_id,
                    account_id=DEMO_ACCOUNT_ID,
                    building_id=BUILDING_ID,
                    label=label,
                    area_sqm_x100=area,
                )
            )
        for renter_id, name in ((RENTER_1, "Frieda Wärmer"), (RENTER_2, "Gustav Heizer")):
            session.merge(Renter(id=renter_id, account_id=DEMO_ACCOUNT_ID, legal_name=name))
        for tenancy_id, unit_id, renter_id in (
            (TENANCY_1, UNIT_1, RENTER_1),
            (TENANCY_2, UNIT_2, RENTER_2),
        ):
            session.merge(
                Tenancy(
                    id=tenancy_id,
                    account_id=DEMO_ACCOUNT_ID,
                    unit_id=unit_id,
                    valid_from=date(2024, 1, 1),
                    valid_to=None,
                    base_rent_cents=80_000,
                    advance_payment_cents=18_000,
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
    owner.dispose()

    yield TestClient(create_app())

    teardown = _owner_engine()
    with Session(teardown) as session, session.begin():
        _drop_confirmations(session)
        for table, ids in _ADDED_ROWS:
            session.execute(text(f"DELETE FROM {table} WHERE id = ANY(:ids)"), {"ids": list(ids)})
    teardown.dispose()


@pytest.fixture
def no_confirmations(client: TestClient) -> Iterator[None]:
    """Every test starts from zero confirmations for this building, so `version`
    is a statement about the test's own calls and not about execution order."""
    engine = _owner_engine()
    with Session(engine) as session, session.begin():
        _drop_confirmations(session)
    yield
    with Session(engine) as session, session.begin():
        _drop_confirmations(session)
    engine.dispose()


def _token(person_id: str, account_id: str) -> dict[str, str]:
    encoded = jwt.encode(
        {"sub": person_id, "account_id": account_id},
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {encoded}"}


DEMO = _token(DEMO_PERSON_ID, DEMO_ACCOUNT_ID)


def _post(client: TestClient, body: dict[str, Any]) -> Any:
    return client.post(BASE, headers=DEMO, json=body)


def _stored() -> list[MdlStatement]:
    """The persisted confirmations, read outside the API under the owner role."""
    engine = _owner_engine()
    with Session(engine) as session:
        rows = list(
            session.scalars(
                select(MdlStatement)
                .where(MdlStatement.building_id == BUILDING_ID)
                .order_by(MdlStatement.version)
            ).all()
        )
        for row in rows:  # load the positions before the session closes
            len(row.positions)
        session.expunge_all()
    engine.dispose()
    return rows


class TestConfirmation:
    def test_a_valid_statement_is_created_and_persisted_as_delivered(
        self, client: TestClient, no_confirmations: None
    ) -> None:
        """H7 pass-through: every figure in the row is the figure that was sent."""
        response = _post(client, NET_BODY)
        assert response.status_code == 201, response.text
        body = response.json()

        assert body["branch"] == "NET"
        assert body["version"] == 1
        assert body["positionCount"] == 2
        assert body["confirmedTotalCents"] == 338_218
        assert body["ownerPositionCents"] == 3_285
        assert body["sourceRef"] == "Techem-Abrechnung 2025, Beleg 4711"
        # Inclusive on both ends as a human reads it, from a half-open period.
        assert body["periodLabel"] == "01.01.2025 – 31.12.2025"

        [row] = _stored()
        assert row.id == body["id"]
        assert row.confirmed_total_cents == 338_218
        assert row.owner_position_cents == 3_285
        assert {p.tenancy_id: p.amount_cents for p in row.positions} == {
            TENANCY_1: 201_784,
            TENANCY_2: 133_149,
        }
        # The request's inclusive end is stored half-open, like every other
        # period in the schema.
        assert (row.period_from, row.period_to) == (date(2025, 1, 1), date(2026, 1, 1))
        # Every position carries the account of the building it was filed under.
        assert {p.account_id for p in row.positions} == {DEMO_ACCOUNT_ID}

    def test_a_control_sum_mismatch_is_422_and_writes_nothing(
        self, client: TestClient, no_confirmations: None
    ) -> None:
        """`01b-F29`: an OCR decimal shift must block, not produce a statement.

        The amount below is one digit short — the exact failure the guard exists
        for. What is asserted twice is that the refusal is *complete*: the engine
        runs as a dry run before `session.add`, so a rejected upload leaves no
        row, no position and nothing for a landlord to discover later.
        """
        broken = {
            **NET_BODY,
            "positions": [
                {"tenancyId": TENANCY_1, "amountCents": 20_178},  # 201.784 → 20.178
                {"tenancyId": TENANCY_2, "amountCents": 133_149},
            ],
        }
        response = _post(client, broken)

        assert response.status_code == 422, response.text
        detail = response.json()["detail"]
        assert "Kontrollsumme" in detail
        assert "blockiert" in detail

        assert _stored() == []
        listed = client.get(BASE, headers=DEMO)
        assert listed.status_code == 200
        assert listed.json() == []

    def test_a_tenancy_from_another_building_is_404_naming_it(
        self, client: TestClient, no_confirmations: None
    ) -> None:
        """Same account, wrong object — the case RLS cannot see.

        The tenancy below is the demo building's, so account scoping is
        satisfied and only the relationship carried in the URL refuses it
        (`CLAUDE.md` § 3.3). The offending id is named because the landlord has
        to be able to find the wrong line in the document they just typed.
        """
        response = _post(
            client,
            {
                **NET_BODY,
                "positions": [
                    {"tenancyId": TENANCY_1, "amountCents": 201_784},
                    {"tenancyId": FOREIGN_BUILDING_TENANCY, "amountCents": 133_149},
                ],
            },
        )

        assert response.status_code == 404, response.text
        detail = response.json()["detail"]
        assert "Mietverhältnis nicht in diesem Objekt" in detail
        assert FOREIGN_BUILDING_TENANCY in detail
        assert TENANCY_1 not in detail  # only the offending one is named
        assert _stored() == []


class TestAppendOnlyVersioning:
    """`CLAUDE.md` § 3.2 over HTTP: a correction is a new row, never an update."""

    def test_a_correction_appends_a_version_and_leaves_the_first_one_readable(
        self, client: TestClient, no_confirmations: None
    ) -> None:
        first = _post(client, NET_BODY)
        assert first.status_code == 201, first.text

        corrected = {
            **NET_BODY,
            "confirmedTotalCents": 340_000,
            "ownerPositionCents": 5_067,
            "positions": [
                {"tenancyId": TENANCY_1, "amountCents": 201_784},
                {"tenancyId": TENANCY_2, "amountCents": 133_149},
            ],
            "sourceRef": "Techem-Korrektur 2025, Beleg 4711-K",
        }
        second = _post(client, corrected)
        assert second.status_code == 201, second.text

        assert second.json()["version"] == 2
        assert second.json()["id"] != first.json()["id"]

        # The superseded row is untouched: same id, same figures, same version.
        original, correction = _stored()
        assert (original.id, original.version) == (first.json()["id"], 1)
        assert original.confirmed_total_cents == 338_218
        assert original.source_ref == "Techem-Abrechnung 2025, Beleg 4711"
        assert (correction.id, correction.version) == (second.json()["id"], 2)
        assert correction.confirmed_total_cents == 340_000
        # Same building period — which is what makes this a correction rather
        # than a second, unrelated document.
        assert (original.period_from, original.period_to) == (
            correction.period_from,
            correction.period_to,
        )

    def test_the_listing_shows_the_superseded_version_too(
        self, client: TestClient, no_confirmations: None
    ) -> None:
        """An append-only record whose earlier versions are invisible is not
        auditable — the reader takes the highest version, but must be able to
        see what it replaced."""
        _post(client, NET_BODY)
        _post(client, {**NET_BODY, "sourceRef": "Techem-Korrektur 2025"})

        listed = client.get(BASE, headers=DEMO)
        assert listed.status_code == 200, listed.text
        rows = listed.json()

        assert [row["version"] for row in rows] == [2, 1]  # newest first
        assert [row["sourceRef"] for row in rows] == [
            "Techem-Korrektur 2025",
            "Techem-Abrechnung 2025, Beleg 4711",
        ]


class TestPathReauthorization:
    """The endpoint verifies the relationship in the URL, not the token's own
    account (`CLAUDE.md` § 3.3). A valid session elsewhere is still a stranger
    here."""

    def test_a_member_of_another_account_cannot_confirm_or_read(
        self, client: TestClient, no_confirmations: None
    ) -> None:
        headers = _token(ISO_PERSON_ID, ISO_ACCOUNT_ID)  # a perfectly valid session

        assert client.post(BASE, headers=headers, json=NET_BODY).status_code == 403
        assert client.get(BASE, headers=headers).status_code == 403
        assert _stored() == []

    def test_the_refusal_does_not_disclose_whether_the_building_exists(
        self, client: TestClient
    ) -> None:
        """403 before the building is ever looked up. If a real object answered
        differently from an invented one, the endpoint would enumerate another
        account's portfolio to anyone holding any valid token."""
        headers = _token(ISO_PERSON_ID, ISO_ACCOUNT_ID)
        real = client.get(BASE, headers=headers)
        invented = client.get(
            f"/a/{DEMO_ACCOUNT_ID}/buildings/bld_gibt_es_nicht/mdl-statements", headers=headers
        )

        assert real.status_code == invented.status_code == 403
        assert real.json() == invented.json()


class TestEnginePath:
    """The renderer keys its entire table off `values.path`
    (`lokara_pdf.statement._mdl_section`), so what the stored row resolves to is
    the difference between a printed pass-through table and a blank section."""

    @pytest.mark.parametrize(
        ("body", "expected_path"),
        [(NET_BODY, "MDL_NET"), (GROSS_BODY, "MDL_GROSS")],
        ids=["net", "gross"],
    )
    def test_a_confirmed_row_lands_on_the_mdl_path(
        self,
        client: TestClient,
        no_confirmations: None,
        body: dict[str, Any],
        expected_path: str,
    ) -> None:
        assert _post(client, body).status_code == 201

        [row] = _stored()
        window = Period(valid_from=row.period_from, valid_to=row.period_to)
        result = calculate_page01b_statement(
            mdl_statement_input(row, get_rule(CO2_SPLIT_TABLE, RULES_AS_OF), window)
        )

        assert result.readiness == "READY"
        assert result.values is not None
        assert result.values.path == expected_path
        # Pass-through, not recomputation: the positions the renderer prints are
        # keyed by the tenancy ids that were confirmed (`docs/03` H7).
        assert set(result.values.renter_ids) == {TENANCY_1, TENANCY_2}
