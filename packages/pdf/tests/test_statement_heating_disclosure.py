"""Gate: the Heizkostenabrechnung's disclosure blocks A, B and C are on the page.

Spec: `docs/08` → "Heizkostenabrechnung — the heating table's disclosure",
items 1–5 (the required rendered text of Block A, Block B and Block C, the
display-rounding rule for a fractional Bemessung, and the § 7 Abs. 3
Berechnungsgrundlagen line) plus **"4a — The rendered form (slice 4)"**, which
fixes the carriers, the order, and the four places where the drafted copy names
a fact the engine result does not carry. Rechtsstand 08/2026. Written before the
template change, red on purpose.

Today the heating section prints six euro columns and nothing else: no
Umlageschlüssel, no Bemessung, no denominator, no §§ 7/8 ratio, no § 9
separation, no Gradtagszahlen (`docs/08` → "The heating table is not ◐ — it is
❌"). Every figure these blocks need is on `HeatingResult` since the
carried-intermediates slice; nothing here is a new calculation and no euro moves.

Four rules this file exists to hold, all from `docs/08`:

1. **Assert the *printed* figure, never the carried one.** A Bemessung is
   ×100 fixed point in the engine; `18.250` renders as `1.825.000` if the render
   boundary forgets to de-scale, and an integer comparison stays green through
   exactly that bug. The scaled forms are asserted **absent** as canaries — the
   same four `scripts/assert_statement_pdf.py` carries over the PDF.
2. **`sum(Bemessungen) == Gesamtbemessung`, read off the rendered table.** The
   money invariant of every allocation test, applied to the denominators the
   tenant re-divides by.
3. **Never a bare promille.** `585 ‰` is a fraction of the *heating year*; over a
   partial billing period a unit's parties sum to less than 1.000 ‰ and the bare
   figure reads as an error. Every `‰` on the page belongs to an `X ‰ von Y ‰`
   pair.
4. **`None` means "not applied", and absence is asserted.** Where no central warm
   water exists, or § 9a Abs. 2 replaced a consumption key with the area key, the
   corresponding Bemessung/formula was never applied — a statement that prints it
   anyway is a false disclosure, and only an absence assertion catches that.

The fixtures are compositions of the **real** engines with rules resolved from
`packages/rules-store`, like `demo.py`: no hand-written `HeatingResult`.

---

**Re-based 05.08.2026 — three defects found by `statement-reviewer` in slice 4,
each with its own `docs/08` section. Written before the template change, red on
purpose.**

* **F1** — `docs/08` item 1 → *"All four rows render"*, *"The withheld cell is a
  sentence, not a blank"*, *"The `Verbrauch Heizung` row under § 9a Abs. 2"*. The
  first render dropped the whole `Verbrauch Heizung` row, so the **largest pot on
  the page** (5.325,03 €, 52 % of the umlagefähige Kosten) had no Umlageschlüssel
  named anywhere in a block titled *Bemessungsgrundlagen*. What is genuinely not
  derivable is the **unit**, which blocks one *cell*, not a row — and under
  § 9a Abs. 2 it blocks nothing at all, because the applied key is then Wohnfläche
  and its denominator is already printed two rows above. The two Wohnfläche rows
  also lost their `§ 7 Abs. 1` / `§ 8 Abs. 1` citations.
* **F2** — `docs/08` item 1 → *"The rounding is disclosed — `rd.`, one sentence,
  and an operator that is the operation"*. `12 m³ × 181 von 365 Tagen = 5,95 m³`
  asserted a false identity (5,9506849…), disclosed the rounding nowhere — the
  printed price per m³ reproduces the two uncontested lines exactly and misses
  **both Nutzerwechsel parties by ~3 ct** — and printed an operator that is not
  the operation performed.
* **I1** — `docs/08` → **4b**, pinned separately in
  `packages/pdf/tests/test_statement_pagination.py`.

---

**Extended 06.08.2026 — slice 5, `docs/08` → "`MeasurementUnit` travels with the
value — the plumbing decision".** The defect: a value travelled from the meter to
the statement **without its unit**, so the largest denominator on the page could
be printed only by guessing what `1.000` meant — and was withheld instead. The
unit now rides on `HeatingUnit.heat_consumption_unit` and is surfaced on
`HeatingResult.heat_consumption_unit`, so the renderer *reads* it rather than
being told it by a second party that could disagree.

Two things this adds to the file, and they are a pair:

* the **positive** case — the demo building's allocators are `HKV_UNITS`
  (`packages/adapters` `_SPEC`), so Block B prints `Gesamtbemessung: 1.000
  HKV-Einheiten`, a `Verbrauch Heizung` Bemessung column, and the device name in
  the Umlageschlüssel cell;
* the **withholding** case, unchanged and not weakened — every assertion about
  `ohne Maßeinheit — nicht ausgewiesen` and its explaining sentence now runs
  against `unitless_statement()`, a building that records no Maßeinheit. Slice 5
  removes the *cause*, not the *branch*.

**And the demo's CO₂ fixture moved** (`docs/06` → *"Scenario 2 — the fuel, the
emissions and the CO₂ price"*): 2.000 kg / 300,00 € implied 150 €/t and
0,1 kg CO₂/kWh. It is now **4.000 kg / 261,80 €** — 65,45 €/t (55,00 € per
§ 10 Abs. 2 BEHG + 19 % USt per § 3 Abs. 3 CO2KostAufG) and 0,200 kg CO₂/kWh
(Erdgas). The CO₂-Vermieteranteil is deducted **before** the renter-facing split,
so every heating euro below moved with it; no Bemessung and no ‰ did.
"""

import re
from collections.abc import Mapping
from decimal import Decimal
from html.parser import HTMLParser

from lokara_domain import (
    AllocationKey,
    Cents,
    MeasurementUnit,
    Occupancy,
    cents,
    format_eur,
    period,
)
from lokara_heating_engine import (
    Co2Input,
    HeatingInput,
    HeatingLine,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    OwnerResidualOrigin,
    WarmWaterInput,
    calculate_heating_statement,
)
from lokara_nk_engine import CostItem, NkInput, UnitBasis, calculate_nk_statement
from lokara_pdf import PartyKey, StatementData, format_number_de, rechtsstand_entry, statement_html
from lokara_pdf.demo import AS_OF, BILLING_PERIOD, PARTY_LABELS, build_demo_statement
from lokara_pdf.heating_disclosure import TENTH_PROMILLE_PER_PROMILLE
from lokara_rules_store import (
    CO2_SPLIT_TABLE,
    DEFAULT_CONSUMPTION_SHARE,
    DEGREE_DAY_TABLE,
    HEATING_SPLIT_BOUNDS,
    WARM_WATER_FORMULA,
    get_rule,
)

# The carriers, from `docs/08` → 4a. One element, one class, so the disclosure is
# addressable by this gate *and* by the stylesheet — the tier assignment in
# `test_statement_legal_typography.py` uses the same three selectors.
BLOCK_A = "cost-split"  # Aufteilung der Gesamtkosten (§§ 7, 8, 9 + CO₂ deduction)
BLOCK_B = "basis-table"  # Bemessungsgrundlagen
BLOCK_C = "party-change"  # Nutzerwechsel (Gradtagszahlen / Zeitanteile)
BLOCK_CO2 = "co2"  # the existing CO₂ block, unchanged in position

# Spelled as a code point: U+2212 MINUS SIGN is the deduction line's operator and
# a hyphen would turn it into a dash (docs/08 → 4a, "Glyphs are part of the
# copy"). A literal here also trips RUF001.
MINUS = chr(0x2212)

# `docs/08` → "`MeasurementUnit` travels with the value — the plumbing decision
# (slice 5)". The *Gesamtbemessung* and the Bemessung *column* for Verbrauch
# Heizung print once the measurement unit is carried, and are withheld together
# where a building records none. The **row** is never withheld — see F1 above.
HEAT_COLUMN = "Verbrauch Heizung"

# The Umlageschlüssel copy, from `docs/08` item 1's table. The citations were
# assigned there and dropped by the first render; § 7 Abs. 1 governs the heating
# split, § 8 Abs. 1 the warm-water split — separate paragraphs, separate pots.
AREA_KEY_HEATING = "Wohnfläche (m²·Tage) — § 7 Abs. 1 HeizkostenV"
AREA_KEY_WARM_WATER = "Wohnfläche (m²·Tage) — § 8 Abs. 1 HeizkostenV"
# § 9a Abs. 2 replaced the consumption key. The citation is the paragraph that
# decided *this* share, not § 7 Abs. 1, which is only why a consumption pot exists.
AREA_KEY_FALLBACK = "Wohnfläche (m²·Tage) — § 9a Abs. 2 HeizkostenV"
HEAT_KEY = "Erfasster Wärmeverbrauch"
HEAT_KEY_WITH_CHANGE = "Erfasster Wärmeverbrauch (Nutzerwechsel: Gradtagszahlen)"
WARM_WATER_KEY = "Erfasster Warmwasserverbrauch (m³)"

# Slice 5, `docs/08` → "Which spelling goes where". **Long form in the
# Umlageschlüssel cell**, because naming the device is what BGH minimum #2 means
# by *Angabe und Erläuterung* des Verteilerschlüssels: `Erfasster Wärmeverbrauch`
# says *what* was measured, `… in Einheiten eines Heizkostenverteilers` says *by
# what*. Parenthesis-free on purpose, so it composes with the Nutzerwechsel
# parenthetical without nesting or doubling a bracket.
HEAT_KEY_HKV = "Erfasster Wärmeverbrauch in Einheiten eines Heizkostenverteilers"
HEAT_KEY_HKV_WITH_CHANGE = f"{HEAT_KEY_HKV} (Nutzerwechsel: Gradtagszahlen)"
HEAT_KEY_KWH = "Erfasster Wärmeverbrauch in kWh am Wärmemengenzähler"
# **Compact form in a numeric cell**: it sits in a column beside `36.500 m²·Tage`
# and `40 m³`, and the long form would wrap a figure column into prose.
HKV_UNIT = "HKV-Einheiten"
HEAT_TOTAL_CELL = f"1.000 {HKV_UNIT}"

