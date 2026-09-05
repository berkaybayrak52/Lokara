"""Offline German postal-code centroids for DWD station assignment.

The vendored ``plz_geocoord.csv`` is from
``WZBSocialScienceCenter/plz_geocoord`` by Markus Konrad, published January
2019 under Apache-2.0. Source repository:
https://github.com/WZBSocialScienceCenter/plz_geocoord
Exact vendored file:
https://raw.githubusercontent.com/WZBSocialScienceCenter/plz_geocoord/927da8a86e9b6e5ebb499cd9259cd1afd3e3c6d2/plz_geocoord.csv
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from importlib import resources
from io import StringIO
from types import MappingProxyType
from typing import Final

PLZ_GEOCOORD_DATASET_IDENTITY: Final = "WZBSocialScienceCenter/plz_geocoord"
PLZ_GEOCOORD_DATASET_VERSION: Final = "2019-01"
PLZ_GEOCOORD_SOURCE_URL: Final = "https://github.com/WZBSocialScienceCenter/plz_geocoord"
PLZ_GEOCOORD_SOURCE_COMMIT: Final = "927da8a86e9b6e5ebb499cd9259cd1afd3e3c6d2"
PLZ_GEOCOORD_RAW_URL: Final = (
    "https://raw.githubusercontent.com/WZBSocialScienceCenter/plz_geocoord/"
    f"{PLZ_GEOCOORD_SOURCE_COMMIT}/plz_geocoord.csv"
)
PLZ_GEOCOORD_SHA256: Final = "d427a6687a7cb286b3a9b4091831a06aaf0a0da40bd7c76cab7a82ac96e0d9a2"
PLZ_GEOCOORD_DATA_ROW_COUNT: Final = 8_298
PLZ_GEOCOORD_LICENSE_ID: Final = "Apache-2.0"
PLZ_GEOCOORD_ATTRIBUTION: Final = (
    "Markus Konrad / Wissenschaftszentrum Berlin für Sozialforschung (WZB), Januar 2019"
)

_DATA_DIRECTORY: Final = "data"
_DATA_FILE: Final = "plz_geocoord.csv"
_HEADER: Final = ("", "lat", "lng")
_PLZ_PATTERN: Final = re.compile(r"[0-9]{5}")
_COORDINATE_PATTERN: Final = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")


class PlzGeocoordLookupError(ValueError):
    """A postal code cannot be resolved from the pinned offline dataset."""


@dataclass(frozen=True)
class PlzGeocoord:
    """One immutable WGS84 postal-code centroid with source evidence."""

    plz: str
    latitude: Decimal
    longitude: Decimal
    dataset_identity: str
    dataset_version: str
    source_url: str
    license_id: str
    attribution: str


def _parse_coordinate(value: str, *, field: str, limit: Decimal) -> Decimal:
    if _COORDINATE_PATTERN.fullmatch(value) is None:
        raise PlzGeocoordLookupError(f"invalid {field} in vendored PLZ dataset")
    try:
        coordinate = Decimal(value)
    except InvalidOperation as exc:
        raise PlzGeocoordLookupError(f"invalid {field} in vendored PLZ dataset") from exc
    if not coordinate.is_finite() or not -limit <= coordinate <= limit:
        raise PlzGeocoordLookupError(f"invalid {field} in vendored PLZ dataset")
    return coordinate


@lru_cache(maxsize=1)
def _load_centroids() -> Mapping[str, PlzGeocoord]:
    data_file = resources.files("lokara_rules_store").joinpath(_DATA_DIRECTORY, _DATA_FILE)
    dataset_bytes = data_file.read_bytes()
    if hashlib.sha256(dataset_bytes).hexdigest() != PLZ_GEOCOORD_SHA256:
        raise PlzGeocoordLookupError("invalid vendored PLZ dataset SHA-256")
    if len(dataset_bytes.splitlines()) - 1 != PLZ_GEOCOORD_DATA_ROW_COUNT:
        raise PlzGeocoordLookupError("invalid vendored PLZ dataset row count")
    try:
        dataset_text = dataset_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PlzGeocoordLookupError("invalid vendored PLZ dataset encoding") from exc

    rows: dict[str, PlzGeocoord] = {}
    with StringIO(dataset_text, newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = tuple(next(reader))
        except StopIteration as exc:
            raise PlzGeocoordLookupError("vendored PLZ dataset is empty") from exc
        if header != _HEADER:
            raise PlzGeocoordLookupError("invalid vendored PLZ dataset header")
        for row in reader:
            if len(row) != 3 or _PLZ_PATTERN.fullmatch(row[0]) is None:
                raise PlzGeocoordLookupError("invalid row in vendored PLZ dataset")
            plz, latitude_raw, longitude_raw = row
            if plz in rows:
                raise PlzGeocoordLookupError("duplicate PLZ in vendored dataset")
            rows[plz] = PlzGeocoord(
                plz=plz,
                latitude=_parse_coordinate(
                    latitude_raw,
                    field="latitude",
                    limit=Decimal("90"),
                ),
                longitude=_parse_coordinate(
                    longitude_raw,
                    field="longitude",
                    limit=Decimal("180"),
                ),
                dataset_identity=PLZ_GEOCOORD_DATASET_IDENTITY,
                dataset_version=PLZ_GEOCOORD_DATASET_VERSION,
                source_url=PLZ_GEOCOORD_SOURCE_URL,
                license_id=PLZ_GEOCOORD_LICENSE_ID,
                attribution=PLZ_GEOCOORD_ATTRIBUTION,
            )
    return MappingProxyType(rows)


def lookup_plz_geocoord(postal_code: str) -> PlzGeocoord:
    """Resolve exactly one five-digit German postal code without network I/O."""

    if type(postal_code) is not str or _PLZ_PATTERN.fullmatch(postal_code) is None:
        raise PlzGeocoordLookupError("invalid PLZ: expected exactly five digits")
    try:
        return _load_centroids()[postal_code]
    except KeyError as exc:
        raise PlzGeocoordLookupError(f"unknown PLZ: {postal_code}") from exc
