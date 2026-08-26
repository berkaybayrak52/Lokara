"""Versioned authority inventory for finalized Page-01 statements.

The rows below are a data transcription of the 26 Page-01 entries in the
authoritative Rechtsstand register.  An empty external-source cell is retained
as a visible register provenance reference; it is not replaced with invented
legal authority.
"""

from dataclasses import dataclass
from datetime import date

from .store import RuleSet, RuleVersion, get_rule

REGISTER_SOURCE = "berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv"


@dataclass(frozen=True, slots=True)
class Page01StatementEvidence:
    """One immutable Page-01 register row."""

    name: str
    source: str
    legal_basis: str
    rechtsnatur: str
    rechtsstand: str
    verification_status: str


@dataclass(frozen=True, slots=True)
class Page01StatementRules:
    """Complete authority inventory frozen by the statement service."""

    evidence: tuple[Page01StatementEvidence, ...]


def _row(
    name: str,
    source: str,
    legal_basis: str,
    rechtsnatur: str,
    verification_status: str,
) -> Page01StatementEvidence:
    return Page01StatementEvidence(
        name=name,
        source=source or REGISTER_SOURCE,
        legal_basis=legal_basis,
        rechtsnatur=rechtsnatur,
        rechtsstand="07/2026",
        verification_status=verification_status,
    )


