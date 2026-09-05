"""Zähler + the heating statement built from real readings.

THE test in this file: the heating goldens — rounded device units and the resulting
€ 776,39 / € 554,87 split, plus
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
Slice A now rounds each renter's device units to one decimal and assigns the
device-unit residual to the owner before the money split. The pot still does
not move — 77.639 + 55.487 = 133.126 — so this remains a re-split, not a
re-price.) The
last four fixtures in statement_service.py (€ 10.300 / 20.000 kWh / 40 m³ / CO₂)
are gone, so this is what stops them from being reintroduced by accident.

Second theme: readings are **create-only**. A correction is an appended row
that supersedes an earlier one for the same date; the wrong value stays
visible and the statement follows the correction.
"""

import os
import time
from collections.abc import Iterator
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lokara_api import create_app, statement_service
from lokara_api.schemas import MeterCreate
from lokara_api.settings import ApiSettings
from lokara_db import DbSettings, create_db_engine, new_id
from lokara_db.seed import DEMO_ACCOUNT_ID, DEMO_PERSON_ID, seed_demo
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

NBSP = " "  # format_eur puts a non-breaking space before the €
_DB_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "db"
TEST_JWT_ISSUER = "https://lokara.test/auth/v1"

BASE = f"/a/{DEMO_ACCOUNT_ID}"
DEMO_BUILDING_ID = "bld_demo_muster12"

# docs/06 Scenario 2 — unit B's heating consumption splits Mieter/Vermieter by
# degree days at the 30.06. move-out. These are the pitch numbers.
GOLDEN_B_RENTER_CENTS = 77639
GOLDEN_B_LANDLORD_CENTS = 55487
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
    owner.dispose()
    test_client = TestClient(create_app())
    try:
        yield test_client
    finally:
        test_client.close()


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


DEMO = _token(DEMO_PERSON_ID)


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


