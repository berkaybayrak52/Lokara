"""Slice B's executable-coverage harness for Page 01 (`08-F01` … `08-F24`).

Spec: `docs/08-statement-document.md` — "Page 01 output contract", § 4 ("#4 is
blocked on the M6 ledger, by decision"), § 8 and Appendix A;
`docs/02-data-model.md` § 5 "Owner residual and Page 01 statement model".
Rechtsstand 08/2026 (the register rows listed in `docs/08` Appendix B).

Why this file exists
--------------------
Slice B reconciles the **persisted calculation path** with Page 01. It does not
own actual paid advances, `Saldo`/`Nachzahlung`/`Guthaben`, immutable
finalization, isolated tenant documents or archives — `docs/08` § 4 and § 8 give
all of those to M6, and `docs/02` § 6 gives M6 the ledger handoff. Most Page 01
fixtures are therefore *mixed*: an allocation half that belongs to this slice and
a Saldo/document half that does not.

The risk this harness closes is a silent one: a fixture that nobody implements
because everyone assumes someone else owned it, or a fixture quietly re-labelled
"M6" to make a slice look finished. So the split is committed as **data**, every
ID carries the rule or dependency that put it in its bucket, and the tests below
assert that the three buckets are a partition of the exact 24-ID set.

Bucket names are the ones the slice plan fixed. `PARTIAL_M6_SALDO` is the widest
of the three: for most of its members the deferred half really is the Saldo, but
for `08-F16`, `08-F17` and `08-F21` it is the M6 document/archive projection
instead. Each `reason` says which, so the label never has to be guessed from the
bucket name alone.

Two further fields sit beside the bucket, and they are deliberately not the same
field, because they have opposite consequences:

* `slice_c_rounding_block` — several Page 01 cent figures are only reproducible
  with the renter half-up + owner-residual method of `docs/02` § 5, while
  production NK stays on largest remainder (`CLAUDE.md` § 8.4; `docs/08` § 3a:
  "production NK remains on its pre-Page-02 method"). The ruling for this slice
  is to keep it that way, so those cents are **deferred to Slice C** and no
  Slice B code change may claim them. A fixture carrying this cannot be called
  executable here, whatever else about it is reachable.
* `slice_b_engine_gap` — a missing engine behaviour that **is** this slice's to
  close, named per fixture so the two are never conflated. Deferring a rounding
  rule is not permission to leave a hole in the input shape or a crash in the
  allocator.

This file asserts no money. It is a coverage gate over the committed oracle in
`berkay_01_golden.py`, which it must never edit.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from berkay_01_golden import PAGE_01_GOLDENS


class SliceBBucket(StrEnum):
    """Where a Page 01 fixture can be driven from, and by whom."""

    EXECUTABLE_IN_SLICE_B = "EXECUTABLE_IN_SLICE_B"
    """Drivable end to end through production code (NK engine, heating engine,
    domain primitives) inside Slice B."""

    PARTIAL_M6_SALDO = "PARTIAL_M6_SALDO"
    """The allocation half is Slice B; the Saldo — or, where the reason says so,
    the M6 document/archive projection — waits for M6."""

    M6_ONLY = "M6_ONLY"
    """Nothing in the fixture is reachable before the M6 ledger exists."""


@dataclass(frozen=True)
class Classification:
    """One auditable line of the split: bucket, why, and where that 'why' is written."""

    bucket: SliceBBucket
    reason: str
    docs_anchor: str
    slice_c_rounding_block: str | None = None
    slice_b_engine_gap: str | None = None


_EXECUTABLE = SliceBBucket.EXECUTABLE_IN_SLICE_B
_PARTIAL = SliceBBucket.PARTIAL_M6_SALDO
_M6_ONLY = SliceBBucket.M6_ONLY

# Deferred to Slice C by decision: the cents are docs/02 § 5 renter half-up +
# owner residual, and production NK keeps largest remainder (CLAUDE.md § 8.4,
# docs/08 § 3a). Verified by arithmetic in the Slice B RED-test session.
_SLICE_C_ROUNDING = (
    "cent figures are docs/02 § 5 half-up + owner residual; production NK keeps largest "
    "remainder in Slice B by decision, so these cents are deferred to Slice C "
    "(CLAUDE.md § 8.4, docs/08 § 3a)"
)
# 08-F11's own trap, and the reason its net-first discrimination is unobservable
# before Slice C rather than merely one cent away.
_F11_NET_FIRST_INDISTINGUISHABLE = (
    "under largest remainder the credit line is -883, so line-wise gives 10.060 — exactly "
    "08-F11's forbidden_net_first_share (57.000 × 365/2.068 = 10.060,4); correct and "
    "forbidden coincide until the rounding moves"
)
# Where 08-F22's two methods actually part company, computed in the B3a session:
# without_fiction reproduces identically under both, so only the with-fiction half
# is deferred.
_F22_WHERE_THE_METHODS_DIVERGE = (
    "verified: without_fiction (33.843/13.105/3.771/11.281) is identical under both methods, "
    "while largest remainder gives Weber 3.657 and the owner 1.859 against the golden's "
    "with_fiction 3.658 and owner_residual 1.858"
)
# Slice B work, and not to be confused with the deferral above: the fictional
# occupancy of a vacant unit (D0) has no NK input shape, because
# `PersonCountPeriod.tenancy_id` is a required `str`.
_D0_INPUT_SHAPE = (
    "D0 Fiktivbelegung has no NK input shape: PersonCountPeriod requires a tenancy_id, so the "
    "derived fictional person-days cannot enter the PERSONS denominator at all; the count itself "
    "is the register convention 'Fiktivbelegung bei Leerstand' (last known occupancy of the unit, "
    "minimum 1, day-exact, switchable to always-1; Konvention, verify-before-production, "
    "Rechtsstand 07/2026), and which layer derives it is an open decision recorded in docs/02 § 5"
)
_NEGATIVE_COST_CRASHES = (
    "a credit is unrepresentable: distribute_cents floors with int(q // 1) and Decimal "
    "truncates toward zero, so a negative total trips its own reconciliation assert"
)
_ZERO_DENOMINATOR_REFUSED = (
    "a zero consumption denominator raises NkInputError instead of leaving the cost on "
    "the landlord side"
)
_OVERLAP_ERROR_CARRIES_NO_FIGURE = (
    "OccupancyOverlapError carries one unit and one date in a message, so the statement "
    "cannot state the over-allocated Bemessung"
)
_NO_TWELVE_MONTH_BLOCK = (
    "_billing_window rejects only an unbounded period, so a period longer than 12 months "
    "is allocated instead of hard-blocked"
)

PAGE_01_SLICE_B_CLASSIFICATION: Final[dict[str, Classification]] = {
    "08-F01": Classification(
        bucket=_PARTIAL,
        reason=(
            "allocation, cost total and owner residual are calculation; the four advances, "
            "balances and § 35a payout figures need M6 actual paid advances"
        ),
        docs_anchor="docs/08 § 4 minimum #4 + Appendix A 08-F01",
        slice_c_rounding_block=_SLICE_C_ROUNDING,
    ),
    "08-F02": Classification(
        bucket=_M6_ONLY,
        reason="the fixture is one Nachzahlung branch: share - geleistete Vorauszahlung",
        docs_anchor="docs/08 'Saldo uses actual payments' + § 4 minimum #4",
    ),
    "08-F03": Classification(
        bucket=_M6_ONLY,
        reason="the fixture is one Guthaben branch and nothing else",
        docs_anchor="docs/08 'Saldo uses actual payments' + § 4 minimum #4",
    ),
    "08-F04": Classification(
        bucket=_M6_ONLY,
        reason="the zero-Saldo branch presupposes an accepted actual-advance allocation",
        docs_anchor="docs/08 'Saldo uses actual payments' + § 4 minimum #4",
    ),
    "08-F05": Classification(
        bucket=_PARTIAL,
        reason=(
            "heat-pump path with no CO₂ block and no § 35a block is engine behaviour; "
            "its advance and balance are M6"
        ),
        docs_anchor="docs/08 § 6.5 (no CO₂ block) + § 4 minimum #4",
    ),
    "08-F06": Classification(
        bucket=_PARTIAL,
        reason=(
            "the owner overview reconciling with an unconditional owner column including zeros "
            "is calculation; its positive-balance and credit totals are M6 aggregates"
        ),
        docs_anchor="docs/08 'The owner view reconciles' + docs/02 § 5",
        slice_c_rounding_block=_SLICE_C_ROUNDING,
    ),
    "08-F07": Classification(
        bucket=_EXECUTABLE,
        reason=(
            "MDL evidence pass-through and 'device delta moves no money' are pure result "
            "behaviour; PLAN gives Slice B the OCR confirmation and statement projection"
        ),
        docs_anchor="docs/08 § 8 (MDL and device-evidence rows)",
    ),
    "08-F09": Classification(
        bucket=_EXECUTABLE,
        reason=(
            "CO₂ mass, annualised intensity, band, landlord share and renter shares come from "
            "the shipped heating engine; no advance and no ledger input appears"
        ),
        docs_anchor="docs/08 § 6.5 + § 8 (CO₂ duty row)",
    ),
    "08-F08": Classification(
        bucket=_PARTIAL,
        reason=(
            "§ 9a area fallback and the mixed-path control difference are engine results that "
            "must hard-warn; the party's advance and balance are M6"
        ),
        docs_anchor="docs/08 § 6 (§ 9a branch) + § 4 minimum #4",
    ),
    "08-F10": Classification(
        bucket=_M6_ONLY,
        reason=(
            "the whole fixture is the advance contract: NULL hard-blocks, confirmed zero is "
            "valid, and only then does a Nachzahlung exist"
        ),
        docs_anchor="docs/08 'Saldo uses actual payments' + docs/02 § 5 finalization list",
    ),
    "08-F11": Classification(
        bucket=_PARTIAL,
        reason=(
            "the structural half - a credit allocating at all and surviving as its own line - "
            "is Slice B; the deferred half is Slice C rounding, not M6"
        ),
        docs_anchor="docs/08 'No document-layer money math' + Appendix A 08-F11",
        slice_c_rounding_block=f"{_SLICE_C_ROUNDING}; {_F11_NET_FIRST_INDISTINGUISHABLE}",
        slice_b_engine_gap=_NEGATIVE_COST_CRASHES,
    ),
    "08-F12": Classification(
        bucket=_PARTIAL,
        reason=(
            "the zero consumption denominator leaving the whole cost with the owner and never "
            "re-keying to AREA is engine behaviour; the -24.871 balance is M6"
        ),
        docs_anchor="docs/02 § 5 basis table (zero denominator) + docs/08 output contract",
        slice_b_engine_gap=_ZERO_DENOMINATOR_REFUSED,
    ),
    "08-F13": Classification(
        bucket=_EXECUTABLE,
        reason=(
            "overlapping tenancies in one unit must block before calculation or rendering, "
            "which happens in the occupancy timeline with no ledger input"
        ),
        docs_anchor="docs/02 § 5 finalization list (overlapping tenancies block)",
        slice_b_engine_gap=_OVERLAP_ERROR_CARRIES_NO_FIGURE,
    ),
    "08-F14": Classification(
        bucket=_PARTIAL,
        reason=(
            "the 275-day Rumpfperiode is day-exact allocation; its Saldo 1.800 is M6 and its "
            "31.12.2026 deadline result belongs to docs/12"
        ),
        docs_anchor="docs/08 'Period boundary' + § 4 minimum #4",
    ),
    "08-F15": Classification(
        bucket=_EXECUTABLE,
        reason=(
            "'more than 12 months hard-blocks before an engine run or render' is an engine "
            "precondition; no cost is ever allocated"
        ),
        docs_anchor="docs/02 § 5 step 1 + docs/08 'Period boundary'",
        slice_b_engine_gap=_NO_TWELVE_MONTH_BLOCK,
    ),
    "08-F16": Classification(
        bucket=_PARTIAL,
        reason=(
            "clipped usage days, area-days and the two shares are calculation; two isolated "
            "documents with no cross-leakage and their balances are M6 finalization"
        ),
        docs_anchor="docs/08 § 3 (audience split) + 'Tenancy changes create separate documents'",
    ),
    "08-F17": Classification(
        bucket=_PARTIAL,
        reason=(
            "zero clipped usage days producing a zero share and no vacancy is calculation; "
            "'no tenant document and no portal item' is M6/M10 finalization, not Saldo"
        ),
        docs_anchor="docs/08 'Tenancy changes create separate documents' + docs/02 § 5",
    ),
    "08-F18": Classification(
        bucket=_M6_ONLY,
        reason=(
            "suppressing a late Nachforderung while keeping 'Rechnerischer Saldo' visible "
            "presupposes a Saldo, so nothing exists before the M6 ledger"
        ),
        docs_anchor="docs/08 'Deadline behavior' + § 4 minimum #4",
    ),
    "08-F19": Classification(
        bucket=_M6_ONLY,
        reason="a late Guthaben remaining payable is a Saldo branch and needs actual advances",
        docs_anchor="docs/08 'Deadline behavior' + § 4 minimum #4",
    ),
    "08-F20": Classification(
        bucket=_EXECUTABLE,
        reason=(
            "'leap years keep their actual days' is day arithmetic over the billing window "
            "with no special money rule and no advance"
        ),
        docs_anchor="docs/08 'Period boundary' + docs/02 § 5 step 1",
    ),
    "08-F21": Classification(
        bucket=_PARTIAL,
        reason=(
            "block (a) vacancy origins are calculation; block (b) needs the docs/09 "
            "non-allocable classification (Slice C) and the Leerstandsaufstellung itself is "
            "the M6/tax projection, not a Saldo"
        ),
        docs_anchor="docs/08 § 3 (Leerstandsaufstellung: Specified, M6/tax handoff) + docs/02 § 5",
        slice_c_rounding_block=_SLICE_C_ROUNDING,
    ),
    "08-F22": Classification(
        bucket=_PARTIAL,
        reason=(
            "the fictional occupancy entering the person-day denominator is Slice B engine "
            "work; its owner-residual cents are Slice C, and neither half is M6"
        ),
        docs_anchor="docs/02 § 5 basis table (Persons row) + docs/08 Appendix A 08-F22",
        slice_c_rounding_block=f"{_SLICE_C_ROUNDING}; {_F22_WHERE_THE_METHODS_DIVERGE}",
        slice_b_engine_gap=_D0_INPUT_SHAPE,
    ),
    "08-F23": Classification(
        bucket=_PARTIAL,
        reason=(
            "'vacancy stays in the denominators' is Slice B allocation over area-days and "
            "person-days; the Leerstandsaufstellung row and the suppressed tenant document are M6"
        ),
        docs_anchor=(
            "docs/02 § 5 basis table (Area and Persons rows) + docs/08 § 3 "
            "(Leerstandsaufstellung: M6/tax handoff)"
        ),
        slice_b_engine_gap=_D0_INPUT_SHAPE,
    ),
    "08-F24": Classification(
        bucket=_PARTIAL,
        reason=(
            "the self-billing heating path, its CO₂ deduction and the owner residual are "
            "calculation; the four advances and balances are M6"
        ),
        docs_anchor="docs/08 'Heating and CO₂ project docs/03' + § 4 minimum #4",
    ),
}

EXPECTED_PAGE_01_IDS: Final[frozenset[str]] = frozenset(
    f"08-F{number:02}" for number in range(1, 25)
)

# A fixture field naming what a renter actually paid, or a result derived from
# it. `docs/08` § 4: minimum #4 deducts *geleistete* advances, and that ledger
# is M6 by decision — so no fixture carrying one of these is executable now.
_M6_ADVANCE_FIELD_MARKERS: Final[tuple[str, ...]] = ("advance", "balance")
_M6_DERIVED_FIELDS: Final[frozenset[str]] = frozenset({"credits"})

# Verified by arithmetic in the Slice B RED-test session, not by reading:
# each of these reproduces only under docs/02 § 5 half-up + owner residual,
# and is therefore deferred to Slice C.
# 08-F23 was on this list and is not any more: its two owner cents were computed
# both ways in the B3a session and are method-independent (property_tax_owner
# 37.381 = 98.000 × 27.010/70.810 truncated, and the same figure as the half-up
# residual; waste_owner 20.667 likewise holds the largest fractional remainder
# either way), so no rounding decision is waiting on it.
_SLICE_C_DEFERRED_IDS: Final[frozenset[str]] = frozenset(
    {"08-F01", "08-F06", "08-F11", "08-F21", "08-F22"}
)
# Engine behaviour this slice owes, one named gap per fixture. These are the
# four gaps `packages/nk-engine/tests/test_page01_edge_cases.py` drives red,
# plus the D0 input shape `08-F22`/`08-F23` need, which
# `packages/nk-engine/tests/test_page01_vacancy_denominators.py` pins as
# `xfail(strict=True)`: the assertions run in full, and closing the gap makes them
# XPASS(strict) — a failure the implementer has to clear by reading them.
_SLICE_B_ENGINE_GAP_IDS: Final[frozenset[str]] = frozenset(
    {"08-F11", "08-F12", "08-F13", "08-F15", "08-F22", "08-F23"}
)


def _bucket_ids(bucket: SliceBBucket) -> frozenset[str]:
    return frozenset(
        fixture_id
        for fixture_id, entry in PAGE_01_SLICE_B_CLASSIFICATION.items()
        if entry.bucket is bucket
    )


def _m6_advance_fields(fixture_id: str) -> frozenset[str]:
    case = PAGE_01_GOLDENS[fixture_id]
    assert isinstance(case, dict)
    return frozenset(
        field
        for field in case
        if field in _M6_DERIVED_FIELDS
        or any(marker in field for marker in _M6_ADVANCE_FIELD_MARKERS)
    )


def test_the_classification_covers_exactly_the_24_page_01_fixture_ids() -> None:
    """The anti-skip gate: the split is over the whole Page 01 oracle, not a subset."""
    assert set(PAGE_01_SLICE_B_CLASSIFICATION) == set(EXPECTED_PAGE_01_IDS)
    assert set(PAGE_01_GOLDENS) == set(EXPECTED_PAGE_01_IDS)


def test_the_three_buckets_partition_the_fixture_set() -> None:
    executable = _bucket_ids(SliceBBucket.EXECUTABLE_IN_SLICE_B)
    partial = _bucket_ids(SliceBBucket.PARTIAL_M6_SALDO)
    m6_only = _bucket_ids(SliceBBucket.M6_ONLY)

    assert executable | partial | m6_only == EXPECTED_PAGE_01_IDS
    assert not executable & partial
    assert not executable & m6_only
    assert not partial & m6_only
    assert len(executable) + len(partial) + len(m6_only) == len(EXPECTED_PAGE_01_IDS)


def test_no_bucket_is_empty_and_the_split_is_the_committed_one() -> None:
    """Pins the shape of the split.

    A later edit may move a fixture — but it then has to change this count, which
    makes the move visible in review instead of silently shrinking the slice.
    """
    assert len(_bucket_ids(SliceBBucket.EXECUTABLE_IN_SLICE_B)) == 5
    assert len(_bucket_ids(SliceBBucket.PARTIAL_M6_SALDO)) == 13
    assert len(_bucket_ids(SliceBBucket.M6_ONLY)) == 6


def test_every_classification_states_a_reason_and_a_docs_anchor() -> None:
    """A bucket without a written rule behind it is an opinion, not a classification."""
    for fixture_id, entry in PAGE_01_SLICE_B_CLASSIFICATION.items():
        assert entry.reason.strip(), fixture_id
        assert "\n" not in entry.reason, f"{fixture_id}: the reason stays one line"
        assert entry.docs_anchor.startswith("docs/"), fixture_id
        for blocker in (entry.slice_c_rounding_block, entry.slice_b_engine_gap):
            if blocker is not None:
                assert blocker.strip(), fixture_id


def test_no_executable_fixture_depends_on_an_actual_advance() -> None:
    """`docs/08` § 4: minimum #4 deducts geleistete advances, and that ledger is M6.

    So a fixture that records an advance, a balance or a credit total cannot be
    called executable in Slice B — this is the mechanical cross-check of the
    judgement above against the committed oracle's own fields.
    """
    for fixture_id in _bucket_ids(SliceBBucket.EXECUTABLE_IN_SLICE_B):
        assert _m6_advance_fields(fixture_id) == frozenset(), fixture_id


def test_every_m6_only_fixture_actually_carries_an_advance_or_balance_field() -> None:
    """The converse guard: `M6_ONLY` may not become a parking lot.

    A fixture is only unreachable-before-M6 if what it records *is* the advance
    or its Saldo. Anything else has a calculation half and belongs in
    `PARTIAL_M6_SALDO` with the split named.
    """
    for fixture_id in _bucket_ids(SliceBBucket.M6_ONLY):
        assert _m6_advance_fields(fixture_id) != frozenset(), fixture_id


def test_the_slice_c_rounding_deferral_is_recorded_where_it_was_verified() -> None:
    """`CLAUDE.md` § 8.4 keeps NK on largest remainder until the Page 02 work.

    These five fixtures state cents that only the `docs/02` § 5 renter half-up +
    owner-residual method produces. `08-F11` is the sharpest case: under largest
    remainder its credit line is -883, so the line-wise total is 10.060 — exactly
    the `forbidden_net_first_share` the fixture rules out. Correct and forbidden
    coincide, so the discrimination is not merely one cent away in Slice B, it is
    unobservable until the rounding moves.

    `08-F22` is the narrow case: its `without_fiction` tuple reproduces under
    both methods and is asserted in
    `packages/nk-engine/tests/test_page01_vacancy_denominators.py`; only the
    with-fiction half (Weber `3.658` vs `3.657`, owner `1.858` vs `1.859`) is
    deferred.
    """
    flagged = frozenset(
        fixture_id
        for fixture_id, entry in PAGE_01_SLICE_B_CLASSIFICATION.items()
        if entry.slice_c_rounding_block is not None
    )
    assert flagged == _SLICE_C_DEFERRED_IDS


def test_a_slice_c_deferral_is_never_left_in_the_executable_bucket() -> None:
    """The deferral has to cost a bucket, or it is decoration.

    A fixture whose cents wait for Slice C cannot also be reported as closable
    here, however much of its structure this slice does prove.
    """
    assert not (_SLICE_C_DEFERRED_IDS & _bucket_ids(SliceBBucket.EXECUTABLE_IN_SLICE_B))


def test_the_slice_b_engine_gaps_stay_named_and_separate_from_the_deferral() -> None:
    """Deferring a rounding rule is not permission to leave a hole in the engine.

    `08-F22` carries both fields at once and is exactly why they are two fields:
    its with-fiction cents wait for Slice C, while the D0 landlord-side
    person-day input that feeds them is this slice's to build.

    `08-F23` is the case that shows the two fields really are independent. It
    carries the same D0 gap and **no** rounding block: its owner cents come out
    the same under either method, so the only thing standing between it and a
    green run is engine work this slice owns.
    """
    flagged = frozenset(
        fixture_id
        for fixture_id, entry in PAGE_01_SLICE_B_CLASSIFICATION.items()
        if entry.slice_b_engine_gap is not None
    )
    assert flagged == _SLICE_B_ENGINE_GAP_IDS

    with_both = PAGE_01_SLICE_B_CLASSIFICATION["08-F22"]
    assert with_both.slice_c_rounding_block is not None
    assert with_both.slice_b_engine_gap is not None
    assert with_both.slice_b_engine_gap != with_both.slice_c_rounding_block

    gap_only = PAGE_01_SLICE_B_CLASSIFICATION["08-F23"]
    assert gap_only.slice_b_engine_gap == _D0_INPUT_SHAPE
    assert gap_only.slice_c_rounding_block is None
