"""Template gate: the statement HTML carries the legally required content.

Deterministic string assertions — no browser involved, so these always run.
The demo composition is the fixture: canonical €1,200 NK + the heating golden
fixture with CO₂, rules resolved from the rules-store.
"""

from decimal import Decimal

from lokara_pdf import DISCLAIMER, format_number_de, statement_html
from lokara_pdf.demo import build_demo_statement

NBSP = " "


def test_statement_contains_the_canonical_amounts() -> None:
    html = statement_html(build_demo_statement())

    # The €1,200 fixture's four shares, German-formatted (NBSP before €).
    assert f"600,00{NBSP}€" in html
    assert f"178,52{NBSP}€" in html
    assert f"181,48{NBSP}€" in html
    assert f"240,00{NBSP}€" in html
    assert f"1.200,00{NBSP}€" in html  # the reconciled total

    # Heating totals of the CO₂ golden fixture (docs/03 hand-computed table):
    # unit A's line total is 565,760 cents; the reconciled grand total €10,300.00.
    assert f"5.657,60{NBSP}€" in html
    assert f"10.300,00{NBSP}€" in html


def test_statement_carries_rechtsstand_stamps_and_disclaimer() -> None:
    html = statement_html(build_demo_statement())

    assert "Rechtsstand 01/2023" in html  # CO2KostAufG
    assert "Rechtsstand 03/1989" in html  # § 7 HeizkostenV bounds
    assert DISCLAIMER in html
    assert "keine Rechts- oder Steuerberatung" in DISCLAIMER


def test_statement_shows_co2_split_and_party_labels() -> None:
    html = statement_html(build_demo_statement())

    assert "CO₂-Kostenaufteilung" in html
    assert "Vermieteranteil 20" in html  # 20 kg/m²/a → step 17–22
    assert f"60,00{NBSP}€" in html  # landlord CO₂ share, deducted pre-split
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
