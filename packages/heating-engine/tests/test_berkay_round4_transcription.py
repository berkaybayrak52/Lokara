"""Executable data-only checks for the Round-4 Page-01b transcription."""

from berkay_round4_golden import ROUND4_PAGE_01B


def test_round4_reduction_has_exactly_three_independent_non_cascading_summands() -> None:
    reduction = ROUND4_PAGE_01B["reduction"]
    assert isinstance(reduction, dict)
    summands = reduction["summands"]
    assert isinstance(summands, tuple)
    assert len(summands) == 3
    assert tuple(item[2] for item in summands) == (15, 3, 3)
    assert all(item[3] is True for item in summands)
    assert reduction["one_unreduced_base_per_summand"] is True
    assert reduction["non_cascading"] is True
    assert reduction["maximum_percent"] == 21
    assert reduction["warning_at_simultaneous_grounds"] == 2
    assert reduction["warning_blocking"] is False


def test_round4_block_c_is_audited_owner_residual_subline_not_a_second_amount() -> None:
    block_c = ROUND4_PAGE_01B["block_c"]
    assert isinstance(block_c, dict)
    assert block_c["is_owner_residual_subline"] is True
    assert block_c["separate_pot"] is False
    assert block_c["has_bemessung"] is False
    assert block_c["has_quota"] is False
    assert block_c["print_only_when_nonzero"] is True
    assert block_c["audit_log_always"] is True
    assert "Rundungsdifferenz" in str(block_c["vacancy_schedule_text"])
    assert block_c["statement_text"] == "davon Rundungsdifferenz"
