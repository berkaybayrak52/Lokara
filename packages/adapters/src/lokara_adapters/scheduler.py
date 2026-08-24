"""Scheduler port — when a background job is due, normalized away from any worker.

`PLAN.md` § M6-C3b ships the three job entrypoints "behind a scheduler port", and
`docs/01` D7 keeps the worker pick open: Redis, Arq and Celery stay uninstalled.
This module is what that means concretely. It answers one question — *which jobs
are due at this instant* — and never runs anything. Execution belongs to the
caller, which is the whole reason no vendor scheduler leaks into the codebase.

A job is named per account on purpose (`docs/15` § 5.6). Jobs are account-scoped
because the data they touch is, and a scheduler entry that named only the job
would have to invent a cross-account run.

TODO(provider): the real implementation registers these with Arq or Celery. Only
this module ever imports that SDK.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol


def _require_aware(value: datetime, field: str) -> None:
    """Refuse a naive timestamp at the boundary.

    A scheduler compares instants across a process that may run anywhere, and a
    naive value silently means "local time" — the same defect class as a `float`
    reaching `cents_from_provider_amount`. Every stored timestamp in this system
    is `TIMESTAMPTZ`, so a naive one can only have come from a caller's clock.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware — a naive datetime has no instant")


@dataclass(frozen=True)
class ScheduledJob:
    """One account-scoped job and the cadence it is claimed to run at.

    `last_run_at` is `None` before the first run, which makes the job immediately
    due. That is deliberate: a newly registered job should run once rather than
    wait a full interval for evidence it has never produced.
    """

    name: str
    account_id: str
    interval_days: int
    last_run_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.last_run_at is not None:
            _require_aware(self.last_run_at, "last_run_at")

    def is_due(self, now: datetime) -> bool:
        _require_aware(now, "now")
        if self.last_run_at is None:
            return True
        return self.last_run_at + timedelta(days=self.interval_days) <= now


class SchedulerPort(Protocol):
    """Port: register account-scoped jobs and ask which are due."""

    def register(self, job: ScheduledJob) -> None:
        """Record `job`. A second registration of the same ``(name, account_id)``
        replaces the first — that pair is the job's identity, and re-registering
        is how a completed run reports its new ``last_run_at``."""
        ...

    def due_jobs(self, now: datetime) -> tuple[ScheduledJob, ...]:
        """The registered jobs due at `now`, in deterministic order. Runs nothing."""
        ...


class StubScheduler:
    """In-memory scheduler for dev, tests and the pitch demo — no broker, no worker.

    It is deterministic by construction: ordering is `(name, account_id)` rather
    than registration order, so a run plan does not depend on how the caller
    happened to build it.

    TODO(provider): swap for the Arq/Celery-backed adapter.
    """

    def __init__(self) -> None:
        self._jobs: dict[tuple[str, str], ScheduledJob] = {}

    def register(self, job: ScheduledJob) -> None:
        if job.interval_days < 1:
            raise ValueError("interval_days must be at least 1 day")
        self._jobs[(job.name, job.account_id)] = job

    def due_jobs(self, now: datetime) -> tuple[ScheduledJob, ...]:
        _require_aware(now, "now")
        return tuple(
            job
            for _, job in sorted(self._jobs.items(), key=lambda item: item[0])
            if job.is_due(now)
        )