def _retire_meter(client: TestClient, meter_id: str, effective_on: date) -> None:
    response = client.post(
        f"{BASE}/meters/{meter_id}/remove",
        headers=DEMO,
        json={"effectiveOn": effective_on.isoformat(), "reason": "Testgerät ausgebaut"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["lifecycleStatus"] == "REMOVED"


# `docs/08` → "Die Eigentümerzeile" (14.08.2026). The landlord side of a
# Liegenschaft is **one** row — the residual `Gesamtkosten abzüglich Σ Mieteranteile` —
# so it is labelled `Eigentümeranteil` and no longer
# `Wohnung B — Leerstand … → Vermieter`. `docs/08` § 3's rule of thumb: a
# Liegenschafts-total gets one row, a single-unit decomposition (Block C) keeps
# the per-unit label.
OWNER_LABEL = "Eigentümeranteil"


def _unit_b_heating(client: TestClient) -> list[dict[str, Any]]:
    """Unit B's renter row, then the Eigentümerzeile that carries its vacancy.

    Deliberately not `startswith("Wohnung B")` any more: the second row is not a
    party of unit B, it is the Liegenschafts-Residuum. The goldens below did not
    move with the re-labelling — the demo has exactly one vacant unit, so the
    residual is unit B's Leerstandsanteil plus a rounding difference of 0 ct
    (34.514 / 55.474 / 11.505 / 26.844 = 128.337, byte-identical to the landlord
    party it replaced). If a second vacancy is ever seeded into the demo, this
    helper stops being an "unit B" reader and the goldens have to be restated
    per unit off the Leerstandsaufstellung instead.
    """
    return [
        line
        for line in _statement(client)["heatingLines"]
        if line["partyLabel"].startswith("Wohnung B") or line["partyLabel"] == OWNER_LABEL
    ]


class TestSeededMeters:
    def test_building_and_unit_meters_are_both_present(self, client: TestClient) -> None:
        meters = _meters(client)
        building_level = [m for m in meters if m["unitId"] is None]
        assert {m["serial"] for m in building_level} >= {
            "WMZ-2022-004711",
            "WWZ-2022-118342",
        }
        # Both are counted differently even where the medium is the same: only
        # the measurement unit separates the kWh Wärmemengenzähler from the
        # dimensionless Heizkostenverteiler in the flats.
        heat = {m["serial"]: m["measurementUnit"] for m in meters if m["kind"] == "HEAT"}
        assert heat["WMZ-2022-004711"] == "KWH"
        assert heat["HKV-A-100231"] == "HKV_UNITS"
        canonical_heat_serials = {
            "WMZ-2022-004711",
            "HKV-A-100231",
            "HKV-B-100232",
            "HKV-C-100233",
        }
        assert {
            m["serial"]: m["valuationFactorX1000"]
            for m in meters
            if m["serial"] in canonical_heat_serials
        } == {serial: 1000 for serial in canonical_heat_serials}
        assert all(m["valuationFactorX1000"] is None for m in meters if m["kind"] != "HEAT")

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
        assert meter["kindLabel"] == "Warmwasserzähler"
        assert meter["unitSymbol"] == "m³"
        assert meter["unitLabel"] is None  # building-level

    def test_device_factor_and_estimate_provenance_round_trip(self, client: TestClient) -> None:
        created = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
            headers=DEMO,
            json={
                "unitId": "unit_demo_a",
                "deviceType": "HEAT_COST_ALLOCATOR",
                "kind": "HEAT",
                "measurementUnit": "HKV_UNITS",
                "serial": f"HKV-A-PAGE01B-{new_id()}",
                "label": "Arbeitszimmer",
                "installedOn": "2025-01-01",
                "calibrationDataState": "NOT_APPLICABLE",
                "valuationFactorX1000": 1250,
            },
        )
        assert created.status_code == 201
        meter_id = created.json()["id"]
        assert created.json()["valuationFactorDisplay"] == "1,25"

        response = client.post(
            f"{BASE}/meters/{meter_id}/readings",
            headers=DEMO,
            json={
                "readAt": "2025-12-31",
                "valueX1000": 0,
                "reason": "INTERIM",
                "tenancyId": "ten_demo_a1",
                "estimatedConsumptionX1000": 30000,
                "estimationBasis": "Vorjahreswert 2024",
                "provenanceRef": "MDL-Datei Zeile 17",
            },
        )
        assert response.status_code == 201
        [reading] = response.json()["readings"]
        assert reading["tenancyId"] == "ten_demo_a1"
        assert reading["estimatedConsumptionX1000"] == 30000
        assert reading["estimationBasis"] == "Vorjahreswert 2024"
        assert reading["provenanceRef"] == "MDL-Datei Zeile 17"
        _retire_meter(client, meter_id, date(2025, 12, 31))


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
        today = date.today()
        created = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
            headers=DEMO,
            json={
                "unitId": "unit_demo_c",
                "deviceType": "COLD_WATER_METER",
                "kind": "COLD_WATER",
                "measurementUnit": "CUBIC_METRE",
                "serial": f"KWZ-SOON-{new_id()}",
                "installedOn": "2025-01-01",
                "calibrationDataState": "DATA_AVAILABLE",
                "calibrationDate": f"{today.year - 6}-01-01",
                "calibrationEvidenceRef": "Test-Gerätekennzeichnung",
            },
        )
        assert created.status_code == 201
        assert created.json()["calibrationStatus"] == "EXPIRING_SOON"
        _retire_meter(client, created.json()["id"], today)


