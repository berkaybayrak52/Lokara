"""Data-only Round-4 Page 01b oracle; it intentionally imports no engine code."""

from typing import Final

ROUND4_PAGE_01B: Final[dict[str, object]] = {
    "source": "Antwort-an-Emir_04.md §§ 1.1–1.2",
    "rechtsstand": "08/2026",
    "reduction": {
        "status": "Konvention / verify-before-production / Anwaltspunkt",
        "summands": (
            ("non_consumption_15_percent", "non_consumption_share_cents", 15, True),
            ("missing_remote_readability_3_percent", "total_share_cents", 3, True),
            ("missing_section_6a_information_3_percent", "total_share_cents", 3, True),
        ),
        "one_unreduced_base_per_summand": True,
        "non_cascading": True,
        "maximum_percent": 21,
        "warning_at_simultaneous_grounds": 2,
        "warning_blocking": False,
    },
    "block_c": {
        "formula": "printed_owner_residual_cents - sum(separately_rounded_origin_cents)",
        "is_owner_residual_subline": True,
        "separate_pot": False,
        "has_bemessung": False,
        "has_quota": False,
        "print_only_when_nonzero": True,
        "audit_log_always": True,
        "vacancy_schedule_text": (
            "Rundungsdifferenz aus der zeilenweisen Verteilung — keiner Einheit zurechenbar"
        ),
        "statement_text": "davon Rundungsdifferenz",
        "status": "Konvention / no external source / no verify-before-production",
    },
}
