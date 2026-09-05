"""U3 PLZ centroid contract for offline DWD nearest-station assignment.

Source commit:
https://github.com/WZBSocialScienceCenter/plz_geocoord/commit/927da8a86e9b6e5ebb499cd9259cd1afd3e3c6d2
Licence: Apache-2.0. Dataset version: January 2019.
"""

from __future__ import annotations

import hashlib
import socket
from dataclasses import FrozenInstanceError
from decimal import Decimal
from importlib import resources
from types import ModuleType
from typing import Any

import lokara_rules_store
import pytest

DATASET_IDENTITY = "WZBSocialScienceCenter/plz_geocoord"
DATASET_VERSION = "2019-01"
SOURCE_URL = "https://github.com/WZBSocialScienceCenter/plz_geocoord"
SOURCE_COMMIT = "927da8a86e9b6e5ebb499cd9259cd1afd3e3c6d2"
RAW_URL = (
    "https://raw.githubusercontent.com/WZBSocialScienceCenter/plz_geocoord/"
    f"{SOURCE_COMMIT}/plz_geocoord.csv"
)
SHA256 = "d427a6687a7cb286b3a9b4091831a06aaf0a0da40bd7c76cab7a82ac96e0d9a2"
DATA_ROW_COUNT = 8_298
LICENSE_ID = "Apache-2.0"
ATTRIBUTION = "Markus Konrad / Wissenschaftszentrum Berlin für Sozialforschung (WZB), Januar 2019"


@pytest.fixture(scope="module")
def plz_geocoord() -> ModuleType:
    return lokara_rules_store


def _lookup(plz_geocoord: ModuleType) -> Any:
    lookup = getattr(plz_geocoord, "lookup_plz_geocoord", None)
    assert callable(lookup), "U3 offline lookup_plz_geocoord is missing"
    return lookup


def test_vendored_dataset_bytes_and_exported_identity_are_immutable(
    plz_geocoord: ModuleType,
) -> None:
    resource = resources.files("lokara_rules_store").joinpath("data", "plz_geocoord.csv")
    dataset_bytes = resource.read_bytes()

    assert len(dataset_bytes.splitlines()) - 1 == DATA_ROW_COUNT
    assert hashlib.sha256(dataset_bytes).hexdigest() == SHA256
    assert {
        "commit": getattr(plz_geocoord, "PLZ_GEOCOORD_SOURCE_COMMIT", None),
        "raw_url": getattr(plz_geocoord, "PLZ_GEOCOORD_RAW_URL", None),
        "sha256": getattr(plz_geocoord, "PLZ_GEOCOORD_SHA256", None),
        "data_row_count": getattr(plz_geocoord, "PLZ_GEOCOORD_DATA_ROW_COUNT", None),
    } == {
        "commit": SOURCE_COMMIT,
        "raw_url": RAW_URL,
        "sha256": SHA256,
        "data_row_count": DATA_ROW_COUNT,
    }


def test_known_plz_resolves_exact_decimal_coordinates_and_frozen_source_metadata(
    plz_geocoord: ModuleType,
) -> None:
    row = _lookup(plz_geocoord)("01067")

    assert row.plz == "01067"
    assert type(row.latitude) is Decimal
    assert type(row.longitude) is Decimal
    assert row.latitude == Decimal("51.05754959999999")
    assert row.longitude == Decimal("13.7170648")
    assert row.dataset_identity == DATASET_IDENTITY
    assert row.dataset_version == DATASET_VERSION
    assert row.source_url == SOURCE_URL
    assert row.license_id == LICENSE_ID
    assert row.attribution == ATTRIBUTION
    with pytest.raises(FrozenInstanceError):
        row.dataset_version = "mutable"


@pytest.mark.parametrize("plz", ("00000", "", "1067", "ABCDE", "01067 "))
def test_unknown_or_malformed_plz_fails_loudly(
    plz_geocoord: ModuleType,
    plz: str,
) -> None:
    error_type = getattr(plz_geocoord, "PlzGeocoordLookupError", None)
    assert isinstance(error_type, type), "U3 PlzGeocoordLookupError is missing"

    with pytest.raises(error_type, match=r"PLZ|postal|unknown|invalid"):
        _lookup(plz_geocoord)(plz)


def test_vendored_lookup_works_with_network_access_refused(
    plz_geocoord: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("PLZ lookup must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", refuse_network)

    row = _lookup(plz_geocoord)("01067")

    assert (row.latitude, row.longitude) == (
        Decimal("51.05754959999999"),
        Decimal("13.7170648"),
    )
