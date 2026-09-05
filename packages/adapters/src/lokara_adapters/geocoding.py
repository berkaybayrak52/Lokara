"""Geocoding port and Nominatim response normalization.

Transport deliberately lives outside this package. An adapter owns the vendor
*format* — the query parameter names, the response shape, the coordinate
validation — and normalizes it before domain code sees it; it does not open
sockets. `dwd.py` draws the same line. `apps/api` performs the HTTP call and
feeds the bytes back through `parse_nominatim_payload`.
"""

import json
import math
import re
from dataclasses import dataclass
from typing import Final, Protocol, cast

from lokara_rules_store import (
    PlzGeocoordLookupError as PlzGeocoordLookupError,
)
from lokara_rules_store import lookup_plz_geocoord

NOMINATIM_PUBLIC_ENDPOINT: Final = "https://nominatim.openstreetmap.org/search"
NOMINATIM_PUBLIC_HOST: Final = "nominatim.openstreetmap.org"
NOMINATIM_DEFAULT_CONTACT: Final = "kontakt@lokara.de"
# Nominatim's usage policy: at most one request per second against the public
# instance, and a User-Agent that identifies the caller.
NOMINATIM_MIN_SECONDS_BETWEEN_REQUESTS: Final = 1.0
NOMINATIM_MAX_RESPONSE_BYTES: Final = 65_536
_GERMAN_PLZ_IN_ADDRESS: Final = re.compile(r"(?<![0-9])([0-9]{5})(?![0-9])")


@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float


class GeocodingGateway(Protocol):
    def geocode(self, address: str) -> GeocodingResult | None:
        """Return coordinates for an address, or ``None`` when unavailable."""
        ...


class DisabledGeocodingGateway:
    """Safe default for environments where external geocoding is disabled."""

    def geocode(self, address: str) -> GeocodingResult | None:
        del address
        return None


class PlzGeocodingGateway:
    """Resolve exactly one German PLZ through the pinned offline centroid data."""

    def geocode(self, address: str) -> GeocodingResult:
        matches = _GERMAN_PLZ_IN_ADDRESS.findall(address)
        if len(matches) != 1:
            raise PlzGeocoordLookupError(
                "invalid address: expected exactly one five-digit German PLZ"
            )
        coordinate = lookup_plz_geocoord(matches[0])
        return GeocodingResult(
            latitude=float(coordinate.latitude),
            longitude=float(coordinate.longitude),
        )


def nominatim_query_params(address: str) -> dict[str, str]:
    """Vendor query shape for a single best match."""
    return {"q": address, "format": "jsonv2", "limit": "1"}


def nominatim_user_agent(contact_email: str) -> str:
    """Identify the caller as the Nominatim usage policy requires."""
    contact = contact_email.strip() or NOMINATIM_DEFAULT_CONTACT
    return f"Lokara/1.0 ({contact})"


def parse_nominatim_payload(body: bytes) -> GeocodingResult | None:
    """Normalize a Nominatim search response, or ``None`` when unusable.

    Every malformed, out-of-range or non-finite coordinate resolves to ``None``:
    a missing pin is a calm empty state, a wrong pin is a lie.
    """
    try:
        payload = cast(object, json.loads(body))
    except (ValueError, TypeError):
        return None

    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    if not isinstance(first, dict):
        return None
    latitude_raw: object = first.get("lat")
    longitude_raw: object = first.get("lon")
    coordinate_types = (str, int, float)
    if (
        not isinstance(latitude_raw, coordinate_types)
        or isinstance(latitude_raw, bool)
        or not isinstance(longitude_raw, coordinate_types)
        or isinstance(longitude_raw, bool)
    ):
        return None
    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
    except (TypeError, ValueError):
        return None
    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90.0 <= latitude <= 90.0
        or not -180.0 <= longitude <= 180.0
    ):
        return None
    return GeocodingResult(latitude=latitude, longitude=longitude)
