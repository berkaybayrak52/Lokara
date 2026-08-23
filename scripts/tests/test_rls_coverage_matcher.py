r"""M6C3R-R12: `_write_tested` in `scripts/check_rls_coverage.py` was vacuous before this repair.

Check 5 of that script is what turns "the table is named somewhere in the isolation
suite" into "the table is named inside a test that attempts a refused cross-account
write". It splits the suite with `re.split(r"\n    def ", test_src)`, i.e. only at method
indentation. A module-level `def` — a `@pytest.fixture` such as `m6c2_bank_rows` — is not
a split point, so its body is glued onto the end of the preceding chunk. Any table named
only in that fixture inherits the `pytest.raises(` and `account_scoped_session(app` of an
unrelated test above it, and the check reports it as write-tested.

That is the exact shape the M6-C2 boundary audit found: the check passed for all nine
matching tables while none of them had a cross-account write assertion.

The source strings below are synthetic on purpose. Pinning this to line numbers in
`packages/db/tests/test_rls_isolation.py` would make the fixture go green the next time
somebody moves a fixture, which proves nothing about the matcher.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "scripts" / "check_rls_coverage.py"

# A module-level fixture that names PaymentAllocation, preceded by an unrelated test that
# carries both write-assertion markers. The two are separate tests of separate tables;
# only the missing split point makes them look like one body.
GLUED_FIXTURE_SOURCE = '''
class TestMeterBoundaries:
    def test_b_cannot_write_a_meter_into_a(self, engines, seed) -> None:
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            with pytest.raises(ProgrammingError):
                session.add(Meter(id=new_id(), account_id=seed.account_a))
                session.flush()


@pytest.fixture(scope="module")
def m6c2_bank_rows(engines, seed):
    """One complete A-side graph, written on the owner engine."""
    owner, _ = engines
    with Session(owner) as session, session.begin():
        session.add(
            PaymentAllocation(
                id=new_id(),
                account_id=seed.account_a,
                principal_cents=108_000,
            )
        )
    return ids
'''

# The same table, named inside a test body that really does attempt the refused write.
# This must keep returning True, so the repair cannot be "return False".
REAL_WRITE_TEST_SOURCE = """
class TestM6C2BankBoundaries:
    def test_b_cannot_write_an_allocation_into_a(self, engines, seed) -> None:
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            with pytest.raises(ProgrammingError):
                session.add(
                    PaymentAllocation(id=new_id(), account_id=seed.account_a)
                )
                session.flush()
"""


def _load_checker() -> ModuleType:
    """Import inside the test, so an absent checker is a clear red assertion."""
    assert CHECK.is_file(), "scripts/check_rls_coverage.py is missing"
    spec = importlib.util.spec_from_file_location("check_rls_coverage", CHECK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_module_level_fixture_does_not_vouch_for_its_table() -> None:
    """M6C3R-R12: the glued chunk must not count as a cross-account write test."""
    checker = _load_checker()

    assert checker._write_tested("payment_allocation", GLUED_FIXTURE_SOURCE) is False, (
        "check 5 is vacuous: `re.split(r'\\n    def ', ...)` splits only at method "
        "indentation, so a module-level fixture's body is glued onto the preceding "
        "test and inherits its pytest.raises + account_scoped_session markers. "
        "payment_allocation is named only in the fixture, which writes on the owner "
        "engine and asserts nothing."
    )


def test_a_genuine_cross_account_write_still_counts() -> None:
    """M6C3R-R12, other direction: the repair may not be `return False`."""
    checker = _load_checker()

    assert checker._write_tested("payment_allocation", REAL_WRITE_TEST_SOURCE) is True, (
        "a real refused cross-account write on the app engine, in one test body, must "
        "still satisfy check 5 — otherwise the fix breaks every table that is covered"
    )


# ── M6C3R-R20 / R21: the two shapes the R12 repair must also survive ──────────────
# Finding M4 of the 23.08.2026 boundary audit re-run. `_DEF = re.compile(r"\n(?:    )?def ")`
# splits only at `def`, so a chunk that starts at a qualifying `test_` runs on until the
# *next* `def` — swallowing whatever follows the test body. Both strings below were
# checked against the live `_write_tested` before being committed:
#   * R20 returns True today (the glue vouches for a table nothing tests);
#   * R21 returns False today (a real cross-account write is not even seen).

# The table is named only in a *following class's* docstring. There is no `def` between
# the qualifying test above and that docstring, so it is glued onto the test's chunk and
# inherits its `pytest.raises` + `account_scoped_session` + account_a/account_b markers.
# A class header, a module-level constant or a comment does the same thing.
FOLLOWING_CLASS_DOCSTRING_SOURCE = '''
class TestMeterBoundaries:
    def test_b_cannot_write_a_meter_into_a(self, engines, seed) -> None:
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            with pytest.raises(ProgrammingError):
                session.add(Meter(id=new_id(), account_id=seed.account_a))
                session.flush()


class TestM6C2BankBoundaries:
    """The PaymentAllocation graph lives here; nothing below asserts anything."""

    note = "payment_allocation"
'''

# The same genuine refused cross-account write, declared `async def`. `\n(?:    )?def `
# does not match `\n    async def `, so the body never begins a chunk of its own and the
# `body.startswith("test_")` filter drops it.
ASYNC_WRITE_TEST_SOURCE = """
class TestM6C2BankBoundaries:
    async def test_b_cannot_write_an_allocation_into_a(self, engines, seed) -> None:
        _, app = engines
        with account_scoped_session(app, seed.account_b) as session:
            with pytest.raises(ProgrammingError):
                session.add(
                    PaymentAllocation(id=new_id(), account_id=seed.account_a)
                )
                session.flush()
"""


def test_a_following_class_docstring_does_not_vouch_for_its_table() -> None:
    """M6C3R-R20: splitting only at `def` glues the next class header onto the last test.

    Pre-repair behaviour: `_write_tested("payment_allocation", ...)` returned **True** for the
    source below, although the only occurrence of the table is a docstring in a class that
    asserts nothing. `docs/02` § 6 and `CLAUDE.md` § 3.3 make the WITH CHECK side of every
    tenant policy something a test must prove; a chunk boundary that stops at `def` cannot
    tell a test body from the text that follows it.
    """
    checker = _load_checker()

    assert checker._write_tested("payment_allocation", FOLLOWING_CLASS_DOCSTRING_SOURCE) is False, (
        "check 5 still vouches on glue: the table is named only in the docstring of the "
        "*next* class, which is swallowed into the preceding test's chunk because "
        "`_DEF` splits at `def` and a class header is not one. A chunk must end where "
        "the test body ends, not where the next `def` starts."
    )


def test_an_async_test_body_is_still_recognised() -> None:
    """M6C3R-R21: `async def test_…` is a test.

    Pre-repair behaviour: `_write_tested` returned **False** for the source below, because
    `\\n(?:    )?def ` never matches `\\n    async def `, so a genuine refused cross-account
    write is invisible to the gate. No isolation test is async today; the moment one is,
    its table silently loses coverage — which is the same failure the M6-C2 audit found,
    in the other direction.
    """
    checker = _load_checker()

    assert checker._write_tested("payment_allocation", ASYNC_WRITE_TEST_SOURCE) is True, (
        "an `async def test_…` carrying a real refused cross-account write on the app "
        "engine must satisfy check 5; the splitter only recognises plain `def`"
    )