# The withheld Gesamtbemessung cell and its explanation. No digit, no dash used
# as a figure: `—`, `0` or a blank all read as *zero* in a numeric column, and a
# zero denominator makes the renter's own share look undefined. Slice 5 removes
# the *cause* (the demo building records its Maßeinheit) and keeps the *branch*:
# a building that records none still owes the renter this disclosure.
WITHHELD_CELL = "ohne Maßeinheit — nicht ausgewiesen"
WITHHELD_NOTE = (
    "Für den erfassten Wärmeverbrauch wird keine Gesamtbemessung ausgewiesen: Die Maßeinheit "
    "der Erfassungsgeräte (kWh oder Einheiten eines Heizkostenverteilers) liegt dieser "
    "Abrechnung nicht vor. Der Verbrauchsanteil wurde gleichwohl nach den erfassten Werten "
    "verteilt."
)

# F2. One sentence, one place: directly beneath Block B's party table, where the
# rounded figures originate. `rd.` marks the instance; this states the convention.
ROUNDING_NOTE = (
    "Gerundete Bemessungen sind mit rd. gekennzeichnet; gerechnet wird mit dem exakten Wert, "
    "sodass eine Nachrechnung aus dem angezeigten Wert um wenige Cent abweichen kann."
)
ROUNDED = "rd."

# `docs/08` → "Die Eigentümerzeile" § 3 (14.08.2026). Block B is a
# Liegenschafts-level table, so every empty/self-used unit's Bemessung is
# aggregated into **one** row under this label, rendered **last** — one-for-one
# with the money table, where it is the reconciling line rather than a party.
# Block C decomposes a single unit and therefore keeps the per-segment party
# label instead. Spelled here rather than imported from `lokara_pdf`, like every
# other piece of required copy in this file: a gate that reads the expected word
# off the renderer cannot see the renderer rename it.
OWNER_LABEL = "Eigentümeranteil"

_TAG = re.compile(r"<[^>]+>")
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL)
_PROMILLE_PAIR = re.compile(r"([\d.,]+) ‰ von ([\d.,]+) ‰")

# NBSP (U+00A0) and narrow NBSP (U+202F): the template joins a figure to its unit
# with one. Spelled as code points — a literal trips RUF001.
_SPACES = ("\xa0", chr(0x202F))

_VOID_TAGS = frozenset({"br", "hr", "img", "meta", "input", "link"})


def _plain(text: str) -> str:
    """Whitespace and NBSP are formatting choices, not part of the spec —
    `scripts/assert_statement_pdf.py` flattens the PDF the same way."""
    for space in _SPACES:
        text = text.replace(space, " ")
    return re.sub(r"\s+", " ", text).strip()


def _text(fragment: str) -> str:
    """Rendered text of an HTML fragment: what a reader sees, tags removed."""
    return _plain(_TAG.sub(" ", fragment))


class _Subtree(HTMLParser):
    """Raw HTML of the first element carrying a given class.

    Block-scoped assertions are the point of this: `Verbrauch Heizung` is a
    legitimate heading of the *money* table and a defect inside Block B, and a
    page-wide substring check cannot tell those apart.
    """

    def __init__(self, class_name: str) -> None:
        super().__init__(convert_charrefs=True)
        self._wanted = class_name
        self._depth = 0
        self._parts: list[str] = []
        self.found: str | None = None

    def _matches(self, attrs: list[tuple[str, str | None]]) -> bool:
        return any(
            name == "class" and value is not None and self._wanted in value.split()
            for name, value in attrs
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.found is not None:
            return
        if tag in _VOID_TAGS:
            if self._depth:
                self._parts.append(" ")
            return
        if self._depth:
            self._depth += 1
            self._parts.append(self.get_starttag_text() or "")
        elif self._matches(attrs):
            self._depth = 1
            self._parts.append(self.get_starttag_text() or "")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._depth and self.found is None:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self.found is not None or not self._depth or tag in _VOID_TAGS:
            return
        self._depth -= 1
        if self._depth == 0:
            self.found = "".join(self._parts)
        else:
            self._parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._depth and self.found is None:
            self._parts.append(data)


def block(html: str, class_name: str) -> str:
    """The block's own HTML. Missing → a named failure, never a KeyError."""
    parser = _Subtree(class_name)
    parser.feed(html)
    parser.close()
    assert parser.found is not None, (
        f"no element with class {class_name!r} on the statement — "
        "docs/08 → 'The rendered form (slice 4)' names the three carriers"
    )
    return parser.found


def has_block(html: str, class_name: str) -> bool:
    parser = _Subtree(class_name)
    parser.feed(html)
    parser.close()
    return parser.found is not None


def block_text(html: str, class_name: str) -> str:
    return _text(block(html, class_name))


def _position(html: str, class_name: str) -> int:
    """Where the block starts in the document — for the order assertions. Matches
    the class among others in the attribute, so styling hooks stay free."""
    match = re.search(rf'class="[^"]*\b{re.escape(class_name)}\b[^"]*"', html)
    assert match is not None, f"no element with class {class_name!r} on the statement"
    return match.start()


def rows(fragment: str) -> list[list[str]]:
    """Rendered table rows of a fragment, cell by cell."""
    return [[_text(cell) for cell in _CELL.findall(row)] for row in _ROW.findall(fragment)]


def has_row(table: list[list[str]], *cells: str) -> bool:
    return list(cells) in table


def _eur(amount: Cents) -> str:
    """`format_eur` of a Cents value, normalised the way the page text is."""
    return _plain(format_eur(amount))


def _n(value: Decimal) -> str:
    return _plain(format_number_de(value))


def _pct(share: Decimal) -> str:
    """`0.7` → `70`. Derived from the resolved rule value, never a literal."""
    return _n(share * 100)


def _de(figure: str) -> Decimal:
    """`rd. 5,95 m³` → `Decimal("5.95")`. Reads the page, not the engine.

    The `rd.` marker is stripped, not required: whether a given figure carries it
    is the subject of its own assertions, and the sum invariant has to hold over
    what is printed either way."""
    match = re.match(r"-?[\d.]+(?:,\d+)?", figure.strip().removeprefix(ROUNDED).strip())
    assert match is not None, f"not a German figure: {figure!r}"
    return Decimal(match.group(0).replace(".", "").replace(",", "."))


def _heating(data: StatementData) -> HeatingResult:
    heating = data.heating_result
    assert heating is not None, "fixture lost its heating section"
    return heating


# --- fixtures ----------------------------------------------------------------
# The canonical building of `docs/03`/`docs/08`: A 50 m², B 30 m², C 20 m²;
# Bernd leaves B on 30.06.2025, B vacant Jul–Dec → a landlord party.

HKV = MeasurementUnit.HKV_UNITS


def heating_units(
    *,
    heat: tuple[Decimal | None, Decimal | None, Decimal | None] = (
        Decimal(600),
        Decimal(250),
        Decimal(150),
    ),
    ww: tuple[Decimal | None, Decimal | None, Decimal | None] = (
        Decimal(20),
        Decimal(12),
        Decimal(8),
    ),
    heat_unit: MeasurementUnit | None = HKV,
) -> tuple[HeatingUnit, ...]:
    """The demo building's three units, with the Maßeinheit of their heat
    allocators (`docs/08` rule 7: `_SPEC` gives all three `HKV_UNITS`).

    Built by a function rather than as a module constant so this file still
    *collects* while `heat_consumption_unit` does not exist yet — the assertions
    then fail one by one with their own message instead of the module erroring
    out at import time.
    """
    return tuple(
        HeatingUnit(
            unit_id=unit_id,
            area_sqm_x100=area,
            heat_consumption=heat_value,
            ww_consumption_m3=ww_value,
            heat_consumption_unit=heat_unit,
        )
        for unit_id, area, heat_value, ww_value in zip(
            ("unit-a", "unit-b", "unit-c"), (5000, 3000, 2000), heat, ww, strict=True
        )
    )


DEMO_OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)
MEASURED_40_M3 = WarmWaterInput(volume_m3=Decimal(40))
CO2_2000_KG = Co2Input(total_co2_kg=Decimal(2000), co2_cost=cents(30_000))


def build_statement(
    *,
    units: tuple[HeatingUnit, ...] | None = None,
    occupancies: tuple[Occupancy, ...] = DEMO_OCCUPANCIES,
    party_labels: Mapping[PartyKey, str] | None = None,
    total_cost: int = 1_030_000,
    total_energy_kwh: int = 20_000,
    warm_water: WarmWaterInput | None = MEASURED_40_M3,
    co2: Co2Input | None = CO2_2000_KG,
) -> StatementData:
    """The demo composition, parameterised — both real engines, rules resolved
    from the store for `AS_OF`, one NK cost so the page keeps both sections."""
    units = heating_units() if units is None else units
    split_bounds = get_rule(HEATING_SPLIT_BOUNDS, AS_OF)
    warm_water_rule = get_rule(WARM_WATER_FORMULA, AS_OF)
    degree_days = get_rule(DEGREE_DAY_TABLE, AS_OF)
    co2_table = get_rule(CO2_SPLIT_TABLE, AS_OF)

    heating = calculate_heating_statement(
        HeatingInput(
            billing_period=BILLING_PERIOD,
            total_cost=cents(total_cost),
            total_energy_kwh=Decimal(total_energy_kwh),
            units=units,
            occupancies=occupancies,
            rules=HeatingRules(
                consumption_share=DEFAULT_CONSUMPTION_SHARE,
                split_bounds=split_bounds.value,
                warm_water_formula=warm_water_rule.value,
                degree_days=degree_days.value,
                co2_table=co2_table.value,
                co2_rechtsstand=co2_table.rechtsstand,
            ),
            warm_water=warm_water,
            co2=co2,
        )
    )
    nk_costs = (
        CostItem(
            cost_id="cost-garbage",
            label="Müllabfuhr",
            amount=cents(120_000),
            key=AllocationKey.AREA,
        ),
    )
    nk_result = calculate_nk_statement(
        NkInput(
            billing_period=BILLING_PERIOD,
            units=tuple(UnitBasis(unit_id=u.unit_id, area_sqm_x100=u.area_sqm_x100) for u in units),
            occupancies=occupancies,
            costs=nk_costs,
        )
    )
    return StatementData(
        landlord_name="Demo Vermieter",
        building_label="Musterstraße 12, 60311 Frankfurt am Main",
        period_label="01.01.2025 – 31.12.2025",
        nk_result=nk_result,
        nk_costs=nk_costs,
        party_labels=PARTY_LABELS if party_labels is None else party_labels,
        rechtsstaende=tuple(
            dict.fromkeys(
                (
                    rechtsstand_entry(split_bounds),
                    rechtsstand_entry(warm_water_rule),
                    rechtsstand_entry(degree_days),
                    rechtsstand_entry(co2_table),
                )
            )
        ),
        heating_result=heating,
    )


