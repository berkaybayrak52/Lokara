"""§ 12 HeizkostenV Round-4 cent oracle; it imports no engine code."""

from typing import Final

SECTION12_GOLDENS: Final[dict[str, object]] = {
    "source": "Antwort-an-Emir_04.md § 1.2",
    "rechtsstand": "08/2026",
    "status": "Konvention / verify-before-production / Anwaltspunkt",
    "warning": (
        "Zwei Kürzungsgründe gleichzeitig — bitte prüfen Sie, ob beide zutreffen. "
        "Die Kürzungen wirken nebeneinander."
    ),
    "mdl_components": {
        "gross_claim_cents": 10_005,
        "non_consumption_claim_cents": 10_005,
        "single": {
            "consumption_billing_missing": (1_501, 0, 0, 1_501, 8_504),
            "remote_readability_missing": (0, 300, 0, 300, 9_705),
            "section_6a_information_missing": (0, 0, 300, 300, 9_705),
        },
        "combinations": {
            ("consumption_billing_missing", "remote_readability_missing"): (
                1_501,
                300,
                0,
                1_801,
                8_204,
            ),
            ("consumption_billing_missing", "section_6a_information_missing"): (
                1_501,
                0,
                300,
                1_801,
                8_204,
            ),
            ("remote_readability_missing", "section_6a_information_missing"): (
                0,
                300,
                300,
                600,
                9_405,
            ),
            (
                "consumption_billing_missing",
                "remote_readability_missing",
                "section_6a_information_missing",
            ): (1_501, 300, 300, 2_101, 7_904),
        },
    },
    "self_billing_all_grounds": (
        ("Muster", 127_217, 4_864, 3_817, 3_817, 12_498, 114_719),
        ("Schneider", 66_203, 3_372, 1_986, 1_986, 7_344, 58_859),
        ("Weber", 40_510, 1_941, 1_215, 1_215, 4_371, 36_139),
        ("Beispiel", 98_426, 4_550, 2_953, 2_953, 10_456, 87_970),
    ),
}