class TestHeatingStatementFromRealReadings:
    """The last four fixtures are gone — these numbers now come from rows."""

    def test_unit_b_rounds_renter_device_units_and_assigns_the_residual_to_owner(
        self, client: TestClient
    ) -> None:
        renter, landlord = _unit_b_heating(client)
        assert renter["isLandlord"] is False
        assert landlord["isLandlord"] is True
        assert renter["heatingConsumptionEur"] == f"776,39{NBSP}€"
        assert landlord["heatingConsumptionEur"] == f"554,87{NBSP}€"

        # K3 first applies the 583,3/416,7 ‰ degree-day split to 250 device
        # units, rounds the renter to 145,8 and leaves the exact 104,2 residual
        # with the owner. The final euro ratio also includes cent rounding, so
        # it must not be used to reconstruct the underlying promille weights.
        assert GOLDEN_B_RENTER_CENTS + GOLDEN_B_LANDLORD_CENTS == 133126

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
            24000,
            18148,
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
        destructive_reading_routes = {
            (path, method.upper())
            for path, methods in paths.items()
            if "readings" in path
            for method in methods
            if method.upper() in {"PUT", "PATCH", "DELETE"}
        }
        assert destructive_reading_routes == set()
        assert "post" in paths["/a/{account_id}/meters/{meter_id}/readings"]

    def test_a_correction_supersedes_without_deleting_and_moves_the_statement(
        self, client: TestClient
    ) -> None:
        """The full loop: append a wrong closing reading, watch the statement
        follow it, append a correction, watch the goldens come back — with all
        prior rows still on file."""
        before = _meter(client, "met_demo_heat_b")
        readings_before = len(before["readings"])
        assert before["periodConsumptionDisplay"] == "250 Einheiten"
        effective_before = next(
            reading
            for reading in before["readings"]
            if not reading["superseded"] and reading["readAt"] == "2025-12-31"
        )

        # ── a typo: 3.850 instead of 3.650 on the closing date ──────────────
        typo = client.post(
            f"{BASE}/meters/met_demo_heat_b/readings",
            headers=DEMO,
            json={
                "readAt": "2025-12-31",
                "valueX1000": 3_850_000,
                "reason": "CORRECTION",
                "supersedesReadingId": effective_before["id"],
                "confirmationNote": "Zahlendreher im Testfall",
            },
        )
        assert typo.status_code == 201
        assert typo.json()["periodConsumptionDisplay"] == "450 Einheiten"
        effective_typo = next(
            reading
            for reading in typo.json()["readings"]
            if not reading["superseded"] and reading["readAt"] == "2025-12-31"
        )
        # The statement really recomputed — B's consumption share moved.
        assert _unit_b_heating(client)[0]["heatingConsumptionEur"] != f"776,39{NBSP}€"

        # ── the fix is an APPEND, not an edit ───────────────────────────────
        fixed = client.post(
            f"{BASE}/meters/met_demo_heat_b/readings",
            headers=DEMO,
            json={
                "readAt": "2025-12-31",
                "valueX1000": 3_650_000,
                "reason": "CORRECTION",
                "note": "Zahlendreher korrigiert",
                "supersedesReadingId": effective_typo["id"],
                "confirmationNote": "Zahlendreher korrigiert",
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
        assert renter["heatingConsumptionEur"] == f"776,39{NBSP}€"
        assert landlord["heatingConsumptionEur"] == f"554,87{NBSP}€"


class TestMissingInputsRefuseRatherThanGuess:
    def test_without_the_building_heat_meter_the_statement_says_so(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A Heizkostenabrechnung on a guessed energy total is not
        "approximately right", it is wrong — so the API refuses and explains,
        while the Betriebskosten still compute."""
        original_meter_facts = statement_service._meter_facts

        def without_total_energy(*args: Any, **kwargs: Any) -> statement_service.MeterFacts:
            return replace(original_meter_facts(*args, **kwargs), total_energy_kwh=None)

        with monkeypatch.context() as scoped:
            scoped.setattr(statement_service, "_meter_facts", without_total_energy)
            body = _statement(client)
            assert body["heatingLines"] == []
            assert body["co2"] is None
            assert "Wärmemengenzähler" in body["heatingMissingReason"]
            # The NK half is untouched — one missing meter must not block it.
            assert body["nkTotalCents"] == 120000
        assert _statement(client)["heatingMissingReason"] is None


class TestMeterValidation:
    @staticmethod
    def _gas_payload(
        *, serial: str, valid_from: date, supplier_reference: str
    ) -> dict[str, object]:
        return {
            "deviceType": "GAS_METER",
            "serial": serial,
            "installedOn": valid_from.isoformat(),
            "calibrationDataState": "REVIEW_REQUIRED",
            "gasConversion": {
                "calorificFactorKwhPerM3": "10.2500",
                "conditionNumber": "0.9500",
                "validFrom": valid_from.isoformat(),
                "validTo": None,
                "supplierInvoiceReference": supplier_reference,
            },
        }

    def test_gas_conversion_schema_is_required_exclusive_exact_and_server_derived(self) -> None:
        payload = self._gas_payload(
            serial="GAS-SCHEMA-01",
            valid_from=date(2027, 1, 1),
            supplier_reference="supplier-invoice-schema-01",
        )
        parsed = MeterCreate.model_validate(payload)
        assert parsed.kind is not None
        assert parsed.measurement_unit is not None
        assert parsed.kind.value == "HEAT"
        assert parsed.measurement_unit.value == "CUBIC_METRE"
        assert parsed.gas_conversion is not None
        assert parsed.gas_conversion.calorific_factor_kwh_per_m3 == Decimal("10.2500")
        assert parsed.gas_conversion.condition_number == Decimal("0.9500")

        rejected = (
            ({key: value for key, value in payload.items() if key != "gasConversion"},),
            (
                {
                    **payload,
                    "gasConversion": {
                        key: value
                        for key, value in cast(dict[str, object], payload["gasConversion"]).items()
                        if key != "conditionNumber"
                    },
                },
            ),
            (
                {
                    **payload,
                    "deviceType": "HEAT_METER",
                    "gasConversion": cast(dict[str, object], payload["gasConversion"]),
                },
            ),
        )
        for (invalid,) in rejected:
            with pytest.raises(ValidationError) as error:
                MeterCreate.model_validate(invalid)
            assert any(
                "gas" in ".".join(str(part) for part in detail["loc"]).lower()
                or "gas" in detail["msg"].lower()
                for detail in error.value.errors()
            )

    def test_gas_meter_creation_appends_exact_supplier_configuration_and_exposes_it(
        self, client: TestClient
    ) -> None:
        engine = create_db_engine(DbSettings().direct_url)
        try:
            with engine.connect() as connection:
                latest = connection.scalar(
                    text(
                        "SELECT max(valid_from) FROM building_uvi_configuration"
                        " WHERE building_id = :building_id"
                    ),
                    {"building_id": DEMO_BUILDING_ID},
                )
            first_valid_from = (latest or date(2025, 1, 1)) + timedelta(days=1)
            second_valid_from = first_valid_from + timedelta(days=1)
            first_reference = f"supplier-invoice-{new_id()}"
            second_reference = f"supplier-invoice-{new_id()}"

            first = client.post(
                f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
                headers=DEMO,
                json=self._gas_payload(
                    serial=f"GAS-{new_id()}",
                    valid_from=first_valid_from,
                    supplier_reference=first_reference,
                ),
            )
            assert first.status_code == 201, first.text
            assert first.json()["kind"] == "HEAT"
            assert first.json()["measurementUnit"] == "CUBIC_METRE"
            assert first.json()["deviceTypeLabel"] == "Gaszähler"
            assert first.json()["gasConversion"] == {
                "calorificFactorKwhPerM3": "10.2500",
                "conditionNumber": "0.9500",
                "validFrom": first_valid_from.isoformat(),
                "validTo": None,
                "supplierInvoiceReference": first_reference,
                "sourceType": "SUPPLIER_INVOICE",
                "sourceId": first_reference,
                "rechtsstand": "08/2026",
                "verificationStatus": "verify-before-production",
                "configurationId": first.json()["gasConversion"]["configurationId"],
                "supersedesConfigurationId": first.json()["gasConversion"][
                    "supersedesConfigurationId"
                ],
            }

            with engine.connect() as connection:
                first_before = (
                    connection.execute(
                        text(
                            "SELECT id, calorific_factor, condition_number, valid_from, valid_to,"
                            " source_type, source_id, rechtsstand, verification_status,"
                            " supersedes_configuration_id FROM building_uvi_configuration"
                            " WHERE source_id = :source_id"
                        ),
                        {"source_id": first_reference},
                    )
                    .mappings()
                    .one()
                )

            second_payload = self._gas_payload(
                serial=f"GAS-{new_id()}",
                valid_from=second_valid_from,
                supplier_reference=second_reference,
            )
            cast(dict[str, object], second_payload["gasConversion"])["calorificFactorKwhPerM3"] = (
                "11.1250"
            )
            cast(dict[str, object], second_payload["gasConversion"])["conditionNumber"] = "0.9750"
            second = client.post(
                f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
                headers=DEMO,
                json=second_payload,
            )
            assert second.status_code == 201, second.text

            with engine.connect() as connection:
                first_after = (
                    connection.execute(
                        text(
                            "SELECT id, calorific_factor, condition_number, valid_from, valid_to,"
                            " source_type, source_id, rechtsstand, verification_status,"
                            " supersedes_configuration_id FROM building_uvi_configuration"
                            " WHERE source_id = :source_id"
                        ),
                        {"source_id": first_reference},
                    )
                    .mappings()
                    .one()
                )
                second_row = (
                    connection.execute(
                        text(
                            "SELECT id, calorific_factor, condition_number, valid_from, valid_to,"
                            " source_type, source_id, rechtsstand, verification_status,"
                            " supersedes_configuration_id FROM building_uvi_configuration"
                            " WHERE source_id = :source_id"
                        ),
                        {"source_id": second_reference},
                    )
                    .mappings()
                    .one()
                )

            assert dict(first_after) == dict(first_before)
            assert first_before["calorific_factor"] == Decimal("10.2500")
            assert first_before["condition_number"] == Decimal("0.9500")
            assert first_before["valid_from"] == first_valid_from
            assert first_before["valid_to"] is None
            assert first_before["source_type"] == "SUPPLIER_INVOICE"
            assert first_before["verification_status"] == "verify-before-production"
            assert second_row["supersedes_configuration_id"] == first_before["id"]
            assert second_row["calorific_factor"] == Decimal("11.1250")
            assert second_row["condition_number"] == Decimal("0.9750")
            assert second.json()["gasConversion"]["supersedesConfigurationId"] == first_before["id"]
        finally:
            engine.dispose()

    def test_a_water_meter_cannot_be_created_in_kwh(self, client: TestClient) -> None:
        """A Kaltwasserzähler counting kWh would silently corrupt the § 9
        denominator, so the boundary rejects it."""
        response = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
            headers=DEMO,
            json={
                "deviceType": "COLD_WATER_METER",
                "kind": "COLD_WATER",
                "measurementUnit": "KWH",
                "serial": f"KWZ-BOGUS-{new_id()}",
                "installedOn": "2025-01-01",
                "calibrationDataState": "MISSING_DATA",
            },
        )
        assert response.status_code == 422

    def test_duplicate_serial_in_one_building_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            f"{BASE}/buildings/{DEMO_BUILDING_ID}/meters",
            headers=DEMO,
            json={
                "deviceType": "WARM_WATER_METER",
                "kind": "WARM_WATER",
                "measurementUnit": "CUBIC_METRE",
                "serial": "WWZ-2022-118342",
                "installedOn": "2025-01-01",
                "calibrationDataState": "MISSING_DATA",
            },
        )
        assert response.status_code == 422

    def test_a_unit_from_another_building_is_rejected(self, client: TestClient) -> None:
        other = client.post(
            f"{BASE}/buildings",
            headers=DEMO,
            json={
                "name": "Zweites Haus",
                "buildingType": "WOHNHAUS",
                "isResidential": True,
                "street": "Nebenweg",
                "houseNumber": "3",
                "postalCode": "60313",
                "city": "Frankfurt am Main",
            },
        ).json()
        response = client.post(
            f"{BASE}/buildings/{other['id']}/meters",
            headers=DEMO,
            json={
                "unitId": "unit_demo_a",  # belongs to the demo building
                "deviceType": "HEAT_COST_ALLOCATOR",
                "kind": "HEAT",
                "measurementUnit": "HKV_UNITS",
                "serial": f"HKV-X-{new_id()}",
                "installedOn": "2025-01-01",
                "calibrationDataState": "NOT_APPLICABLE",
            },
        )
        assert response.status_code == 422


class TestIsolation:
    def test_another_account_sees_no_meters(self, client: TestClient) -> None:
        """Enforced twice: the membership gate answers first, RLS underneath."""
        response = client.get(
            "/a/acc_does_not_exist/buildings/bld_demo_muster12/meters",
            headers=_token(DEMO_PERSON_ID),
        )
        assert response.status_code == 403