def no_co2_statement() -> StatementData:
    return build_statement(total_cost=1_000_000, co2=None)


def area_fallback_statement() -> StatementData:
    """§ 9 Abs. 2: warm-water volume not measured → the Ersatzwert branch."""
    return build_statement(
        total_cost=1_000_000, warm_water=WarmWaterInput(volume_m3=None), co2=None
    )


def no_warm_water_statement() -> StatementData:
    """No central warm water at all — *not* a § 9a Abs. 2 fallback."""
    return build_statement(total_cost=1_000_000, warm_water=None, co2=None)


def ww_key_fallback_statement() -> StatementData:
    """§ 9a Abs. 2 on the warm-water column only: B + C (50 % of the area) have
    no reading, the heating column keeps its measured Bemessung."""
    units = heating_units(ww=(Decimal(20), None, None))
    return build_statement(units=units, total_cost=1_000_000, co2=None)


def heat_key_fallback_statement() -> StatementData:
    """§ 9a Abs. 2 on the heating column only — the mirror image.

    The devices still declare their Maßeinheit; § 9a Abs. 2 replaced the *key*,
    so no consumption Bemessung was applied and none may be labelled (`docs/08`
    rule 4 — `None` means *not applied*)."""
    units = heating_units(heat=(Decimal(600), None, None))
    return build_statement(units=units, total_cost=1_000_000, co2=None)


def unitless_statement() -> StatementData:
    """A building that records **no** Maßeinheit for its heat allocators — the
    withholding branch `docs/08` deliberately keeps (rule 3).

    Every assertion that used to run against the demo composition lives here
    now: slice 5 removed the *cause* on the demo building, not the branch, and
    an unrecorded unit still owes the renter the honest disclosure. Nothing was
    weakened in the move — the copy, the absence checks and the adjacency rule
    are the same assertions against a fixture that still reaches the branch.
    """
    return build_statement(units=heating_units(heat_unit=None))


def single_party_statement() -> StatementData:
    """Every unit used by one party for the whole period — no Nutzerwechsel, so
    Block C has nothing to disclose and must not render."""
    occupancies = (
        Occupancy("unit-a", "ten-a", period("2025-01-01")),
        Occupancy("unit-b", "ten-b", period("2024-08-01")),
        Occupancy("unit-c", "ten-c", period("2023-01-01")),
    )
    labels = dict(PARTY_LABELS) | {("unit-b", "ten-b"): "Wohnung B — Bernd Muster"}
    return build_statement(occupancies=occupancies, party_labels=labels, total_cost=1_000_000)


# Unit B used by three parties: Bernd to 30.06., vacancy Jul–Sep, Doris from
# 01.10. Its 12 m³ split by days is 5,9506… / 3,0246… / 3,0246… — rounded
# independently to 2 decimals those print 5,95 + 3,02 + 3,02 and the column then
# sums to 39,99 against a printed Gesamtbemessung of 40. Largest remainder
# (docs/08 → "Display rounding of a fractional Bemessung") puts the missing
# hundredth on the largest remainder, ties by party order → 3,03 on Doris.
THREE_PARTY_OCCUPANCIES = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-b", "ten-d", period("2025-10-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)
THREE_PARTY_LABELS: dict[PartyKey, str] = dict(PARTY_LABELS) | {
    ("unit-b", "ten-d"): "Wohnung B — Doris Muster (Einzug 01.10.2025)",
    ("unit-b", None): "Wohnung B — Leerstand 01.07.–30.09.2025 → Vermieter",
}


def three_party_statement() -> StatementData:
    return build_statement(
        occupancies=THREE_PARTY_OCCUPANCIES, party_labels=THREE_PARTY_LABELS, total_cost=1_000_000
    )


# --- Block A -----------------------------------------------------------------


class TestBlockACostSplit:
    """`docs/08` item 1 → "Required rendered text — Block A", items 2 and 3.

    How 10.300,00 € became four pots. Every figure comes off `HeatingResult`;
    the percentages are derived from the resolved rule values and are never
    template literals.
    """

    def test_the_co2_deduction_leads_to_the_billable_cost(self) -> None:
        data = build_demo_statement()
        heating = _heating(data)
        co2 = heating.co2
        assert co2 is not None, "the demo fixture carries a CO₂ split"
        text = block_text(statement_html(data), BLOCK_A)

        assert "Aufteilung der Gesamtkosten (HeizkostenV)" in text
        assert f"Gesamtkosten Heizung und Warmwasser {_eur(heating.total)}" in text
        assert (
            f"{MINUS} CO₂-Vermieteranteil (§ 7 Abs. 1 CO2KostAufG) {_eur(co2.landlord_amount)}"
        ) in text
        assert f"= umlagefähige Kosten {_eur(heating.billable_cost)}" in text

    def test_the_worked_examples_figures_are_the_ones_printed(self) -> None:
        """Self-check against `docs/08` → "The worked example": if these move, the
        fixture drifted rather than the renderer."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_A)

        assert "10.300,00 €" in text
        assert "157,08 €" in text
        assert "10.142,92 €" in text
        assert "2.535,73 €" in text and "7.607,19 €" in text
        assert "2.282,16 €" in text and "5.325,03 €" in text
        assert "760,72 €" in text and "1.775,01 €" in text

    def test_paragraph_9_prints_the_formula_with_its_operands(self) -> None:
        """Item 3, measured branch: the line is reproducible from what it prints."""
        data = build_demo_statement()
        heating = _heating(data)
        separation = heating.warm_water_separation
        assert separation is not None and separation.method == "MEASURED"
        assert separation.volume_m3 is not None
        assert separation.factor_kwh_per_m3_kelvin is not None
        assert separation.hot_temp_c is not None and separation.cold_temp_c is not None
        text = block_text(statement_html(data), BLOCK_A)

        assert "§ 9 HeizkostenV — Trennung von Heizung und Warmwasser" in text
        assert (
            f"Q(WW) = {_n(separation.factor_kwh_per_m3_kelvin)} kWh/(m³·K) "
            f"× {_n(separation.volume_m3)} m³ "
            f"× ({_n(separation.hot_temp_c)} °C {MINUS} {_n(separation.cold_temp_c)} °C) "
            f"= {_n(separation.q_ww_kwh)} kWh von {_n(separation.total_energy_kwh)} kWh "
            "Gesamtenergie"
        ) in text
        assert (
            f"→ Warmwasser {_eur(heating.ww_pot)} · Heizung {_eur(heating.heating_pot)}"
        ) in text

    def test_the_measured_branch_never_says_ersatzwert(self) -> None:
        """Item 3: the two branches print different text and the fallback is
        legally weaker than a measurement. The wrong one must be unprintable."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_A)

        assert "Ersatzwert" not in text
        assert "nicht gemessen" not in text

    def test_the_applied_ratio_and_the_legal_bound_are_two_printed_facts(self) -> None:
        """Item 2: what was applied, and what the law permits. A statement that
        prints only the applied share says nothing about whether it was lawful."""
        data = build_demo_statement()
        heating = _heating(data)
        bounds = heating.split_bounds
        share = heating.applied_consumption_share
        text = block_text(statement_html(data), BLOCK_A)

        assert (
            "§§ 7, 8 HeizkostenV — Grund- und Verbrauchskosten: "
            f"angewendet {_pct(1 - share)} % Grundkosten / {_pct(share)} % Verbrauch"
        ) in text
        assert (
            f"(zulässiger Rahmen: {_pct(bounds.min_consumption_share)} % bis "
            f"{_pct(bounds.max_consumption_share)} % Verbrauchskosten, § 7 Abs. 1 HeizkostenV)"
        ) in text

    def test_the_four_pots_are_printed_per_cost_type(self) -> None:
        data = build_demo_statement()
        heating = _heating(data)
        text = block_text(statement_html(data), BLOCK_A)

        assert (
            f"Heizung: Grundkosten {_eur(heating.heat_base_pot)} "
            f"· Verbrauchskosten {_eur(heating.heat_cons_pot)}"
        ) in text
        assert (
            f"Warmwasser: Grundkosten {_eur(heating.ww_base_pot)} "
            f"· Verbrauchskosten {_eur(heating.ww_cons_pot)}"
        ) in text

    def test_without_a_co2_split_no_deduction_line_renders(self) -> None:
        """`docs/08` → 4a: the deduction line is dropped, both figures still print
        and they are equal — one code path, no branch asserting an equality in
        words."""
        data = no_co2_statement()
        heating = _heating(data)
        assert heating.co2 is None
        text = block_text(statement_html(data), BLOCK_A)

        assert "CO₂-Vermieteranteil" not in text
        assert f"Gesamtkosten Heizung und Warmwasser {_eur(heating.total)}" in text
        assert f"= umlagefähige Kosten {_eur(heating.billable_cost)}" in text
        assert int(heating.billable_cost) == int(heating.total)

    def test_the_area_fallback_prints_its_own_formula_and_says_it_was_not_measured(
        self,
    ) -> None:
        """Item 3, § 9 Abs. 2: *nicht gemessen* and *Ersatzwert* carry the legal
        weakness of the figure, and the measured formula must not appear."""
        data = area_fallback_statement()
        heating = _heating(data)
        separation = heating.warm_water_separation
        assert separation is not None and separation.method == "AREA_FALLBACK"
        assert separation.area_fallback_kwh_per_sqm_year is not None
        assert separation.heated_area_sqm is not None
        assert separation.period_days is not None and separation.reference_year_days is not None
        text = block_text(statement_html(data), BLOCK_A)

        assert (
            "Warmwasserverbrauch nicht gemessen — Ersatzwert nach § 9 Abs. 2 HeizkostenV:"
        ) in text
        # F2: the day share is parenthesised here for the same reason as in
        # Block C, and the result is **exact**, so it carries no `rd.` — the
        # marker doing its job in the one branch where a reader could not
        # otherwise tell (docs/08 → "The rounding is disclosed", ruling 3).
        assert (
            f"{_n(separation.area_fallback_kwh_per_sqm_year)} kWh je m² Wohnfläche und Jahr "
            f"× {_n(separation.heated_area_sqm)} m² "
            f"× ({_n(Decimal(separation.period_days))} von "
            f"{_n(Decimal(separation.reference_year_days))} Tagen) "
            f"= {_n(separation.q_ww_kwh)} kWh von {_n(separation.total_energy_kwh)} kWh"
        ) in text
        assert ROUNDED not in text
        # The measured branch's formula is not a plausible alternative here.
        assert "Q(WW) =" not in text
        assert "kWh/(m³·K)" not in text
        # Both branches print the euro pots — that is what the tenant can check.
        assert (
            f"→ Warmwasser {_eur(heating.ww_pot)} · Heizung {_eur(heating.heating_pot)}"
        ) in text

    def test_without_central_warm_water_no_paragraph_9_section_renders(self) -> None:
        """`docs/08` → 4a, correction 4: nothing was separated and the warm-water
        pots are 0 by construction. `Warmwasser: Grundkosten 0,00 €` would state a
        split that does not exist."""
        data = no_warm_water_statement()
        heating = _heating(data)
        assert heating.warm_water_separation is None
        text = block_text(statement_html(data), BLOCK_A)

        assert "§ 9 HeizkostenV" not in text
        assert "Trennung von Heizung und Warmwasser" not in text
        assert "Warmwasser: Grundkosten" not in text
        assert "Ersatzwert" not in text
        # Heating keeps its two lines: that split did happen.
        assert (
            f"Heizung: Grundkosten {_eur(heating.heat_base_pot)} "
            f"· Verbrauchskosten {_eur(heating.heat_cons_pot)}"
        ) in text


