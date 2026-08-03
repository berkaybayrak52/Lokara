"""`person` READ isolation — the global identity table gets a policy, not a scope column.

docs/02-data-model.md → "The `person` edge splits: READ is a policy (M5a), WRITE is an
ordering rule (M10)". `person` is deliberately global (one human, many accounts; Supabase
Auth maps onto it), so it carries no `account_id` and the composite-FK rule of migration
0004 cannot reach it. Its isolation has to be a policy over the edges that point *at* it.

The read side is expressible precisely because it is not circular: the witness
(`membership` / `renter`) is an already-scoped table, and the row being tested is not the
row that creates the relationship. The write side is not expressible at any milestone and
is not attempted here — see the docstring of
`packages/db/tests/test_rls_isolation.py::TestGlobalPersonIsolation`.

Deny by default, and no exception for the unscoped connection
-------------------------------------------------------------
With no `app.account_id`, `current_setting(..., true)` is NULL, both `EXISTS` clauses are
false, and the caller sees zero rows — same as every other table. `OR current_setting(
'app.account_id', true) IS NULL` is **deliberately absent**: it would switch the policy off
for every unscoped connection in the system, which is most of them. The login/bootstrap
lookup (find the Person behind a Supabase Auth user, *before* any account context exists) is
a genuinely different read and needs a genuinely different path.
`TODO(M5-remainder)`: name it — a `SECURITY DEFINER` function, a dedicated role, or Supabase
Auth's own tables.

Decision 1 — the renter disjunct: **included** (docs/02 left this OPEN)
----------------------------------------------------------------------
"Shares an account" means `membership` **or** `renter`, not `membership` alone. Without the
disjunct, an account that has linked a renter's portal login (M10, `Renter.person_id`) cannot
read that `person` row back through `Renter.person` — the row would be invisible to the very
account that controls the `renter` row and granted the access, so `renter.person` would
silently resolve to None and the API would need a `SECURITY DEFINER` escape hatch for an
ordinary, legitimate read. Adding a bypass to make a normal read work is exactly the failure
mode this policy exists to prevent.

It widens visibility by no more than the account already controls: `renter` is account-scoped
and FORCEd, so the disjunct can only match a `renter` row belonging to the querying account —
a human that account invited and whose `legal_name` it already stores. It gives a renter
*session* nothing: the renter portal is not an `app.account_id` context (docs/02, constraint
3 — that is M10's problem and must not be solved by handing a renter the landlord's account
id).

Decision 2 — `FOR SELECT`, so INSERT/UPDATE/DELETE have no policy at all
------------------------------------------------------------------------
A policy created `FOR ALL` with only a `USING` clause gets `WITH CHECK` defaulting to `USING`.
Measured against this database (both variants, in a rolled-back transaction, as `lokara_app`):

| write, as `lokara_app` in account B  | `FOR ALL` (USING=WITH CHECK) | `FOR SELECT` (this one) |
| ------------------------------------ | ---------------------------- | ----------------------- |
| INSERT a brand-new Person (signup)   | **rejected**                 | rejected                |
| UPDATE a Person met via that account | **allowed, 1 row**           | 0 rows                  |
| DELETE that Person                   | refused only by an FK        | 0 rows                  |

`FOR ALL` therefore grants **no** write that signup actually needs — a brand-new Person has no
Membership yet, so it fails its own policy either way — while granting one that nobody should
have: any account sharing a membership could rewrite (or, absent a referencing row, delete)
that human's **global** identity row, including the `email` their login hangs on. That is a
cross-account write on the one table shared by all accounts, refused today only by referential
integrity, which is an accident rather than a rule.

`FOR SELECT` leaves INSERT/UPDATE/DELETE with no policy → deny by default.

**The consequence M5-remainder inherits, stated so it is not a surprise:** under
`lokara_app`, `person` is read-only. There is no API write path to `person` until the
bootstrap path above exists — signup, profile edits and account invitations all need it.
Two shapes to expect:

- an INSERT raises `InsufficientPrivilege: new row violates row-level security policy`;
- an UPDATE/DELETE raises nothing and matches **0 rows** (a raw statement no-ops silently;
  the SQLAlchemy ORM turns it into `StaleDataError`).

Already-shipped callers are unaffected because none of them writes `person` as `lokara_app`
against an empty table: `lokara-seed-demo` and the test fixtures run as the schema owner
(superuser locally → RLS bypassed), and `/demo/load` → `seed_demo` merges a Person that
already exists with identical values, so the ORM emits no UPDATE.
`TODO(supabase)`: there the owner is *not* a superuser and FORCE binds it, so seeding a
Person needs the same bootstrap path — setting a context does not help, because a Person that
does not exist yet has no Membership to be witnessed by.

Mechanism, verified rather than assumed
---------------------------------------
A table named inside a policy expression is itself subject to RLS for the querying role, so
the `EXISTS` runs under `membership_isolation` / `renter_isolation`. Confirmed empirically:
with `membership_isolation` temporarily set to `USING (false)`, **every** `person` row
disappeared; restoring it brought them back. It is harmless here only because those policies
carry the same `account_id = current_setting('app.account_id', true)` predicate this one
does, so the composition is an intersection of identical filters. It is not free of coupling:
narrowing `membership_isolation` or `renter_isolation` later (e.g. "you only see your own
membership row") would silently narrow `person` visibility with it. That is the reason this
policy repeats the account comparison instead of relying on the referenced table's policy to
supply it — the predicate stays true on its own terms.

Deliberately **not** filtered on `membership.revoked_at`: docs/02 specifies "an `EXISTS` over
`membership` scoped by `current_setting('app.account_id', true)`", and a revoked colleague
must stay readable so historical records (who created which statement) still render a name.
Authorization to *act* is a separate check and already lives in `apps/api` (`deps.py` requires
`revoked_at IS NULL`).

Known, accepted limit (docs/02, unchanged by this migration): `person.email` is globally
UNIQUE and a unique violation fires regardless of row visibility, so any account can probe
whether an address is registered. Inherent to a global identity table; recorded, not fixed.

`person` stays in `scripts/check_rls_coverage.py`'s EXEMPT set — that set means "not scoped by
a local `account_id` column", never "unprotected", and `person` still has no such column.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # FORCE, not just ENABLE: without it the table owner bypasses the policy, and the
    # owner is exactly the connection a migration, a seed script or an admin task uses.
    op.execute("ALTER TABLE person ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE person FORCE ROW LEVEL SECURITY")
    # FOR SELECT on purpose — see "Decision 2" above. No WITH CHECK exists to write,
    # because a SELECT policy has none; INSERT/UPDATE/DELETE stay policy-less and denied.
    op.execute(
        """
        CREATE POLICY person_isolation ON person
        FOR SELECT
        USING (EXISTS (SELECT 1 FROM membership m
                       WHERE m.person_id = person.id
                         AND m.account_id = current_setting('app.account_id', true))
            OR EXISTS (SELECT 1 FROM renter r
                       WHERE r.person_id = person.id
                         AND r.account_id = current_setting('app.account_id', true)))
        """
    )


def downgrade() -> None:
    # Order matters: DISABLE first would leave a policy attached to a table with RLS off,
    # which reads as protected in `pg_policies` and protects nothing.
    op.execute("DROP POLICY person_isolation ON person")
    op.execute("ALTER TABLE person NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE person DISABLE ROW LEVEL SECURITY")
