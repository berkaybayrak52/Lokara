# ruff: noqa: RUF001
"""Data-only, cent-exact oracle transcribed from Berkay Page 04.

This module imports no production code. It records exactly ``11-F01`` through
``11-F16`` plus the complete source, register, non-goal, correspondence,
readiness and blocked-format surfaces used by the D2 transcription. Money is
integer cents. Anlage-V lines, SKR accounts, EXTF parameters/Soll-Haben
orientation and the BFH citation remain explicitly unverified.
"""

from typing import Final

Golden = dict[str, object]
RegisterRow = tuple[str, str, str, str, str, str, str, str, str]

PAGE_04_SOURCE_SECTIONS: Final[tuple[str, ...]] = (
    "metadata_dependencies_and_two_outputs",
    "1_purpose",
    "2_1_legal_basis",
    "2_2_case_law_gap",
    "2_3_conventions_11_k01_through_11_k11",
    "2_4_open_authority_and_format_questions",
    "3_inputs_payment_afa_adviser_and_mapping",
    "4_rules_r1_through_r9",
    "5_edge_cases_11_e01_through_11_e15",
    "6_worked_examples_11_f01_through_11_f16",
    "7_page_scope_boundaries",
    "non_goals_v1_exact_eight",
    "readme_for_emir_arithmetic_audit",
    "seven_file_correspondence_ledger",
)

PAGE_04_REGISTER_PAGE: Final = (
    "04 · Anlage V + DATEV-Export "
    "(https://app.notion.com/p/04-Anlage-V-DATEV-Export-"
    "3a95fd420731810c8a16dfe93cc85cbd?pvs=21)"
)