# --- Block B -----------------------------------------------------------------


class TestBlockBBemessungsgrundlagen:
    """`docs/08` item 1 → "Required rendered text — Block B".

    One row per money column stating that column's Umlageschlüssel and
    Gesamtbemessung, then one row per party with its Bemessung values. The four
    money columns do not share a denominator, which is why the NK solution (one
    label on the cost header row) does not transfer.
    """

    def test_each_money_column_states_its_umlageschluessel_and_gesamtbemessung(self) -> None:
        """**F1.** All **four** money columns get a row — the heating table's four
        columns do not share a denominator, and a column with no row named is a
        column with no Umlageschlüssel anywhere on the page (BGH minimum #2).

        The two Wohnfläche rows carry their citations. `Rechtsstand: § 7 Abs. 1
        HeizkostenV 03/1989` in the footer dates a rule; it does not attach it to
        a column, and a renter checking *why their base costs go by area* has
        nowhere else to look."""
        table = rows(block(statement_html(build_demo_statement()), BLOCK_B))

        assert has_row(table, "Spalte", "Umlageschlüssel", "Gesamtbemessung")
        assert has_row(table, "Grundkosten Heizung", AREA_KEY_HEATING, "36.500 m²·Tage")
        assert has_row(table, HEAT_COLUMN, HEAT_KEY_HKV_WITH_CHANGE, HEAT_TOTAL_CELL)
        assert has_row(table, "Grundkosten Warmwasser", AREA_KEY_WARM_WATER, "36.500 m²·Tage")
        assert has_row(table, "Verbrauch Warmwasser", WARM_WATER_KEY, "40 m³")

    def test_the_column_rows_follow_the_money_tables_column_order(self) -> None:
        """A renter reads across the money table and down this one. `docs/08`:
        Grundkosten Heizung → Verbrauch Heizung → Grundkosten Warmwasser →
        Verbrauch Warmwasser."""
        expected = [
            "Grundkosten Heizung",
            HEAT_COLUMN,
            "Grundkosten Warmwasser",
            "Verbrauch Warmwasser",
        ]
        table = rows(block(statement_html(build_demo_statement()), BLOCK_B))

        assert [row[0] for row in table if row and row[0] in set(expected)] == expected

    def test_every_party_prints_its_bemessung_per_column(self) -> None:
        """**F2**: `rd.` marks the two Bemessungen that were rounded and only
        those. `20 m³` and `8 m³` are exact readings — `rd. 20 m³` would state a
        rounding that did not happen, and a marker on every figure is decoration
        rather than a fact."""
        table = rows(block(statement_html(build_demo_statement()), BLOCK_B))

        assert has_row(table, "Partei", "Fläche·Tage", HEAT_COLUMN, "Verbrauch Warmwasser")
        assert has_row(table, "Wohnung A — Anna Beispiel", "18.250", f"600 {HKV_UNIT}", "20 m³")
        assert has_row(
            table,
            "Wohnung B — Bernd Muster (Auszug 30.06.2025)",
            "5.430",
            f"rd. 145,83 {HKV_UNIT}",
            "rd. 5,95 m³",
        )
        # Re-labelled 14.08.2026: Block B is a Liegenschafts-level table whose
        # column sums to the printed Gesamtbemessung, so it carries the single
        # `Eigentümeranteil` row one-for-one with the money table — not a party
        # row per vacant unit (`docs/08` → "Die Eigentümerzeile" § 3). The
        # Bemessungen are unchanged: one vacant unit, so the aggregate is that
        # unit's own. Block C keeps the per-segment label, deliberately.
        assert has_row(
            table,
            "Eigentümeranteil",
            "5.520",
            f"rd. 104,17 {HKV_UNIT}",
            "rd. 6,05 m³",
        )
        assert has_row(table, "Wohnung C — Clara Vorlage", "7.300", f"150 {HKV_UNIT}", "8 m³")
        assert has_row(table, "Gesamtbemessung", "36.500", HEAT_TOTAL_CELL, "40 m³")

    def test_the_rounded_heat_bemessungen_carry_the_rd_marker(self) -> None:
        """**F2's rule, applied to the new column.** `rd.` marks the *value*, not
        the line: a marker on a figure that was not rounded states a rounding that
        did not happen, and a missing marker on one that was hides it.

        Under the VDI 2067 table (K3, `docs/03`) the Nutzerwechsel figures are no
        longer exact: 250 × 5.833/10.000 = 145,825 and 250 × 4.167/10.000 = 104,175.
        Both are marked. 600 and 150 are whole readings and stay bare. This test
        previously asserted that *no* heat Bemessung carried the marker, which was
        true only of the old 585/415 table where 146,25 and 103,75 came out exact —
        the premise moved with the table, not the rule.

        The two rounded halves still sum to the exact 250 the meter recorded.

        Since 14.08.2026 the second half is on the `Eigentümeranteil` row, which
        renders **last** rather than in unit order — so the filter cannot be
        `startswith("Wohnung")` (it would drop the row this test is about) and
        the expected order is the printed one, owner last. No figure moved:
        104,17 is where it always was, one row further down."""
        table = rows(block(statement_html(build_demo_statement()), BLOCK_B))
        party_labels = ("Wohnung", OWNER_LABEL)
        heat_cells = [row[2] for row in table if len(row) == 4 and row[0].startswith(party_labels)]

        assert heat_cells == [
            f"600 {HKV_UNIT}",
            f"rd. 145,83 {HKV_UNIT}",
            f"150 {HKV_UNIT}",
            f"rd. 104,17 {HKV_UNIT}",
        ]
        assert [cell.startswith(ROUNDED) for cell in heat_cells] == [False, True, False, True]
        assert Decimal("145.83") + Decimal("104.17") == Decimal("250.00")

    def test_the_rounding_is_disclosed_once_and_under_the_table_it_qualifies(self) -> None:
        """**F2**, `docs/08` → "The rounding is disclosed".

        The printed Verbrauchskosten Warmwasser ÷ the printed 40 m³ reproduces
        Wohnung A and Wohnung C to the cent and misses **both** Nutzerwechsel
        parties by ~3 ct: the renter checking the uncontested line succeeds, the
        renter checking the contested line fails. The last clause of the sentence
        is that, said out loud, before they discover it.

        One sentence, one place — a caveat repeated per block is a caveat nobody
        reads — and directly beneath the party table, not two paragraphs away."""
        html = statement_html(build_demo_statement())
        text = block_text(html, BLOCK_B)

        assert ROUNDING_NOTE in text
        assert text.index("Gesamtbemessung 36.500") < text.index(ROUNDING_NOTE)
        assert _plain(_text(html)).count(ROUNDING_NOTE) == 1, (
            "the rounding disclosure is one sentence in one place (docs/08)"
        )
        # It states a display convention, so it does not branch on whether a
        # figure happened to need it — one code path, nothing to be wrong about.
        assert ROUNDING_NOTE in block_text(statement_html(single_party_statement()), BLOCK_B)

    def test_the_bemessungen_are_de_scaled(self) -> None:
        """⚠️ `docs/03`: the engine carries m²·Tage ×100. `18.250` renders as
        `1.825.000` if the render boundary forgets to de-scale, and an
        integer-vs-integer test stays green through exactly that bug. The scaled
        forms are asserted **absent** — the four canaries
        `scripts/assert_statement_pdf.py` carries over the PDF."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_B)

        assert "18.250" in text and "36.500" in text
        assert "1.825.000" not in text  # unit A's weight, ×100 fixed point, leaked
        assert "3.650.000" not in text  # the Gesamtbemessung, likewise
        assert "543.000" not in text  # Bernd's
        assert "552.000" not in text  # the landlord party's
        assert "730.000" not in text  # unit C's
        # A meter register is ×1000 in the DB (`value_x1000`, `packages/db` →
        # `MeterReading`), so the leak forms of the two consumption columns are
        # the same figure with three zeros: `1.000 HKV-Einheiten` → `1.000.000`,
        # `40 m³` → `40.000`, `rd. 5,95 m³` → `5950`. Block-scoped, because no
        # legitimate Bemessung in this block is in that range — page-wide the
        # same canary would fire on a 40.000,00 € invoice.
        assert HEAT_TOTAL_CELL in text and "40 m³" in text
        assert "1.000.000" not in text  # Σ heat Bemessung, ×1000, leaked
        assert "600.000" not in text  # unit A's heat Bemessung, likewise
        assert "40.000" not in text  # Σ warm-water Bemessung, ×1000, leaked
        assert "5950" not in text  # Bernd's 5,95 m³, ×1000, leaked

    def test_the_printed_bemessungen_sum_to_the_printed_gesamtbemessung(self) -> None:
        """The invariant of every allocation test, over rendered text: a document
        that is supposed to add up must add up as printed, not merely as computed
        (`docs/08` → Block B, and the same rule as the NK reference totals).

        The addends are the Mietverhältnis rows **plus** the one
        `Eigentümeranteil` row: 36.500 m²·Tage includes the vacancy's 5.520, and
        a sum taken over `heating.lines` alone would be asserting that the
        printed column does *not* add up (`docs/08` → "Die Eigentümerzeile" § 3).
        """
        data = build_demo_statement()
        table = rows(block(statement_html(data), BLOCK_B))
        labels = {PARTY_LABELS[(line.unit_id, line.tenancy_id)] for line in _heating(data).lines}
        labels.add(OWNER_LABEL)

        party_rows = [row for row in table if row and row[0] in labels]
        assert len(party_rows) == len(_heating(data).lines) + 1, (
            "one row per Mietverhältnis, plus the one Eigentümerzeile"
        )
        total_row = next(row for row in table if row and row[0] == "Gesamtbemessung")

        # Three Bemessung columns since slice 5: Fläche·Tage, Verbrauch Heizung,
        # Verbrauch Warmwasser — in the money table's column order.
        for column in (1, 2, 3):
            printed = [_de(row[column]) for row in party_rows]
            assert sum(printed) == _de(total_row[column]), (
                f"column {column}: printed Bemessungen {printed} do not sum to the "
                f"printed Gesamtbemessung {total_row[column]!r}"
            )

    def test_a_fractional_bemessung_rounds_by_largest_remainder(self) -> None:
        """`docs/08` → "Display rounding of a fractional Bemessung": at most 2
        decimals, trailing zeros suppressed, and the column rounded by largest
        remainder so the printed values sum to the printed Gesamtbemessung.

        Rounding each value independently prints 20 + 5,95 + 3,02 + 3,02 + 8 =
        39,99 under a Gesamtbemessung of 40 — the invariant above, broken by the
        one thing the invariant cannot express on the demo fixture (its splits
        happen to round exactly).

        Five rows, not four: the fifth is the `Eigentümeranteil`, rendered last
        (`docs/08` § 3). **No value moved** on 14.08.2026 — the column still
        prints 20 / 5,95 / 3,03 / 8 / 3,02 and the +0,01 still lands on Doris,
        who precedes the owner in party order. Only the owner row's position
        changed, from third to last."""
        data = three_party_statement()
        table = rows(block(statement_html(data), BLOCK_B))
        labels = {
            THREE_PARTY_LABELS[(line.unit_id, line.tenancy_id)] for line in _heating(data).lines
        }
        labels.add(OWNER_LABEL)
        party_rows = [row for row in table if row and row[0] in labels]

        printed = [_de(row[3]) for row in party_rows]
        assert printed == [
            Decimal(20),
            Decimal("5.95"),
            Decimal("3.03"),  # +0,01: largest remainder, ties by party order
            Decimal(8),
            Decimal("3.02"),  # the Eigentümerzeile, last
        ]
        assert sum(printed) == Decimal(40)
        assert has_row(table, "Gesamtbemessung", "36.500", HEAT_TOTAL_CELL, "40 m³")
        # F2: the three rounded ones are marked, the two exact ones are not.
        assert [row[3].startswith(ROUNDED) for row in party_rows] == [
            False,
            True,
            True,
            False,
            True,
        ]

    def test_the_heating_column_states_its_unit_where_the_building_records_one(self) -> None:
        """**Slice 5**, `docs/08` → "`MeasurementUnit` travels with the value".

        `HeatingUnit.heat_consumption` is kWh at a Wärmemengenzähler and
        dimensionless HKV-Einheiten at a Heizkostenverteiler, and nothing in the
        input distinguished them — so the largest denominator on the page was
        withheld. The unit now rides on the row that carries the value, and the
        demo building's allocators are `HKV_UNITS` (`packages/adapters` `_SPEC`:
        1200→1800, 3400→3650, 880→1030 ⇒ 600 / 250 / 150, Σ 1.000).

        The long form is in the Umlageschlüssel cell, where naming the device is
        the *Erläuterung* half of BGH minimum #2; the compact form is in the
        figure cell beside it."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_B)

        assert HEAT_COLUMN in text
        assert HEAT_KEY_HKV_WITH_CHANGE in text
        assert HEAT_TOTAL_CELL in text
        # The two spellings do not leak into each other's cell: a numeric cell
        # naming a device wraps, and a key cell without one is the old defect.
        assert f"1.000 {HEAT_KEY_HKV}" not in text
        assert "Einheiten (Heizkostenverteiler)" not in text  # the un-composed long form
        # And nothing is withheld any more on this building.
        assert WITHHELD_CELL not in text
        assert WITHHELD_NOTE not in text

    def test_a_kwh_building_names_its_heat_meter_instead(self) -> None:
        """The other lawful configuration, and why the device belongs in the copy
        at all: `MeterKind.HEAT` does not say which device it is, and the two
        differ by three orders of magnitude in what their figures mean."""
        data = build_statement(units=heating_units(heat_unit=MeasurementUnit.KWH))
        table = rows(block(statement_html(data), BLOCK_B))

        assert has_row(
            table, HEAT_COLUMN, f"{HEAT_KEY_KWH} (Nutzerwechsel: Gradtagszahlen)", "1.000 kWh"
        )
        assert not has_row(table, HEAT_COLUMN, HEAT_KEY_HKV_WITH_CHANGE, HEAT_TOTAL_CELL)

    def test_only_the_heating_gesamtbemessung_is_withheld_never_the_row(self) -> None:
        """**F1**, and the branch **slice 5 deliberately kept** (`docs/08` rule 3):
        a building that records no Maßeinheit still withholds the *figure* — a
        guessed unit on a Verbrauchsabrechnung is a defect that reaches a tenant,
        and a unit-free `1.000` invites the assumption (the sub-question the lead
        answered on 06.08.2026: withhold).

        It does **not** block the Umlageschlüssel, which is a name and is BGH
        formal minimum #2 in its own right. Dropping the row left 5.325,03 € —
        52 % of the umlagefähige Kosten — with no key named anywhere on a page
        headed *Bemessungsgrundlagen*."""
        data = unitless_statement()
        assert _heating(data).heat_consumption_unit is None
        text = block_text(statement_html(data), BLOCK_B)

        assert HEAT_COLUMN in text  # the row is on the page
        assert HEAT_KEY_WITH_CHANGE in text  # with the key that was applied
        assert WITHHELD_CELL in text  # and only the figure withheld
        assert "1.000" not in text  # Σ of the heat Bemessungen, withheld
        assert "145,83" not in text  # Bernd's heat Bemessung, withheld
        assert "103,75" not in text  # the landlord party's, withheld
        # No device is named either — the key cell may not name a
        # Heizkostenverteiler while the cell beside it says the unit is unknown.
        assert HEAT_KEY_HKV not in text
        assert HEAT_KEY_KWH not in text

    def test_the_withheld_cell_can_be_read_as_neither_zero_nor_an_oversight(self) -> None:
        """**F1**, `docs/08` → "The withheld cell is a sentence, not a blank".

        The cell sits in a column of denominators. Anything that parses as a
        figure — `0`, a bare `—`, an empty cell — tells the renter their own
        share is undefined. `nicht ausgewiesen` is an act of the landlord's in
        the register § 7 Abs. 3 CO2KostAufG uses; `ohne Maßeinheit` is the only
        reason that makes a figure unprintable rather than merely absent."""
        table = rows(block(statement_html(unitless_statement()), BLOCK_B))
        heat_row = next(row for row in table if row and row[0] == HEAT_COLUMN)

        assert heat_row == [HEAT_COLUMN, HEAT_KEY_WITH_CHANGE, WITHHELD_CELL]
        assert not re.search(r"\d", heat_row[2]), (
            f"the withheld cell {heat_row[2]!r} contains a digit and will be read as a figure"
        )
        assert heat_row[2] not in {"", "—", "–", "-", "0", "n/a", "k. A."}

    def test_the_withheld_column_is_absent_from_the_party_table(self) -> None:
        """The Gesamtbemessung and the per-party Bemessung are withheld together:
        a column of unit-less figures under a withheld total is the assumption
        the cell above it exists to prevent."""
        table = rows(block(statement_html(unitless_statement()), BLOCK_B))

        assert has_row(table, "Partei", "Fläche·Tage", "Verbrauch Warmwasser")
        assert has_row(table, "Wohnung A — Anna Beispiel", "18.250", "20 m³")
        assert has_row(table, "Gesamtbemessung", "36.500", "40 m³")

    def test_the_withholding_is_explained_directly_beneath_the_column_table(self) -> None:
        """The note carries two facts, and the second is not optional: without
        *"Der Verbrauchsanteil wurde gleichwohl nach den erfassten Werten
        verteilt"* a renter can read a withheld denominator as a withheld
        **method** and conclude the pot was never consumption-allocated — a § 7
        Abs. 1 HeizkostenV defect rather than a display gap.

        Adjacency is part of the rule (`docs/08`): the note sits between the two
        tables, not at the end of the block. Byte-identical to the copy that
        shipped in slice 4 — slice 5 removed the cause, not the branch."""
        rendered = block(statement_html(unitless_statement()), BLOCK_B)
        text = _text(rendered)

        assert WITHHELD_NOTE in text
        assert text.index(WITHHELD_CELL) < text.index(WITHHELD_NOTE) < text.index("Partei")
        # No claim about who owed the unit, and no right of inspection asserted:
        # both would be claims this document has not transcribed (docs/08).
        assert "Messdienst" not in text
        assert "Einsicht" not in text

    def test_the_heating_row_states_the_area_key_when_9a_abs_2_replaced_it(self) -> None:
        """**F1**, `docs/08` → "The `Verbrauch Heizung` row under § 9a Abs. 2".

        With `heat_fallback_to_area` the applied Umlageschlüssel of that column
        **is** Wohnfläche and its denominator is the 36.500 m²·Tage already
        printed above — the measurement-unit problem evaporated with the key it
        applied to, so nothing is withheld. The citation is § 9a Abs. 2, the rule
        that decided this share; § 7 Abs. 1 would send the renter to a paragraph
        that does not contain it."""
        data = heat_key_fallback_statement()
        heating = _heating(data)
        assert heating.heat_fallback_to_area is True
        table = rows(block(statement_html(data), BLOCK_B))

        assert has_row(table, HEAT_COLUMN, AREA_KEY_FALLBACK, "36.500 m²·Tage")
        text = block_text(statement_html(data), BLOCK_B)
        assert WITHHELD_CELL not in text
        assert HEAT_KEY not in text  # the key that was *not* applied
        assert "Gradtagszahlen" not in text
        # Slice 5, `docs/08` rule 4: the devices still declare `HKV_UNITS`, but
        # no consumption Bemessung was applied, so no unit is stated for one —
        # `None` means *not applied*, and a unit here would label a Bemessung
        # that determined no euro on the page.
        assert _heating(data).heat_consumption_unit is None
        assert HKV_UNIT not in text
        assert HEAT_KEY_HKV not in text

    def test_the_nutzerwechsel_parenthetical_renders_only_at_a_nutzerwechsel(self) -> None:
        """`(Nutzerwechsel: Gradtagszahlen)` names the method that split one
        unit's reading between two parties. With one party per unit it was never
        applied, and the row states the bare key — the rule the whole block is
        built on (`docs/08` → "states no fact the data does not carry")."""
        table = rows(block(statement_html(single_party_statement()), BLOCK_B))

        assert has_row(table, HEAT_COLUMN, HEAT_KEY_HKV, HEAT_TOTAL_CELL)
        assert not has_row(table, HEAT_COLUMN, HEAT_KEY_HKV_WITH_CHANGE, HEAT_TOTAL_CELL)

    def test_the_key_cell_carries_exactly_one_parenthetical(self) -> None:
        """`docs/08` → "Which spelling goes where": the long form is
        parenthesis-free *so that* the Nutzerwechsel parenthetical stays the only
        bracket in the cell. `Erfasster Wärmeverbrauch (Einheiten
        (Heizkostenverteiler)) (Nutzerwechsel: …)` is the failure this rule
        exists to prevent, and it is one word choice away."""
        table = rows(block(statement_html(build_demo_statement()), BLOCK_B))
        key_cell = next(row for row in table if row and row[0] == HEAT_COLUMN)[1]

        assert key_cell == HEAT_KEY_HKV_WITH_CHANGE
        assert key_cell.count("(") == 1 and key_cell.count(")") == 1

    def test_a_warm_water_key_fallback_withholds_the_consumption_bemessung(self) -> None:
        """§ 9a Abs. 2: the area key was applied to that column, so Block B states
        *that* key — and no m³ Bemessung may be shown, because none was applied."""
        data = ww_key_fallback_statement()
        heating = _heating(data)
        assert heating.ww_fallback_to_area is True
        assert heating.heat_fallback_to_area is False
        assert all(line.ww_consumption_weight_m3 is None for line in heating.lines)
        rendered = block(statement_html(data), BLOCK_B)
        table = rows(rendered)

        assert has_row(table, "Verbrauch Warmwasser", AREA_KEY_FALLBACK, "36.500 m²·Tage")
        assert "Erfasster Warmwasserverbrauch" not in _text(rendered)
        assert "m³" not in _text(rendered)
        # The heating column did *not* fall back, so it states its own key and
        # its own denominator. The two columns' absences and presences have
        # different causes and different copy, and must stay distinguishable.
        assert has_row(table, HEAT_COLUMN, HEAT_KEY_HKV_WITH_CHANGE, HEAT_TOTAL_CELL)

    def test_without_central_warm_water_no_warm_water_column_appears(self) -> None:
        """No warm-water column exists at all — that is not § 9a Abs. 2 and the
        page must not claim a fallback happened either."""
        data = no_warm_water_statement()
        assert all(line.ww_consumption_weight_m3 is None for line in _heating(data).lines)
        text = block_text(statement_html(data), BLOCK_B)

        assert "Verbrauch Warmwasser" not in text
        assert "Grundkosten Warmwasser" not in text
        assert "m³" not in text
        # The two columns that do exist, both stated (F1) — and the heating one
        # with its own denominator, which no warm-water branch may take away.
        assert "Grundkosten Heizung" in text
        assert HEAT_COLUMN in text and HEAT_TOTAL_CELL in text


