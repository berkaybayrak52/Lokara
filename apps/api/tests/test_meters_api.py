"""Zähler + the heating statement built from real readings.

THE test in this file: the heating goldens — 583,3/416,7 ‰, € 776,52 / € 554,74 and
the CO₂ block — must come out of `meter_reading` and `heating_cost_entry` rows,
not out of a constant. (Those two euro figures were € 786,24 / € 557,76 until
05.08.2026, when the demo's CO₂ fixture was corrected: 4.000 kg / 261,80 €
instead of 2.000 kg / 300,00 €, which had implied 150 €/t and half the emission
factor of any fuel. The CO₂-Vermieteranteil is deducted before the renter-facing
split, so every heating euro followed. `docs/06` → "Scenario 2 — the fuel, the
emissions and the CO₂ price"; that re-base did not move the ratio.

The ratio itself then moved on 13.08.2026 — K3 (`docs/03`) adopts VDI 2067 Bl. 1,
12/1983, Tab. 22, whose June/July/August/December values differ, taking Jan–Jun
from 585,0 ‰ to 583,3 ‰. That is the third re-base of this pair, and the reason
the engine now carries **Zehntelpromille**: the table's months are fractional.
The pot did not move — 77.652 + 55.474 = 133.126, as before — so this was a
re-split, not a re-price.) The
last four fixtures in statement_service.py (€ 10.300 / 20.000 kWh / 40 m³ / CO₂)
are gone, so this is what stops them from being reintroduced by accident.

Second theme: readings are **create-only**. A correction is an appended row
that supersedes an earlier one for the same date; the wrong value stays
visible and the statement follows the correction.
"""

import os
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app
from lokara_api.settings import ApiSettings
from lokara_db import DbSettings, create_db_engine
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

NBSP = " "  # format_eur puts a non-breaking space before the €
_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"

BASE = f"/a/{DEMO_ACCOUNT_ID}"
DEMO_BUILDING_ID = "bld_demo_muster12"

# docs/06 Scenario 2 — unit B's heating consumption splits Mieter/Vermieter by
# degree days at the 30.06. move-out. These are the pitch numbers.
GOLDEN_B_RENTER_CENTS = 77652
GOLDEN_B_LANDLORD_CENTS = 55474
GOLDEN_HEATING_TOTAL_CENTS = 1_030_000


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
        # Deterministic start: exactly the seeded meters, readings and heating
        # invoice. Leftovers from an interrupted run (an extra reading, a second
        # heating cost) would break the exact golden assertions below.
        session.execute(
            text("DELETE FROM meter_reading WHERE account_id = :a AND id NOT LIKE 'mr_met_demo_%'"),
            {"a": DEMO_ACCOUNT_ID},
        )
        session.execute(
            text("DELETE FROM meter WHERE account_id = :a AND id NOT LIKE 'met_demo_%'"),
            {"a": DEMO_ACCOUNT_ID},
        )
        session.execute(
            text(
                "DELETE FROM heating_cost_entry WHERE account_id = :a AND id <> 'hcost_demo_2025'"
            ),
            {"a": DEMO_ACCOUNT_ID},
        )
    owner.dispose()
    yield TestClient(create_app())


