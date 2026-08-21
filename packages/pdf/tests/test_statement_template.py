"""Template gate: the statement HTML carries the legally required content.

Deterministic string assertions — no browser involved, so these always run.
The demo composition is the fixture: canonical €1,200 NK + the heating golden
fixture with CO₂, rules resolved from the rules-store.
"""

import re
from dataclasses import replace
from decimal import Decimal

from lokara_domain import cents
from lokara_heating_engine import ReductionRisk
from lokara_pdf import DISCLAIMER, format_number_de, statement_html
from lokara_pdf.demo import AS_OF, build_demo_statement
from lokara_rules_store import CO2_SPLIT_TABLE, get_rule

_CO2_BLOCK = re.compile(r'<div class="co2">(.*?)</div>', re.DOTALL)

NBSP = " "


def test_statement_contains_the_canonical_amounts() -> None:
    html = statement_html(build_demo_statement())

    # The €1,200 fixture's four shares, German-formatted (NBSP before €).
    assert f"600,00{NBSP}€" in html
    assert f"178,52{NBSP}€" in html
    assert f"181,48{NBSP}€" in html
    assert f"240,00{NBSP}€" in html
    assert f"1.200,00{NBSP}€" in html  # the reconciled total

    # Heating totals of the CO₂ golden fixture: unit A's line total is 560,397
    # cents; the reconciled grand total €10,300.00. Unit A's figure moved from
    # 5.657,60 € on 05.08.2026 with the demo's CO₂ fixture — the CO₂-Vermieteranteil
    # is deducted before the renter-facing split, so a corrected CO₂ cost moves
    # every heating euro. `docs/06` → "Scenario 2 — the fuel, the emissions and the
    # CO₂ price". The **invoice total** did not move, which is why it is asserted
    # beside it.
    assert f"5.603,97{NBSP}€" in html
    assert f"10.300,00{NBSP}€" in html


def test_co2_block_cites_its_rule_and_the_page_carries_the_disclaimer() -> None:
    """The § 7 Abs. 3 CO2KostAufG citation inside the CO₂ block, plus the
    "tool, not advice" line.

    This test used to assert a bare ``Rechtsstand 03/1989`` anywhere on the page.
    `docs/08` item 6 **abolished that form**: the footer now prints the label once
    and names each rule beside its own date (`§ 7 Abs. 1 HeizkostenV 03/1989` …),
    so no bare stamp survives there — `test_statement_rechtsstand_labels.py`
    asserts exactly that, resolved from the rules-store, for all four rules. The
    old assertion was not a regression but its opposite, and re-adding it would
    contradict the ratified gate; it is deleted rather than restated, so the two
    files cannot drift apart.

    What is *not* superseded is the stamp inside the CO₂ block. The footer gate is
    footer-scoped on purpose, and after item 6 the raw string ``Rechtsstand
    MM/JJJJ`` renders in exactly one place on the page: this block, where the
    citation stands next to it (`docs/08` item 5 — "already discharged by the
    existing co2_block"). So the assertion stays here, block-scoped and resolved
    from the store: a hardcoded ``01/2023`` that happens to match still passes,
    but a store edit that moves the date should surface in a test rather than on a
    tenant's statement.
    """
    html = statement_html(build_demo_statement())

    block = _CO2_BLOCK.search(html)
    assert block is not None, "no CO₂ block — § 7 Abs. 3 CO2KostAufG requires the disclosure"
    co2_rule = get_rule(CO2_SPLIT_TABLE, AS_OF)
    assert f"CO2KostAufG, {co2_rule.rechtsstand}" in block.group(1), (
        f"the CO₂ block does not stamp {co2_rule.rechtsstand!r} beside its citation"
    )

    assert DISCLAIMER in html
    assert "keine Rechts- oder Steuerberatung" in DISCLAIMER


# `docs/08` → "The disclaimer states what Lokara is, never that this Abrechnung
# is complete". Transcribed, not paraphrased: one sentence, the subject is the
# product, and nothing in it points at this artifact.
EXPECTED_DISCLAIMER = (
    "Lokara ist ein Werkzeug für die rechtskonforme Betriebs- und Heizkostenabrechnung, "
    "keine Rechts- oder Steuerberatung."
)

# The form that must never return. `Dieses Dokument` + a perfect passive is a
# per-document warranty, and this page cannot make one: BGH formal minimum #4
# (Abzug der geleisteten Vorauszahlungen) is not rendered at all, by decision,
# until the M6 ledger (`docs/08` → "#4 is blocked on the M6 ledger").
ATTESTATION_FORMS = (
    "Dieses Dokument wurde",
    "rechtskonform erstellt",
    "Rechtskonform erstellt",
)