# Wert, Betrag/Satz, Flag, Letzte Änderung, Prüfen bis, Quelle,
# Rechtsgrundlage, Rechtsnatur, Rechtsstand. ``Betroffene Seite`` is the shared
# PAGE_04_REGISTER_PAGE value. Values are copied from the authoritative CSV.
PAGE_04_REGISTER_ROWS: Final[tuple[RegisterRow, ...]] = (
    (
        "Kaution = durchlaufender Posten (Verrechnungskonto, nie Ertrag)",
        "",
        "verify-before-production",
        "28. Juli 2026 17:16",
        "5. August 2026",
        "",
        "§ 551 BGB / Rechenkonvention (11-K04)",
        "Konvention",
        "07/2026",
    ),
    (
        "GoBD / Unveränderbarkeit — Export-Archiv (Hash + Zeitstempel) + Ledger-Audit-Trail",
        "",
        "geprüft",
        "28. Juli 2026 17:16",
        "",
        "",
        "§§ 145–147 AO, GoBD (BMF v. 28.11.2019)",
        "Gesetz",
        "07/2026",
    ),
    (
        "Tilgungsreihenfolge bei Teilleistung (Analogie: erst Kaltmiete, dann NK-Vorauszahlung)",
        "",
        "geprüft",
        "28. Juli 2026 17:16",
        "",
        "https://www.gesetze-im-internet.de/bgb/__366.html",
        "§ 366 Abs. 2 BGB",
        "Gesetz",
        "07/2026",
    ),
    (
        "DATEV-EXTF-Formatparameter (EXTF/700/21/Buchungsstapel/13, Win-1252, ';', CRLF, TTMM)",
        "Header-Version 700, Kategorie 21, Formatversion 13",
        "verify-before-production",
        "28. Juli 2026 17:16",
        "5. August 2026",
        "https://developer.datev.de/de/file-format/details/datev-format/format-description/header",
        "DATEV-Formatspezifikation (proprietär, http://developer.datev.de)",
        "Konvention",
        "07/2026",
    ),
    (
        "Schuldzinsen als gekennzeichneter Vorschlagswert aus dem Tilgungsplan "
        "(nie stille Übernahme)",
        "",
        "verify-before-production",
        "28. Juli 2026 17:16",
        "5. August 2026",
        "",
        "§ 9 Abs. 1 S. 3 Nr. 1 EStG (Umsetzungskonvention 11-K07)",
        "Konvention",
        "07/2026",
    ),
    (
        "Anlage-V-Zeilennummern je Steuerjahr (anlage_v_layout_<JJJJ>) — PLATZHALTER, "
        "jährlich verschoben",
        "Zeilen 13/14/32/33/37/42/47–50/82/84 unbestätigt",
        "verify-before-production",
        "28. Juli 2026 17:16",
        "5. August 2026",
        "https://www.elster.de",
        "Formular Anlage V (BMF/ELSTER), jahresversioniert",
        "Konvention",
        "07/2026",
    ),
    (
        "Zufluss-/Abflussprinzip + 10-Tage-Regel (Periodenzuordnung nach Zahlungsdatum)",
        "Fenster 22.12.–10.01., beide Bedingungen (Fälligkeit UND Zahlung)",
        "geprüft",
        "28. Juli 2026 17:16",
        "",
        "https://www.gesetze-im-internet.de/estg/__11.html",
        "§ 11 Abs. 1 S. 2, Abs. 2 S. 2 EStG",
        "Gesetz",
        "07/2026",
    ),
    (
        "Weitergabe Mieter-Personendaten an StB + Datenminimierung im Buchungstext",
        "",
        "geprüft",
        "28. Juli 2026 17:16",
        "",
        "https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32016R0679",
        "Art. 6 Abs. 1 lit. c/f DSGVO",
        "Verordnung",
        "07/2026",
    ),
    (
        "10-Tage-Regel — tragendes BFH-Aktenzeichen (ZITAT UNSICHER, kein Az. erfunden)",
        "",
        "verify-before-production",
        "28. Juli 2026 17:16",
        "5. August 2026",
        "",
        "§ 11 Abs. 1 S. 2 EStG / BFH (Az. offen, ggf. VIII R 9/09)",
        "Rechtsprechung",
        "07/2026",
    ),
    (
        "SKR03/SKR04-Default-Konten für private Vermietung — PLATZHALTER, kanzleiabhängig",
        "",
        "verify-before-production",
        "28. Juli 2026 17:16",
        "5. August 2026",
        "",
        "DATEV-Kontenrahmen SKR03/SKR04 (proprietär)",
        "Konvention",
        "07/2026",
    ),
    (
        "Befugnisgrenze Steuerhilfe — Ausfüllhilfe/Datentransport, keine Beratung/Übermittlung",
        "",
        "geprüft",
        "28. Juli 2026 17:16",
        "",
        "https://www.gesetze-im-internet.de/stberg/",
        "§§ 1–5 StBerG",
        "Gesetz",
        "07/2026",
    ),
    (
        "Einkünfte aus Vermietung und Verpachtung — Überschussrechnung Einnahmen − Werbungskosten",
        "",
        "geprüft",
        "28. Juli 2026 17:16",
        "",
        "https://www.gesetze-im-internet.de/estg/__21.html",
        "§ 21 EStG",
        "Gesetz",
        "07/2026",
    ),
    (
        "Aufbewahrungspflicht 6 Jahre ab Überschusseinkünften > 500.000 €",
        "500.000 € / 6 Jahre",
        "geprüft",
        "28. Juli 2026 17:16",
        "",
        "https://www.gesetze-im-internet.de/ao_1977/__147a.html",
        "§ 147a AO",
        "Gesetz",
        "07/2026",
    ),
)

CONVENTION_IDS: Final = tuple(f"11-K{number:02}" for number in range(1, 12))
RULE_IDS: Final = tuple(f"R{number}" for number in range(1, 10))
EDGE_CASE_IDS: Final = tuple(f"11-E{number:02}" for number in range(1, 16))
EDGE_05_SUBCASES: Final = ("11-E05a", "11-E05b", "11-E05c")

PAGE_04_NON_GOALS: Final[tuple[str, ...]] = (
    "ELSTER-Direktübermittlung (ERiC)",
    "DATEV Buchungsdatenservice (REST-API)",
    "Belegbild-Übergabe (DATEV Unternehmen online / Belegbilderservice)",
    "Rückkanal vom StB (Statusabgleich, Korrekturen zurück nach Lokara)",
    "Umsatzsteuer-Logik (BU-Schlüssel, § 9 UStG-Option, Vorsteueraufteilung)",
    "§ 82b EStDV (Verteilung größeren Erhaltungsaufwands auf 2–5 Jahre)",
    "Kontenrahmen jenseits SKR03/SKR04 (SKR14, individuelle)",
    "Verbilligte Vermietung (§ 21 Abs. 2 EStG, 66-%-Grenze)",
)

PAGE_04_DELEGATED_BOUNDARIES: Final[tuple[str, ...]] = (
    "AfA-, Zins- und Disagio-Berechnung kommt fertig von Seite 03",
    "Umlageschlüssel, NK-Arithmetik, Fristen und UVI bleiben auf Seiten 01/02/05",
)

