"""Page 01 D1 over HTTP: one calculation, three projections, one privacy boundary.

Spec: `docs/08-statement-document.md` "Page 01 output contract" and § 3 "Audience
split and privacy boundary" — "The server constructs each projection from the
selected result before rendering. It never renders an all-renters PDF and crops,
covers or hides rows afterward; hidden PDF structure is still a disclosure." —
plus `docs/02-data-model.md` § 5 steps 1–4.

THE test in this file is `TestTenantProjectionIsAPrivacyBoundary`: it asserts
against the **serialized response body**, not the parsed line list. A field a
client forgets to hide is the failure mode the projection type exists to make
impossible, and only the bytes on the wire can prove it did.

Second theme: period and object selection. `period_to` is inclusive in the URL
and half-open internally, a Rumpfperiode is day-exact, and more than 12 months
hard-blocks with a German sentence naming the latest permitted end date
(`docs/08` "Period boundary", `08-F15`).

Same skip contract as the other live suites: skips without a reachable DB, but
LOKARA_REQUIRE_DB (set in CI) forbids the skip.
"""

import os
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.settings import ApiSettings
from lokara_db import (
    Building,
    DbSettings,
    Meter,
    MeterReading,
    PersonCount,
    Renter,
    Tenancy,
    TenancyParty,
    Unit,
    create_db_engine,
)
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from lokara_domain import MeasurementUnit, MeterKind, ReadingReason, ReadingSource
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

NBSP = " "  # format_eur puts a non-breaking space before the € sign
_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"

BASE = f"/a/{DEMO_ACCOUNT_ID}"
DEMO_BUILDING_ID = "bld_demo_muster12"
STATEMENT = f"{BASE}/buildings/{DEMO_BUILDING_ID}/statement"

# The seeded scenario (docs/06 Scenario 1 + 2), by party.
TEN_A = "ten_demo_a1"  # Anna Beispiel, Wohnung A, whole window
TEN_B = "ten_demo_b1"  # Bernd Muster, Wohnung B, moves out 30.06.2025
TEN_C = "ten_demo_c1"  # Clara Vorlage, Wohnung C, whole window

# Rows this suite adds to the demo account and removes again in teardown.
SECOND_BUILDING_ID = "bld_p01_zweites_haus"
SECOND_UNIT_ID = "unit_p01_zweites"
SECOND_TENANCY_ID = "ten_p01_zweites"
SECOND_RENTER_ID = "ren_p01_zweites"
# A tenancy of the DEMO building that starts after the billing window: it exists,
# it is account- and building-valid, and it has zero clipped usage days.
FUTURE_TENANCY_ID = "ten_p01_zukunft"
FUTURE_RENTER_ID = "ren_p01_zukunft"

# The canonical €1.200,00 AREA split (docs/03), in party order A, B-renter,
# B-vacancy, C. Repeated here rather than imported so a change to the shared
# fixture cannot silently move this file's expectations too.
GOLDEN_AREA_SHARES = [60000, 17852, 18148, 24000]

_ADDED_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("tenancy_party", (f"tp_{SECOND_TENANCY_ID}", f"tp_{FUTURE_TENANCY_ID}")),
    ("tenancy", (SECOND_TENANCY_ID, FUTURE_TENANCY_ID)),
    ("renter", (SECOND_RENTER_ID, FUTURE_RENTER_ID)),
    ("unit", (SECOND_UNIT_ID,)),
    ("building", (SECOND_BUILDING_ID,)),
)


def _owner_engine() -> Any:
    return create_db_engine(DbSettings().direct_url)