# --- Block C -----------------------------------------------------------------


class TestBlockCNutzerwechsel:
    """`docs/08` item 4 → "Degree-day apportionment at a Nutzerwechsel", with the
    rendered form of 4a (segments named by party label, caveat without a stamp).

    Rendered only for a unit used by more than one party in the period.
    """

    def test_the_block_renders_for_a_unit_with_more_than_one_party(self) -> None:
        text = block_text(statement_html(build_demo_statement()), BLOCK_C)

        assert "Nutzerwechsel — Aufteilung des erfassten Verbrauchs" in text
        assert "Diese Einheit wurde im Abrechnungszeitraum von mehreren Parteien genutzt." in text
        assert (
            "Der für die Einheit erfasste Wärmeverbrauch wurde nach monatlichen "
            "Gradtagszahlen auf die Nutzungszeiträume aufgeteilt:"
        ) in text

    def test_no_block_renders_when_every_unit_has_one_party(self) -> None:
        """Nothing was apportioned, so there is nothing to disclose."""
        data = single_party_statement()
        units = {line.unit_id for line in _heating(data).lines}
        assert len(units) == len(_heating(data).lines), "fixture has one party per unit"

        assert not has_block(statement_html(data), BLOCK_C)

    def test_every_promille_is_printed_with_its_total(self) -> None:
        """`docs/08` item 4: **never a bare `585 ‰`.** The promille of a segment is
        a fraction of the *heating year*; over a partial billing period a unit's
        parties sum to less than 1.000 ‰ and a bare figure reads as wrong."""
        data = build_demo_statement()
        rendered = block_text(statement_html(data), BLOCK_C)
        pairs = _PROMILLE_PAIR.findall(rendered)

        assert pairs == [("583,3", "1.000"), ("416,7", "1.000")]
        assert rendered.count("‰") == 2 * len(pairs), (
            "a ‰ figure is printed without its per-unit total — docs/08 item 4"
        )

    def test_each_promille_line_names_its_party(self) -> None:
        """4a, correction 1: the segment is identified by the party label the
        money table already prints. `HeatingLine` carries no dates, and reading
        them off the engine *input* is the drift this spec forbids."""
        data = build_demo_statement()
        heating = _heating(data)
        text = block_text(statement_html(data), BLOCK_C)

        for line in heating.lines:
            if line.unit_id != "unit-b":
                continue
            label = PARTY_LABELS[(line.unit_id, line.tenancy_id)]
            # De-scaled with the renderer's own constant, not a literal 10: the
            # field is Zehntelpromille since K3 (`docs/03`), and a test that
            # formatted the raw integer would assert `5.833 ‰` — the very
            # de-scaling bug this suite exists to catch, frozen into a golden.
            own = line.degree_day_promille / TENTH_PROMILLE_PER_PROMILLE
            total = line.unit_degree_day_promille_total / TENTH_PROMILLE_PER_PROMILLE
            assert f"{label}: {_n(own)} ‰ von {_n(total)} ‰" in text

    def test_the_day_apportionment_is_printed_with_its_operands(self) -> None:
        """**F2**, `docs/08` → "The rounding is disclosed": the line is
        `12 m³ × (181 von 365 Tagen) = rd. 5,95 m³`.

        Three things at once. The **parentheses** make `181 von 365 Tagen` one
        operand — unparenthesised, `×` binds to `181` and the line reads
        `12 × 181 = 2.172`. **`rd.`** turns an identity that is false
        (5,9506849…) into a statement that is true, without printing a second
        figure for one quantity (the lead's ruling: reuse Block B's). And the
        unit's reading is still the **sum of its parties' Bemessungen**, never
        carried twice.

        *Its parties'* now means both carriers: since 14.08.2026 the vacancy
        segment's Bemessung lives on `owner_residual.origins` rather than on a
        `HeatingLine` (`docs/08` → "Die Eigentümerzeile" § 5). Summing
        `heating.lines` alone would make the printed reading 5,95 m³ instead of
        the 12 m³ the meter recorded — i.e. it would assert that the two
        segments are *not* halves of one reading, which is the one thing this
        line exists to say. Block C keeps the per-segment party label (§ 3), so
        the vacancy segment still reads `… → Vermieter` here even though its
        money row is gone."""
        data = build_demo_statement()
        heating = _heating(data)
        unit_b: list[tuple[str, HeatingLine | OwnerResidualOrigin]] = [
            *(
                (PARTY_LABELS[(line.unit_id, line.tenancy_id)], line)
                for line in heating.lines
                if line.unit_id == "unit-b"
            ),
            *(
                (PARTY_LABELS[(origin.unit_id, None)], origin)
                for origin in heating.owner_residual.origins
                if origin.unit_id == "unit-b"
            ),
        ]
        weights = [segment.ww_consumption_weight_m3 for _, segment in unit_b]
        assert all(w is not None for w in weights)
        reading = sum((w for w in weights if w is not None), Decimal(0))
        assert reading == Decimal(12), "the two segments must be halves of one reading"
        text = block_text(statement_html(data), BLOCK_C)

        assert "Grundkosten und Warmwasserverbrauch werden nach Tagen aufgeteilt:" in text
        for (label, segment), weight in zip(unit_b, weights, strict=True):
            assert weight is not None
            assert (
                f"{label}: {_n(reading)} m³ × ({_n(Decimal(segment.days))} von "
                f"{_n(Decimal(segment.unit_total_days))} Tagen) "
                f"= {ROUNDED} {_n(weight.quantize(Decimal('0.01')))} m³"
            ) in text

    def test_no_derivation_line_asserts_a_bare_equality(self) -> None:
        """**F2**, the defect itself: `= 5,95 m³` claims `12 × 181 ÷ 365` equals
        5,95, and it does not. Asserted as an absence, because the wrong form is
        one character away from the right one and only an absence catches a
        revert."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_C)

        for exact, printed in ((181, "5,95"), (184, "6,05")):
            assert f"({exact} von 365 Tagen) = {printed} m³" not in text
            assert f"× {exact} von 365 Tagen" not in text  # unparenthesised operand

    def test_the_convention_caveat_renders_where_the_promille_does(self) -> None:
        """Item 4, and the point of it: a disclosure that presents a convention as
        law invites a tenant to check a statute that does not contain the number.
        The caveat renders **wherever a ‰ figure renders**, not only in the footer.

        4a, correction 2: without a `Rechtsstand` stamp — item 6 leaves the raw
        form in exactly one place, and no degree-day stamp reaches the result.

        Citing **§ 9b Abs. 2** in this block is permitted (item 4, lead decision
        of 04.08.2026) and deliberately not asserted either way. What is asserted
        is the rule that decision came with: the paragraph must never end up
        beside `01/1981`, which dates the promille table and not the statute —
        the block carries no stamp at all, so the pair cannot arise."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_C)

        assert (
            "Gradtagszahlen sind eine anerkannte Konvention (VDI-Promilletabelle), "
            "keine gesetzliche Vorgabe."
        ) in text
        assert "Rechtsstand" not in text
        assert "1981" not in text
        assert "verify before production" not in text  # internal marker, never renders

    def test_no_promille_renders_when_the_area_key_replaced_the_readings(self) -> None:
        """4a, correction 3: with § 9a Abs. 2 the degree-day apportionment
        determined no euro on the page, so disclosing it would state a method that
        was not applied. The day apportionment still renders — the base Bemessung
        is day-weighted in every branch."""
        data = heat_key_fallback_statement()
        heating = _heating(data)
        assert heating.heat_fallback_to_area is True
        assert all(line.heat_consumption_weight is None for line in heating.lines)
        text = block_text(statement_html(data), BLOCK_C)

        assert "‰" not in text
        assert "Gradtagszahlen" not in text
        assert "nach Tagen aufgeteilt:" in text

    def test_a_third_party_is_disclosed_like_the_others(self) -> None:
        """The block is per unit, not per Nutzerwechsel: three parties, three
        lines, and the promille still sum to the printed per-unit total."""
        data = three_party_statement()
        text = block_text(statement_html(data), BLOCK_C)
        pairs = _PROMILLE_PAIR.findall(text)

        assert pairs == [("583,3", "1.000"), ("360", "1.000"), ("56,7", "1.000")]
        assert sum(_de(own) for own, _total in pairs) == _de(pairs[0][1])


