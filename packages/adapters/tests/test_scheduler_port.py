"""Port conformance for the M6-C3b scheduler boundary (`docs/15` § 5.6).

`StubScheduler` is consumed **through `SchedulerPort`**, the pattern of
`test_ports_and_stubs.py`: mypy strict then enforces the structural conformance
these annotations claim, so a stub drifting from its port breaks the build.

`docs/15` § 5.6 pins the rules asserted here — `interval_days >= 1`, replace on the
same `(name, account_id)`, deterministic `(name, account_id)` ordering, `last_run_at
is None` means due, timezone-aware datetimes only, and `due_jobs` executes nothing.
Redis, Arq and Celery stay uninstalled (`docs/01` D7); this port exists so the
process boundary is designed before a queue is chosen.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest
from lokara_adapters import ScheduledJob, SchedulerPort, StubScheduler

_NOW = datetime(2026, 8, 24, 6, 0, tzinfo=UTC)


def _job(
    name: str = "sync_bank_transactions",
    account_id: str = "acc-1",
    interval_days: int = 1,
    last_run_at: datetime | None = None,
) -> ScheduledJob:
    return ScheduledJob(
        name=name,
        account_id=account_id,
        interval_days=interval_days,
        last_run_at=last_run_at,
    )


class TestScheduledJob:
    def test_the_record_is_frozen(self) -> None:
        job = _job()
        with pytest.raises(FrozenInstanceError):
            job.name = "other"  # type: ignore[misc]

    def test_last_run_at_defaults_to_never_run(self) -> None:
        assert _job().last_run_at is None


class TestSchedulerPort:
    def test_registered_job_is_due_when_it_never_ran(self) -> None:
        scheduler: SchedulerPort = StubScheduler()
        job = _job(interval_days=30)
        scheduler.register(job)

        assert scheduler.due_jobs(_NOW) == (job,)

    def test_interval_shorter_than_one_day_is_refused(self) -> None:
        scheduler: SchedulerPort = StubScheduler()

        for interval in (0, -1):
            with pytest.raises(ValueError):
                scheduler.register(_job(interval_days=interval))

        assert scheduler.due_jobs(_NOW) == ()

    def test_same_name_and_account_replaces_the_earlier_entry(self) -> None:
        scheduler: SchedulerPort = StubScheduler()
        scheduler.register(_job(interval_days=1))
        replacement = _job(interval_days=7, last_run_at=_NOW - timedelta(days=2))
        scheduler.register(replacement)

        assert scheduler.due_jobs(_NOW) == ()
        assert scheduler.due_jobs(_NOW + timedelta(days=5)) == (replacement,)

    def test_same_name_in_another_account_is_a_separate_entry(self) -> None:
        scheduler: SchedulerPort = StubScheduler()
        first = _job(account_id="acc-1")
        second = _job(account_id="acc-2")
        scheduler.register(first)
        scheduler.register(second)

        assert scheduler.due_jobs(_NOW) == (first, second)

    def test_due_jobs_are_sorted_by_name_then_account(self) -> None:
        scheduler: SchedulerPort = StubScheduler()
        jobs = [
            _job(name="watch_deadlines", account_id="acc-2"),
            _job(name="expire_bank_consents", account_id="acc-9"),
            _job(name="watch_deadlines", account_id="acc-1"),
            _job(name="expire_bank_consents", account_id="acc-3"),
        ]
        for job in jobs:
            scheduler.register(job)

        due = scheduler.due_jobs(_NOW)
        assert [(item.name, item.account_id) for item in due] == [
            ("expire_bank_consents", "acc-3"),
            ("expire_bank_consents", "acc-9"),
            ("watch_deadlines", "acc-1"),
            ("watch_deadlines", "acc-2"),
        ]
        # Deterministic, not insertion-ordered: registering again in another order
        # must not change the answer.
        again: SchedulerPort = StubScheduler()
        for job in reversed(jobs):
            again.register(job)
        assert again.due_jobs(_NOW) == due

    def test_interval_boundary_is_inclusive(self) -> None:
        scheduler: SchedulerPort = StubScheduler()
        job = _job(interval_days=7, last_run_at=_NOW - timedelta(days=7))
        scheduler.register(job)

        assert scheduler.due_jobs(_NOW) == (job,)

    def test_a_job_inside_its_interval_is_not_due(self) -> None:
        scheduler: SchedulerPort = StubScheduler()
        scheduler.register(_job(interval_days=7, last_run_at=_NOW - timedelta(days=6, hours=23)))

        assert scheduler.due_jobs(_NOW) == ()

    def test_naive_now_is_refused(self) -> None:
        scheduler: SchedulerPort = StubScheduler()
        scheduler.register(_job())

        with pytest.raises(ValueError):
            scheduler.due_jobs(datetime(2026, 8, 24, 6, 0))

    def test_naive_last_run_at_is_refused(self) -> None:
        scheduler: SchedulerPort = StubScheduler()

        with pytest.raises(ValueError):
            scheduler.register(_job(last_run_at=datetime(2026, 8, 1, 6, 0)))

        assert scheduler.due_jobs(_NOW) == ()

    def test_due_jobs_executes_nothing_and_has_no_side_effect(self) -> None:
        """`docs/15` § 5.6: `due_jobs` is a query. It never runs a job."""
        scheduler: SchedulerPort = StubScheduler()
        job = _job(interval_days=1)
        scheduler.register(job)

        first = scheduler.due_jobs(_NOW)
        second = scheduler.due_jobs(_NOW)

        # A scheduler that ran the job would have stamped `last_run_at` and the
        # second query would come back empty. Both stay identical, and the frozen
        # record the caller registered is untouched.
        assert first == second == (job,)
        assert first[0].last_run_at is None
        assert job.last_run_at is None