CORRESPONDENCE_RETIREMENT_FILES: Final[tuple[str, ...]] = (
    "FEEDBACK-to-Berkay-01b.md",
    "FRAGEN-an-Berkay-02.md",
    "FRAGEN-an-Berkay-03.md",
    "berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md",
    "berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md",
    "berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md",
    "berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md",
)

FUTURE_CONTRACTS: Final[tuple[str, ...]] = (
    "payment_ledger_snapshot",
    "page_03_afa_handoff",
    "tax_adviser_profile",
    "year_versioned_tax_category_mapping",
    "immutable_readiness_result",
    "versioned_export_archive",
)

PAGE_03_HANDOFF_FIELDS: Final[tuple[str, ...]] = (
    "afaAbziehbarCent",
    "zinsAbziehbarCent",
    "disagioAbziehbarCent",
    "erhaltungsaufwandCent",
)

UNMAPPED_HANDOFF_GAPS: Final[tuple[str, ...]] = (
    "disagio_anlage_v_line",
    "erhaltungsaufwand_line_and_ledger_instandhaltung_deduplication",
)

UNVERIFIED_BLOCKERS: Final[tuple[str, ...]] = (
    "anlage_v_lines_by_tax_year",
    "skr03_skr04_default_accounts",
    "extf_header_field_list_and_versions",
    "extf_festschreibung_semantics",
    "extf_soll_haben_orientation",
    "ten_day_rule_bfh_case_number",
)

READINESS_FINDINGS: Final[dict[str, tuple[str, str]]] = {
    "R-r1": ("rot", "payment_without_date"),
    "R-r2": ("rot", "datev_without_adviser_or_client_number"),
    "R-r3": ("rot", "no_payment_data_in_period"),
    "R-g1": ("gelb", "bank_movement_without_renter"),
    "R-g2": ("gelb", "payment_without_category"),
    "R-g3": ("gelb", "category_without_selected_skr_account"),
    "R-g4": ("gelb", "object_without_afa_record"),
    "R-g5": ("gelb", "year_window_payment_without_clear_assignment"),
    "R-g6": ("gelb", "unconfirmed_interest_proposal"),
    "R-g7": ("gelb", "expected_rent_gap"),
    "R-g8": ("gelb", "vat_case_detected"),
}

EXTF_WORKING_CONVENTION: Final[dict[str, object]] = {
    "marker": "EXTF",
    "header_version": 700,
    "data_category": 21,
    "format_version": 13,
    "encoding": "windows-1252",
    "delimiter": ";",
    "decimal_separator": ",",
    "line_ending": "\r\n",
    "document_date_format": "TTMM",
    "filename_prefix": "EXTF_",
    "production_blocked": True,
}

# category, placeholder Anlage-V line, placeholder SKR03, placeholder SKR04, direction.
# Empty strings mean deliberately no line/account. Every non-empty number is unverified.
UNVERIFIED_REFERENCE_MAPPING: Final[tuple[tuple[str, str, str, str, str], ...]] = (
    ("kaltmiete", "13", "8100", "4100", "einnahme"),
    ("nk_vorauszahlung", "14", "8105", "4105", "einnahme"),
    ("nk_nachzahlung", "14", "8105", "4105", "einnahme"),
    ("nk_guthaben", "14", "8105", "4105", "ausgabe"),
    ("afa", "33", "4831", "6221", "non_cash"),
    ("schuldzinsen", "37", "8xxx", "6xxx", "ausgabe"),
    ("grundsteuer", "47", "4900", "6300", "ausgabe"),
    ("versicherung", "48", "4360", "6400", "ausgabe"),
    ("hauswart", "49", "4210", "6210", "ausgabe"),
    ("heizkosten", "50", "4240", "6240", "ausgabe"),
    ("muellbeseitigung", "50", "4250", "6250", "ausgabe"),
    ("instandhaltung", "42", "4260", "6260", "ausgabe"),
    ("kaution", "", "1590", "1370", "clearing"),
    ("bank", "", "1200", "1800", "counter_account"),
)

ARITHMETIC_AUDIT: Final[dict[str, object]] = {
    "fixture_count": 16,
    "fixture_range": "11-F01…11-F16",
    "printed_cent_arithmetic": "exact",
    "clears_unverified_values": False,
}

