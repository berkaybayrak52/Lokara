"""Best-effort address → coordinates via OpenStreetMap Nominatim (Spec 02-objekte, O5).

Server-side only, hard ~3s timeout, and it NEVER raises: any failure (network
blocked/sandbox without egress, timeout, empty result, malformed JSON) returns
(None, None) so building creation neither fails nor slows past the timeout
because of geocoding.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

_ENDPOINT = "https://nominatim.openstreetmap.org/search"
# ⚠️ MUSS-INPUT: contact e-mail for the User-Agent (Nominatim usage policy).
# Placeholder until Berkay/Emir supply the real address — see Build-Notes.
_USER_AGENT = "Lokara/1.0 (kontakt@lokara.de)"
_TIMEOUT_SECONDS = 3.0


def geocode_address(
    street: str, postal_code: str, city: str, country: str
) -> tuple[float | None, float | None]:
    """Return (lat, lon) for the address, or (None, None) on any problem."""
    query = f"{street}, {postal_code} {city}, {country}"
    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": "1"})
    request = urllib.request.Request(
        f"{_ENDPOINT}?{params}",
        headers={"User-Agent": _USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, list) and payload:
            first = payload[0]
            return float(first["lat"]), float(first["lon"])
    except Exception:
        return None, None
    return None, None
