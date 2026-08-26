"""Focused red contracts from the M9 statement/UI re-review."""

from __future__ import annotations

import importlib
import inspect
from datetime import date
from types import ModuleType
from typing import cast


def _module() -> ModuleType:
    return importlib.import_module("lokara_api.routers.guards_delivery")


def test_blocked_occurrence_carries_german_warning_and_real_rule_evidence() -> None:
    """An internal blocker code is evidence, never landlord-facing warning copy."""

    blocker_code = "W7-APPROVED-NORMALIZED-INPUTS-MISSING"
    occurrence = _module()._blocked_guard_occurrence(
        guard_code="W7",
        source_type="tenancy",
        source_id="tenancy-1",
        building_id="building-1",
        today=date(2026, 8, 25),
        blockers=(blocker_code,),
    )

    result = cast(dict[str, object], occurrence.result_snapshot)
    warning = result.get("warning_de")
    assert isinstance(warning, str) and warning.strip()
    assert "gesperrt" in warning.lower()
    assert blocker_code not in warning

    rule = cast(dict[str, object], occurrence.rule_snapshot)
    assert isinstance(rule.get("source"), str) and cast(str, rule["source"]).strip()
    assert isinstance(rule.get("rechtsstand"), str) and cast(str, rule["rechtsstand"]).strip()
    evidence = rule.get("evidence")
    assert isinstance(evidence, list) and evidence


def test_guard_list_supplies_a_server_owned_account_discovery_token_for_first_run() -> None:
    """The client selects no legal facts; it replays a server-owned account-scope token."""

    module = _module()
    token_factory = getattr(module, "guard_discovery_source_token", None)
    assert callable(token_factory), "M9 needs a documented server-owned discovery token"
    documentation = inspect.getdoc(token_factory) or ""
    assert "server" in documentation.lower()
    assert "account" in documentation.lower() or "konto" in documentation.lower()

    token = token_factory("acc-1")
    assert isinstance(token, str) and token.strip()
    response = module.GuardListResponse(guards=[], source_ids=[token])
    payload = response.model_dump(mode="json", by_alias=True)
    assert payload["guards"] == []
    assert payload["sourceIds"] == [token]

    endpoint_source = inspect.getsource(module.list_guards)
    assert "guard_discovery_source_token" in endpoint_source
    assert "source_ids" in endpoint_source


def test_blocked_w1_w2_w4_use_their_approved_guard_specific_evidence() -> None:
    cases = {
        "W1": {
            "rows": {"26", "126"},
            "bases": {
                "§ 556 Abs. 3 S. 2–3 BGB",
                "§§ 187, 188 BGB; KONVENTION-D1/D4/D5",
            },
            "rechtsstand": {"07/2026"},
        },
        "W2": {
            "rows": {"128", "129"},
            "bases": {
                "§ 34 Abs. 2 MessEV; supersedes KONVENTION-D2",
                "MessEV Anlage 7 Nr. 5.5.1/5.5.2 und 7.1/7.2",
            },
            "rechtsstand": {"08/2026"},
        },
        "W4": {
            "rows": {"4", "117", "30"},
            "bases": {
                "§ 6a Abs. 1 Nr. 2 HeizkostenV",
                "KONVENTION-D3; month-end due date",
                "§ 5 Abs. 2 HeizkostenV",
            },
            "rechtsstand": {"07/2026", "10/2023"},
        },
    }
    for guard_code, expected in cases.items():
        occurrence = _module()._blocked_guard_occurrence(
            guard_code=guard_code,
            source_type="building",
            source_id=f"source-{guard_code.lower()}",
            building_id="building-1",
            today=date(2026, 8, 25),
            blockers=(f"{guard_code}-APPROVED-NORMALIZED-INPUTS-MISSING",),
        )
        rule = cast(dict[str, object], occurrence.rule_snapshot)
        evidence = cast(list[dict[str, object]], rule["evidence"])
        assert evidence
        assert {item["register_row"] for item in evidence} == expected["rows"]
        assert {item["legal_basis"] for item in evidence} == expected["bases"]
        assert {item["rechtsstand"] for item in evidence} == expected["rechtsstand"]
        assert all(isinstance(item.get("source"), str) and item["source"] for item in evidence)
        assert all(item["register_row"] != "Page 05" for item in evidence)
