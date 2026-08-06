"""German display spellings of a ``MeasurementUnit`` at the render boundary.

Spec: ``docs/08-statement-document.md`` → "`MeasurementUnit` travels with the
value — the plumbing decision (slice 5)", rule 6 ("Which spelling goes where").

The unit rides on the row that carries the value and is surfaced on the engine
result, so this layer only *spells* what the engine divided in. It never picks
a unit, never guesses one, and never invents a spelling for a combination the
data cannot produce.

Two forms, and they are not interchangeable:

* **compact** — a numeric cell. It sits in a column beside ``36.500 m²·Tage``
  and ``40 m³``; the long form would wrap a figure column into prose.
* **long** — the one place a device is named, the heating column's
  Umlageschlüssel cell. Naming the device is the *Erläuterung* half of the BGH
  formal minimum: the short label says *what* was measured, the long one says
  *by what*. It is deliberately free of parentheses so it composes with the
  ``(Nutzerwechsel: Gradtagszahlen)`` parenthetical without nesting brackets.

``CUBIC_METRE`` has no long form on purpose. A m³ device is not a heat meter —
the API schema already rejects that pairing — and outside the heating column
the unit does not determine the device at all (m³ is a cold- or a hot-water
device), so a device name there would state a fact the data does not carry.
"""

from lokara_domain import MeasurementUnit

# Compact form, for a numeric cell.
UNIT_SYMBOLS: dict[MeasurementUnit, str] = {
    MeasurementUnit.KWH: "kWh",
    MeasurementUnit.CUBIC_METRE: "m³",
    MeasurementUnit.HKV_UNITS: "HKV-Einheiten",
}

# Long form, heating column only — see the module docstring for why
# ``CUBIC_METRE`` is absent rather than mapped to something plausible.
HEAT_KEY_BY_UNIT: dict[MeasurementUnit, str] = {
    MeasurementUnit.KWH: "Erfasster Wärmeverbrauch in kWh am Wärmemengenzähler",
    MeasurementUnit.HKV_UNITS: "Erfasster Wärmeverbrauch in Einheiten eines Heizkostenverteilers",
}