PAGE_04_GOLDENS: Final[dict[str, Golden]] = {
    "11-F01": {
        "cold_rent_month": 194_000,
        "advance_month": 47_000,
        "months": 12,
        "cold_rent_year": 2_328_000,
        "advance_year": 564_000,
        "income_total": 2_892_000,
        "line_numbers_unverified": True,
    },
    "11-F02": {
        "cash_costs": (98_000, 124_000, 180_000, 360_000, 72_000, 150_000),
        "cash_cost_total": 984_000,
        "afa_handoff": 540_103,
        "interest_proposal": 840_000,
        "interest_confirmation": "yellow",
        "advertising_cost_total": 2_364_103,
        "missing_afa_readiness": "yellow_line_empty",
        "line_numbers_unverified": True,
    },
    "11-F03": {
        "income_total": 2_892_000,
        "advertising_cost_total": 2_364_103,
        "result": 527_897,
    },
    "11-F04": {
        "economic_period": 2024,
        "payment_date": "2025-03-14",
        "category": "nk_nachzahlung",
        "recurring": False,
        "tax_year": 2025,
        "amount": 34_000,
        "reference_income_before": 2_892_000,
        "reference_income_after": 2_926_000,
    },
    "11-F05": {
        "payment_date": "2025-12-28",
        "due_date": "2026-01-01",
        "recurring": True,
        "both_dates_in_window": True,
        "tax_year": 2026,
        "amount": 74_000,
        "assignment_label_required": True,
    },
    "11-F06": {
        "payment_date": "2026-01-05",
        "due_date": "2025-12-31",
        "recurring": True,
        "both_dates_in_window": True,
        "tax_year": 2025,
        "amount": 74_000,
    },
    "11-F07": {
        "payment_date": "2026-01-05",
        "due_date": "2025-10-01",
        "recurring": True,
        "both_dates_in_window": False,
        "tax_year": 2026,
        "amount": 74_000,
    },
    "11-F08": {
        "payment": 77_000,
        "cold_rent_due": 62_000,
        "advance_due": 15_000,
        "cold_rent_share": 62_000,
        "advance_share": 15_000,
        "rounding": "none",
    },
    "11-F09": {
        "payment": 60_000,
        "cold_rent_due": 62_000,
        "advance_due": 15_000,
        "cold_rent_share": 60_000,
        "advance_share": 0,
        "cold_rent_open": 2_000,
        "advance_open": 15_000,
        "open_amounts_exported": False,
    },
    "11-F10": {
        "category": "nk_guthaben",
        "direction": "ausgabe",
        "amount": 20_000,
        "advance_income_before": 564_000,
        "advance_income_after": 544_000,
        "datev_booking": "reverse_revenue_payment",
    },
    "11-F11": {
        "category": "kaution",
        "amount": 174_000,
        "anlage_v_effect": 0,
        "datev_account_kind": "clearing",
        "placeholder_skr03": "1590",
        "return_is_result_neutral": True,
        "production_blocked": True,
    },
    "11-F12": {
        "income_amount": 92_000,
        "expense_amount": 36_000,
        "document_date": "1503",
        "income_reference": "MIETE-WE02-0325",
        "expense_reference": "HEIZ-0325",
        "income_text": "Miete WE-02 März 2025",
        "expense_text": "Heizkosten Objekt Musterstr 12 März 2025",
        "encoding_probe": "Müllbeseitigung Grünstraße ä ö ü ß €",
        "encoding": "windows-1252",
        "line_ending": "\r\n",
        "account_numbers_unverified": True,
        "soll_haben_orientation_unverified": True,
    },
    "11-F13": {
        "debit_parts": (92_000, 36_000),
        "credit_parts": (92_000, 36_000),
        "debit_total": 128_000,
        "credit_total": 128_000,
        "extf_single_row_orientation_unverified": True,
    },
    "11-F14": {
        "amount": 98_000,
        "skr03_expense": "4900",
        "skr03_bank": "1200",
        "skr04_expense": "6300",
        "skr04_bank": "1800",
        "only_accounts_change": True,
        "missing_account_readiness": "yellow",
        "production_blocked": True,
    },
    "11-F15": {
        "payment": 80_000,
        "cold_rent_share": 62_000,
        "advance_share": 15_000,
        "renter_credit": 3_000,
        "income_booked": 77_000,
        "renter_credit_is_income": False,
    },
    "11-F16": {
        "gross_amount": 119_000,
        "net_reference_only": 100_000,
        "vat_reference_only": 19_000,
        "exported_amount": 119_000,
        "readiness": "yellow",
        "bu_key": None,
        "vat_split_performed": False,
        "warning": (
            "USt-Fall erkannt — dieser Export enthält keine Umsatzsteuer-Logik. "
            "Bitte mit Ihrem Steuerberater klären."
        ),
    },
}
