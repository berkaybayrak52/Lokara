"""Red source contract for the API side of the bootstrap-context design.

The database exception is useful only if API call sites cannot quietly grow around it.
These checks require no database and therefore cannot be skipped by a missing Postgres.
"""

import ast
import re
from pathlib import Path

API_SRC = Path(__file__).resolve().parent.parent / "src" / "lokara_api"

BOOTSTRAP_HELPER = "bootstrap_contexts"
UNMEMBERED_HELPER = "unmembered_account_session"
RETIRED_HELPERS = ("raw_account_scoped_session", "AccountSession")


def _modules() -> dict[str, str]:
    return {
        str(path.relative_to(API_SRC.parent.parent.parent.parent)): path.read_text()
        for path in sorted(API_SRC.rglob("*.py"))
    }


def _callers(symbol: str) -> set[str]:
    return {
        name
        for name, source in _modules().items()
        if f"{symbol}(" in source and f"def {symbol}(" not in source
    }


class TestPreContextCallSites:
    def test_bootstrap_read_has_exactly_one_call_site(self) -> None:
        assert _callers(BOOTSTRAP_HELPER) == {"apps/api/src/lokara_api/routers/me.py"}

    def test_unmembered_account_session_is_confined_to_demo_router(self) -> None:
        """Only fixed-account demo bootstrap writes may omit the Membership gate."""
        assert _callers(UNMEMBERED_HELPER) == {"apps/api/src/lokara_api/routers/demo.py"}

    def test_retired_helpers_are_absent(self) -> None:
        offenders = {
            symbol: sorted(
                name
                for name, source in _modules().items()
                if re.search(rf"\b{re.escape(symbol)}\b", source)
            )
            for symbol in RETIRED_HELPERS
        }
        assert offenders == {symbol: [] for symbol in RETIRED_HELPERS}

    def test_me_carries_no_account_context(self) -> None:
        source = (API_SRC / "routers" / "me.py").read_text()
        for scoped in ("account_scoped_session", "auth.account_id", "PathAccountSession"):
            assert scoped not in source

    def test_auth_context_contains_only_the_verified_subject(self) -> None:
        tree = ast.parse((API_SRC / "auth.py").read_text())
        auth_context = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "AuthContext"
        )
        fields = {
            node.target.id
            for node in auth_context.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        }
        assert fields == {"person_id"}

    def test_nothing_opens_a_bare_api_session(self) -> None:
        offenders = sorted(name for name, source in _modules().items() if "Session(" in source)
        assert offenders == []

    def test_only_url_carried_account_dependency_remains(self) -> None:
        source = (API_SRC / "deps.py").read_text()
        assert "def account_session(" not in source
        assert "PathAccountSession" in source
