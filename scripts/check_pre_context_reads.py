#!/usr/bin/env python3
"""Verify that Lokara has exactly one bounded pre-account-context read.

Login must resolve a verified JWT subject before an account can be placed in the
URL.  That exceptional read is deliberately narrow: one SECURITY DEFINER
function, one inert owner role, three identity tables, and one API caller.

Exit 0 means the database and source boundaries are clean.  Exit 1 means an
invariant is broken.  Exit 2 means the live database could not be inspected.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Connection, create_engine, text

REPO = Path(__file__).resolve().parent.parent
API_SRC = REPO / "apps/api/src"

BOOTSTRAP_FUNCTION = "app_bootstrap_contexts"
BOOTSTRAP_ROLE = "lokara_bootstrap"
APP_ROLE = "lokara_app"
READABLE_TABLES = frozenset({"person", "membership", "account"})
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
EXPECTED_IDENTITY_POLICIES = {
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
}

EXPECTED_CALLERS = {
    "bootstrap_contexts": "lokara_api/routers/me.py",
    "unmembered_account_session": "lokara_api/routers/demo.py",
}
BOOTSTRAP_WRAPPER = "resolve_bootstrap_subject"
EXPECTED_BOOTSTRAP_WRAPPER_CALLERS = frozenset(
    {
        "lokara_api/routers/me.py",
        "lokara_api/routers/renter_activation.py",
    }
)
RETIRED_HELPERS = ("raw_account_scoped_session", "AccountSession")

Q_SECURITY_DEFINERS = text(
    """
    SELECT p.proname, oidvectortypes(p.proargtypes)
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.prosecdef
    ORDER BY p.proname
    """
)

Q_FUNCTION_METADATA = text(
    """
    SELECT owner.rolname, p.provolatile, language.lanname, p.proconfig
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    JOIN pg_roles owner ON owner.oid = p.proowner
    JOIN pg_language language ON language.oid = p.prolang
    WHERE n.nspname = 'public'
      AND p.proname = :function
      AND oidvectortypes(p.proargtypes) = 'text'
    """
)

Q_SCHEMA_PRIVILEGES = text(
    """
    SELECT
        has_schema_privilege(:bootstrap, 'public', 'USAGE'),
        has_schema_privilege(:bootstrap, 'public', 'CREATE'),
        has_schema_privilege(:app, 'public', 'CREATE')
    """
)

Q_OTHER_EXECUTABLE_SECURITY_DEFINERS = text(
    """
    SELECT n.nspname, p.proname, oidvectortypes(p.proargtypes)
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE p.prosecdef
      AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
      AND n.nspname NOT LIKE 'pg_temp_%'
      AND has_function_privilege(:app, p.oid, 'EXECUTE')
      AND NOT (
          n.nspname = 'public'
          AND p.proname = :function
          AND oidvectortypes(p.proargtypes) = 'text'
      )
    ORDER BY n.nspname, p.proname
    """
)

Q_ROLE = text(
    """
    SELECT rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls
    FROM pg_roles
    WHERE rolname = :role
    """
)

Q_ROLE_MEMBERSHIP = text(
    """
    SELECT 1
    FROM pg_auth_members membership
    JOIN pg_roles granted ON granted.oid = membership.roleid
    JOIN pg_roles grantee ON grantee.oid = membership.member
    WHERE granted.rolname = :bootstrap AND grantee.rolname = :app
    """
)

Q_EFFECTIVE_ROLE_MEMBERSHIP = text("SELECT pg_has_role(:app, :bootstrap, 'MEMBER')")

Q_BOOTSTRAP_ROLE_MEMBERSHIP_EDGES = text(
    """
    SELECT granted.rolname, member.rolname, member.rolcanlogin
    FROM pg_auth_members membership
    JOIN pg_roles granted ON granted.oid = membership.roleid
    JOIN pg_roles member ON member.oid = membership.member
    WHERE granted.rolname = :bootstrap OR member.rolname = :bootstrap
    ORDER BY granted.rolname, member.rolname
    """
)

Q_GRANTS = text(
    """
    SELECT table_name, privilege_type
    FROM information_schema.role_table_grants
    WHERE table_schema = 'public' AND grantee = :role
    ORDER BY table_name, privilege_type
    """
)

Q_POLICIES = text(
    """
    SELECT tablename, policyname, permissive, cmd, roles::text, qual, with_check
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN ('person', 'membership', 'account')
    ORDER BY tablename, policyname
    """
)

Q_UNCONDITIONAL_PUBLIC_POLICIES = text(
    """
    SELECT tablename, policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN ('person', 'membership', 'account')
      AND permissive = 'PERMISSIVE'
      AND cmd IN ('SELECT', 'ALL')
      AND 'public' = ANY(roles)
      AND regexp_replace(lower(COALESCE(qual, '')), '[()[:space:]]', '', 'g') = 'true'
    ORDER BY tablename, policyname
    """
)

Q_EXECUTE = text(
    """
    SELECT grantee
    FROM information_schema.routine_privileges
    WHERE routine_schema = 'public'
      AND routine_name = :function
      AND privilege_type = 'EXECUTE'
    ORDER BY grantee
    """
)


def _url() -> str:
    load_dotenv(REPO / ".env")
    url = os.environ.get("DIRECT_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print(
            "check_pre_context_reads: set DIRECT_URL (or DATABASE_URL) and migrate the database.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return (
        url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://")
        else url
    )


def _db_invariants(conn: Connection) -> list[str]:
    """Return catalog problems without printing, so the checker is mutation-testable."""
    problems: list[str] = []

    security_definers = {
        (str(name), str(arguments)) for name, arguments in conn.execute(Q_SECURITY_DEFINERS).all()
    }
    expected_function = {(BOOTSTRAP_FUNCTION, "text")}
    if security_definers != expected_function:
        problems.append(
            "SECURITY DEFINER functions in public are "
            f"{sorted(security_definers)}, expected exactly {sorted(expected_function)}"
        )

    other_executable_definers = conn.execute(
        Q_OTHER_EXECUTABLE_SECURITY_DEFINERS,
        {"app": APP_ROLE, "function": BOOTSTRAP_FUNCTION},
    ).all()
    for schema, name, arguments in other_executable_definers:
        problems.append(
            f"{APP_ROLE} can execute unaccounted SECURITY DEFINER {schema}.{name}({arguments})"
        )

    metadata = conn.execute(Q_FUNCTION_METADATA, {"function": BOOTSTRAP_FUNCTION}).one_or_none()
    if metadata is None:
        problems.append(f"{BOOTSTRAP_FUNCTION}(text) has no inspectable metadata")
    else:
        owner, volatility, language, config = metadata
        if str(owner) != BOOTSTRAP_ROLE:
            problems.append(f"{BOOTSTRAP_FUNCTION} is owned by {owner}, not {BOOTSTRAP_ROLE}")
        if str(volatility) not in {"s", "i"}:
            problems.append(f"{BOOTSTRAP_FUNCTION} is writable/volatile ({volatility})")
        if str(language) != "sql":
            problems.append(f"{BOOTSTRAP_FUNCTION} must be LANGUAGE sql, found {language}")
        settings = {str(entry).replace(" ", "") for entry in (config or ())}
        if "search_path=pg_catalog,public" not in settings:
            problems.append(
                f"{BOOTSTRAP_FUNCTION} has unsafe search_path metadata {list(config or ())}"
            )

    role = conn.execute(Q_ROLE, {"role": BOOTSTRAP_ROLE}).one_or_none()
    if role is None:
        problems.append(f"bootstrap role {BOOTSTRAP_ROLE} does not exist")
    elif any(bool(attribute) for attribute in role):
        problems.append(
            f"{BOOTSTRAP_ROLE} must be NOLOGIN/NOINHERIT/NOSUPERUSER/NOCREATEDB/"
            f"NOCREATEROLE/NOBYPASSRLS, found {tuple(role)}"
        )

    inherited = conn.execute(
        Q_ROLE_MEMBERSHIP, {"bootstrap": BOOTSTRAP_ROLE, "app": APP_ROLE}
    ).first()
    if inherited is not None:
        problems.append(f"{APP_ROLE} inherits {BOOTSTRAP_ROLE}; the exception became ambient")
    effective_inheritance = conn.execute(
        Q_EFFECTIVE_ROLE_MEMBERSHIP,
        {"bootstrap": BOOTSTRAP_ROLE, "app": APP_ROLE},
    ).scalar()
    if bool(effective_inheritance):
        problems.append(
            f"{APP_ROLE} effectively inherits {BOOTSTRAP_ROLE} directly or transitively"
        )
    bootstrap_membership_edges = {
        (str(granted), str(member), bool(member_can_login))
        for granted, member, member_can_login in conn.execute(
            Q_BOOTSTRAP_ROLE_MEMBERSHIP_EDGES, {"bootstrap": BOOTSTRAP_ROLE}
        ).all()
    }
    if bootstrap_membership_edges:
        problems.append(
            f"{BOOTSTRAP_ROLE} must have no role-membership edges, found "
            f"{sorted(bootstrap_membership_edges)}"
        )

    bootstrap_usage, bootstrap_create, app_create = conn.execute(
        Q_SCHEMA_PRIVILEGES,
        {"bootstrap": BOOTSTRAP_ROLE, "app": APP_ROLE},
    ).one_or_none() or (False, False, False)
    if not bool(bootstrap_usage):
        problems.append(f"{BOOTSTRAP_ROLE} must have USAGE on schema public")
    if bool(bootstrap_create):
        problems.append(f"{BOOTSTRAP_ROLE} must not have CREATE on schema public")
    if bool(app_create):
        problems.append(f"{APP_ROLE} must not have CREATE on schema public")

    grants = {
        (str(table_name), str(privilege))
        for table_name, privilege in conn.execute(Q_GRANTS, {"role": BOOTSTRAP_ROLE}).all()
    }
    expected_grants = {(table, "SELECT") for table in READABLE_TABLES}
    if grants != expected_grants:
        problems.append(
            f"{BOOTSTRAP_ROLE} table grants are {sorted(grants)}, "
            f"expected exactly {sorted(expected_grants)}"
        )

    identity_policies = {
        tuple(str(value) if value is not None else None for value in row)
        for row in conn.execute(Q_POLICIES).all()
    }
    if identity_policies != EXPECTED_IDENTITY_POLICIES:
        problems.append(
            "identity policy catalog differs from the six approved policies; "
            f"found {sorted(identity_policies, key=str)}"
        )
    for table_name, policy_name in conn.execute(Q_UNCONDITIONAL_PUBLIC_POLICIES).all():
        problems.append(
            f"unconditional permissive PUBLIC SELECT policy {policy_name} exposes {table_name}"
        )

    execute_grantees = {
        str(row[0]) for row in conn.execute(Q_EXECUTE, {"function": BOOTSTRAP_FUNCTION}).all()
    }
    expected_execute = {APP_ROLE, BOOTSTRAP_ROLE}
    if execute_grantees != expected_execute:
        problems.append(
            f"EXECUTE grantees are {sorted(execute_grantees)}, "
            f"expected exactly {sorted(expected_execute)}; PUBLIC must never execute it"
        )

    return problems


def _calls(path: Path) -> list[tuple[str, ast.Call]]:
    """Return canonical called names, resolving direct import aliases."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for imported in node.names:
                aliases[imported.asname or imported.name] = imported.name

    called: list[tuple[str, ast.Call]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called.append((aliases.get(node.func.id, node.func.id), node))
        elif isinstance(node.func, ast.Attribute):
            called.append((node.func.attr, node))
    return called


def _is_auth_person_id(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "person_id"
        and isinstance(node.value, ast.Name)
        and node.value.id == "auth"
    )


def _source_invariant(api_src: Path = API_SRC) -> list[str]:
    """Return source-boundary problems for the real or a synthesized API tree."""
    if not api_src.is_dir():
        return [f"API source directory is missing: {api_src}"]

    problems: list[str] = []
    files = sorted(api_src.rglob("*.py"))
    calls_by_symbol: dict[str, set[str]] = {symbol: set() for symbol in EXPECTED_CALLERS}
    bootstrap_wrapper_callers: set[str] = set()
    bootstrap_calls: list[tuple[str, ast.Call]] = []
    unmembered_calls: list[tuple[str, ast.Call]] = []

    for path in files:
        relative = path.relative_to(api_src).as_posix()
        source = path.read_text(encoding="utf-8")
        calls = _calls(path)
        called = {symbol for symbol, _node in calls}
        for symbol in calls_by_symbol:
            if symbol in called:
                calls_by_symbol[symbol].add(relative)
        if BOOTSTRAP_WRAPPER in called:
            bootstrap_wrapper_callers.add(relative)
        bootstrap_calls.extend(
            (relative, node) for symbol, node in calls if symbol == "bootstrap_contexts"
        )
        unmembered_calls.extend(
            (relative, node) for symbol, node in calls if symbol == "unmembered_account_session"
        )
        if "Session" in called:
            problems.append(
                f"bare Session(...) in {relative}; API DB access must use a bounded helper"
            )
        for retired in RETIRED_HELPERS:
            if re.search(rf"\b{re.escape(retired)}\b", source):
                problems.append(f"retired helper {retired} remains in {relative}")
        if "account_scoped_session" in called and relative != "lokara_api/deps.py":
            problems.append(
                f"direct account_scoped_session(...) call in {relative}; only deps.py may use it"
            )
        engine_calls = [node for symbol, node in calls if symbol == "_engine"]
        if relative != "lokara_api/deps.py":
            approved_engine_calls = {
                id(call.args[0])
                for symbol, call in calls
                if symbol == "bootstrap_contexts"
                and call.args
                and isinstance(call.args[0], ast.Call)
                and not call.args[0].args
                and not call.args[0].keywords
            }
            for engine_call in engine_calls:
                if id(engine_call) not in approved_engine_calls:
                    problems.append(
                        f"_engine() call in {relative} is outside the exact API allow-list"
                    )
        if {"connect", "begin"} & called:
            problems.append(
                f"raw engine/connection access in {relative}; "
                "API DB access must use a bounded helper"
            )
        for symbol, node in calls:
            if symbol != "execute" or not isinstance(node.func, ast.Attribute):
                continue
            owner = node.func.value
            if (
                isinstance(owner, ast.Call)
                and isinstance(owner.func, ast.Name)
                and owner.func.id == "_engine"
            ):
                problems.append(
                    f"raw engine execution in {relative}; API DB access must use a bounded helper"
                )

    for symbol, expected_module in EXPECTED_CALLERS.items():
        callers = calls_by_symbol[symbol]
        if callers != {expected_module}:
            problems.append(
                f"{symbol} call sites are {sorted(callers)}, expected only [{expected_module}]"
            )

    if bootstrap_wrapper_callers != EXPECTED_BOOTSTRAP_WRAPPER_CALLERS:
        problems.append(
            f"{BOOTSTRAP_WRAPPER} call sites are {sorted(bootstrap_wrapper_callers)}, "
            f"expected exactly {sorted(EXPECTED_BOOTSTRAP_WRAPPER_CALLERS)}"
        )

    for relative, call in bootstrap_calls:
        if relative != EXPECTED_CALLERS["bootstrap_contexts"]:
            continue
        if len(call.args) < 2 or not _is_auth_person_id(call.args[1]):
            problems.append(
                f"bootstrap_contexts in {relative} must receive auth.person_id as its subject"
            )

    expected_demo = EXPECTED_CALLERS["unmembered_account_session"]
    demo_calls = [call for relative, call in unmembered_calls if relative == expected_demo]
    if len(demo_calls) != 2:
        problems.append(
            f"unmembered_account_session in {expected_demo} must have exactly two fixed demo calls"
        )
    for call in demo_calls:
        if (
            not call.args
            or not isinstance(call.args[0], ast.Name)
            or call.args[0].id != "DEMO_ACCOUNT_ID"
        ):
            problems.append(
                f"unmembered_account_session in {expected_demo} must receive DEMO_ACCOUNT_ID"
            )

    return problems


def main() -> int:
    engine = create_engine(_url())
    try:
        with engine.connect() as conn:
            problems = _db_invariants(conn)
    except Exception as exc:
        print(f"check_pre_context_reads: cannot inspect database: {exc}", file=sys.stderr)
        return 2
    finally:
        engine.dispose()

    problems.extend(_source_invariant())
    if problems:
        print(f"pre-context reads: {len(problems)} problem(s)\n", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print(
        "pre-context reads: clean — one bounded SECURITY DEFINER function, "
        "one bootstrap caller, one demo-only unmembered helper"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