def _token(person_id: str, account_id: str) -> dict[str, str]:
    encoded = jwt.encode(
        {"sub": person_id, "account_id": account_id},
        ApiSettings().supabase_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {encoded}"}


DEMO = _token(DEMO_PERSON_ID, DEMO_ACCOUNT_ID)


def _meters(client: TestClient) -> list[dict[str, Any]]:
    response = client.get(f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters", headers=DEMO)
    assert response.status_code == 200
    meters: list[dict[str, Any]] = response.json()["meters"]
    return meters


def _meter(client: TestClient, meter_id: str) -> dict[str, Any]:
    return next(m for m in _meters(client) if m["id"] == meter_id)


def _statement(client: TestClient) -> dict[str, Any]:
    body: dict[str, Any] = client.get(f"{BASE}/statements/demo", headers=DEMO).json()
    return body


def _unit_b_heating(client: TestClient) -> list[dict[str, Any]]:
    return [
        line
        for line in _statement(client)["heatingLines"]
        if line["partyLabel"].startswith("Wohnung B")
    ]


class TestSeededMeters:
    def test_building_and_unit_meters_are_both_present(self, client: TestClient) -> None:
        meters = _meters(client)
        building_level = [m for m in meters if m["unitId"] is None]
        assert {m["serial"] for m in building_level} == {
            "WMZ-2022-004711",
            "WWZ-2022-118342",
        }
        # Both are counted differently even where the medium is the same: only
        # the measurement unit separates the kWh Wärmemengenzähler from the
        # dimensionless Heizkostenverteiler in the flats.
        heat = {m["serial"]: m["measurementUnit"] for m in meters if m["kind"] == "HEAT"}
        assert heat["WMZ-2022-004711"] == "KWH"
        assert heat["HKV-A-100231"] == "HKV_UNITS"

    def test_period_consumption_matches_the_engine_inputs(self, client: TestClient) -> None:
        by_serial = {m["serial"]: m["periodConsumptionDisplay"] for m in _meters(client)}
        assert by_serial["WMZ-2022-004711"] == "20.000 kWh"
        assert by_serial["WWZ-2022-118342"] == "40 m³"
        assert by_serial["HKV-A-100231"] == "600 Einheiten"
        assert by_serial["HKV-B-100232"] == "250 Einheiten"
        assert by_serial["HKV-C-100233"] == "150 Einheiten"
        assert by_serial["WWZ-A-556101"] == "20 m³"

    def test_german_labels_and_unit_symbols(self, client: TestClient) -> None:
        meter = _meter(client, "met_demo_ww_main")
        assert meter["kindLabel"] == "Warmwasser"
        assert meter["unitSymbol"] == "m³"
        assert meter["unitLabel"] is None  # building-level


class TestEichfrist:
    def test_expired_calibration_is_flagged(self, client: TestClient) -> None:
        """The demo's cold-water meter is deliberately out of Eichfrist — it
        proves the warning without touching a number the engines consume."""
        meter = _meter(client, "met_demo_kw_c")
        assert meter["calibrationValidUntil"] == "2025-12-31"
        assert meter["calibrationStatus"] == "EXPIRED"

    def test_valid_calibration_is_not_flagged(self, client: TestClient) -> None:
        assert _meter(client, "met_demo_ww_main")["calibrationStatus"] == "VALID"

    def test_heat_cost_allocators_are_not_eichpflichtig(self, client: TestClient) -> None:
        """A NULL Eichfrist means "not applicable", never "unknown" — an HKV is
        not a Messgerät under MessEG, so it must not raise a warning."""
        meter = _meter(client, "met_demo_heat_a")
        assert meter["calibrationValidUntil"] is None
        assert meter["calibrationStatus"] == "NOT_APPLICABLE"

    def test_status_is_computed_not_stored(self, client: TestClient) -> None:
        """A meter created with an Eichfrist just inside the warning window
        reports EXPIRING_SOON — derived on read, so it can never go stale."""
        soon = date.today() + timedelta(days=30)
        created = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
            headers=DEMO,
            json={
                "kind": "COLD_WATER",
                "measurementUnit": "CUBIC_METRE",
                "serial": "KWZ-SOON-1",
                "calibrationValidUntil": soon.isoformat(),
            },
        )
        assert created.status_code == 201
        assert created.json()["calibrationStatus"] == "EXPIRING_SOON"
        client.delete(f"{BASE}/meters/{created.json()['id']}", headers=DEMO)


class TestHeatingStatementFromRealReadings:
    """The last four fixtures are gone — these numbers now come from rows."""

    def test_unit_b_splits_583_3_416_7_permille_between_renter_and_landlord(
        self, client: TestClient
    ) -> None:
        renter, landlord = _unit_b_heating(client)
        assert renter["isLandlord"] is False
        assert landlord["isLandlord"] is True
        assert renter["heatingConsumptionEur"] == f"776,52{NBSP}€"
        assert landlord["heatingConsumptionEur"] == f"554,74{NBSP}€"

        renter_cents, landlord_cents = GOLDEN_B_RENTER_CENTS, GOLDEN_B_LANDLORD_CENTS
        total = renter_cents + landlord_cents
        # 583,3/416,7 ‰ — the degree-day split at the 30.06. move-out, which is
        # the depth the competitors do not show (docs/06). The tenths matter: the
        # VDI 2067 table (K3, docs/03) has fractional months, which is why the
        # engine carries Zehntelpromille and why this is no longer 585/415.
        assert round(renter_cents * 10_000 / total) == 5_833
        assert round(landlord_cents * 10_000 / total) == 4_167

    def test_heating_reconciles_to_the_entered_invoice(self, client: TestClient) -> None:
        body = _statement(client)
        assert body["heatingMissingReason"] is None
        assert body["heatingInputTotalCents"] == GOLDEN_HEATING_TOTAL_CENTS
        assert body["heatingTotalCents"] == GOLDEN_HEATING_TOTAL_CENTS
        assert body["heatingTotalEur"] == f"10.300,00{NBSP}€"

    def test_co2_block_carries_its_rechtsstand(self, client: TestClient) -> None:
        co2 = _statement(client)["co2"]
        # 4.000 kg over 100 m² → 40 kg/m²/a → step 37-42 → 60 % landlord.
        # `docs/06`: 200 kWh/m²/a of Erdgas lands near 40 kg CO₂/m²/a, so the
        # band moved with the corrected fixture rather than being chosen.
        assert co2["intensityDisplay"] == "40"
        assert co2["landlordSharePercent"] == 60
        assert co2["landlordAmountEur"] == f"157,08{NBSP}€"
        assert co2["renterAmountEur"] == f"104,72{NBSP}€"
        assert co2["rechtsstand"] == "Rechtsstand 01/2023"

    def test_nk_goldens_are_untouched_by_the_meter_work(self, client: TestClient) -> None:
        body = _statement(client)
        [garbage] = body["nkCosts"]
        assert [line["amountCents"] for line in garbage["lines"]] == [
            60000,
            17852,
            18148,
            24000,
        ]

    def test_heating_costs_carry_no_umlageschluessel(self, client: TestClient) -> None:
        """§§ 7-9 HeizkostenV decide the split, so the heating invoice must not
        appear among the NK costs where a key could be chosen for it."""
        body = _statement(client)
        assert [c["label"] for c in body["nkCosts"]] == ["Müllabfuhr"]
        heating_costs = client.get(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/heating-costs", headers=DEMO
        ).json()["heatingCosts"]
        [entry] = heating_costs
        assert entry["amountEur"] == f"10.300,00{NBSP}€"
        # Re-based 05.08.2026 with the demo's CO₂ fixture, like the two goldens
        # this module's docstring describes — these two were missed then.
        assert entry["co2KgDisplay"] == "4.000"
        assert entry["co2CostEur"] == f"261,80{NBSP}€"
        assert "key" not in entry


class TestReadingsAreCreateOnly:
    def test_there_is_no_update_or_patch_route_for_a_reading(self, client: TestClient) -> None:
        """Not a style preference: without an edit path, a billed reading can
        never be rewritten after the fact (GoBD / § 147 AO)."""
        paths: dict[str, dict[str, Any]] = create_app().openapi()["paths"]
        reading_routes = {
            (path, method.upper())
            for path, methods in paths.items()
            if "readings" in path
            for method in methods
        }
        assert reading_routes == {("/a/{account_id}/meters/{meter_id}/readings", "POST")}

    def test_a_correction_supersedes_without_deleting_and_moves_the_statement(
        self, client: TestClient
    ) -> None:
        """The full loop: append a wrong closing reading, watch the statement
        follow it, append a correction, watch the goldens come back — with all
        three rows still on file."""
        before = _meter(client, "met_demo_heat_b")
        readings_before = len(before["readings"])
        assert before["periodConsumptionDisplay"] == "250 Einheiten"

        # ── a typo: 3.850 instead of 3.650 on the closing date ──────────────
        typo = client.post(
            f"{BASE}/meters/met_demo_heat_b/readings",
            headers=DEMO,
            json={
                "readAt": "2025-12-31",
                "valueX1000": 3_850_000,
                "reason": "PERIODIC",
            },
        )
        assert typo.status_code == 201
        assert typo.json()["periodConsumptionDisplay"] == "450 Einheiten"
        # The statement really recomputed — B's consumption share moved.
        assert _unit_b_heating(client)[0]["heatingConsumptionEur"] != f"776,52{NBSP}€"

        # ── the fix is an APPEND, not an edit ───────────────────────────────
        fixed = client.post(
            f"{BASE}/meters/met_demo_heat_b/readings",
            headers=DEMO,
            json={
                "readAt": "2025-12-31",
                "valueX1000": 3_650_000,
                "reason": "CORRECTION",
                "note": "Zahlendreher korrigiert",
            },
        )
        assert fixed.status_code == 201
        assert fixed.json()["periodConsumptionDisplay"] == "250 Einheiten"

        after = _meter(client, "met_demo_heat_b")
        # Nothing was removed: every version is still on file.
        assert len(after["readings"]) == readings_before + 2
        superseded = [r for r in after["readings"] if r["superseded"]]
        assert {r["valueX1000"] for r in superseded} == {3_650_000, 3_850_000}
        effective = next(
            r for r in after["readings"] if not r["superseded"] and r["readAt"] == "2025-12-31"
        )
        assert effective["valueX1000"] == 3_650_000
        assert effective["reason"] == "CORRECTION"
        assert effective["note"] == "Zahlendreher korrigiert"

        # ── and the goldens are back, to the cent ───────────────────────────
        renter, landlord = _unit_b_heating(client)
        assert renter["heatingConsumptionEur"] == f"776,52{NBSP}€"
        assert landlord["heatingConsumptionEur"] == f"554,74{NBSP}€"

        # Clean up so the module's other tests keep their exact fixture.
        with Session(create_db_engine(DbSettings().direct_url)) as session, session.begin():
            session.execute(
                text(
                    "DELETE FROM meter_reading WHERE account_id = :a "
                    "AND id NOT LIKE 'mr_met_demo_%'"
                ),
                {"a": DEMO_ACCOUNT_ID},
            )


class TestMissingInputsRefuseRatherThanGuess:
    def test_without_the_building_heat_meter_the_statement_says_so(
        self, client: TestClient
    ) -> None:
        """A Heizkostenabrechnung on a guessed energy total is not
        "approximately right", it is wrong — so the API refuses and explains,
        while the Betriebskosten still compute."""
        engine = create_db_engine(DbSettings().direct_url)
        with Session(engine) as session, session.begin():
            session.execute(text("DELETE FROM meter_reading WHERE meter_id = 'met_demo_heat_main'"))
        try:
            body = _statement(client)
            assert body["heatingLines"] == []
            assert body["co2"] is None
            assert "Wärmemengenzähler" in body["heatingMissingReason"]
            # The NK half is untouched — one missing meter must not block it.
            assert body["nkTotalCents"] == 120000
        finally:
            with Session(engine) as session, session.begin():
                seed_demo(session)
            engine.dispose()
        assert _statement(client)["heatingMissingReason"] is None


class TestMeterValidation:
    def test_a_water_meter_cannot_be_created_in_kwh(self, client: TestClient) -> None:
        """A Kaltwasserzähler counting kWh would silently corrupt the § 9
        denominator, so the boundary rejects it."""
        response = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
            headers=DEMO,
            json={
                "kind": "COLD_WATER",
                "measurementUnit": "KWH",
                "serial": "KWZ-BOGUS-1",
            },
        )
        assert response.status_code == 422

    def test_duplicate_serial_in_one_building_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
            headers=DEMO,
            json={
                "kind": "WARM_WATER",
                "measurementUnit": "CUBIC_METRE",
                "serial": "WWZ-2022-118342",
            },
        )
        assert response.status_code == 422

    def test_a_unit_from_another_building_is_rejected(self, client: TestClient) -> None:
        other = client.post(
            f"{BASE}/buildings",
            headers=DEMO,
            json={
                "name": "Zweites Haus",
                "street": "Nebenweg 3",
                "postalCode": "60313",
                "city": "Frankfurt am Main",
            },
        ).json()
        response = client.post(
            f"{BASE}/buildings/{other['id']}/meters",
            headers=DEMO,
            json={
                "unitId": "unit_demo_a",  # belongs to the demo building
                "kind": "HEAT",
                "measurementUnit": "HKV_UNITS",
                "serial": "HKV-X-1",
            },
        )
        assert response.status_code == 422


class TestIsolation:
    def test_another_account_sees_no_meters(self, client: TestClient) -> None:
        """Enforced twice: the membership gate answers first, RLS underneath."""
        response = client.get(
            "/a/acc_does_not_exist/buildings/bld_demo_muster12/meters",
            headers=_token(DEMO_PERSON_ID, "acc_does_not_exist"),
        )
        assert response.status_code == 403
