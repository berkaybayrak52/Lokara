"""Personenschlüssel inputs: entered counts, plus the derived D0 Fiktivbelegung.

This module is the layer `docs/02` § 5 decided should own the D0 convention. The
NK engine takes a landlord-side `PersonCountPeriod` as given and weights it by
days; deriving the count needs a person-count *history*, and a unit vacant for a
whole billing period needs a figure from before that period — a lookup a pure,
history-free engine must not be able to perform (`CLAUDE.md` § 3.1).

So the split is: the engine owns "a fictional occupancy is a denominator weight
on the landlord side", and this module owns "which number, for which days".

What is derived here is never stored. Vacancy is always the remainder of the
timeline (`docs/02`: "Vacancy is never stored"), and the fictional count on top
of it is a flagged convention applied at calculation time — `Konvention`,
`verify-before-production`, Rechtsstand 07/2026, resting on split instance case
law (LG Krefeld 2 S 56/09; BGH VIII ZR 180/12 leaves the Ansatz a Tatfrage).
Persisting it would make a convention look like entered data and would freeze it
against the pending legal review.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from lokara_db import FiktivbelegungMode, PersonCount, SelfUsePeriod, Tenancy, Unit
from lokara_domain import Occupancy, Period, build_unit_segments
from lokara_nk_engine import PersonCountPeriod
from lokara_pdf import format_number_de
from sqlalchemy import select
from sqlalchemy.orm import Session

# Page 01 § 3.5: `wohnung.letzteBelegungPersonen`, "integer, ≥ 1 … fallback 1".
# The floor is not cosmetic — it is what keeps a derived branch from collapsing
# into the `keine` denominator, which is the constellation the cited decisions
# reject (Page 01 E18).
_MINIMUM_DERIVED_PERSONS = 1

# A half-open day range `[from, to)`, the same convention as `Period` and as the
# occupancy timeline. Local to this module's interval arithmetic — it never
# reaches an engine, which takes `Period`.
_Span = tuple[date, date]


@dataclass(frozen=True)
class PersonCountInputs:
    """Entered person counts plus the derived D0 rows, and what had to be said."""

    rows: tuple[PersonCountPeriod, ...]
    # German, statement-facing. A derivation that had to make an assumption says
    # so on the document rather than resolving it silently (docs/08 rule 1).
    findings: tuple[str, ...]


def person_count_inputs(
    session: Session,
    *,
    units: list[Unit],
    occupancies: tuple[Occupancy, ...],
    window: Period,
    mode: FiktivbelegungMode,
) -> PersonCountInputs:
    """Every `PersonCountPeriod` the PERSONS key needs for one building period."""
    entered = _entered_rows(session, units)
    derived, findings = _fictional_rows(session, units, occupancies, window, mode)
    return PersonCountInputs(rows=(*entered, *derived), findings=findings)


def _entered_rows(session: Session, units: list[Unit]) -> tuple[PersonCountPeriod, ...]:
    """The Personenzahl a landlord actually entered, clipped to its own tenancy.

    **Not** clipped to the billing window — the engine already intersects each
    row with it (`overlap_days`), and clipping twice is how a day goes missing.

    Clipped to the *tenancy*, though, and that is a different clip. A row may
    run open-ended (`valid_to IS NULL`, "still this many people"), and nothing
    closes it when the lease ends: no CHECK can express it and no FK implies it.
    Left alone, a person count would keep counting a renter who had already
    moved out — over exactly the days D0 then adds a fictional occupancy for, so
    the same days would be counted twice and every share in the building would
    be wrong. `docs/02` § 5 adds the fiction to days that belong to nobody.

    A row entirely outside its tenancy contributes nothing and is dropped rather
    than clamped to an empty period.
    """
    tenancy_periods = {
        tenancy.id: (tenancy.valid_from, tenancy.valid_to)
        for unit in units
        for tenancy in unit.tenancies
    }
    if not tenancy_periods:
        return ()
    rows = session.scalars(
        select(PersonCount)
        .where(PersonCount.tenancy_id.in_(list(tenancy_periods)))
        .order_by(PersonCount.valid_from, PersonCount.id)
    ).all()
    entered: list[PersonCountPeriod] = []
    for row in rows:
        tenancy_from, tenancy_to = tenancy_periods[row.tenancy_id]
        start = max(row.valid_from, tenancy_from)
        end = _earliest(row.valid_to, tenancy_to)
        if end is not None and start >= end:
            continue
        entered.append(
            PersonCountPeriod(tenancy_id=row.tenancy_id, count=row.count, period=Period(start, end))
        )
    return tuple(entered)


def _earliest(left: date | None, right: date | None) -> date | None:
    """The earlier of two half-open ends, where `None` means "still running"."""
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def _fictional_rows(
    session: Session,
    units: list[Unit],
    occupancies: tuple[Occupancy, ...],
    window: Period,
    mode: FiktivbelegungMode,
) -> tuple[tuple[PersonCountPeriod, ...], tuple[str, ...]]:
    """D0: one landlord row per vacancy period of each unit.

        for each Leerstandsperiode L of a unit:
          letzteBelegung -> max(1, wohnung.letzteBelegungPersonen)
          immer1         -> 1
          keine          -> 0   // only with logged confirmation
          nPersTage += fiktivPersonen x L.tage

    `keine` emits **no row at all** rather than a zero-weight one: a zero
    landlord line would print as a party contributing nothing, which is a
    different statement from "this building applies no fictional occupancy".
    """
    if mode is FiktivbelegungMode.KEINE:
        return (), ()

    assert window.valid_to is not None  # the billing window is always bounded
    rows: list[PersonCountPeriod] = []
    findings: list[str] = []
    for unit in units:
        self_used, partial = _self_use_spans(session, unit, window)
        segments = build_unit_segments(unit.id, occupancies, window.valid_from, window.valid_to)
        gaps = [
            (segment.start, segment.start + timedelta(days=segment.days))
            for segment in segments
            if segment.tenancy_id is None
        ]
        # Only a partial self-use that actually meets vacancy is worth saying.
        # Reported here rather than where the spans are read, because whether a
        # gap exists is not knowable until the timeline is built — and a finding
        # about days that do not exist is worse than no finding.
        findings.extend(note for span, note in partial if any(_overlaps(span, gap) for gap in gaps))
        for gap in gaps:
            for start, end in _subtract(gap, self_used):
                period = Period(valid_from=start, valid_to=end)
                persons = (
                    _MINIMUM_DERIVED_PERSONS
                    if mode is FiktivbelegungMode.IMMER_1
                    else max(_MINIMUM_DERIVED_PERSONS, _last_known_persons(session, unit, period))
                )
                rows.append(
                    PersonCountPeriod(
                        tenancy_id=None,
                        count=persons,
                        period=period,
                        unit_id=unit.id,
                    )
                )
    return tuple(rows), tuple(findings)


def _self_use_spans(
    session: Session, unit: Unit, window: Period
) -> tuple[tuple[_Span, ...], tuple[tuple[_Span, str], ...]]:
    """Which days of this unit are self-used rather than vacant — and what we cannot tell.

    `docs/02` § 4 separates the two states: `VACANT` is "neither rented nor
    self-used", and Page 01 § 4 D0 runs "for each Leerstandsperiode". So a
    self-used day is not a D0 vacancy day and gets no fictional occupancy.

    The hard part is that `SelfUsePeriod` stores an **area**, not a flag
    (`sqm_x100`, "partial self-use is an area, not a boolean"), and Page 01 has
    no rule for a partial self-use overlapping a vacancy. Full-unit self-use is
    unambiguous and suppresses the fiction for exactly the days it covers. A
    partial one leaves those days as vacancy and says so on the document — the
    conservative direction, because dropping the fiction there would hand the
    renters the person-keyed fixed cost, which is exactly what BGH VIII ZR
    159/05 and LG Krefeld 2 S 56/09 reject. Recorded as an open source question
    in `FRAGEN-an-Berkay-04.md`.

    An open-ended row (`valid_to IS NULL`) is clipped to the window, not treated
    as infinite: a self-use that is still running covers the rest of this period
    and nothing beyond it.
    """
    assert window.valid_to is not None
    spans: list[_Span] = []
    findings: list[tuple[_Span, str]] = []
    for row in session.scalars(
        select(SelfUsePeriod)
        .where(SelfUsePeriod.unit_id == unit.id)
        .order_by(SelfUsePeriod.valid_from, SelfUsePeriod.id)
    ).all():
        start = max(row.valid_from, window.valid_from)
        end = min(row.valid_to or window.valid_to, window.valid_to)
        if start >= end:
            continue
        if row.sqm_x100 >= unit.area_sqm_x100:
            spans.append((start, end))
            continue
        # Paired with its span so the caller can drop it when the unit turns out
        # to have no vacancy for it to meet. Areas go through `format_number_de`
        # like every other figure on a German document — `20,00`, not `20.00`,
        # and via Decimal rather than a float division of two integers.
        findings.append(
            (
                (start, end),
                f"{unit.label}: Teil-Eigennutzung "
                f"({format_number_de(Decimal(row.sqm_x100) / 100)} m² von "
                f"{format_number_de(Decimal(unit.area_sqm_x100) / 100)} m²) vom "
                f"{start.strftime('%d.%m.%Y')} bis "
                f"{(end - timedelta(days=1)).strftime('%d.%m.%Y')}. Leerstandstage in diesem "
                "Zeitraum werden mit Fiktivbelegung gerechnet; die anteilige Eigennutzung ist "
                "nicht abgegrenzt.",
            )
        )
    return tuple(spans), tuple(findings)


def _overlaps(left: _Span, right: _Span) -> bool:
    """Do two half-open day ranges share at least one day?"""
    return left[0] < right[1] and right[0] < left[1]


def _subtract(gap: _Span, covered: tuple[_Span, ...]) -> tuple[_Span, ...]:
    """`gap` minus every span in `covered`, as the half-open pieces that survive.

    A list rather than a boolean because a self-use period can start or end
    inside a vacancy gap, leaving vacancy on one or both sides. Collapsing that
    to "covered / not covered" would either invent self-use days or invent
    vacancy days, and both change the person-day denominator.
    """
    pieces = [gap]
    for cover_from, cover_to in covered:
        remaining: list[_Span] = []
        for start, end in pieces:
            if cover_to <= start or cover_from >= end:
                remaining.append((start, end))
                continue
            if start < cover_from:
                remaining.append((start, cover_from))
            if cover_to < end:
                remaining.append((cover_to, end))
        pieces = remaining
    return tuple(pieces)


def _last_known_persons(session: Session, unit: Unit, gap: Period) -> int:
    """Page 01 § 3.5 `wohnung.letzteBelegungPersonen` — "last ended tenancy of
    that unit; fallback 1".

    Looked up in the database rather than in `NkInput`, and deliberately not
    restricted to the billing period: a unit that stood empty all year has no
    in-period history at all, and its last count comes from before the period.
    That single sentence is why this lives here and not in the engine.
    """
    tenancy = session.scalars(
        select(Tenancy)
        .where(
            Tenancy.unit_id == unit.id,
            Tenancy.valid_from <= gap.valid_from,
        )
        .order_by(Tenancy.valid_from.desc(), Tenancy.id.desc())
    ).first()
    if tenancy is None:
        return _MINIMUM_DERIVED_PERSONS
    latest = session.scalars(
        select(PersonCount)
        .where(PersonCount.tenancy_id == tenancy.id)
        .order_by(PersonCount.valid_from.desc(), PersonCount.id.desc())
    ).first()
    if latest is None:
        return _MINIMUM_DERIVED_PERSONS
    return latest.count
