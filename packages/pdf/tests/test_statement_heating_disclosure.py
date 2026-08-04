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
"""

import re
from collections.abc import Mapping
from decimal import Decimal
from html.parser import HTMLParser

from lokara_domain import AllocationKey, Cents, Occupancy, cents, format_eur, period
from lokara_heating_engine import (
    Co2Input,
    HeatingInput,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    WarmWaterInput,
    calculate_heating_statement,
)
from lokara_nk_engine import CostItem, NkInput, UnitBasis, calculate_nk_statement
from lokara_pdf import PartyKey, StatementData, format_number_de, rechtsstand_entry, statement_html
from lokara_pdf.demo import AS_OF, BILLING_PERIOD, PARTY_LABELS, build_demo_statement
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

# `docs/08` → the gap "the unit of the heating-consumption Bemessung": no
# Gesamtbemessung and no Bemessung column for Verbrauch Heizung until the
# measurement unit is carried. That is **slice 5** and must not be pulled forward.
WITHHELD_HEAT_COLUMN = "Verbrauch Heizung"

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
    """`5,95 m³` → `Decimal("5.95")`. Reads the page, not the engine."""
    match = re.match(r"-?[\d.]+(?:,\d+)?", figure.strip())
    assert match is not None, f"not a German figure: {figure!r}"
    return Decimal(match.group(0).replace(".", "").replace(",", "."))


def _heating(data: StatementData) -> HeatingResult:
    heating = data.heating_result
    assert heating is not None, "fixture lost its heating section"
    return heating


# --- fixtures ----------------------------------------------------------------
# The canonical building of `docs/03`/`docs/08`: A 50 m², B 30 m², C 20 m²;
# Bernd leaves B on 30.06.2025, B vacant Jul–Dec → a landlord party.

DEMO_UNITS = (
    HeatingUnit("unit-a", 5000, heat_consumption=Decimal(600), ww_consumption_m3=Decimal(20)),
    HeatingUnit("unit-b", 3000, heat_consumption=Decimal(250), ww_consumption_m3=Decimal(12)),
    HeatingUnit("unit-c", 2000, heat_consumption=Decimal(150), ww_consumption_m3=Decimal(8)),
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
    units: tuple[HeatingUnit, ...] = DEMO_UNITS,
    occupancies: tuple[Occupancy, ...] = DEMO_OCCUPANCIES,
    party_labels: Mapping[PartyKey, str] | None = None,
    total_cost: int = 1_030_000,
    total_energy_kwh: int = 20_000,
    warm_water: WarmWaterInput | None = MEASURED_40_M3,
    co2: Co2Input | None = CO2_2000_KG,
) -> StatementData:
    """The demo composition, parameterised — both real engines, rules resolved
    from the store for `AS_OF`, one NK cost so the page keeps both sections."""
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
    units = (
        DEMO_UNITS[0],
        HeatingUnit("unit-b", 3000, heat_consumption=Decimal(250), ww_consumption_m3=None),
        HeatingUnit("unit-c", 2000, heat_consumption=Decimal(150), ww_consumption_m3=None),
    )
    return build_statement(units=units, total_cost=1_000_000, co2=None)


def heat_key_fallback_statement() -> StatementData:
    """§ 9a Abs. 2 on the heating column only — the mirror image."""
    units = (
        DEMO_UNITS[0],
        HeatingUnit("unit-b", 3000, heat_consumption=None, ww_consumption_m3=Decimal(12)),
        HeatingUnit("unit-c", 2000, heat_consumption=None, ww_consumption_m3=Decimal(8)),
    )
    return build_statement(units=units, total_cost=1_000_000, co2=None)


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
        assert "60,00 €" in text
        assert "10.240,00 €" in text
        assert "2.560,00 €" in text and "7.680,00 €" in text
        assert "2.304,00 €" in text and "5.376,00 €" in text
        assert "768,00 €" in text and "1.792,00 €" in text

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
        assert (
            f"{_n(separation.area_fallback_kwh_per_sqm_year)} kWh je m² Wohnfläche und Jahr "
            f"× {_n(separation.heated_area_sqm)} m² "
            f"× {_n(Decimal(separation.period_days))} von "
            f"{_n(Decimal(separation.reference_year_days))} Tagen "
            f"= {_n(separation.q_ww_kwh)} kWh von {_n(separation.total_energy_kwh)} kWh"
        ) in text
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
        table = rows(block(statement_html(build_demo_statement()), BLOCK_B))

        assert has_row(table, "Spalte", "Umlageschlüssel", "Gesamtbemessung")
        assert has_row(table, "Grundkosten Heizung", "Wohnfläche (m²·Tage)", "36.500 m²·Tage")
        assert has_row(table, "Grundkosten Warmwasser", "Wohnfläche (m²·Tage)", "36.500 m²·Tage")
        assert has_row(table, "Verbrauch Warmwasser", "Erfasster Warmwasserverbrauch (m³)", "40 m³")

    def test_every_party_prints_its_bemessung_per_column(self) -> None:
        table = rows(block(statement_html(build_demo_statement()), BLOCK_B))

        assert has_row(table, "Partei", "Fläche·Tage", "Verbrauch Warmwasser")
        assert has_row(table, "Wohnung A — Anna Beispiel", "18.250", "20 m³")
        assert has_row(table, "Wohnung B — Bernd Muster (Auszug 30.06.2025)", "5.430", "5,95 m³")
        assert has_row(table, "Wohnung B — Leerstand ab 01.07.2025 → Vermieter", "5.520", "6,05 m³")
        assert has_row(table, "Wohnung C — Clara Vorlage", "7.300", "8 m³")
        assert has_row(table, "Gesamtbemessung", "36.500", "40 m³")

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

    def test_the_printed_bemessungen_sum_to_the_printed_gesamtbemessung(self) -> None:
        """The invariant of every allocation test, over rendered text: a document
        that is supposed to add up must add up as printed, not merely as computed
        (`docs/08` → Block B, and the same rule as the NK reference totals)."""
        data = build_demo_statement()
        table = rows(block(statement_html(data), BLOCK_B))
        labels = {PARTY_LABELS[(line.unit_id, line.tenancy_id)] for line in _heating(data).lines}

        party_rows = [row for row in table if row and row[0] in labels]
        assert len(party_rows) == len(_heating(data).lines), "one row per party"
        total_row = next(row for row in table if row and row[0] == "Gesamtbemessung")

        for column in (1, 2):
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
        happen to round exactly)."""
        data = three_party_statement()
        table = rows(block(statement_html(data), BLOCK_B))
        labels = {
            THREE_PARTY_LABELS[(line.unit_id, line.tenancy_id)] for line in _heating(data).lines
        }
        party_rows = [row for row in table if row and row[0] in labels]

        printed = [_de(row[2]) for row in party_rows]
        assert printed == [
            Decimal(20),
            Decimal("5.95"),
            Decimal("3.03"),  # +0,01: largest remainder, ties by party order
            Decimal("3.02"),
            Decimal(8),
        ]
        assert sum(printed) == Decimal(40)
        assert has_row(table, "Gesamtbemessung", "36.500", "40 m³")

    def test_the_heating_consumption_column_is_withheld(self) -> None:
        """`docs/08` gap: `HeatingUnit.heat_consumption` is kWh at a
        Wärmemengenzähler and dimensionless HKV-Einheiten at a Heizkostenverteiler,
        and nothing distinguishes them. **Slice 5**, not this one — a guessed unit
        on a Verbrauchsabrechnung is a defect that reaches a tenant, and a
        unit-free `1.000` invites the assumption."""
        text = block_text(statement_html(build_demo_statement()), BLOCK_B)

        assert WITHHELD_HEAT_COLUMN not in text
        assert "Erfasster Wärmeverbrauch" not in text
        assert "1.000" not in text  # Σ of the heat Bemessungen, withheld
        assert "146,25" not in text  # Bernd's heat Bemessung, withheld

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

        assert has_row(table, "Verbrauch Warmwasser", "Wohnfläche (m²·Tage)", "36.500 m²·Tage")
        assert "Erfasster Warmwasserverbrauch" not in _text(rendered)
        assert "m³" not in _text(rendered)

    def test_without_central_warm_water_no_warm_water_column_appears(self) -> None:
        """No warm-water column exists at all — that is not § 9a Abs. 2 and the
        page must not claim a fallback happened either."""
        data = no_warm_water_statement()
        assert all(line.ww_consumption_weight_m3 is None for line in _heating(data).lines)
        text = block_text(statement_html(data), BLOCK_B)

        assert "Verbrauch Warmwasser" not in text
        assert "Grundkosten Warmwasser" not in text
        assert "m³" not in text
        assert "Grundkosten Heizung" in text  # the column that does exist


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

        assert pairs == [("585", "1.000"), ("415", "1.000")]
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
            assert (
                f"{label}: {_n(line.degree_day_promille)} ‰ von "
                f"{_n(line.unit_degree_day_promille_total)} ‰"
            ) in text

    def test_the_day_apportionment_is_printed_with_its_operands(self) -> None:
        """Item 4: `12 m³ × 181 von 365 Tagen = 5,95 m³` — the derivation is the
        exact figure, the 2-decimal one is the readable figure, and the unit's
        reading is the sum of its parties' Bemessungen (never carried twice)."""
        data = build_demo_statement()
        heating = _heating(data)
        unit_b = [line for line in heating.lines if line.unit_id == "unit-b"]
        weights = [line.ww_consumption_weight_m3 for line in unit_b]
        assert all(w is not None for w in weights)
        reading = sum((w for w in weights if w is not None), Decimal(0))
        text = block_text(statement_html(data), BLOCK_C)

        assert "Grundkosten und Warmwasserverbrauch werden nach Tagen aufgeteilt:" in text
        for line, weight in zip(unit_b, weights, strict=True):
            assert weight is not None
            label = PARTY_LABELS[(line.unit_id, line.tenancy_id)]
            assert (
                f"{label}: {_n(reading)} m³ × {_n(Decimal(line.days))} von "
                f"{_n(Decimal(line.unit_total_days))} Tagen "
                f"= {_n(weight.quantize(Decimal('0.01')))} m³"
            ) in text

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

        assert pairs == [("585", "1.000"), ("365", "1.000"), ("50", "1.000")]
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
            f"→ {_n(co2.intensity_kg_per_sqm)} kg CO₂/m²/Jahr "
            f"· Einstufung: {_n(co2.band_min_inclusive)} bis unter "
            f"{_n(co2.band_max_exclusive)} kg CO₂/m²/Jahr "
            f"· CO₂-Kosten {_eur(co2.co2_cost)}"
        ) in text

    def test_the_reader_can_add_the_split_up(self) -> None:
        """`240,00 + 60,00 = 300,00`: the amount being split is on the page, which
        is the only way the two shares are checkable."""
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

        assert "Einstufung: 17 bis unter 22" in text
        assert "Stufe 3" not in text


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


class TestNothingThatAlreadyRendersMoves:
    """Guard: this slice adds disclosure and moves no amount. The party totals and
    the reconciliation `scripts/assert_statement_pdf.py` pins stay as they are."""

    def test_the_worked_examples_party_totals_are_unchanged(self) -> None:
        heating = _heating(build_demo_statement())

        assert [int(line.total) for line in heating.lines] == [
            565_760,
            150_984,
            129_336,
            177_920,
        ]
        assert int(heating.total) == 1_030_000

    def test_the_heating_footer_still_reconciles(self) -> None:
        html = _plain(statement_html(build_demo_statement()))

        assert "Gesamtkosten Heizung und Warmwasser (inkl. CO₂-Vermieteranteil)" in html
        assert "Summe der oben ausgewiesenen Anteile: 10.240,00 €" in html
