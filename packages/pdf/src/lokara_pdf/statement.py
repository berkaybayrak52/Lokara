"""The NK + heating/CO₂ statement template (M3 layout, first cut in Phase D).

The engines compute; this layer only formats their results. Every legal output
carries the ``Rechtsstand MM/JJJJ`` stamps of the rules that produced it and
the "tool, not advice" disclaimer (CLAUDE.md). German copy, docs/05 design
tokens, no ad-hoc colors.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from html import escape

from lokara_domain import AllocationKey, MeasurementUnit, cents, format_eur
from lokara_heating_engine import HeatingResult, Page01bStatementResult
from lokara_nk_engine import CostItem, NkResult, ShareLine

from .formatting import format_co2_intensity_de, format_number_de
from .heating_disclosure import (
    OWNER_LABEL,
    OWNER_RESIDUAL_SENTENCE,
    co2_grounds,
    heating_disclosure_html,
)
from .measurement_units import UNIT_SYMBOLS

# (unit_id, tenancy_id) as they appear on result lines; tenancy_id=None is the
# landlord side (vacancy/self-use) of that unit.
PartyKey = tuple[str | None, str | None]

_ALLOCATION_KEY_LABELS: dict[AllocationKey, str] = {
    AllocationKey.AREA: "Wohnfläche (m²·Tage)",
    AllocationKey.PERSONS: "Personenzahl (Personen·Tage)",
    AllocationKey.CONSUMPTION: "Verbrauch",
    AllocationKey.UNITS: "Einheiten (Einheiten·Tage)",
    AllocationKey.DIRECT: "Direktzuordnung",
    AllocationKey.MEA: "Miteigentumsanteile (MEA·Tage)",
}

# Engine weights are fixed-point (m² × 100, MEA × 10000); the statement shows
# the human figure the docs/03 table shows — 18,250 m²·Tage, not 1,825,000.
_WEIGHT_DISPLAY_DIVISORS: dict[AllocationKey, Decimal] = {
    AllocationKey.AREA: Decimal(100),
    AllocationKey.MEA: Decimal(10000),
}

# Unit of the reference total (Gesamtbemessung) per key — docs/08 table. Keys
# absent here are resolved in _reference_total_unit(): CONSUMPTION reads the
# Maßeinheit off the engine result, DIRECT depends on the target.
_REFERENCE_TOTAL_UNITS: dict[AllocationKey, str] = {
    AllocationKey.AREA: "m²·Tage",
    AllocationKey.PERSONS: "Personen·Tage",
    AllocationKey.UNITS: "Einheiten·Tage",
    AllocationKey.MEA: "MEA·Tage",
}

# "Tool, not advice" (CLAUDE.md) is a *positioning* claim about the product. The
# earlier wording — "Dieses Dokument wurde … erstellt" — warranted that THIS
# Abrechnung was produced in conformity with the law, which it cannot: BGH formal
# minimum #4 (Abzug der geleisteten Vorauszahlungen) is not rendered at all until
# the M6 payment ledger. The subject is Lokara; nothing in the sentence points at
# this artifact. docs/08 → "The disclaimer states what Lokara is, never that this
# Abrechnung is complete". Tier 2, footer, one line, no internal break.
DISCLAIMER = (
    "Lokara ist ein Werkzeug für die rechtskonforme Betriebs- und Heizkostenabrechnung, "
    "keine Rechts- oder Steuerberatung."
)


@dataclass(frozen=True)
class StatementData:
    """Everything the template needs, already computed and labeled.

    ``rechtsstaende`` is one entry per rule version used (deduped, display
    order), each naming the rule *and* carrying its date —
    ``§ 7 Abs. 1 HeizkostenV 03/1989``. The caller resolves the rules, so only
    the caller knows them; ``rechtsstand_entry`` composes an entry from a
    ``ResolvedRule``. A bare date discloses nothing (docs/08 item 6), so the
    footer prints the word ``Rechtsstand`` once and every date after it is named.
    """

    landlord_name: str
    building_label: str
    period_label: str
    nk_result: NkResult
    nk_costs: tuple[CostItem, ...]
    party_labels: Mapping[PartyKey, str]
    rechtsstaende: tuple[str, ...]
    heating_result: HeatingResult | None = None
    page01b_result: Page01bStatementResult | None = None
    heating_cost_label: str = field(default="Heiz- und Warmwasserkosten")


def _display_weight(key: AllocationKey, weight: Decimal) -> Decimal:
    """De-scale an engine weight to the human figure (docs/03).

    The single de-scaling site for both the per-party Bemessung and the
    Gesamtbemessung — two sites drift apart, and integer-comparing tests stay
    green while they do.
    """
    return weight / _WEIGHT_DISPLAY_DIVISORS.get(key, Decimal(1))


def _reference_total_unit(cost: CostItem, consumption_unit: MeasurementUnit | None) -> str | None:
    """Unit of this cost's Gesamtbemessung, or None if none is printed.

    docs/08: DIRECT → a tenancy has a denominator of 1 (noise, no row); DIRECT →
    a unit is day-split inside that unit and does have one, in Tage.

    CONSUMPTION takes the Maßeinheit the engine divided in, read off the result
    (docs/08 → "`MeasurementUnit` travels with the value"). Where the rows
    supplied none the engine resolves None and no denominator is printed at all:
    a guessed unit on a Verbrauchsabrechnung is a defect that reaches a tenant,
    and a unit-free figure in this column invites the renter to assume one.
    """
    if cost.key is AllocationKey.DIRECT:
        return None if cost.direct_tenancy_id is not None else "Tage"
    if cost.key is AllocationKey.CONSUMPTION:
        return None if consumption_unit is None else UNIT_SYMBOLS[consumption_unit]
    return _REFERENCE_TOTAL_UNITS.get(cost.key)


def _key_label(cost: CostItem, consumption_unit: MeasurementUnit | None) -> str:
    """The Umlageschlüssel, with the unit where the key has one (docs/08).

    A figure column whose unit appears only in its denominator is a column the
    renter has to reconstruct. The label names the **unit**, never a device:
    outside the heating column the Maßeinheit does not determine the device —
    m³ is a cold- or a hot-water meter — so a device name here would state a
    fact the data does not carry.
    """
    label = _ALLOCATION_KEY_LABELS[cost.key]
    if cost.key is AllocationKey.CONSUMPTION and consumption_unit is not None:
        return f"{label} ({UNIT_SYMBOLS[consumption_unit]})"
    return label


def _reference_total(
    cost: CostItem, lines: list[ShareLine], consumption_unit: MeasurementUnit | None
) -> str:
    """`· Gesamtbemessung: 36.500 m²·Tage` — the denominator the engine divided
    by, so the tenant can check their share (docs/08, BGH minimum #2/#3).

    The **sum** is de-scaled once; de-scaling per line and summing would
    reintroduce the rounding error the engine avoids (docs/08 → Rounding).

    Figure and unit are joined by a non-breaking space, as ``format_eur`` joins
    the amount and the euro sign.
    """
    unit = _reference_total_unit(cost, consumption_unit)
    if unit is None or not lines:
        return ""
    total = _display_weight(cost.key, sum((line.weight for line in lines), Decimal(0)))
    # <span class="ref-total"> only prevents the figure from being split off its
    # label when the cost header wraps; it inherits .key-label's tokens.
    return (
        ' · <span class="ref-total">Gesamtbemessung: '
        f"{escape(format_number_de(total))} {escape(unit)}</span>"
    )


def _party(labels: Mapping[PartyKey, str], unit_id: str | None, tenancy_id: str | None) -> str:
    """The label of one party row, or of one empty/self-used unit's segment.

    ``tenancy_id is None`` no longer names a *heating* party: since 14.08.2026
    the Eigentümeranteil is a residual line rather than a party (`docs/02`), so
    the heating money table renders it from ``owner_residual`` under
    ``OWNER_LABEL`` and never through this function. The branch is still live
    for two callers:

    * the **Betriebskosten** table, which keeps its per-unit landlord party
      until Seite 02 lands in `docs/09` (`docs/08` → "The one asymmetry this
      slice leaves");
    * **Block C**, the one per-unit block on the page, which keeps the
      per-segment landlord label because it decomposes a single unit's timeline
      (`docs/08` → "Die Eigentümerzeile" § 3).
    """
    label = labels.get((unit_id, tenancy_id))
    if label is not None:
        return label
    if tenancy_id is None:
        return "Leerstand/Eigennutzung → Vermieter"
    return f"{unit_id} / {tenancy_id}"


def _nk_section(data: StatementData) -> str:
    rows: list[str] = []
    # One field today, because `NkInput.consumptions` is one flat tuple shared by
    # every CONSUMPTION cost — "one key, one unit" is literally true (docs/08).
    consumption_unit = data.nk_result.consumption_unit
    for cost in data.nk_costs:
        lines = [line for line in data.nk_result.lines if line.cost_id == cost.cost_id]
        rows.append(
            f'<tr class="cost-row"><td colspan="3">{escape(cost.label)}'
            f'<span class="key-label">Umlageschlüssel: '
            f"{escape(_key_label(cost, consumption_unit))}"
            f"{_reference_total(cost, lines, consumption_unit)}</span></td>"
            f'<td class="num">{escape(format_eur(cost.amount))}</td></tr>'
        )
        for line in lines:
            party = _party(data.party_labels, line.unit_id, line.tenancy_id)
            rows.append(
                "<tr>"
                f'<td class="indent">{escape(party)}</td>'
                f'<td class="num">'
                f"{escape(format_number_de(_display_weight(cost.key, line.weight)))}</td>"
                f"<td></td>"
                f'<td class="num">{escape(format_eur(line.amount))}</td>'
                "</tr>"
            )
    total = format_eur(data.nk_result.total)
    return f"""
  <h2>Betriebskosten</h2>
  <table>
    <thead>
      <tr><th>Kostenart / Partei</th><th class="num">Bemessung</th><th></th>
      <th class="num">Anteil</th></tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
    <tfoot>
      <tr><td colspan="3">Summe Betriebskosten (stimmt centgenau mit den
      Gesamtkosten überein)</td><td class="num">{escape(total)}</td></tr>
    </tfoot>
  </table>"""


def _heating_section(data: StatementData) -> str:
    heating = data.heating_result
    if heating is None:
        # A confirmed Messdienstleister statement has party totals but no
        # §§ 7/8/9 column split, so it gets its own table rather than an empty
        # five-column one. `heating_result is None` alone still means "nothing
        # to print" — the MDL table only appears when the values are there.
        return _mdl_section(data) + _page01b_section(data.page01b_result)
    rows = []
    # Resolved once and handed to the disclosure blocks: the same label names a
    # party in the money table, in Block B and in Block C, so a reader can follow
    # one row across all three.
    party_labels = tuple(
        _party(data.party_labels, line.unit_id, line.tenancy_id) for line in heating.lines
    )
    # Block C decomposes one unit's timeline, so its vacancy segment keeps the
    # per-unit label the money table no longer prints (`docs/08` § 3).
    origin_labels = tuple(
        _party(data.party_labels, origin.unit_id, None) for origin in heating.owner_residual.origins
    )
    for line, party in zip(heating.lines, party_labels, strict=True):
        rows.append(
            "<tr>"
            f"<td>{escape(party)}</td>"
            f'<td class="num">{escape(format_eur(line.heating_base))}</td>'
            f'<td class="num">{escape(format_eur(line.heating_consumption))}</td>'
            f'<td class="num">{escape(format_eur(line.ww_base))}</td>'
            f'<td class="num">{escape(format_eur(line.ww_consumption))}</td>'
            f'<td class="num">{escape(format_eur(line.total))}</td>'
            "</tr>"
        )
    # The Eigentümerzeile, last and unconditional — `docs/08` → "Die
    # Eigentümerzeile" §§ 1 and 3. One row across all four blocks, rendered even
    # at 0,00 € and even where nothing is vacant: a suppressed zero row and an
    # omitted row are indistinguishable on paper. It is the reconciling line, so
    # it comes after every Mietverhältnis — the reader adds the rows above and
    # the last one closes the column. **No Bemessung cell and no quota**: this
    # table's first column is a label, and § 2 forbids a percentage on this row
    # in any column, by shape as well as by rule (`OwnerResidual` has no
    # percentage field to print).
    owner = heating.owner_residual
    rows.append(
        "<tr>"
        f"<td>{escape(OWNER_LABEL)}</td>"
        f'<td class="num">{escape(format_eur(owner.heating_base))}</td>'
        f'<td class="num">{escape(format_eur(owner.heating_consumption))}</td>'
        f'<td class="num">{escape(format_eur(owner.ww_base))}</td>'
        f'<td class="num">{escape(format_eur(owner.ww_consumption))}</td>'
        f'<td class="num">{escape(format_eur(owner.total))}</td>'
        "</tr>"
    )

    co2_block = ""
    if heating.co2 is not None:
        co2 = heating.co2
        # § 7 Abs. 3 CO2KostAufG wants the Einstufung *and* its grounds. The
        # grounds line is appended to this block rather than given a surface of
        # its own — same disclosure, one place to read it (docs/08 item 5).
        co2_block = f"""
  <div class="co2">
    <strong>CO₂-Kostenaufteilung (CO2KostAufG, {escape(co2.rechtsstand)}):</strong>
    Emissionsintensität {escape(format_co2_intensity_de(co2.intensity_kg_per_sqm))} kg CO₂/m²/Jahr
    → Vermieteranteil {co2.landlord_share_percent} %
    ({escape(format_eur(co2.landlord_amount))}, vor der Umlage abgezogen);
    Mieteranteil {escape(format_eur(co2.renter_amount))}.
    {co2_grounds(co2)}
  </div>"""

    notes = []
    if heating.estimated_unit_ids:
        estimated = ", ".join(escape(u) for u in heating.estimated_unit_ids)
        notes.append(
            f"<p class='note'>Fehlende Ablesungen wurden gemäß § 9a HeizkostenV "
            f"geschätzt (Einheiten: {estimated}).</p>"
        )
    if heating.consumption_fallback_to_area:
        notes.append(
            "<p class='note'>Mehr als 25 % der Fläche ohne Ablesung — der "
            "Verbrauchsanteil wurde nach Wohnfläche umgelegt (§ 9a Abs. 2 HeizkostenV).</p>"
        )

    # The footer figure is the Gesamtkosten — *not* the sum of the column above
    # it: the CO₂-Vermieteranteil is deducted before the renter-facing split
    # (§ 7 Abs. 1 CO2KostAufG) and is not a row in this table, so the party
    # shares add up to less. docs/08 → "Heating table footer". One code path for
    # both branches: without a CO₂ split the two figures are equal by
    # construction, and printing them still beats asserting the equality in
    # words — the reader adds the printed numbers, the document claims nothing.
    # Fixed copy, deliberately not derived from ``heating_cost_label`` (that
    # field spells "Heiz- und Warmwasserkosten" → "Gesamtkosten Heiz- und
    # Warmwasserkosten").
    footer_label = "Gesamtkosten Heizung und Warmwasser"
    # Every row printed above, the Eigentümerzeile included: the sentence names
    # the sum of what is actually there, and leaving the residual out of it would
    # restate the very defect this footer exists to fix.
    share_sum = cents(sum(int(line.total) for line in heating.lines) + int(owner.total))
    reconciliation = f"Summe der oben ausgewiesenen Anteile: {escape(format_eur(share_sum))}."
    if heating.co2 is not None:
        footer_label += " (inkl. CO₂-Vermieteranteil)"
        reconciliation += (
            f" Die Differenz von {escape(format_eur(heating.co2.landlord_amount))} "
            "ist der CO₂-Vermieteranteil; er wird vor der Umlage abgezogen "
            "(§ 7 Abs. 1 CO2KostAufG)."
        )
    # Required copy wherever the row renders (`docs/08` § 4). It sits in the
    # footer's second line — the carrier that already holds this table's
    # reconciliation prose — so the sentence stands directly under the row it
    # explains, and there is exactly one of it on the page.
    reconciliation += f" {escape(OWNER_RESIDUAL_SENTENCE)}"

    total = format_eur(heating.total)
    return f"""
  <h2>{escape(data.heating_cost_label)}</h2>
  <table>
    <thead>
      <tr><th>Partei</th><th class="num">Grundkosten<br>Heizung</th>
      <th class="num">Verbrauch<br>Heizung</th><th class="num">Grundkosten<br>Warmwasser</th>
      <th class="num">Verbrauch<br>Warmwasser</th><th class="num">Summe</th></tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
    <tfoot>
      <tr><td colspan="5">{footer_label}<span class="foot-note">{reconciliation}</span></td>
      <td class="num">{escape(total)}</td></tr>
    </tfoot>
  </table>
  {heating_disclosure_html(heating, party_labels, origin_labels)}
  {co2_block}
  {"".join(notes)}
  {_page01b_section(data.page01b_result)}"""


def _party_by_tenancy(labels: Mapping[PartyKey, str], tenancy_id: str) -> str:
    """The label for a tenancy whose unit the caller does not know.

    A confirmed MDL statement names parties by tenancy and says nothing about
    units, so the unit half of the `PartyKey` has to be recovered rather than
    assumed. Falls back to the raw id: an unlabelled row is a visible defect,
    while a silently dropped one is not.
    """
    for (_, key_tenancy), label in labels.items():
        if key_tenancy == tenancy_id:
            return label
    return tenancy_id


def _mdl_section(data: StatementData) -> str:
    """Party totals as the Messdienstleister document states them.

    Four columns short of the self-billing table on purpose. `docs/03` H7:
    "validate and pass through; never recompute MDL amounts" — the document
    discloses one amount per party, so printing Grundkosten/Verbrauch columns
    would mean Lokara invented a split that nothing in the source supports.
    The sentence under the table says so, because a reader comparing this page
    with a self-billed one is owed the reason the columns are missing.

    The Eigentümer row is printed unconditionally, at `0,00 €` too — the same
    rule as every other statement here (`docs/08` "Die Eigentümerzeile").
    """
    page = data.page01b_result
    if page is None or page.values is None or page.values.path not in ("MDL_NET", "MDL_GROSS"):
        return ""
    values = page.values
    rows = "".join(
        "<tr>"
        f"<td>{escape(_party_by_tenancy(data.party_labels, tenancy_id))}</td>"
        f'<td class="num">{escape(format_eur(total))}</td>'
        "</tr>"
        for tenancy_id, total in zip(values.renter_ids, values.renter_totals, strict=True)
    )
    rows += (
        "<tr>"
        f"<td>{escape(OWNER_LABEL)}</td>"
        f'<td class="num">{escape(format_eur(values.owner_total))}</td>'
        "</tr>"
    )
    branch_label = (
        "Nettoabrechnung — der Vermieteranteil nach CO2KostAufG ist bereits abgezogen."
        if values.path == "MDL_NET"
        else "Bruttoabrechnung — die Positionen wurden nach Abzug des Vermieteranteils skaliert."
    )
    return f"""
  <h2>{escape(data.heating_cost_label)}</h2>
  <table>
    <thead>
      <tr><th>Partei</th><th class="num">Summe</th></tr>
    </thead>
    <tbody>{rows}</tbody>
    <tfoot>
      <tr><td>Bestätigte Gesamtsumme</td>
      <td class="num">{escape(format_eur(values.source_total))}</td></tr>
    </tfoot>
  </table>
  <p class="note">Bestätigte Abrechnung des Messdienstleisters. Die Beträge wurden geprüft und
  unverändert übernommen; eine Aufteilung in Grund- und Verbrauchskosten weist das Dokument nicht
  aus und wird hier nicht nachgerechnet. {escape(branch_label)}</p>"""


def _page01b_section(page: Page01bStatementResult | None) -> str:
    if page is None:
        return ""
    severity_labels = {"NOTICE": "Hinweis", "WARNING": "Warnung", "BLOCKER": "Blockiert"}
    allocation_labels = {
        "PARTY": "Mietverhältnis",
        "OWNER": "Eigentümer",
        "ANNUAL_UNSEGMENTED": "Jahreswert",
    }
    findings = "".join(
        f'<p class="note"><strong>{severity_labels[finding.severity]}:</strong> '
        f"{escape(finding.message_de)}</p>"
        for finding in page.findings
    )
    evidence_rows = "".join(
        "<tr>"
        f"<td>{escape(line.device_id)} · {escape(line.room)}</td>"
        f"<td>{allocation_labels[line.allocation_kind]}</td>"
        f'<td class="num">{escape(format_number_de(line.valuation_factor))}</td>'
        f'<td class="num">{escape(format_number_de(line.units))}</td>'
        "</tr>"
        for line in page.device_evidence
    )
    evidence = (
        "<h3>Geräte- und Ableseprotokoll</h3>"
        "<table><thead><tr><th>Gerät / Raum</th><th>Zuordnung</th>"
        '<th class="num">Faktor</th><th class="num">Einheiten</th></tr></thead>'
        f"<tbody>{evidence_rows}</tbody></table>"
        if evidence_rows
        else ""
    )
    provenance = (
        "<h3>Herkunft der Angaben</h3><ul>"
        + "".join(
            f"<li><strong>{escape(entry.source_ref)}:</strong> {escape(entry.detail_de)}</li>"
            for entry in page.provenance
        )
        + "</ul>"
        if page.provenance
        else ""
    )
    risks = "".join(
        '<div class="co2"><strong>'
        f"{escape(format_number_de(risk.percent))}-%-Risiko:</strong> "
        f"{escape(risk.message_de)} Einzelbeträge: "
        f"{escape(' · '.join(format_eur(amount) for amount in risk.amounts))}."
        "</div>"
        for risk in page.risks
    )
    annual = ""
    if page.annual_comparison is not None:
        comparison = page.annual_comparison
        if comparison.state == "READY":
            label = "Heizverbrauch mit bestätigten DWD-Klimafaktoren."
        elif comparison.state == "RAW_FALLBACK":
            label = "Heizverbrauch unbereinigt; DWD-Klimafaktor fehlt."
        else:
            label = "Kein Vorjahreswert vorhanden."
        annual = (
            "<h3>Verbrauchsvergleich zum Vorjahr</h3>"
            f'<p class="note">{escape(comparison.note_de or label)}</p>'
        )
    return (
        '<div class="page01b-evidence">'
        "<h2>Prüf- und Herkunftsangaben</h2>"
        f"{findings}{evidence}{provenance}{risks}{annual}</div>"
    )


def _party_total_section(data: StatementData) -> str:
    """`Anteile je Partei` — the one figure about themselves each party is owed.

    docs/08 → "`Ihr Anteil gesamt` — the per-party total, and why it is never a
    Saldo". Nothing is calculated here: ``Anteil gesamt = Betriebskosten-Anteil +
    Heizungs-Anteil``, both addends already computed, already rounded by the
    engines and already printed above. Integer cents are summed and formatted
    once; formatted strings are never added.

    **Not a Saldo, and no word that implies one.** BGH minimum #4 is
    *Vorauszahlungen minus Anteil = Nachzahlung oder Guthaben*; this document renders
    only the middle term until the M6 payment ledger, so the label is `Anteil` —
    what the figure is — and the note below the table names the quantity that is
    missing, in § 556 Abs. 3 BGB's own word.

    **No second person.** `Ihr Anteil gesamt` is the Mieter-Einzelabrechnung's
    form, where the document has one addressee. This render is the
    Vermieter-Gesamtübersicht: several parties, no addressee block, and one of
    the parties is the landlord reading it.

    **One code path, no branch on the heating section.** Without heating that
    column is simply absent from ``columns`` and `Anteil gesamt` equals the
    Betriebskosten column by construction — printed, rather than asserted in
    words. A party's total across cost types is not on the page even then.
    """
    heating = data.heating_result
    # (column header, {party: cents}) in the order the reader met the columns.
    # The headers name the sections the figures come from — a summary column that
    # renames its source section makes the reader hunt for it. Summed *across*
    # cost items, so a second Betriebskostenart lands in the same row.
    #
    # The landlord side is kept out of the per-party mapping and accumulated in
    # `owner_figures` instead: `docs/08` → "Die Eigentümerzeile" § 3a gives this
    # block **one** `Eigentümeranteil` row, not one per vacant unit and not one
    # per engine. Its Betriebskosten figure is the sum of `nk-engine`'s per-unit
    # landlord parties (which still exist until Seite 02 lands in `docs/09`), its
    # heating figure is the Liegenschafts-Residuum. That is a **display**
    # aggregation and asserts nothing about how either was computed — the
    # Betriebskosten table above still itemises its part per unit, and no copy
    # here calls the NK part a residual.
    nk_shares: dict[PartyKey, int] = {}
    owner_figures: list[int] = [0]
    for nk_line in data.nk_result.lines:
        if nk_line.tenancy_id is None:
            owner_figures[0] += int(nk_line.amount)
            continue
        nk_key = (nk_line.unit_id, nk_line.tenancy_id)
        nk_shares[nk_key] = nk_shares.get(nk_key, 0) + int(nk_line.amount)
    columns: list[tuple[str, dict[PartyKey, int]]] = [("Betriebskosten", nk_shares)]
    if heating is not None:
        heat_shares: dict[PartyKey, int] = {}
        for heat_line in heating.lines:
            heat_key = (heat_line.unit_id, heat_line.tenancy_id)
            heat_shares[heat_key] = heat_shares.get(heat_key, 0) + int(heat_line.total)
        columns.append((data.heating_cost_label, heat_shares))
        owner_figures.append(int(heating.owner_residual.total))

    # Row order: first appearance over the money tables, in their own order. A
    # reader reads down two tables and down this one. The Eigentümer row is
    # appended last regardless — it is the reconciling line, not a party.
    parties: list[PartyKey] = []
    for _, amounts in columns:
        for party_key in amounts:
            if party_key not in parties:
                parties.append(party_key)

    def _cells(figures: list[int]) -> str:
        return "".join(
            f'<td class="num">{escape(format_eur(cents(figure)))}</td>'
            for figure in [*figures, sum(figures)]
        )

    rows: list[str] = []
    for party_key in parties:
        # Every party gets a row under the same header: the rows are the addends
        # of the Σ row, and a blank or a dash in a money column reads as zero.
        party = _party(data.party_labels, party_key[0], party_key[1])
        figures = [amounts.get(party_key, 0) for _, amounts in columns]
        rows.append(f"<tr><td>{escape(party)}</td>{_cells(figures)}</tr>")
    # …and the owner's one row, last and unconditional, for the same reason the
    # money table prints it at 0,00 €: omitting it makes the Σ row false.
    rows.append(f"<tr><td>{escape(OWNER_LABEL)}</td>{_cells(owner_figures)}</tr>")

    headers = "".join(f'<th class="num">{escape(header)}</th>' for header, _ in columns)
    sums = [
        sum(amounts.values()) + owner
        for (_, amounts), owner in zip(columns, owner_figures, strict=True)
    ]
    # `Summe` is licensed here, unlike in the heating tfoot: the rows above this
    # one really are its addends. The heating column therefore sums to the party
    # shares, not to heating.total — the difference is the CO₂-Vermieteranteil,
    # deducted before the renter-facing split and carried by no party.
    return f"""
  <div class="party-total">
    <h3 class="disclosure-title">Anteile je Partei</h3>
    <table>
      <thead>
        <tr><th>Partei</th>{headers}<th class="num">Anteil gesamt</th></tr>
      </thead>
      <tbody>
        {"".join(rows)}
      </tbody>
      <tfoot>
        <tr><td>Summe der Anteile</td>{_cells(sums)}</tr>
      </tfoot>
    </table>
    <p class="advance-note">Der Anteil gesamt ist die Summe der in derselben Zeile
    ausgewiesenen Anteile; geleistete Vorauszahlungen sind darin nicht berücksichtigt.</p>
  </div>"""


def statement_html(data: StatementData) -> str:
    rechtsstaende = " · ".join(escape(r) for r in data.rechtsstaende)
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<!-- Becomes the PDF's /Title. Chromium takes it from <title>; it is NOT produced
     by page.pdf(tagged=True), which only supplies /StructTreeRoot, /MarkInfo and
     /Lang. An untitled PDF is announced by its filename in a screen reader and in
     every document list, so the three parts a reader needs to tell two statements
     apart — what it is, which building, which period — belong here. Same three
     facts as the <h1> and the meta line below it. -->
<title>Betriebs- und Heizkostenabrechnung — {escape(data.building_label)} \
· Abrechnungszeitraum {escape(data.period_label)}</title>
<style>
  /* docs/05 design tokens — no ad-hoc colors */
  :root {{
    --color-ink: #18212a;
    --color-green: #1a6558;
    --color-forest: #123f37;
    --color-mint: #e7efeb;
    --color-slate: #5c6a6b;
    --color-paper: #fbfbfa;
  }}
  body {{
    font-family: 'Manrope', 'Helvetica Neue', Arial, sans-serif;
    font-variant-ligatures: none;
    font-feature-settings: "liga" 0, "clig" 0;
    color: var(--color-ink);
    background: var(--color-paper);
    margin: 0;
    font-size: 10pt;
  }}
  h1, h2, h3 {{
    font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 700;
  }}
  h1 {{ font-size: 18pt; margin: 0 0 2mm; }}
  h2 {{ font-size: 12pt; margin: 8mm 0 3mm; color: var(--color-forest); }}
  .band {{ height: 3mm; background: var(--color-green); margin-bottom: 8mm; }}
  .meta {{ color: var(--color-slate); margin: 0 0 6mm; line-height: 1.5; }}
  table {{ width: 100%; border-collapse: collapse; }}
  /* Pagination (docs/08 → 4b): break at the seams, never inside a statement.
     `break-inside: avoid` belongs on the SMALLEST element that is one
     indivisible claim and is wrong on every container above it. A row is one
     claim — a party's label and their figure; split across a sheet, a reader
     gets a figure with no name or a name with no figure. */
  tr {{ break-inside: avoid; }}
  /* A column header separated from its first row leaves a page of unlabelled
     numbers. In the disclosure block the FIRST table is also what gives the
     second's columns their meaning. */
  thead {{ break-after: avoid; }}
  th {{
    background: var(--color-ink); color: var(--color-paper);
    font-weight: 600; text-align: left; padding: 2mm 2.5mm; font-size: 9pt;
  }}
  td {{ padding: 1.8mm 2.5mm; border-bottom: 0.5pt solid var(--color-mint); }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.indent {{ padding-left: 7mm; }}
  tr.cost-row td {{ background: var(--color-mint); font-weight: 600; }}
  /* Tier 1 (docs/05, docs/08): carries BGH minimum #2 and the denominator #3
     rests on. No font-size — it inherits body copy, so `legal-t1-size` holds
     even if body copy moves. Forest Deep on the cost row's Mint is 10,01:1
     (>= 7:1, SC 1.4.6); weight 400 against the row's 600 keeps the label
     secondary without buying that quietness with contrast.
     Comments here render into the document's <style>; keep domain vocabulary
     out of them so text-occurrence gates count the page, not the stylesheet. */
  .key-label {{ font-weight: 400; color: var(--color-forest); margin-left: 3mm; }}
  /* The reference total stays one unbroken phrase when the cost header wraps. */
  .ref-total {{ white-space: nowrap; }}
  tfoot td {{
    font-weight: 700; border-top: 1pt solid var(--color-ink); border-bottom: none;
    /* Keeps the amount on the label's line when the cell has a second line. */
    vertical-align: top;
  }}
  /* Second line of a footer cell: the reconciliation sentence. Tier 1 — it
     reconciles the total a reader adds up. Inherits body copy (no font-size);
     Forest Deep on Paper is 11,32:1 (>= 7:1, SC 1.4.6). Quieter than the footer
     label through weight, not through size or ink. */
  tfoot .foot-note {{
    display: block; font-weight: 400; color: var(--color-forest);
    line-height: 1.4; margin-top: 1.2mm;
  }}
  .co2 {{
    background: var(--color-mint); border-radius: 8px; padding: 4mm;
    margin-top: 4mm; line-height: 1.5;
  }}
  /* Estimation / fallback disclosure. Tier 1: it changes how the printed
     allocation key must be read, so it inherits body copy and takes Forest Deep
     on Paper (11,32:1). line-height 1.5 is the hygiene both tiers owe (>= 1,4);
     it is running prose and is now set at body size. */
  .note {{ color: var(--color-forest); line-height: 1.5; }}
  .page01b-evidence {{
    color: var(--color-forest); line-height: 1.45; margin-top: 4mm;
    padding-top: 3mm; border-top: 0.5pt solid var(--color-mint);
    orphans: 2; widows: 2;
  }}
  .page01b-evidence h2 {{ margin-top: 0; }}
  .page01b-evidence h3 {{ font-size: 10.5pt; margin: 2.5mm 0 1.5mm; break-after: avoid; }}
  .page01b-evidence td {{ padding: 1.1mm 2.5mm; }}
  .page01b-evidence p {{ margin: 1.5mm 0; }}
  .page01b-evidence ul {{ margin: 0; padding-left: 5mm; }}
  /* The three heating-disclosure carriers. All tier 1: no font-size, so each
     inherits body copy, and Forest Deep on Paper is 11,32:1 (>= 7:1, SC 1.4.6).
     They sit on Paper rather than on a tinted panel — three stacked slabs under
     the money table would be ornament, not clarity — and they recede below it
     through weight and a hairline rule, never through a lighter ink. Declared
     one selector each, because a grouped rule is not addressable per carrier.
     Keep every comment in this stylesheet English: it ships inside the document
     and the text-occurrence gates count the whole file.
     All three GROW with the number of parties, so none of them may refuse to
     break (docs/08 → 4b): a block that cannot split cannot be laid out beyond
     one sheet, and long before that it strands the page above it and lands the
     justification on a different sheet from the figures it justifies. Splitting
     such a block is normal; stranding it is the defect. `orphans`/`widows` keep
     a lone line of running prose off a sheet on its own. */
  .cost-split {{
    color: var(--color-forest); line-height: 1.5; margin-top: 6mm;
    padding-top: 4mm; border-top: 0.5pt solid var(--color-mint);
    orphans: 2; widows: 2;
  }}
  .basis-table {{
    color: var(--color-forest); line-height: 1.5; margin-top: 6mm;
    padding-top: 4mm; border-top: 0.5pt solid var(--color-mint);
    orphans: 2; widows: 2;
  }}
  .party-change {{
    color: var(--color-forest); line-height: 1.5; margin-top: 6mm;
    padding-top: 4mm; border-top: 0.5pt solid var(--color-mint);
    orphans: 2; widows: 2;
  }}
  /* A heading alone at the foot of a sheet is the same defect at its smallest
     scale, and the cheapest one to prevent. */
  .disclosure-title {{
    font-size: 10.5pt; font-weight: 600; margin: 0 0 2.5mm; break-after: avoid;
  }}
  .cost-split p, .party-change p {{ margin: 0 0 1.5mm; }}
  /* Which rule was applied, then what the rule permits: the second is quieter
     by weight alone, so both stay at the tier-1 pair. */
  .cost-split .rule-line {{ font-weight: 600; margin-top: 3.5mm; }}
  .cost-split .rule-bound {{ font-weight: 400; }}
  .cost-split .formula, .cost-split .pot-figures, .apportionment li {{
    font-variant-numeric: tabular-nums;
  }}
  .cost-split td {{ border-bottom: none; padding: 0.9mm 0; }}
  .cost-split .split-sum td {{
    border-top: 0.5pt solid var(--color-forest); font-weight: 600;
  }}
  .cost-split .pots {{ margin-top: 1.5mm; }}
  .basis-table table {{ margin-bottom: 4mm; }}
  .basis-table th {{
    background: none; color: var(--color-forest); font-size: inherit; font-weight: 600;
    padding: 1.5mm 2.5mm; border-bottom: 0.5pt solid var(--color-forest);
  }}
  .basis-table td {{ padding: 1.5mm 2.5mm; }}
  /* A figure and the unit it is in are one token and may not be split. The
     compact unit spellings contain U+002D, which is a break opportunity, so a
     cell wrapped mid-token — leaving a trailing hyphen that reads for a beat as
     a minus sign in a right-aligned column, above a dangling remainder. On the
     summary row, the one a reader uses to confirm the column adds up, that is
     the most visibly broken thing on the page. The withheld cell below opts
     back out: it is prose, and prose must wrap. */
  .basis-table td.num {{ white-space: nowrap; }}
  .basis-table tfoot td {{
    font-weight: 600; border-top: 0.5pt solid var(--color-forest);
  }}
  /* The column table names a money column, its key and its denominator. The
     first column holds the shortest phrases, so it gets just enough width to
     keep them on one line; the key is prose and may wrap. */
  .basis-table .columns th:first-child, .basis-table .columns td:first-child {{ width: 29%; }}
  .basis-table .columns th:last-child, .basis-table .columns td:last-child {{ width: 24%; }}
  /* The one cell in the reference-total column that holds prose instead of a
     figure. Left-aligned and with tabular figures switched off, so it cannot be
     mistaken for a broken number in a column of denominators. */
  .basis-table td .withheld {{
    display: block; text-align: left; font-variant-numeric: normal;
    white-space: normal;
  }}
  /* Both notes sit directly beneath the table they qualify — adjacency is part
     of the rule, not a layout preference. Tier 1, so no font-size and no
     lighter ink: they recede by weight and by the space above them. */
  .basis-table .withheld-note, .basis-table .rounding-note {{
    margin: 0 0 4mm; font-weight: 400;
  }}
  .basis-table .rounding-note {{ margin-bottom: 0; }}
  /* The sentence that says what the list below it is. Separated from the list
     by a break it leaves bare derivation lines on a fresh sheet with nothing
     naming what was apportioned — the same defect the headings are held to,
     one scale down. */
  .apportionment-lead {{ break-after: avoid; }}
  .apportionment {{ margin: 0 0 2mm; padding-left: 5mm; list-style: none; }}
  /* One derivation line is one statement and is never legible in halves. */
  .apportionment li {{ margin-bottom: 0.8mm; break-inside: avoid; }}
  .party-change .caveat {{ margin-top: 2.5mm; }}
  /* The document's bottom line: one row per party, and the one figure a reader
     is otherwise never given about themselves. Tier 1, but the *result* of the
     BGH minimum rather than a basis for it, so it keeps the money tables' full
     ink body copy (no `color`, no `font-size`: both inherit, which is the
     highest pair available) instead of the quieter forest of the three blocks
     above it. Its surface is Paper like theirs — a fourth tinted slab under
     three of them is ornament, not clarity — and it is set apart by space and a
     hairline rule instead. It GROWS with the number of parties, so it must not
     refuse to break; orphans/widows keep a lone line off a sheet of its own. */
  .party-total {{
    line-height: 1.5; margin-top: 6mm; padding-top: 4mm;
    border-top: 0.5pt solid var(--color-mint);
    orphans: 2; widows: 2;
  }}
  /* The sentence naming what the total does not contain. Same idiom as the
     heating footer's reconciliation line: quieter by weight, never by size and
     never by ink below the tier-1 pair (Forest Deep on Paper, 11,32:1). */
  .party-total .advance-note {{
    color: var(--color-forest); font-weight: 400; line-height: 1.5; margin: 3mm 0 0;
  }}
  .co2-grounds {{ display: block; margin-top: 2mm; }}
  footer {{
    color: var(--color-slate); font-size: 8pt; border-top: 0.5pt solid var(--color-slate);
    padding-top: 3mm; margin-top: 6mm; line-height: 1.6;
  }}
</style>
</head>
<body>
  <div class="band"></div>
  <h1>Betriebs- und Heizkostenabrechnung</h1>
  <p class="meta">
    {escape(data.building_label)} · Abrechnungszeitraum {escape(data.period_label)}<br />
    Vermieter: {escape(data.landlord_name)}
  </p>
  {_nk_section(data)}
  {_heating_section(data)}
  {_party_total_section(data)}
  <footer>
    Rechtsstand: {rechtsstaende} · Erstellt mit Lokara.<br />
    {escape(DISCLAIMER)}
  </footer>
</body>
</html>"""
