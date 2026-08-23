"""Refusals this engine raises rather than guessing — `docs/15-bank-matching.md`.

`docs/15` § 5.2 records one genuinely missing convention.  Where a source is silent
about a rule that would change money, the engine refuses.  A statement built on an
invented convention is not approximately right, it is wrong (`CLAUDE.md` § 4: "If an
original Page, annex or register contradicts its approved doc, stop and ask.  Do not
choose silently.").
"""

from __future__ import annotations


class MatchingEngineError(Exception):
    """Base class for every refusal raised by the bank-matching engine."""


class TieBreakUnspecifiedError(MatchingEngineError):
    """Two Largest-Remainder candidates tie and no source says which one wins.

    `docs/15` § 5.2, verbatim: *"Page 08 does not specify the tie-break between equal
    fractional remainders; that missing deterministic convention must be added to the
    authoritative source before a future implementation claims the unexercised tie
    branch."*

    Picking "lowest index", "largest nominal" or any other order here would fabricate a
    distribution convention for renter money.  The engine therefore stops.  Delete this
    branch only once original Page 08 (or an approved correction to it) states the rule.
    """