# --- item 5's remainder, and placement ---------------------------------------


class TestCo2Berechnungsgrundlagen:
    """`docs/08` item 5 — the **remainder** only: § 7 Abs. 3 CO2KostAufG requires
    the Berechnungsgrundlagen of the Einstufung, i.e. the two inputs the intensity
    was computed from and the band it selected. Appended to the existing `.co2`
    block, same surface, no new block; everything else there already ships.

    The short-period wording of item 5 is **not** this slice (`docs/08` → 4a,
    "Not in this slice"): the demo period is a full year, factor exactly 1.
    """

    def test_the_grounds_of_the_einstufung_are_printed(self) -> None:
        data = build_demo_statement()
        co2 = _heating(data).co2
        assert co2 is not None
        assert co2.band_min_inclusive is not None and co2.band_max_exclusive is not None
        text = block_text(statement_html(data), BLOCK_CO2)

        assert (
            f"Berechnungsgrundlagen: CO₂-Emissionen des Gebäudes {_n(co2.total_co2_kg)} kg "
            f"· beheizte Fläche {_n(co2.heated_area_sqm)} m² "
            f"→ {format(co2.intensity_kg_per_sqm, '.1f').replace('.', ',')} kg CO₂/m²/Jahr "
            f"· Einstufung: {_n(co2.band_min_inclusive)} bis unter "
            f"{_n(co2.band_max_exclusive)} kg CO₂/m²/Jahr "
            f"· CO₂-Kosten {_eur(co2.co2_cost)}"
        ) in text

    def test_the_reader_can_add_the_split_up(self) -> None:
        """`104,72 + 157,08 = 261,80`: the amount being split is on the page,
        which is the only way the two shares are checkable."""
        data = build_demo_statement()
        co2 = _heating(data).co2
        assert co2 is not None
        text = block_text(statement_html(data), BLOCK_CO2)

        assert _eur(co2.co2_cost) in text
        assert _eur(co2.landlord_amount) in text
        assert _eur(co2.renter_amount) in text
        assert int(co2.landlord_amount) + int(co2.renter_amount) == int(co2.co2_cost)

    def test_the_einstufung_is_a_band_not_a_step_number(self) -> None:
        """`Co2Step` carries no ordinal, so a step *number* would be invented."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_CO2)

        assert "Einstufung: 37 bis unter 42" in text
        assert "Stufe 7" not in text


class TestCo2S3FixedOneDecimalDisplay:
    """Antwort 03 § 6: the rounded classified value is printed as `12,0`.

    Both render sites are pinned because the generic number formatter suppresses
    trailing zeros. These stay red after the engine is fixed until the statement
    uses one fixed-one-decimal CO₂-intensity formatter in both places.
    """

    def test_the_co2_summary_prints_exactly_12_0(self) -> None:
        data = build_statement(co2=Co2Input(total_co2_kg=Decimal(1196), co2_cost=cents(10_000)))
        text = block_text(statement_html(data), BLOCK_CO2)

        assert "Emissionsintensität 12,0 kg CO₂/m²/Jahr" in text
        assert "Vermieteranteil 10 %" in text

    def test_the_berechnungsgrundlagen_print_exactly_the_same_12_0(self) -> None:
        data = build_statement(co2=Co2Input(total_co2_kg=Decimal(1196), co2_cost=cents(10_000)))
        text = block_text(statement_html(data), BLOCK_CO2)

        assert "→ 12,0 kg CO₂/m²/Jahr · Einstufung: 12 bis unter 17" in text


class TestTheDemosCo2FixtureIsPlausibleOnItsFace:
    """`docs/06` → "Scenario 2 — the fuel, the emissions and the CO₂ price";
    statutory figures transcribed in `docs/03` → "Where `total_co2_kg` and
    `co2_cost` come from". Found by `statement-reviewer` (**I9**), promoted by
    the lead 05.08.2026.

    The demo printed `2.000 kg` and `300,00 €` — **150 €/t**, nearly three times
    the 2025 rate — and, against its own 20.000 kWh, **0,1 kg CO₂/kWh**, about
    half of Erdgas. Both are readable off the page in one step by anyone with a
    property background, which is who this document goes in front of.

    These assertions are deliberately **derived, not literal**: they recompute
    the implied price and the implied emission factor from the figures the page
    prints, so a future fixture edit that breaks the plausibility fails here
    rather than surviving as a plausible-looking pair of numbers.
    """

    # § 10 Abs. 2 BEHG: 55,00 € je Emissionszertifikat (= 1 t CO₂) für 2025.
    # § 3 Abs. 3 CO2KostAufG: der Preisbestandteil ist der Zertifikatspreis
    # "zuzüglich einer auf diesen Betrag anfallenden Umsatzsteuer" → 19 %.
    BEHG_2025_NET_PER_TONNE = Decimal("55.00")
    GROSS_PER_TONNE = Decimal("65.45")
    # Anlage 2 Teil 4 EBeV 2030: Erdgas 0,0558 t CO₂/GJ = 0,20088 kg CO₂/kWh
    # (heizwertbezogen, as § 3 Abs. 1 Nr. 3 CO2KostAufG requires).
    EBEV_ERDGAS_KG_PER_KWH = Decimal("0.20088")
    DEMO_ENERGY_KWH = Decimal(20_000)

    def test_the_co2_cost_implies_the_2025_behg_rate_including_ust(self) -> None:
        co2 = _heating(build_demo_statement()).co2
        assert co2 is not None

        tonnes = co2.total_co2_kg / Decimal(1000)
        per_tonne = (Decimal(int(co2.co2_cost)) / Decimal(100) / tonnes).quantize(Decimal("0.01"))

        assert per_tonne == self.GROSS_PER_TONNE, (
            f"{per_tonne} €/t is not the 2025 rate. § 10 Abs. 2 BEHG gives "
            f"{self.BEHG_2025_NET_PER_TONNE} € je Zertifikat and § 3 Abs. 3 CO2KostAufG adds USt "
            f"→ {self.GROSS_PER_TONNE} €/t (docs/03)"
        )
        assert (self.BEHG_2025_NET_PER_TONNE * Decimal("1.19")).quantize(
            Decimal("0.01")
        ) == self.GROSS_PER_TONNE

    def test_the_emission_factor_implied_by_the_demo_is_that_of_erdgas(self) -> None:
        """`docs/06` fixes the fuel: Erdgas. The demo's 0,200 kg CO₂/kWh is 0,44 %
        below the EBeV standard value, which is inside the spread of real
        Erdgas-H qualities and inside what a supplier states under § 3 Abs. 1
        Nr. 3 CO2KostAufG. Half of it — the old fixture — is no fuel at all."""
        co2 = _heating(build_demo_statement()).co2
        assert co2 is not None

        factor = co2.total_co2_kg / self.DEMO_ENERGY_KWH
        deviation = abs(factor - self.EBEV_ERDGAS_KG_PER_KWH) / self.EBEV_ERDGAS_KG_PER_KWH

        assert deviation < Decimal("0.01"), (
            f"{factor} kg CO₂/kWh is {deviation:.1%} off the EBeV 2030 Anlage 2 standard value "
            f"for Erdgas ({self.EBEV_ERDGAS_KG_PER_KWH} kg CO₂/kWh) — docs/03"
        )

    def test_the_page_prints_the_corrected_figures(self) -> None:
        """The literals, once, so a report can be checked against the page."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_CO2)

        assert "CO₂-Emissionen des Gebäudes 4.000 kg" in text
        assert "CO₂-Kosten 261,80 €" in text
        assert "40,0 kg CO₂/m²/Jahr" in text
        assert "Vermieteranteil 60 %" in text
        assert "2.000 kg" not in text and "300,00 €" not in text

    def test_the_intensity_is_not_a_boundary_case_of_its_band(self) -> None:
        """`docs/06`: the band moved 17–22 → 37–42 because the physics forced it
        (200 kWh/m²/a of any fossil fuel lands near 40 kg CO₂/m²/a). It has to
        stay an *unambiguous* golden, so the intensity sits clear of both bounds
        — and at one decimal place, so the demo does not depend on the
        unimplemented § 5 Abs. 1 S. 3 rounding (`docs/03`, `PLAN.md` row 4.5)."""
        co2 = _heating(build_demo_statement()).co2
        assert co2 is not None
        assert co2.band_min_inclusive is not None and co2.band_max_exclusive is not None

        intensity = co2.intensity_kg_per_sqm
        assert co2.band_min_inclusive + 1 < intensity < co2.band_max_exclusive - 1
        assert intensity == intensity.quantize(Decimal("0.1"))


