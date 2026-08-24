"""Blocked, year-versioned Page-04 mapping and EXTF convention data.

These records reproduce the approved oracle's placeholders.  Their explicit
flag prevents technical fixture coverage from becoming a production claim.
"""

from dataclasses import dataclass
from datetime import date

from .store import RuleSet, RuleVersion


@dataclass(frozen=True)
class TaxCategoryMapping:
    category: str
    anlage_v_line: str | None
    skr03_account: str | None
    skr04_account: str | None
    direction: str


@dataclass(frozen=True)
class AnlageVLayout:
    tax_year: int
    mappings: tuple[TaxCategoryMapping, ...]
    verification_flag: str
    production_blocked: bool


_REFERENCE_MAPPINGS = (
    TaxCategoryMapping("kaltmiete", "13", "8100", "4100", "einnahme"),
    TaxCategoryMapping("nk_vorauszahlung", "14", "8105", "4105", "einnahme"),
    TaxCategoryMapping("nk_nachzahlung", "14", "8105", "4105", "einnahme"),
    TaxCategoryMapping("nk_guthaben", "14", "8105", "4105", "ausgabe"),
    TaxCategoryMapping("afa", "33", "4831", "6221", "non_cash"),
    TaxCategoryMapping("schuldzinsen", "37", "8xxx", "6xxx", "ausgabe"),
    TaxCategoryMapping("grundsteuer", "47", "4900", "6300", "ausgabe"),
    TaxCategoryMapping("versicherung", "48", "4360", "6400", "ausgabe"),
    TaxCategoryMapping("hauswart", "49", "4210", "6210", "ausgabe"),
    TaxCategoryMapping("heizkosten", "50", "4240", "6240", "ausgabe"),
    TaxCategoryMapping("muellbeseitigung", "50", "4250", "6250", "ausgabe"),
    TaxCategoryMapping("instandhaltung", "42", "4260", "6260", "ausgabe"),
    TaxCategoryMapping("kaution", None, "1590", "1370", "clearing"),
    TaxCategoryMapping("bank", None, "1200", "1800", "counter_account"),
)


ANLAGE_V_LAYOUTS: RuleSet[AnlageVLayout] = RuleSet(
    key="tax.anlage_v.layout",
    versions=(
        RuleVersion(
            valid_from=date(2025, 1, 1),
            valid_to=date(2026, 1, 1),
            source="Page 04 reference table; annual official form verification pending",
            value=AnlageVLayout(
                tax_year=2025,
                mappings=_REFERENCE_MAPPINGS,
                verification_flag="verify-before-production",
                production_blocked=True,
            ),
        ),
    ),
)


@dataclass(frozen=True)
class ExtfProfile:
    marker: str
    header_version: int
    data_category: int
    format_version: int
    encoding: str
    delimiter: str
    decimal_separator: str
    line_ending: str
    document_date_format: str
    filename_prefix: str
    verification_flag: str
    official_datev_profile: bool
    production_blocked: bool


EXTF_PROFILES: RuleSet[ExtfProfile] = RuleSet(
    key="tax.datev.extf.profile",
    versions=(
        RuleVersion(
            valid_from=date(2026, 7, 1),
            source="docs/11-tax-export.md 11-K11; official target format pending",
            value=ExtfProfile(
                marker="EXTF",
                header_version=700,
                data_category=21,
                format_version=13,
                encoding="windows-1252",
                delimiter=";",
                decimal_separator=",",
                line_ending="\r\n",
                document_date_format="TTMM",
                filename_prefix="EXTF_",
                verification_flag="verify-before-production",
                official_datev_profile=False,
                production_blocked=True,
            ),
        ),
    ),
)


VERIFIED_TEST_EXTF_PROFILES: RuleSet[ExtfProfile] = RuleSet(
    key="tax.datev.extf.profile.test-only",
    versions=(
        RuleVersion(
            valid_from=date(2025, 1, 1),
            source="M7 deterministic encoder fixture; never a production DATEV profile",
            value=ExtfProfile(
                marker="EXTF-TEST",
                header_version=1,
                data_category=21,
                format_version=1,
                encoding="windows-1252",
                delimiter=";",
                decimal_separator=",",
                line_ending="\r\n",
                document_date_format="TTMM",
                filename_prefix="EXTF_TEST_",
                verification_flag="verified-test-only",
                official_datev_profile=False,
                production_blocked=False,
            ),
        ),
    ),
)


__all__ = [
    "ANLAGE_V_LAYOUTS",
    "EXTF_PROFILES",
    "VERIFIED_TEST_EXTF_PROFILES",
    "AnlageVLayout",
    "ExtfProfile",
    "TaxCategoryMapping",
]
