"""Shared immutable provenance shapes required by the UVI result contract."""

from dataclasses import FrozenInstanceError, fields
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType

import pytest


def _provenance_module() -> ModuleType:
    spec = find_spec("lokara_domain.provenance")
    assert spec is not None, "U1b requires lokara_domain.provenance"
    return import_module("lokara_domain.provenance")


def test_u1b_shared_provenance_types_have_exact_frozen_slotted_shape() -> None:
    provenance = _provenance_module()
    source_identity_type = provenance.SourceIdentity
    rule_evidence_type = provenance.RuleEvidence
    rule_conflict_type = provenance.RuleConflict

    assert tuple(field.name for field in fields(source_identity_type)) == (
        "source_type",
        "source_id",
    )
    assert tuple(field.name for field in fields(rule_evidence_type)) == (
        "source",
        "register_row",
        "legal_basis",
        "rechtsstand",
        "verification_status",
    )
    assert tuple(field.name for field in fields(rule_conflict_type)) == (
        "code",
        "description",
        "production_blocking",
        "applies_to_media",
    )

    source_identity = source_identity_type(source_type="uvi", source_id="uvi-2026-08")
    evidence = rule_evidence_type(
        source="docs/16-uvi.md",
        register_row="UVI_REGISTER_ROWS",
        legal_basis="HeizkostenV § 6a",
        rechtsstand="08/2026",
        verification_status="verify-before-production",
    )
    conflict = rule_conflict_type(
        code="missing_uvi_register_rows",
        description="caller supplied",
        production_blocking=True,
        applies_to_media=("uvi",),
    )
    conflict_for_all_media = rule_conflict_type(
        code="all_media",
        description="caller supplied",
        production_blocking=False,
    )

    assert not hasattr(source_identity, "__dict__")
    assert not hasattr(evidence, "__dict__")
    assert not hasattr(conflict, "__dict__")
    assert conflict_for_all_media.applies_to_media is None
    with pytest.raises(FrozenInstanceError):
        source_identity.source_id = "changed"
    with pytest.raises(FrozenInstanceError):
        evidence.rechtsstand = "changed"
    with pytest.raises(FrozenInstanceError):
        conflict.production_blocking = False