class TestPlacement:
    """`docs/08` item 1: the blocks sit **directly beneath the money table**, in
    this order — A, B, C — and the existing CO₂ block and § 9a notes keep their
    position after them."""

    def test_the_blocks_render_in_the_specified_order(self) -> None:
        html = statement_html(build_demo_statement())
        heading = "<h2>Heiz- und Warmwasserkosten</h2>"
        assert heading in html, "fixture no longer renders the heating section"

        positions = [_position(html, name) for name in (BLOCK_A, BLOCK_B, BLOCK_C)]
        assert positions == sorted(positions), (
            "docs/08 order is Aufteilung → Bemessungsgrundlagen → Nutzerwechsel"
        )
        assert html.index(heading) < positions[0]
        assert positions[-1] < _position(html, BLOCK_CO2)

    def test_the_disclosure_sits_in_the_heating_section_only(self) -> None:
        """The Betriebskosten table keeps the `.key-label` solution; these blocks
        are the heating table's, because its four money columns do not share a
        denominator."""
        html = statement_html(build_demo_statement())
        nk_heading = html.index("<h2>Betriebskosten</h2>")
        heating_heading = html.index("<h2>Heiz- und Warmwasserkosten</h2>")

        for name in (BLOCK_A, BLOCK_B, BLOCK_C):
            position = _position(html, name)
            assert position > heating_heading > nk_heading