def _remove_added_rows(session: Session) -> None:
    for table, ids in _ADDED_ROWS:
        session.execute(text(f"DELETE FROM {table} WHERE id = ANY(:ids)"), {"ids": list(ids)})


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
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
    with Session(owner) as session, session.begin():
        seed_demo(session)
        # Deterministic start: exactly the seeded cost with exactly its seeded
        # AREA assignment. Leftovers from an interrupted run would break the
        # golden-number assertions below.
        session.execute(
            text(
                "DELETE FROM allocation_key_assignment "
                "WHERE account_id = :a AND id <> 'aka_demo_garbage_1'"
            ),
            {"a": DEMO_ACCOUNT_ID},
        )
        session.execute(
            text("DELETE FROM cost_entry WHERE account_id = :a AND id <> 'cost_demo_garbage'"),
            {"a": DEMO_ACCOUNT_ID},
        )
        session.execute(
            text("DELETE FROM person_count WHERE account_id = :a"), {"a": DEMO_ACCOUNT_ID}
        )
        _remove_added_rows(session)

        # A SECOND building in the SAME account. RLS cannot separate these two —
        # only the endpoint's own check of the relationship carried in the URL
        # can (`CLAUDE.md` § 3.3).
        session.add(
            Building(
                id=SECOND_BUILDING_ID,
                account_id=DEMO_ACCOUNT_ID,
                name="Zweites Haus",
                street="Nebenweg 3",
                postal_code="60313",
                city="Frankfurt am Main",
            )
        )
        session.add(
            Unit(
                id=SECOND_UNIT_ID,
                account_id=DEMO_ACCOUNT_ID,
                building_id=SECOND_BUILDING_ID,
                label="Wohnung N (Nebenweg)",
                area_sqm_x100=4000,
            )
        )
        session.add(
            Renter(id=SECOND_RENTER_ID, account_id=DEMO_ACCOUNT_ID, legal_name="Dora Nachbar")
        )
        session.add(
            Tenancy(
                id=SECOND_TENANCY_ID,
                account_id=DEMO_ACCOUNT_ID,
                unit_id=SECOND_UNIT_ID,
                valid_from=date(2024, 1, 1),
                valid_to=None,
                base_rent_cents=70000,
                advance_payment_cents=16000,
            )
        )
        session.add(
            TenancyParty(
                id=f"tp_{SECOND_TENANCY_ID}",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=SECOND_TENANCY_ID,
                renter_id=SECOND_RENTER_ID,
            )
        )

        # A future tenancy of unit B: no overlap with Bernd Muster's lease and no
        # clipped usage day in 2025 (`docs/08`: "Zero clipped usage days produces
        # no tenant document or portal item and is not itself vacancy").
        session.add(
            Renter(id=FUTURE_RENTER_ID, account_id=DEMO_ACCOUNT_ID, legal_name="Emil Künftig")
        )
        session.add(
            Tenancy(
                id=FUTURE_TENANCY_ID,
                account_id=DEMO_ACCOUNT_ID,
                unit_id="unit_demo_b",
                valid_from=date(2026, 2, 1),
                valid_to=date(2026, 6, 1),
                base_rent_cents=70000,
                advance_payment_cents=16000,
            )
        )
        session.add(
            TenancyParty(
                id=f"tp_{FUTURE_TENANCY_ID}",
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=FUTURE_TENANCY_ID,
                renter_id=FUTURE_RENTER_ID,
            )
        )
    owner.dispose()

    yield TestClient(create_app())

    teardown = create_db_engine(settings.direct_url)
    with Session(teardown) as session, session.begin():
        session.execute(
            text("DELETE FROM person_count WHERE account_id = :a"), {"a": DEMO_ACCOUNT_ID}
        )
        _remove_added_rows(session)
    teardown.dispose()


