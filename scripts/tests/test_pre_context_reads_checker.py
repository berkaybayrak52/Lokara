"""Mutation proof for the lead-owned pre-context-read checker.

Catalog checks run against an in-memory connection double; source checks run against a
throwaway API tree.  No live database, repository source mutation, or environment-dependent
skip is involved. The mutations include the alias and catalog-indirection cases found by the
boundary audit, not only the direct spellings the first checker implementation recognized.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
CHECK = ROOT / "scripts" / "check_pre_context_reads.py"

BOOTSTRAP_FUNCTION = "app_bootstrap_contexts"
BOOTSTRAP_ROLE = "lokara_bootstrap"
APP_ROLE = "lokara_app"
ACCOUNT_SCOPE = "((id)::text = current_setting('app.account_id'::text, true))"
MEMBERSHIP_SCOPE = "((account_id)::text = current_setting('app.account_id'::text, true))"
PERSON_SCOPE = (
    "((EXISTS ( SELECT 1\n"
    "   FROM membership m\n"
    "  WHERE (((m.person_id)::text = (person.id)::text) AND "
    "((m.account_id)::text = current_setting('app.account_id'::text, true))))) "
    "OR (EXISTS ( SELECT 1\n"
    "   FROM renter r\n"
    "  WHERE (((r.person_id)::text = (person.id)::text) AND "
    "((r.account_id)::text = current_setting('app.account_id'::text, true))))))"
)


def _load_checker() -> ModuleType:
    """Import only inside a test, so an absent checker is a clear red assertion."""
    assert CHECK.is_file(), (
        "scripts/check_pre_context_reads.py is not implemented; these are the red "
        "mutation fixtures for its catalog and source seams"
    )
    spec = importlib.util.spec_from_file_location("check_pre_context_reads", CHECK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Any, ...]]:
        return list(self._rows)

    def first(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def one_or_none(self) -> tuple[Any, ...] | None:
        assert len(self._rows) <= 1
        return self.first()

    def scalar(self) -> Any | None:
        row = self.first()
        return row[0] if row is not None else None


@dataclass(frozen=True)
class _Catalog:
    security_definers: tuple[tuple[str, str], ...] = ((BOOTSTRAP_FUNCTION, "text"),)
    executable_non_system_security_definers: tuple[tuple[str, str, str], ...] = ()
    # can-login, inherit, superuser, create-db, create-role, bypass-RLS
    bootstrap_role: tuple[bool, bool, bool, bool, bool, bool] | None = (
        False,
        False,
        False,
        False,
        False,
        False,
    )
    app_directly_inherits_bootstrap: bool = False
    app_effectively_inherits_bootstrap: bool = False
    # granted role, member role, whether the member can log in
    bootstrap_role_membership_edges: tuple[tuple[str, str, bool], ...] = ()
    # USAGE, CREATE on schema public
    bootstrap_schema_privileges: tuple[bool, bool] = (True, False)
    app_schema_create: bool = False
    grants: tuple[tuple[str, str], ...] = (
        ("person", "SELECT"),
        ("membership", "SELECT"),
        ("account", "SELECT"),
    )
    # table, name, permissiveness, command, roles, using, with-check
    policies: tuple[tuple[str, str, str, str, str, str | None, str | None], ...] = (
        (
            "account",
            "account_bootstrap_select",
            "PERMISSIVE",
            "SELECT",
            "{lokara_bootstrap}",
            "true",
            None,
        ),
        (
            "account",
            "account_isolation",
            "PERMISSIVE",
            "ALL",
            "{public}",
            ACCOUNT_SCOPE,
            ACCOUNT_SCOPE,
        ),
        (
            "membership",
            "membership_bootstrap_select",
            "PERMISSIVE",
            "SELECT",
            "{lokara_bootstrap}",
            "true",
            None,
        ),
        (
            "membership",
            "membership_isolation",
            "PERMISSIVE",
            "ALL",
            "{public}",
            MEMBERSHIP_SCOPE,
            MEMBERSHIP_SCOPE,
        ),
        (
            "person",
            "person_bootstrap_select",
            "PERMISSIVE",
            "SELECT",
            "{lokara_bootstrap}",
            "true",
            None,
        ),
        (
            "person",
            "person_isolation",
            "PERMISSIVE",
            "SELECT",
            "{public}",
            PERSON_SCOPE,
            None,
        ),
    )
    unconditional_public_select_policies: tuple[tuple[str, str], ...] = ()
    execute_grantees: tuple[tuple[str], ...] = ((APP_ROLE,), (BOOTSTRAP_ROLE,))
    function_metadata: tuple[str, str, str, tuple[str, ...]] = (
        BOOTSTRAP_ROLE,
        "s",
        "sql",
        ("search_path=pg_catalog, public",),
    )


@dataclass
class _Connection:
    """The small SQLAlchemy Connection seam used by ``_db_invariants``."""

    catalog: _Catalog
    statements: list[str] = field(default_factory=list)

    def execute(self, statement: object, parameters: dict[str, object] | None = None) -> _Result:
        sql = str(statement)
        self.statements.append(sql)

        if "has_function_privilege" in sql:
            return _Result(list(self.catalog.executable_non_system_security_definers))
        if "provolatile" in sql or "proconfig" in sql:
            if "lanname" in sql or "pg_language" in sql:
                return _Result([self.catalog.function_metadata])
            owner, volatility, _language, config = self.catalog.function_metadata
            return _Result([(owner, volatility, config)])
        if "pg_get_function_identity_arguments" in sql or "prosecdef" in sql:
            return _Result(list(self.catalog.security_definers))
        if "FROM pg_roles" in sql and "rolname" in sql:
            if self.catalog.bootstrap_role is None:
                rows: list[tuple[Any, ...]] = []
            elif "rolinherit" in sql:
                rows = [self.catalog.bootstrap_role]
            else:
                role = self.catalog.bootstrap_role
                rows = [(role[0], *role[2:])]
            return _Result(rows)
        if "pg_has_role" in sql:
            return _Result([(self.catalog.app_effectively_inherits_bootstrap,)])
        if "pg_auth_members" in sql:
            if ":app" in sql:
                return _Result([(1,)] if self.catalog.app_directly_inherits_bootstrap else [])
            if "WHERE member.rolname = :bootstrap" in sql and " OR " not in sql:
                return _Result(
                    [
                        (granted,)
                        for granted, member, _can_login in (
                            self.catalog.bootstrap_role_membership_edges
                        )
                        if member == BOOTSTRAP_ROLE
                    ]
                )
            if "WHERE granted.rolname = :bootstrap" in sql and " OR " not in sql:
                return _Result(
                    [
                        (member, can_login)
                        for granted, member, can_login in (
                            self.catalog.bootstrap_role_membership_edges
                        )
                        if granted == BOOTSTRAP_ROLE
                    ]
                )
            return _Result(list(self.catalog.bootstrap_role_membership_edges))
        if "has_schema_privilege" in sql:
            usage, bootstrap_create = self.catalog.bootstrap_schema_privileges
            if ":bootstrap" in sql and ":app" in sql:
                return _Result([(usage, bootstrap_create, self.catalog.app_schema_create)])
            schema_role = str((parameters or {}).get("role", ""))
            if schema_role == BOOTSTRAP_ROLE:
                return _Result([(usage, bootstrap_create)])
            if schema_role == APP_ROLE:
                return _Result([(self.catalog.app_schema_create,)])
            raise AssertionError(f"unknown schema-privilege role in checker query: {parameters}")
        if "role_table_grants" in sql or ("aclexplode" in sql and "pg_class" in sql):
            return _Result(list(self.catalog.grants))
        if "pg_policies" in sql and "'public' = ANY(roles)" in sql:
            return _Result(list(self.catalog.unconditional_public_select_policies))
        if "pg_policies" in sql:
            if all(column in sql for column in ("permissive", "qual", "with_check")):
                return _Result(list(self.catalog.policies))
            projected = [
                (table, name, command, roles)
                for (
                    table,
                    name,
                    _permissive,
                    command,
                    roles,
                    _qual,
                    _with_check,
                ) in self.catalog.policies
                if "lokara_bootstrap" in roles
            ]
            return _Result(projected)
        if "routine_privileges" in sql or ("aclexplode" in sql and "pg_proc" in sql):
            return _Result(list(self.catalog.execute_grantees))
        raise AssertionError(f"unhandled catalog query from checker: {sql}")


def _catalog_problems(catalog: _Catalog) -> list[str]:
    checker = _load_checker()
    problems = checker._db_invariants(_Connection(catalog))
    assert isinstance(problems, list)
    return [str(problem) for problem in problems]


def _write_clean_api(api_src: Path) -> None:
    routers = api_src / "lokara_api" / "routers"
    routers.mkdir(parents=True)
    (routers / "me.py").write_text(
        "from somewhere import bootstrap_contexts\n"
        "from somewhere_else import _engine\n"
        "def me(auth):\n"
        "    return bootstrap_contexts(_engine(), auth.person_id)\n"
    )
    (routers / "demo.py").write_text(
        "from somewhere import DEMO_ACCOUNT_ID, unmembered_account_session\n"
        "def load():\n"
        "    with unmembered_account_session(DEMO_ACCOUNT_ID):\n"
        "        pass\n"
        "def reset():\n"
        "    with unmembered_account_session(DEMO_ACCOUNT_ID):\n"
        "        pass\n"
    )
    (api_src / "lokara_api" / "deps.py").write_text(
        "from somewhere import _engine, account_scoped_session\n"
        "def scoped(engine, account_id):\n"
        "    return account_scoped_session(_engine(), account_id)\n"
    )


def _source_problems(api_src: Path) -> list[str]:
    checker = _load_checker()
    problems = checker._source_invariant(api_src)
    assert isinstance(problems, list)
    return [str(problem) for problem in problems]


def _joined(problems: list[str]) -> str:
    return "\n".join(problems)


class TestCleanSynthesizedShape:
    def test_correct_catalog_and_source_shape_are_green(self, tmp_path: Path) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)

        assert _catalog_problems(_Catalog()) == []
        assert _source_problems(api_src) == []


class TestCatalogMutations:
    @pytest.mark.parametrize(
        "security_definers",
        [
            (),
            ((BOOTSTRAP_FUNCTION, "text"), ("unaccounted_bypass", "text")),
        ],
        ids=["missing", "extra"],
    )
    def test_missing_or_extra_security_definer_is_red(
        self, security_definers: tuple[tuple[str, str], ...]
    ) -> None:
        problems = _catalog_problems(replace(_Catalog(), security_definers=security_definers))
        assert "SECURITY DEFINER" in _joined(problems)

    def test_missing_bootstrap_role_is_red(self) -> None:
        problems = _catalog_problems(replace(_Catalog(), bootstrap_role=None))
        assert BOOTSTRAP_ROLE in _joined(problems)

    def test_bootstrap_function_language_is_exactly_sql(self) -> None:
        catalog = replace(
            _Catalog(),
            function_metadata=(
                BOOTSTRAP_ROLE,
                "s",
                "plpgsql",
                ("search_path=pg_catalog, public",),
            ),
        )
        problems = _catalog_problems(catalog)
        report = _joined(problems)
        assert "LANGUAGE" in report
        assert "sql" in report

    @pytest.mark.parametrize(
        ("bootstrap_privileges", "app_create", "expected_role", "expected_privilege"),
        [
            ((False, False), False, BOOTSTRAP_ROLE, "USAGE"),
            ((True, True), False, BOOTSTRAP_ROLE, "CREATE"),
            ((True, False), True, APP_ROLE, "CREATE"),
        ],
        ids=["bootstrap-missing-usage", "bootstrap-create", "app-create"],
    )
    def test_exact_public_schema_privileges_are_required(
        self,
        bootstrap_privileges: tuple[bool, bool],
        app_create: bool,
        expected_role: str,
        expected_privilege: str,
    ) -> None:
        catalog = replace(
            _Catalog(),
            bootstrap_schema_privileges=bootstrap_privileges,
            app_schema_create=app_create,
        )
        problems = _catalog_problems(catalog)
        report = _joined(problems)
        assert expected_role in report
        assert expected_privilege in report

    def test_bootstrap_role_is_explicitly_noinherit(self) -> None:
        catalog = replace(
            _Catalog(),
            bootstrap_role=(False, True, False, False, False, False),
        )
        problems = _catalog_problems(catalog)
        assert "NOINHERIT" in _joined(problems)

    def test_bootstrap_role_is_not_a_member_of_any_role(self) -> None:
        catalog = replace(
            _Catalog(),
            bootstrap_role_membership_edges=(("ambient_identity_reader", BOOTSTRAP_ROLE, False),),
        )
        problems = _catalog_problems(catalog)
        report = _joined(problems)
        assert BOOTSTRAP_ROLE in report
        assert "ambient_identity_reader" in report

    def test_no_login_role_is_a_member_of_bootstrap_role(self) -> None:
        catalog = replace(
            _Catalog(),
            bootstrap_role_membership_edges=((BOOTSTRAP_ROLE, "batch_login", True),),
        )
        problems = _catalog_problems(catalog)
        report = _joined(problems)
        assert BOOTSTRAP_ROLE in report
        assert "batch_login" in report

    def test_public_execute_is_red(self) -> None:
        catalog = replace(
            _Catalog(),
            execute_grantees=((APP_ROLE,), (BOOTSTRAP_ROLE,), ("PUBLIC",)),
        )
        problems = _catalog_problems(catalog)
        assert "PUBLIC" in _joined(problems)

    def test_executable_security_definer_outside_public_is_red(self) -> None:
        catalog = replace(
            _Catalog(),
            executable_non_system_security_definers=(
                ("private_tools", "hidden_bootstrap", "text"),
            ),
        )
        problems = _catalog_problems(catalog)
        report = _joined(problems)
        assert "private_tools" in report
        assert "hidden_bootstrap" in report

    def test_transitive_bootstrap_role_inheritance_is_red(self) -> None:
        """No direct pg_auth_members edge: lokara_app inherits through another role."""
        catalog = replace(
            _Catalog(),
            app_directly_inherits_bootstrap=False,
            app_effectively_inherits_bootstrap=True,
        )
        problems = _catalog_problems(catalog)
        assert "inherit" in _joined(problems).lower()

    def test_unconditional_public_select_policy_is_red(self) -> None:
        catalog = replace(
            _Catalog(),
            unconditional_public_select_policies=(("person", "person_everyone_select"),),
        )
        problems = _catalog_problems(catalog)
        report = _joined(problems)
        assert "PUBLIC" in report
        assert "person_everyone_select" in report

    @pytest.mark.parametrize(
        ("column", "mutated_value"),
        [
            (1, "renamed_person_bootstrap"),
            (2, "RESTRICTIVE"),
            (3, "ALL"),
            (4, "{lokara_app}"),
            (4, "{lokara_bootstrap,lokara_app}"),
            (5, "1 = 1"),
            (6, "true"),
        ],
        ids=[
            "name",
            "permissiveness",
            "command",
            "lokara-app-role",
            "inherited-role-exposure",
            "using-one-equals-one",
            "with-check",
        ],
    )
    def test_exact_bootstrap_policy_catalog_is_required(
        self, column: int, mutated_value: str
    ) -> None:
        rows = [list(row) for row in _Catalog().policies]
        person_bootstrap = next(
            index for index, row in enumerate(rows) if row[1] == "person_bootstrap_select"
        )
        rows[person_bootstrap][column] = mutated_value
        policies = tuple(tuple(row) for row in rows)
        catalog = replace(_Catalog(), policies=policies)  # type: ignore[arg-type]

        problems = _catalog_problems(catalog)
        assert problems

    def test_catalog_queries_role_inheritance_and_complete_policy_shape(self) -> None:
        checker = _load_checker()
        connection = _Connection(_Catalog())
        checker._db_invariants(connection)
        role_queries = [sql for sql in connection.statements if "FROM pg_roles" in sql]
        policy_queries = [
            sql
            for sql in connection.statements
            if "FROM pg_policies" in sql and "'public' = ANY(roles)" not in sql
        ]

        assert any("rolinherit" in sql for sql in role_queries)
        assert any(
            all(
                column in sql
                for column in ("policyname", "permissive", "cmd", "roles", "qual", "with_check")
            )
            for sql in policy_queries
        )


class TestSourceMutations:
    @pytest.mark.parametrize("symbol", ["bootstrap_contexts", "unmembered_account_session"])
    def test_an_extra_helper_call_site_is_red(self, tmp_path: Path, symbol: str) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        extra = api_src / "lokara_api" / "routers" / "extra.py"
        extra.write_text(f"def extra():\n    return {symbol}('acc_or_subject')\n")

        problems = _source_problems(api_src)
        report = _joined(problems)
        assert symbol in report
        assert "extra.py" in report

    def test_a_bare_api_session_is_red(self, tmp_path: Path) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        unsafe = api_src / "lokara_api" / "routers" / "unsafe.py"
        unsafe.write_text("def unsafe(engine):\n    return Session(engine)\n")

        problems = _source_problems(api_src)
        report = _joined(problems)
        assert "Session" in report
        assert "unsafe.py" in report

    @pytest.mark.parametrize("symbol", ["bootstrap_contexts", "unmembered_account_session"])
    def test_an_aliased_helper_call_site_is_red(self, tmp_path: Path, symbol: str) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        hidden = api_src / "lokara_api" / "routers" / "hidden.py"
        hidden.write_text(
            f"from somewhere import {symbol} as disguised\n"
            "def hidden():\n"
            "    return disguised('acc_or_subject')\n"
        )

        problems = _source_problems(api_src)
        report = _joined(problems)
        assert symbol in report
        assert "hidden.py" in report

    def test_direct_account_scoped_session_outside_deps_is_red(self, tmp_path: Path) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        bypass = api_src / "lokara_api" / "routers" / "bypass.py"
        bypass.write_text(
            "from somewhere import account_scoped_session\n"
            "def bypass(engine):\n"
            "    return account_scoped_session(engine, 'acc')\n"
        )

        problems = _source_problems(api_src)
        report = _joined(problems)
        assert "account_scoped_session" in report
        assert "bypass.py" in report

    def test_me_must_pass_auth_person_id(self, tmp_path: Path) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        me = api_src / "lokara_api" / "routers" / "me.py"
        me.write_text(me.read_text().replace("auth.person_id", "'per_constant'"))

        problems = _source_problems(api_src)
        report = _joined(problems)
        assert "auth.person_id" in report
        assert "me.py" in report

    @pytest.mark.parametrize(
        "unsafe_source",
        [
            "def unsafe():\n    return _engine().connect()\n",
            "def unsafe():\n    return _engine().begin()\n",
            "def unsafe(statement):\n    return _engine().execute(statement)\n",
            (
                "def unsafe(statement):\n"
                "    engine = _engine()\n"
                "    with engine.connect() as connection:\n"
                "        return connection.execute(statement)\n"
            ),
        ],
        ids=["engine-connect", "engine-begin", "engine-execute", "connection-execute"],
    )
    def test_raw_api_connection_execution_is_red(self, tmp_path: Path, unsafe_source: str) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        unsafe = api_src / "lokara_api" / "routers" / "unsafe_connection.py"
        unsafe.write_text(unsafe_source)

        report = _joined(_source_problems(api_src))
        assert "unsafe_connection.py" in report

    @pytest.mark.parametrize(
        "unsafe_source",
        [
            "def unsafe():\n    return _engine().raw_connection()\n",
            "def unsafe():\n    return Connection(_engine())\n",
            "def unsafe():\n    return consume_engine(_engine())\n",
        ],
        ids=["raw-connection", "connection-constructor", "alternate-consumer"],
    )
    def test_engine_call_outside_exact_allow_list_is_red(
        self, tmp_path: Path, unsafe_source: str
    ) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        unsafe = api_src / "lokara_api" / "routers" / "engine_escape.py"
        unsafe.write_text(unsafe_source)

        report = _joined(_source_problems(api_src))
        assert "_engine" in report
        assert "engine_escape.py" in report

    @pytest.mark.parametrize("function_name", ["load", "reset"])
    def test_each_demo_unmembered_call_uses_demo_account_id(
        self, tmp_path: Path, function_name: str
    ) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        demo = api_src / "lokara_api" / "routers" / "demo.py"
        source = demo.read_text()
        source = source.replace(
            f"def {function_name}():\n    with unmembered_account_session(DEMO_ACCOUNT_ID):",
            f"def {function_name}():\n    with unmembered_account_session('acc_other'):",
        )
        demo.write_text(source)

        report = _joined(_source_problems(api_src))
        assert "DEMO_ACCOUNT_ID" in report
        assert "demo.py" in report

    def test_demo_has_exactly_two_unmembered_calls(self, tmp_path: Path) -> None:
        api_src = tmp_path / "apps" / "api" / "src"
        _write_clean_api(api_src)
        demo = api_src / "lokara_api" / "routers" / "demo.py"
        demo.write_text(
            demo.read_text().replace(
                "def reset():\n"
                "    with unmembered_account_session(DEMO_ACCOUNT_ID):\n"
                "        pass\n",
                "def reset():\n    pass\n",
            )
        )

        report = _joined(_source_problems(api_src))
        assert "unmembered_account_session" in report
        assert "demo.py" in report