_PAGE_01_EVIDENCE = (
    _row(
        "Fiktivbelegung bei Leerstand",
        "",
        "LG Krefeld 2 S 56/09; BGH VIII ZR 180/12 (Tatfrage, nicht höchstrichterlich geklärt)",
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "Gradtagszahltabelle VDI (K3)",
        "https://www.gesetze-im-internet.de/heizkostenv/__9b.html",
        (
            '§ 9b Abs. 2 HeizkostenV („anerkannte Regeln der Technik"); Tabelle selbst: '
            "VDI 2067 Blatt 1, Ausgabe 12/1983, Tabelle 22."
        ),
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "CO₂-Stufenmodell Wohngebäude",
        "https://www.gesetze-im-internet.de/co2kostaufg/BJNR215400022.html",
        "§§ 5–7 + Anlage CO2KostAufG",
        "Gesetz",
        "geprüft",
    ),
    _row(
        "CO₂-Pflichtangaben in der Abrechnung",
        "https://www.gesetze-im-internet.de/co2kostaufg/BJNR215400022.html",
        "§ 7 Abs. 3 CO2KostAufG",
        "Gesetz",
        "geprüft",
    ),
    _row(
        "Kürzungsrecht — fehlende fernablesbare Ausstattung",
        "https://www.gesetze-im-internet.de/heizkostenv/__12.html",
        "§ 12 Abs. 1 S. 2 HeizkostenV",
        "Verordnung",
        "verify-before-production",
    ),
    _row(
        "§ 35a-Ausweis für den Mieter",
        "https://www.gesetze-im-internet.de/estg/__35a.html",
        "§ 35a Abs. 2–3 EStG",
        "Gesetz",
        "geprüft",
    ),
    _row(
        "Kürzungsrecht — nicht verbrauchsabhängig abgerechnet",
        "https://www.gesetze-im-internet.de/heizkostenv/__12.html",
        "§ 12 Abs. 1 S. 1 HeizkostenV",
        "Verordnung",
        "geprüft",
    ),
    _row(
        "Rundungsweg (Seite 01 / docs/03 § 6)",
        "",
        (
            "keine — reine Hauskonvention; beide Wege sind vertretbar, wir binden uns an den, "
            "den der Mieter nachrechnen kann. Recherche 27.07.2026: keine externe Quelle "
            "vorhanden."
        ),
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "Abrechnungsfrist Betriebskosten",
        "https://www.gesetze-im-internet.de/bgb/__556.html",
        "§ 556 Abs. 3 S. 2–3 BGB",
        "Gesetz",
        "geprüft",
    ),
    _row(
        "Geräteliste auf der Mieterausfertigung (K10)",
        (
            "https://juris.bundesgerichtshof.de/cgi-bin/rechtsprechung/document.py?"
            "Gericht=bgh&Art=en&nr=81444"
        ),
        (
            "keine; Motiv: BGH VIII ZR 189/17, Urteil v. 07.02.2018 "
            "(Darlegungs- und Beweislast für die Richtigkeit der Abrechnung liegt beim Vermieter; "
            "umfassendes Belegeinsichtsrecht des Mieters, auch in Verbrauchsdaten anderer Nutzer)"
        ),
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "Zahlungsfrist bei Nachzahlung",
        "https://www.gesetze-im-internet.de/bgb/__286.html",
        (
            "keine gesetzliche Frist; Fälligkeit tritt mit Zugang einer ordnungsgemäßen "
            "Abrechnung ein. Anknüpfung für die 30 Tage: § 286 Abs. 3 BGB (Verzug 30 Tage nach "
            "Fälligkeit und Zugang der Rechnung; gegenüber Verbrauchern nur bei besonderem "
            "Hinweis)."
        ),
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "§ 6a Abs. 3 — Pflichtinformationen zur Abrechnung",
        "https://www.gesetze-im-internet.de/heizkostenv/__6a.html",
        "§ 6a Abs. 3 S. 1 Nr. 1–5 HeizkostenV",
        "Verordnung",
        "geprüft",
    ),
    _row(
        "Leerstand bleibt im Gesamtverteiler",
        (
            "https://www.bundesgerichtshof.de/SharedDocs/Entscheidungen/DE/Zivilsenate/"
            "VIII_ZS/2005/VIII_ZR_159-05.pdf?__blob=publicationFile&v=1"
        ),
        "BGH VIII ZR 159/05 v. 31.05.2006",
        "Rechtsprechung",
        "geprüft",
    ),
    _row(
        "CO₂-Kürzungsrecht",
        "https://www.gesetze-im-internet.de/co2kostaufg/BJNR215400022.html",
        "§ 7 Abs. 4 CO2KostAufG",
        "Gesetz",
        "geprüft",
    ),
    _row(
        "Verteilungsrest (K9)",
        "",
        (
            "keine — reine Hauskonvention. Recherche 27.07.2026: keine externe Quelle "
            "vorhanden, weder Norm noch anerkannte Regel der Technik."
        ),
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "Grundkostenanteil (K1)",
        "https://www.gesetze-im-internet.de/heizkostenv/BJNR002610981.html",
        "§ 7 Abs. 1, § 8 Abs. 1 HeizkostenV",
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "Belegeinsicht und Beweislast der Erfassung",
        "https://www.bundesgerichtshof.de/SharedDocs/Termine/DE/Termine/VIIIZR189.html",
        "BGH VIII ZR 189/17 v. 07.02.2018",
        "Rechtsprechung",
        "geprüft",
    ),
    _row(
        "Einwendungsfrist des Mieters",
        "https://www.gesetze-im-internet.de/bgb/__556.html",
        "§ 556 Abs. 3 S. 5–6 BGB",
        "Gesetz",
        "geprüft",
    ),
    _row(
        "Kürzungsrecht — fehlende oder unvollständige § 6a-Information "
        "(UVI + Abrechnungs-Infoblock)",
        "https://www.gesetze-im-internet.de/heizkostenv/__12.html",
        "§ 12 Abs. 1 S. 3 i. V. m. § 6a HeizkostenV",
        "Verordnung",
        "verify-before-production",
    ),
    _row(
        "Belegeinsicht — elektronische Bereitstellung zulässig (Wohnraum)",
        "https://www.gesetze-im-internet.de/bgb/__556.html",
        "§ 556 Abs. 4 BGB",
        "Gesetz",
        "geprüft",
    ),
    _row(
        "Verbrauchsvergleich — Umfang und Bereinigung",
        "https://www.gesetze-im-internet.de/heizkostenv/__6a.html",
        "§ 6a Abs. 3 S. 2–3 HeizkostenV",
        "Verordnung",
        "verify-before-production",
    ),
    _row(
        "Grundkosten-Verteilung nach m²-Tagen (K2)",
        "https://www.gesetze-im-internet.de/heizkostenv/__9b.html",
        (
            "Maßstab: § 7 Abs. 1 S. 5 HeizkostenV (übrige Kosten Wärme nach Wohn-/Nutzfläche "
            "oder umbautem Raum) und § 8 Abs. 1 HeizkostenV (übrige Kosten Warmwasser nach "
            "Wohn-/Nutzfläche). Zeitanteil: § 9b Abs. 2 HeizkostenV lässt für die übrigen "
            "Wärmekosten bei Nutzerwechsel Gradtagszahlen ODER zeitanteilig zu, für Warmwasser "
            "nur zeitanteilig — wir nehmen durchgängig zeitanteilig, weil die NK-Engine (Seite "
            "01) denselben Nenner benutzt. § 9b Abs. 2 allein trägt den Flächenmaßstab NICHT; "
            "er regelt nur die Aufteilung zwischen Vor- und Nachnutzer."
        ),
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "§ 35a-Block auf der Betriebskostenabrechnung",
        "https://www.gesetze-im-internet.de/estg/__35a.html",
        (
            "§ 35a Abs. 2–3 EStG (Anspruch des Mieters); keine Norm begründet eine "
            "Ausweispflicht des Vermieters auf der Abrechnung"
        ),
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "Wording Leerstandsaufstellung",
        "https://www.gesetze-im-internet.de/ao_1977/__90.html",
        (
            "§§ 9, 21 EStG (Werbungskostenabzug setzt fortbestehende Einkünfteerzielungsabsicht "
            "voraus); § 90 AO (Feststellungslast beim Steuerpflichtigen); BFH IX R 68/10. Keine "
            "Norm schreibt Form oder Existenz einer Leerstandsaufstellung vor."
        ),
        "Konvention",
        "verify-before-production",
    ),
    _row(
        "Kürzungsrecht — CO₂-Anteil nicht ausgewiesen",
        "https://www.gesetze-im-internet.de/co2kostaufg/__7.html",
        (
            "§ 7 Abs. 4 CO2KostAufG (Wohngebäude); § 8 Abs. 4 CO2KostAufG erklärt § 7 Abs. 3 "
            "und 4 für Nichtwohngebäude für entsprechend anwendbar"
        ),
        "Gesetz",
        "verify-before-production",
    ),
    _row(
        "CO₂-Mieteranteil — Pro-rata-Ableitung (D7 Schritt 6)",
        "https://www.gesetze-im-internet.de/co2kostaufg/__7.html",
        (
            "§ 7 Abs. 1 S. 2 CO2KostAufG verlangt die Verteilung „gemäß der Vereinbarung über "
            "die Verteilung der Heiz- und Warmwasserkosten auf Grundlage der §§ 6 bis 10 "
            'HeizkostenV" — die konkrete Pro-rata-Formel steht dort nicht und ist unsere '
            "Konvention. Der AUSWEIS des Anteils ist dagegen Pflicht (§ 7 Abs. 3), das "
            "Kürzungsrecht bei Verstoß folgt aus § 7 Abs. 4."
        ),
        "Konvention",
        "verify-before-production",
    ),
)


PAGE_01_STATEMENT_RULES = RuleSet(
    key="page01.statement.authority",
    versions=(
        RuleVersion(
            valid_from=date(2026, 7, 1),
            source=REGISTER_SOURCE,
            value=Page01StatementRules(evidence=_PAGE_01_EVIDENCE),
        ),
    ),
)


def resolve_page01_statement_rules(as_of: date) -> Page01StatementRules:
    """Resolve the complete Page-01 authority inventory for ``as_of``."""

    return get_rule(PAGE_01_STATEMENT_RULES, as_of).value


__all__ = [
    "PAGE_01_STATEMENT_RULES",
    "Page01StatementEvidence",
    "Page01StatementRules",
    "resolve_page01_statement_rules",
]