def test_the_disclaimer_claims_something_about_lokara_not_about_this_document() -> None:
    """`CLAUDE.md` mandates a *positioning* claim — "rechtskonform, keine Rechts-
    oder Steuerberatung" — and `docs/07` already writes it as one ("Lokara ist
    ein Werkzeug, …"). The rendered string had drifted into an attestation that
    *this* Abrechnung is legally complete, which it is not.

    Three assertions, and each covers a different way back to the defect:
    the constant is the transcribed sentence; the page really renders it (a
    constant nothing prints is not a disclaimer); and the attestation form is
    gone from the *whole* page, not merely from `DISCLAIMER` — a second copy in
    a template string would otherwise slip through.
    """
    html = statement_html(build_demo_statement())

    assert DISCLAIMER == EXPECTED_DISCLAIMER
    assert DISCLAIMER in html

    present = [form for form in ATTESTATION_FORMS if form in html]
    assert not present, (
        "the page attests to its own legal completeness: "
        + ", ".join(repr(form) for form in present)
        + " — the claim is about Lokara, never about this Abrechnung (docs/08)"
    )


def test_statement_shows_co2_split_and_party_labels() -> None:
    html = statement_html(build_demo_statement())

    assert "CO₂-Kostenaufteilung" in html
    # 40 kg/m²/a → step 37–42. Moved from 20 % / 60,00 € on 05.08.2026 with the
    # demo's CO₂ fixture: docs/06 → "Scenario 2 — the fuel, the emissions and the
    # CO₂ price". The sibling golden in this file was re-based then and this one
    # was missed.
    assert "Vermieteranteil 60" in html
    assert f"157,08{NBSP}€" in html  # landlord CO₂ share, deducted pre-split
    assert "Wohnung B — Leerstand ab 01.07.2025 → Vermieter" in html
    assert "Müllabfuhr" in html
    assert "Umlageschlüssel: Wohnfläche" in html
    assert 'lang="de"' in html


def test_weights_display_human_scale_and_heating_is_coherent() -> None:
    html = statement_html(build_demo_statement())

    # AREA weights shown as m²·Tage (docs/03 table), not the ×100 fixed point.
    assert "18.250" in html
    assert "1.825.000" not in html

    # The heating section uses the same occupancy timeline as the NK section:
    # unit B splits Bernd/landlord, so the landlord label appears in both
    # tables (once for the NK vacancy line, once for the heating lines).
    assert html.count("Leerstand ab 01.07.2025") >= 2


def test_page01b_evidence_and_separate_three_percent_risks_render() -> None:
    data = build_demo_statement()
    assert data.page01b_result is not None
    page = replace(
        data.page01b_result,
        risks=(
            ReductionRisk("remote", Decimal(3), (cents(300),), "Fernablesung fehlt."),
            ReductionRisk("section6a", Decimal(3), (cents(300),), "§ 6a fehlt."),
        ),
    )
    html = statement_html(replace(data, page01b_result=page))

    assert "Geräte- und Ableseprotokoll" in html
    assert "Kein Vorjahreswert vorhanden" in html
    assert html.count("3-%-Risiko") == 2
    assert "6-%-Risiko" not in html


def test_measured_warm_water_energy_has_its_own_disclosure_branch() -> None:
    data = build_demo_statement()
    assert data.heating_result is not None
    separation = data.heating_result.warm_water_separation
    assert separation is not None
    measured_energy = replace(
        separation,
        method="MEASURED_ENERGY",
        q_ww_kwh=Decimal(5000),
        volume_m3=None,
        factor_kwh_per_m3_kelvin=None,
        hot_temp_c=None,
        cold_temp_c=None,
    )
    heating = replace(data.heating_result, warm_water_separation=measured_energy)
    html = statement_html(replace(data, heating_result=heating))

    assert "Warmwasserenergie durch Wärmemengenzähler erfasst" in html
    assert "Warmwasserverbrauch nicht gemessen" not in html


def test_untrusted_names_are_escaped() -> None:
    data = build_demo_statement()
    evil = type(data)(
        landlord_name='<script>alert("x")</script>',
        building_label=data.building_label,
        period_label=data.period_label,
        nk_result=data.nk_result,
        nk_costs=data.nk_costs,
        party_labels=data.party_labels,
        rechtsstaende=data.rechtsstaende,
        heating_result=data.heating_result,
    )
    html = statement_html(evil)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_german_number_formatting() -> None:
    assert format_number_de(Decimal(18250)) == "18.250"
    assert format_number_de(Decimal("146.25")) == "146,25"
    assert format_number_de(Decimal("20")) == "20"
    assert format_number_de(Decimal("1234567.5")) == "1.234.567,5"