class TestOnlyTheCo2FixtureMovedTheAmounts:
    """Guard on the blast radius of the CO₂ re-base (`docs/06`).

    The CO₂-Vermieteranteil is deducted **before** the renter-facing split
    (§ 7 Abs. 1 CO2KostAufG), so correcting 300,00 € → 261,80 € and 20 % → 60 %
    moves every heating euro. Nothing else may move with it: no Bemessung, no ‰,
    no Gesamtkosten, and — the `CLAUDE.md` definition-of-done — not one cent of
    the canonical €1.200 garbage allocation, which shares this statement's
    building and is independent of heating by construction.
    """

    def test_the_worked_examples_party_totals_follow_the_new_billable_cost(self) -> None:
        heating = _heating(build_demo_statement())

        # Re-based by K3 (VDI 2067, `docs/03`): the degree-day split moves the two
        # unit-B parties against each other. 149.553 + 128.110 = 277.663 =
        # 149.326 + 128.337 — the pair re-splits, the pot does not move, and the
        # two unaffected units do not move at all.
        #
        # 128.337 is asserted off `owner_residual` since 14.08.2026: the landlord
        # segment is no longer a `HeatingLine` (`docs/08` → "Die Eigentümerzeile").
        # It is **cent-identical** to the line it replaced, which is the whole
        # point of that slice — the Eigentümer-Residuum re-labels a figure, it
        # does not compute a new one — so this guard on the CO₂ blast radius
        # holds unchanged, over the same four amounts.
        assert [int(line.total) for line in heating.lines] == [
            560_397,
            149_326,
            176_232,
        ]
        assert int(heating.owner_residual.total) == 128_337
        assert int(heating.total) == 1_030_000  # the invoice did not move
        assert int(heating.billable_cost) == 1_014_292

    def test_the_heating_footer_still_reconciles(self) -> None:
        html = _plain(statement_html(build_demo_statement()))

        assert "Gesamtkosten Heizung und Warmwasser (inkl. CO₂-Vermieteranteil)" in html
        assert "Summe der oben ausgewiesenen Anteile: 10.142,92 €" in html
        assert "Die Differenz von 157,08 €" in html

    def test_the_canonical_1200_garbage_allocation_is_byte_identical(self) -> None:
        """`CLAUDE.md` definition-of-done #3. The NK engine never sees a CO₂
        figure; this asserts that as text on the page, because the two sections
        share one building and one occupancy timeline."""
        html = _plain(statement_html(build_demo_statement()))

        for golden in ("1.200,00 €", "600,00 €", "178,52 €", "181,48 €", "240,00 €"):
            assert golden in html, f"the canonical €1.200 allocation moved: {golden} is gone"
        assert "Summe Betriebskosten (stimmt centgenau mit den Gesamtkosten überein)" in html

    def test_the_degree_day_ratio_is_the_table_and_nothing_else(self) -> None:
        """The ratio is a property of the Gradtagszahl table, not of the CO₂
        split — which is why it moves when, and only when, the table moves.

        It has now moved once: K3 (`docs/03`) adopts VDI 2067 Bl. 1, 12/1983,
        Tab. 22, and Jan–Jun goes 585,0 ‰ → 583,3 ‰, so 778,79 / 552,47 re-bases
        to 776,52 / 554,74. **The pot does not move** — 77.652 + 55.474 = 133.126,
        the same total as before — which is the check that this was a re-split and
        not a re-price."""
        heating = _heating(build_demo_statement())
        # 14.08.2026: unit B's Vermieter half is no longer a party row — it is
        # the Liegenschafts-Residuum. **Neither figure moves**: this building has
        # exactly one landlord party, so its amount already *was* the residual,
        # which is why `scripts/assert_statement_pdf.py`'s 776,52 / 554,74
        # goldens hold across the model change (`docs/03` § 9.2).
        mieter = int(
            next(line for line in heating.lines if line.unit_id == "unit-b").heating_consumption
        )
        vermieter = int(heating.owner_residual.heating_consumption)
        assert (mieter, vermieter) == (77_652, 55_474)
        assert mieter + vermieter == 133_126
        # Within the cent the pot-level rounding can move it — the ratio is the
        # invariant, the last cent belongs to the distribution primitive.
        assert abs(Decimal(mieter) - Decimal("0.5833") * (mieter + vermieter)) <= 1


class TestTheEigentuemerzeileRendersInAFullyLetBuilding:
    """`docs/08` → "Die Eigentümerzeile" § 1, the case the row exists for.

    Added 14.08.2026. Every other rendering fixture in this repo has a vacancy,
    so the branch that had *no* landlord row at all was never rendered — and
    that is precisely the building Berkay's § 1.3 Frage 1 is about:
    *"Auch bei 0,00 €, auch ohne Leerstand, auch ohne Eigennutzung."*

    `single_party_statement()` is fully let, one party per unit. Under the model
    it still has an Eigentümerzeile; under the current renderer it has none, so
    this class is **red on purpose**. Its sibling assertions live in
    `test_statement_owner_residual.py`, which runs against the demo (where the
    row carries a real amount); this one is the zero end of the same rule.
    """

    def test_the_row_renders_even_though_there_is_no_vacancy(self) -> None:
        data = single_party_statement()
        heating = _heating(data)
        assert all(line.tenancy_id is not None for line in heating.lines)
        assert heating.owner_residual.origins == ()  # nothing empty, nothing self-used

        text = _plain(statement_html(data))
        assert "Eigentümeranteil" in text, (
            "a fully let building renders no Eigentümerzeile — a suppressed zero "
            "row and an omitted row are indistinguishable on paper, and only one "
            "of them is honest (docs/08 § 1)"
        )

    def test_the_bemessung_column_stays_empty_rather_than_printing_a_zero(self) -> None:
        """§ 2: with no vacancy and no self-use there is no Fiktivbelegung, so
        the Bemessung is `None` — and `None` must render as *nothing*, never as
        `0`, which would imply an allocation base of zero rather than none."""
        owner = _heating(single_party_statement()).owner_residual
        assert owner.base_weight_sqm_days_x100 is None
        assert owner.heat_consumption_weight is None
        assert owner.ww_consumption_weight_m3 is None

    def test_the_money_table_still_reconciles_with_the_row_in_it(self) -> None:
        data = single_party_statement()
        heating = _heating(data)
        assert sum(int(line.total) for line in heating.lines) + int(
            heating.owner_residual.total
        ) == int(heating.billable_cost)