def _token(person_id: str, account_id: str) -> dict[str, str]:
    encoded = jwt.encode(
        {"sub": person_id, "account_id": account_id},
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {encoded}"}


DEMO = _token(DEMO_PERSON_ID, DEMO_ACCOUNT_ID)


def _get(client: TestClient, **params: str) -> Any:
    response = client.get(STATEMENT, headers=DEMO, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _lines(body: Any) -> list[Any]:
    return [line for cost in body["costs"] for line in cost["lines"]]


# ── Audience projection ───────────────────────────────────────────────────────


class TestOwnerProjection:
    """ "The owner view reconciles" (`docs/08`): every covered tenancy plus one
    unconditional owner residual."""

    def test_every_party_line_is_present_and_reconciles_to_the_cost(
        self, client: TestClient
    ) -> None:
        body = _get(client, audience="OWNER")
        [garbage] = body["costs"]
        assert garbage["label"] == "Müllabfuhr"
        assert garbage["keyLabel"] == "Wohnfläche (m²·Tage)"
        assert [line["amountCents"] for line in garbage["lines"]] == GOLDEN_AREA_SHARES
        assert sum(line["amountCents"] for line in garbage["lines"]) == garbage["totalCents"]

    def test_the_vacancy_line_is_marked_as_the_landlords(self, client: TestClient) -> None:
        body = _get(client, audience="OWNER")
        [garbage] = body["costs"]
        [vacancy] = [line for line in garbage["lines"] if line["isLandlord"]]
        assert vacancy["amountCents"] == 18148
        assert vacancy["partyLabel"] == "Wohnung B (EG rechts) — Leerstand → Vermieter"

    def test_the_owner_residual_is_present_and_is_the_last_heating_line(
        self, client: TestClient
    ) -> None:
        body = _get(client, audience="OWNER")
        lines = body["heatingLines"]
        assert len(lines) == 4  # A, B-renter, C, then the Eigentümeranteil
        residual = lines[-1]
        assert residual["partyLabel"] == "Eigentümeranteil"
        assert residual["isLandlord"] is True
        assert body["ownerResidualCents"] == residual["totalCents"]

    def test_it_carries_no_tenancy_id(self, client: TestClient) -> None:
        assert _get(client, audience="OWNER")["tenancyId"] is None

    def test_owner_is_the_default_audience(self, client: TestClient) -> None:
        assert _get(client) == _get(client, audience="OWNER")


class TestTenantProjectionIsAPrivacyBoundary:
    """`docs/08` § 3: never render everything and crop. What the response does
    not contain, no client can leak."""

    def test_only_that_tenancys_lines_are_returned(self, client: TestClient) -> None:
        body = _get(client, audience="TENANT", tenancy_id=TEN_B)
        assert body["tenancyId"] == TEN_B
        lines = _lines(body)
        assert len(lines) == 1
        assert lines[0]["amountCents"] == 17852
        assert "Bernd Muster" in lines[0]["partyLabel"]
        assert "Auszug 30.06.2025" in lines[0]["partyLabel"]

    def test_the_gesamtkosten_of_the_cost_stay_visible(self, client: TestClient) -> None:
        """Formal minimum #1 (`docs/08` § 4): the renter's own document still
        states the Zusammenstellung der Gesamtkosten per cost type."""
        body = _get(client, audience="TENANT", tenancy_id=TEN_B)
        [garbage] = body["costs"]
        assert garbage["totalCents"] == 120000
        assert garbage["totalEur"] == f"1.200,00{NBSP}€"

    def test_no_owner_residual_reaches_a_renter(self, client: TestClient) -> None:
        body = _get(client, audience="TENANT", tenancy_id=TEN_B)
        assert body["ownerResidualCents"] is None
        assert all(line["isLandlord"] is False for line in body["heatingLines"])
        assert all(line["isLandlord"] is False for line in _lines(body))

    def test_the_vacancy_line_of_its_own_unit_is_excluded(self, client: TestClient) -> None:
        """Unit B is both rented and vacant in 2025. Bernd Muster's document must
        carry his 181 days and not the 184 that followed them."""
        response = client.get(
            STATEMENT, headers=DEMO, params={"audience": "TENANT", "tenancy_id": TEN_B}
        )
        assert "Leerstand" not in response.text
        assert "18148" not in response.text
        assert f"181,48{NBSP}€" not in response.text

    def test_no_other_partys_label_or_amount_appears_in_the_serialized_body(
        self, client: TestClient
    ) -> None:
        """The assertion that matters, made against the bytes on the wire."""
        owner = _get(client, audience="OWNER")
        tenant_response = client.get(
            STATEMENT, headers=DEMO, params={"audience": "TENANT", "tenancy_id": TEN_B}
        )
        assert tenant_response.status_code == 200
        body = tenant_response.text

        own_amounts = {line["amountEur"] for line in _lines(tenant_response.json())}
        own_labels = {line["partyLabel"] for line in _lines(tenant_response.json())}
        foreign_amounts_checked = 0
        for line in _lines(owner):
            if line["partyLabel"] in own_labels:
                continue
            assert line["partyLabel"] not in body, line["partyLabel"]
            # Only skip an amount that is genuinely also this renter's own — a
            # coincidence of figures may not silently disarm the assertion.
            if line["amountEur"] in own_amounts:
                continue
            assert line["amountEur"] not in body, line["amountEur"]
            foreign_amounts_checked += 1
        assert foreign_amounts_checked == 3  # A, the B vacancy and C

    def test_no_other_renters_name_appears_in_the_serialized_body(self, client: TestClient) -> None:
        response = client.get(
            STATEMENT, headers=DEMO, params={"audience": "TENANT", "tenancy_id": TEN_B}
        )
        for name in ("Anna Beispiel", "Clara Vorlage", "Dora Nachbar", "Emil Künftig"):
            assert name not in response.text, name
        for label in ("Wohnung A (EG links)", "Wohnung C (1. OG)"):
            assert label not in response.text, label

    def test_no_other_partys_heating_figures_appear(self, client: TestClient) -> None:
        response = client.get(
            STATEMENT, headers=DEMO, params={"audience": "TENANT", "tenancy_id": TEN_B}
        )
        body = response.json()
        [line] = body["heatingLines"]
        # The renter's own degree-day share (docs/06 Scenario 2) is present …
        assert line["heatingConsumptionEur"] == f"776,39{NBSP}€"
        # … and the Eigentümeranteil that mirrors it across the move-out is not.
        assert f"554,87{NBSP}€" not in response.text
        assert "Eigentümeranteil" not in response.text

    def test_building_wide_findings_stay_on_the_landlords_side(self, client: TestClient) -> None:
        """Findings name other units by label, so they are operational notes for
        the landlord, not renter copy."""
        assert _get(client, audience="TENANT", tenancy_id=TEN_B)["findings"] == []


class TestTaxProjection:
    """Leerstandsaufstellung — landlord/tax evidence, no renter data."""

    def test_only_owner_side_rows_are_returned(self, client: TestClient) -> None:
        body = _get(client, audience="TAX")
        lines = _lines(body)
        assert [line["amountCents"] for line in lines] == [18148]
        assert all(line["isLandlord"] is True for line in lines)

    def test_the_vacancy_row_keeps_its_origin_unit(self, client: TestClient) -> None:
        """`docs/08`: "Block (a) itemises vacancy by unit and cost type"."""
        [line] = _lines(_get(client, audience="TAX"))
        assert line["partyLabel"] == "Wohnung B (EG rechts) — Leerstand → Vermieter"

    def test_it_carries_the_owner_residual_but_no_renter_heating_line(
        self, client: TestClient
    ) -> None:
        body = _get(client, audience="TAX")
        [line] = body["heatingLines"]
        assert line["partyLabel"] == "Eigentümeranteil"
        assert body["ownerResidualCents"] == line["totalCents"]

    def test_no_renter_name_appears_anywhere(self, client: TestClient) -> None:
        response = client.get(STATEMENT, headers=DEMO, params={"audience": "TAX"})
        assert response.status_code == 200
        for name in ("Anna Beispiel", "Bernd Muster", "Clara Vorlage"):
            assert name not in response.text, name

    def test_it_carries_no_tenancy_id(self, client: TestClient) -> None:
        assert _get(client, audience="TAX")["tenancyId"] is None


class TestTenantSelectionFailsClosed:
    """ "A missing or foreign tenancy fails and never falls back to an owner
    view" (`docs/08` Page 01 output contract)."""

    def _refused(self, client: TestClient, **params: str) -> Any:
        response = client.get(STATEMENT, headers=DEMO, params=params)
        assert response.status_code == 404, response.text
        # Never the owner view: not one figure of it may be in the body.
        assert "60000" not in response.text
        assert "ownerResidualCents" not in response.text
        return response.json()

    def test_a_missing_tenancy_id_is_a_404(self, client: TestClient) -> None:
        body = self._refused(client, audience="TENANT")
        assert body["detail"] == "Mietverhältnis nicht gefunden."

    def test_an_unknown_tenancy_id_is_a_404(self, client: TestClient) -> None:
        body = self._refused(client, audience="TENANT", tenancy_id="ten_does_not_exist")
        assert body["detail"] == "Mietverhältnis nicht gefunden."

    def test_a_tenancy_of_another_building_in_the_same_account_is_a_404(
        self, client: TestClient
    ) -> None:
        """RLS cannot help here — both buildings belong to the demo account. The
        endpoint verifies the relationship carried in the URL itself."""
        body = self._refused(client, audience="TENANT", tenancy_id=SECOND_TENANCY_ID)
        assert body["detail"] == "Mietverhältnis nicht gefunden."

    def test_that_same_tenancy_resolves_on_its_own_building(self, client: TestClient) -> None:
        """Which proves the 404 above is about the building relationship and not
        about an id the account cannot see at all."""
        response = client.get(
            f"{BASE}/buildings/{SECOND_BUILDING_ID}/statement",
            headers=DEMO,
            params={"audience": "TENANT", "tenancy_id": SECOND_TENANCY_ID},
        )
        assert response.status_code == 200, response.text
        assert response.json()["tenancyId"] == SECOND_TENANCY_ID

    def test_a_tenancy_with_zero_clipped_usage_days_produces_no_document(
        self, client: TestClient
    ) -> None:
        """`docs/08`: "Zero clipped usage days produces no tenant document or
        portal item and is not itself vacancy." Its own answer, separate from
        "no such party here", so the 404 does not reveal which ids exist."""
        body = self._refused(client, audience="TENANT", tenancy_id=FUTURE_TENANCY_ID)
        assert body["detail"] == (
            "Dieses Mietverhältnis hat im Abrechnungszeitraum keine Nutzungstage; "
            "es entsteht keine Mieterabrechnung."
        )

    def test_an_unknown_building_is_a_404(self, client: TestClient) -> None:
        response = client.get(f"{BASE}/buildings/bld_does_not_exist/statement", headers=DEMO)
        assert response.status_code == 404


# ── Period and object selection ───────────────────────────────────────────────


class TestPeriodSelection:
    def test_omitting_the_dates_reproduces_the_demo_preset(self, client: TestClient) -> None:
        body = _get(client, audience="OWNER")
        assert body["periodLabel"] == "01.01.2025 – 31.12.2025"
        assert [line["amountCents"] for line in _lines(body)] == GOLDEN_AREA_SHARES

    def test_period_to_is_inclusive_in_the_url(self, client: TestClient) -> None:
        """`31.12.2025` means the year, not the year minus its last day."""
        explicit = _get(client, audience="OWNER", period_from="2025-01-01", period_to="2025-12-31")
        assert explicit == _get(client, audience="OWNER")

    def test_a_rumpfperiode_is_day_exact(self, client: TestClient) -> None:
        """Half a year: A keeps 181 of 181 days, B is still rented for all of
        them (the move-out is 30.06.), C keeps 181 — so the same €1.200,00
        divides 5.000/3.000/2.000 m² clean, and no vacancy line exists at all."""
        body = _get(client, audience="OWNER", period_from="2025-01-01", period_to="2025-06-30")
        assert body["periodLabel"] == "01.01.2025 – 30.06.2025"
        lines = _lines(body)
        assert [line["amountCents"] for line in lines] == [60000, 36000, 24000]
        assert all(line["isLandlord"] is False for line in lines)
        assert sum(line["amountCents"] for line in lines) == 120000

    def test_a_rumpfperiode_changes_the_renters_share(self, client: TestClient) -> None:
        """The point of day-exactness: Bernd Muster carries 178,52 € of the year
        and 360,00 € of the half-year he was there for all of."""
        year = _get(client, audience="TENANT", tenancy_id=TEN_B)
        half = _get(
            client,
            audience="TENANT",
            tenancy_id=TEN_B,
            period_from="2025-01-01",
            period_to="2025-06-30",
        )
        assert _lines(year)[0]["amountCents"] == 17852
        assert _lines(half)[0]["amountCents"] == 36000

    def test_a_leap_day_window_keeps_its_366_days(self, client: TestClient) -> None:
        """`08-F20`: leap years keep their actual days, and 12 months is still
        12 months — 2024 must be accepted, not rejected as 366 > 365."""
        body = _get(client, audience="OWNER", period_from="2024-01-01", period_to="2024-12-31")
        assert body["periodLabel"] == "01.01.2024 – 31.12.2024"


class TestPeriodIsRefusedInGerman:
    def _rejected(self, client: TestClient, **params: str) -> str:
        response = client.get(STATEMENT, headers=DEMO, params=params)
        assert response.status_code == 422, response.text
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        return detail

    def test_more_than_twelve_months_hard_blocks(self, client: TestClient) -> None:
        """`docs/08` "Period boundary" / `08-F15`: the block happens before any
        cost is allocated, and the message names the latest permitted end date
        because shortening the period is the landlord's next action."""
        detail = self._rejected(client, period_from="2025-01-01", period_to="2026-01-01")
        assert detail == (
            "Ein Abrechnungszeitraum darf höchstens 12 Monate umfassen. "
            "Für einen Beginn am 01.01.2025 ist spätestens der 31.12.2025 zulässig."
        )

    def test_the_named_end_date_follows_the_start(self, client: TestClient) -> None:
        detail = self._rejected(client, period_from="2025-07-01", period_to="2026-07-01")
        assert "spätestens der 30.06.2026 zulässig" in detail

    def test_no_share_is_returned_with_the_block(self, client: TestClient) -> None:
        response = client.get(
            STATEMENT, headers=DEMO, params={"period_from": "2025-01-01", "period_to": "2026-01-01"}
        )
        assert "costs" not in response.text

    def test_only_a_start_date_is_refused(self, client: TestClient) -> None:
        assert (
            self._rejected(client, period_from="2025-01-01")
            == "Abrechnungszeitraum braucht Anfang und Ende."
        )

    def test_only_an_end_date_is_refused(self, client: TestClient) -> None:
        assert (
            self._rejected(client, period_to="2025-12-31")
            == "Abrechnungszeitraum braucht Anfang und Ende."
        )

    def test_an_end_before_the_start_is_refused(self, client: TestClient) -> None:
        assert (
            self._rejected(client, period_from="2025-12-31", period_to="2025-01-01")
            == "Das Ende des Abrechnungszeitraums liegt vor seinem Anfang."
        )


class TestObjectSelection:
    def test_the_building_comes_from_the_url_not_from_a_preset(self, client: TestClient) -> None:
        demo = _get(client, audience="OWNER")
        second = client.get(f"{BASE}/buildings/{SECOND_BUILDING_ID}/statement", headers=DEMO)
        assert second.status_code == 200, second.text
        assert demo["buildingName"] == "Musterstraße 12"
        assert second.json()["buildingName"] == "Zweites Haus"
        # No cost entered there yet, so there is nothing to allocate — and that
        # is a valid statement, not an error.
        assert second.json()["costs"] == []


# ── The keys that used to reach the engine without their inputs ───────────────


def _add_demo_person_counts(session: Session) -> None:
    """Personenzahl per tenancy — a temporal row, never a scalar (`docs/02`).

    Each row is closed exactly where its tenancy closes. Bernd Muster's count
    therefore ends on 01.07.2025 (exclusive) like his lease; see
    `TestPersonCountsOutlivingTheirTenancy` for what happens when it does not.
    """
    for count_id, tenancy_id, count, valid_from, valid_to in (
        ("pcd_demo_b1", TEN_B, 3, date(2021, 9, 1), date(2025, 7, 1)),
        ("pcd_demo_a1", TEN_A, 2, date(2023, 4, 1), None),
        ("pcd_demo_c1", TEN_C, 1, date(2024, 1, 1), None),
    ):
        session.merge(
            PersonCount(
                id=count_id,
                account_id=DEMO_ACCOUNT_ID,
                tenancy_id=tenancy_id,
                count=count,
                valid_from=valid_from,
                valid_to=valid_to,
            )
        )


def _create_cost(client: TestClient, label: str, amount_cents: int, key: str) -> str:
    response = client.post(
        f"{BASE}/buildings/{DEMO_BUILDING_ID}/costs",
        headers=DEMO,
        json={
            "label": label,
            "amountCents": amount_cents,
            "periodFrom": "2025-01-01",
            "periodTo": "2026-01-01",
            "key": key,
        },
    )
    assert response.status_code == 201, response.text
    cost_id: str = response.json()["id"]
    return cost_id


class TestPersonsKeyReachesTheEngineWithItsInputs:
    """The live defect this closes: `routers/costs.py` accepts every key, and a
    persisted PERSONS cost then raised `NkInputError` into an unhandled 500
    because no person-day input ever reached `NkInput`."""

    def test_a_persisted_persons_cost_produces_a_statement_not_a_500(
        self, client: TestClient
    ) -> None:
        engine = _owner_engine()
        with Session(engine) as session, session.begin():
            _add_demo_person_counts(session)
        cost_id = _create_cost(client, "Aufzug", 100000, "PERSONS")
        try:
            response = client.get(f"{BASE}/statements/demo", headers=DEMO)
            assert response.status_code == 200, response.text
            body = response.json()
            lift = next(c for c in body["nkCosts"] if c["label"] == "Aufzug")
            assert lift["keyLabel"] == "Personenzahl (Personen·Tage)"
            # 3 × 181 + 2 × 365 + 1 × 365 + 3 × 184 = 543 + 730 + 365 + 552
            # = 2.190 Personen·Tage — the `08-F23` denominator shape: a vacant
            # stretch stays in the Gesamtverteiler through its fictional count.
            assert [line["weightDisplay"] for line in lift["lines"]] == [
                "543",
                "730",
                "365",
                "552",
            ]
            assert [line["amountCents"] for line in lift["lines"]] == [
                24795,
                33333,
                16667,
                25205,
            ]
            assert sum(line["amountCents"] for line in lift["lines"]) == 100000
        finally:
            assert client.delete(f"{BASE}/costs/{cost_id}", headers=DEMO).status_code == 204
            with Session(engine) as session, session.begin():
                session.execute(
                    text("DELETE FROM person_count WHERE account_id = :a"),
                    {"a": DEMO_ACCOUNT_ID},
                )
            engine.dispose()

    def test_the_d0_row_lands_on_the_landlord_and_names_its_unit(self, client: TestClient) -> None:
        """`docs/02` § 5 D0: a denominator weight on the owner side, never a party."""
        engine = _owner_engine()
        with Session(engine) as session, session.begin():
            _add_demo_person_counts(session)
        cost_id = _create_cost(client, "Aufzug", 100000, "PERSONS")
        try:
            body = client.get(f"{BASE}/statements/demo", headers=DEMO).json()
            lift = next(c for c in body["nkCosts"] if c["label"] == "Aufzug")
            [landlord] = [line for line in lift["lines"] if line["isLandlord"]]
            assert landlord["partyLabel"] == "Wohnung B (EG rechts) — Leerstand → Vermieter"
            assert landlord["weightDisplay"] == "552"
        finally:
            assert client.delete(f"{BASE}/costs/{cost_id}", headers=DEMO).status_code == 204
            with Session(engine) as session, session.begin():
                session.execute(
                    text("DELETE FROM person_count WHERE account_id = :a"),
                    {"a": DEMO_ACCOUNT_ID},
                )
            engine.dispose()

    def test_without_any_person_count_the_fiktivbelegung_alone_carries_the_cost(
        self, client: TestClient
    ) -> None:
        """No entered Personenzahl at all still yields a statement rather than a
        500: unit B's vacancy has no history either, so the fallback 1 of Page 01
        § 3.5 is the whole denominator and the cost lands on the owner."""
        cost_id = _create_cost(client, "Aufzug ohne Personen", 100000, "PERSONS")
        try:
            response = client.get(f"{BASE}/statements/demo", headers=DEMO)
            assert response.status_code == 200, response.text
            lift = next(
                c for c in response.json()["nkCosts"] if c["label"] == "Aufzug ohne Personen"
            )
            assert [(line["amountCents"], line["isLandlord"]) for line in lift["lines"]] == [
                (100000, True)
            ]
        finally:
            assert client.delete(f"{BASE}/costs/{cost_id}", headers=DEMO).status_code == 204


class TestPersonCountsOutlivingTheirTenancy:
    """An entered Personenzahl that is never closed at the move-out.

    `PersonCount.valid_to` is nullable and nothing — no CHECK, no composite FK,
    no code in `person_counts.py` and no code in the engine — clips the row to
    its own tenancy. `_entered_rows` is unclipped "on purpose" because the engine
    intersects each row with the billing *window*; that is a different clip from
    intersecting it with the *tenancy*, and no layer performs the second one.

    So a landlord who enters "3 Personen ab 01.09.2021" and never closes the row
    on move-out has unit B counted twice for the same days: 3 renter person-days
    *and* the D0 fictional occupancy of the vacancy that followed. `docs/02` § 5
    says the fictional occupancy is "added before forming person-days" — added to
    a denominator in which those days belong to nobody, not stacked on top of a
    renter who had already left.

    This test asserts the correct arithmetic and is red today. There is no write
    path for `person_count` yet, so it is a latent gap rather than a live 500 —
    but the table and its migration landed in this slice and the UI will follow.
    """

    def test_a_never_closed_count_must_not_outlive_its_tenancy(self, client: TestClient) -> None:
        engine = _owner_engine()
        with Session(engine) as session, session.begin():
            session.merge(
                PersonCount(
                    id="pcd_demo_b1_open",
                    account_id=DEMO_ACCOUNT_ID,
                    tenancy_id=TEN_B,  # the lease ends 01.07.2025 (exclusive)
                    count=3,
                    valid_from=date(2021, 9, 1),
                    valid_to=None,
                )
            )
        cost_id = _create_cost(client, "Aufzug offen", 100000, "PERSONS")
        try:
            body = client.get(f"{BASE}/statements/demo", headers=DEMO).json()
            lift = next(c for c in body["nkCosts"] if c["label"] == "Aufzug offen")
            renter = next(line for line in lift["lines"] if "Bernd Muster" in line["partyLabel"])
            # 3 persons x 181 rented days, not 3 x 365: the 184 days after the
            # move-out are the vacancy the D0 row already weights.
            assert renter["weightDisplay"] == "543"
        finally:
            assert client.delete(f"{BASE}/costs/{cost_id}", headers=DEMO).status_code == 204
            with Session(engine) as session, session.begin():
                session.execute(text("DELETE FROM person_count WHERE id = 'pcd_demo_b1_open'"))
            engine.dispose()


class TestConsumptionKeyReachesTheEngineWithItsInputs:
    """Kaltwasser is the NK CONSUMPTION Bemessung. Before this slice the meter
    figures were folded away unused, so a CONSUMPTION-keyed cost had no data."""

    def test_a_persisted_consumption_cost_produces_a_statement_not_a_500(
        self, client: TestClient
    ) -> None:
        cost_id = _create_cost(client, "Wasser/Abwasser", 50000, "CONSUMPTION")
        try:
            response = client.get(f"{BASE}/statements/demo", headers=DEMO)
            assert response.status_code == 200, response.text
            water = next(c for c in response.json()["nkCosts"] if c["label"] == "Wasser/Abwasser")
            assert water["keyLabel"] == "Verbrauch"
            # met_demo_kw_c: 340,900 minus 302,400 = 38,5 m³, and unit C had exactly
            # one user across the window, so the figure is attributable.
            [line] = water["lines"]
            assert line["weightDisplay"] == "38,5"
            assert line["partyLabel"] == "Wohnung C (1. OG) — Clara Vorlage"
            assert line["amountCents"] == 50000
        finally:
            assert client.delete(f"{BASE}/costs/{cost_id}", headers=DEMO).status_code == 204


class TestUnattributableConsumptionIsSaidNotSplit:
    """A unit whose renter changed mid-window has one meter figure and two
    parties. `docs/08` forbids document-layer money math, and a day-weighted
    division of a consumption is exactly that."""

    def _add_cold_water_meter_to_unit_b(self, session: Session) -> None:
        session.merge(
            Meter(
                id="met_p01_kw_b",
                account_id=DEMO_ACCOUNT_ID,
                building_id=DEMO_BUILDING_ID,
                unit_id="unit_demo_b",
                kind=MeterKind.COLD_WATER,
                measurement_unit=MeasurementUnit.CUBIC_METRE,
                serial="KWZ-B-441098",
                calibration_valid_until=date(2029, 12, 31),
            )
        )
        for suffix, read_at, value in (
            ("open", date(2025, 1, 1), 100_000),
            ("close", date(2025, 12, 31), 122_000),
        ):
            session.merge(
                MeterReading(
                    id=f"mr_p01_kw_b_{suffix}",
                    account_id=DEMO_ACCOUNT_ID,
                    meter_id="met_p01_kw_b",
                    read_at=read_at,
                    value_x1000=value,
                    reason=ReadingReason.PERIODIC,
                    source=ReadingSource.MDL,
                    recorded_at=datetime(2026, 1, 5, 9, 0),
                )
            )

    def test_the_owner_projection_carries_a_german_finding_and_the_renter_none(
        self, client: TestClient
    ) -> None:
        engine = _owner_engine()
        with Session(engine) as session, session.begin():
            self._add_cold_water_meter_to_unit_b(session)
        try:
            owner = _get(client, audience="OWNER")
            [finding] = owner["findings"]
            assert finding.startswith("Wohnung B (EG rechts): ")
            assert "Nutzerwechsel" in finding
            assert "Zwischenablesung" in finding

            tenant = client.get(
                STATEMENT, headers=DEMO, params={"audience": "TENANT", "tenancy_id": TEN_B}
            )
            assert tenant.json()["findings"] == []
            assert "Nutzerwechsel" not in tenant.text
        finally:
            with Session(engine) as session, session.begin():
                session.execute(text("DELETE FROM meter_reading WHERE meter_id = 'met_p01_kw_b'"))
                session.execute(text("DELETE FROM meter WHERE id = 'met_p01_kw_b'"))
            engine.dispose()

    def test_the_unattributable_unit_contributes_no_consumption_share(
        self, client: TestClient
    ) -> None:
        engine = _owner_engine()
        with Session(engine) as session, session.begin():
            self._add_cold_water_meter_to_unit_b(session)
        cost_id = _create_cost(client, "Wasser/Abwasser", 50000, "CONSUMPTION")
        try:
            body = _get(client, audience="OWNER")
            water = next(c for c in body["costs"] if c["label"] == "Wasser/Abwasser")
            # Unit C only: unit B's 22 m³ are recorded but not allocated.
            assert [line["weightDisplay"] for line in water["lines"]] == ["38,5"]
            assert sum(line["amountCents"] for line in water["lines"]) == 50000
        finally:
            assert client.delete(f"{BASE}/costs/{cost_id}", headers=DEMO).status_code == 204
            with Session(engine) as session, session.begin():
                session.execute(text("DELETE FROM meter_reading WHERE meter_id = 'met_p01_kw_b'"))
                session.execute(text("DELETE FROM meter WHERE id = 'met_p01_kw_b'"))
            engine.dispose()
