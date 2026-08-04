"""Footer `Rechtsstand` entries: every stamp printed beside the rule it dates.

Spec: ``docs/08-statement-document.md`` → "M2 — every ``Rechtsstand`` names its
statute". Presentation only. The statutory citations are already carried by
``packages/rules-store`` as ``ResolvedRule.source`` and were simply discarded by
the caller; nothing here resolves a rule, changes one, or introduces a legal
value into this package.

The caller (``demo.py``, later the API) holds the ``ResolvedRule``s and composes
one entry per rule; the template prints the word ``Rechtsstand`` once, in front
of the joined entries.
"""

from lokara_rules_store import DEGREE_DAY_TABLE, ResolvedRule

# The degree-day table is the one resolved rule whose printed label is *not* its
# stored `source`. The deviation is deliberate; do not "simplify" it back into
# `rule.source`, and do not derive it by cutting the source at its em dash:
#
# 1. Its `source` ends in the internal developer marker "— verify before
#    production", which must never reach a renter.
# 2. Its `source` opens with "§ 9b Abs. 2 und Abs. 3 HeizkostenV", but
#    `Rechtsstand 01/1981` dates the *promille table*, not the paragraph.
#    § 9b's own in-force date is unverified in this repo — see the module
#    docstring of `packages/rules-store/.../rules/degree_days.py`: "no output
#    may pair the paragraph with that stamp". Printing "§ 9b … 01/1981" on a
#    renter's statement would be a legal claim we cannot make.
#
# docs/08 item 6 therefore fixes this one label as copy in the template layer:
# the table is named, and named as a convention rather than as law — an
# unqualified 1981 date standing among three statutory ones reads as law from
# 1981, which is exactly what a VDI convention is not.
DEGREE_DAY_LABEL = "Gradtagszahlen-Promilletabelle (VDI-Konvention, keine Rechtsnorm)"

_FIXED_LABELS: dict[str, str] = {DEGREE_DAY_TABLE.key: DEGREE_DAY_LABEL}


def rechtsstand_entry[T](rule: ResolvedRule[T]) -> str:
    """``§ 7 Abs. 1 HeizkostenV 03/1989`` — the rule's label beside its stamp.

    The label is the store's own ``source`` for every rule that has a citation
    to print, so a store edit moves the statement instead of drifting from it.
    ``_FIXED_LABELS`` is the documented exception above.

    The word ``Rechtsstand`` is stripped here because the footer prints it once,
    as a prefix; the entry carries only the date.
    """
    label = _FIXED_LABELS.get(rule.key, rule.source)
    stamp = rule.rechtsstand.removeprefix("Rechtsstand ").strip()
    return f"{label} {stamp}"
