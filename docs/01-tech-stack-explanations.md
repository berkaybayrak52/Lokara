# 01 — Explanations (companion to `01-tech-stack-and-decisions.md`)

Questions from the read-through, answered inline. Answers follow the rule in 0): every
abbreviation is written out the first time it appears.

0) TO-DO First.
    - Next to every abbrevation, write their full form. For example: "... RLS (Row-Level Security) ..."
    - And do this for everything in the future and also for existing .md files.

    → Applied in this file. The sweep over the existing `docs/` files is a separate pass;
      see the note at the end.

1) Question about stack:
    - What is Bun? For what do we need it? What are the alternatives?

      A JavaScript/TypeScript runtime that is also a package manager, bundler and test runner
      in one binary — the fast replacement for Node.js + npm. We need it to install and run
      the TypeScript side (`apps/web`, `apps/mobile`, `packages/ui`).
      **Alternatives:** Node.js with pnpm / npm / yarn, or Deno. D7 already says: if a tool
      breaks under Bun, fall back to Node.js for that one command — don't re-platform.

    - What is uv? For what do we need it? What are the alternatives?

      The Python equivalent: a very fast package and virtual-environment manager (written in
      Rust, by Astral, the makers of Ruff). It installs the Python side and locks it in
      `uv.lock`. Every command in this repo that starts with `uv run` goes through it.
      **Alternatives:** `pip` + `venv`, Poetry, PDM, Conda.

    - What is shadcn/ui? For what do we need it? What are the alternatives?

      Not a dependency — a collection of React components you **copy into your own repo**,
      built on Radix UI (accessible, unstyled primitives) and styled with Tailwind. We need it
      because the source lands in `packages/ui` and we can theme it to the Lokara tokens in
      `docs/05` instead of fighting a library's defaults.
      **Alternatives:** Material UI (MUI), Mantine, Chakra UI, or Radix UI directly with our
      own styling.

    - What is Jotai? For what do we need it? What are the alternatives?

      A small state manager for **client** state — state the browser owns and no server knows
      about (which modal is open, the selected building in a switcher, a wizard step).
      **Alternatives:** Zustand, Redux Toolkit, Recoil, or plain React Context.

    - What is TanStack Query? For what do we need it? What are the alternatives?

      A manager for **server** state — data that lives in the database and is only borrowed by
      the browser. It handles fetching, caching, refetching after a mutation, retries and
      loading/error states, so we never hand-roll `useEffect` + `fetch`.
      **Alternatives:** SWR, RTK Query (Redux Toolkit Query), Apollo Client (GraphQL only).
      The Jotai/TanStack Query split is deliberate: two kinds of state, two tools.

    - What is React Hook Form? For what do we need it? What are the alternatives?

      A form library. It keeps inputs uncontrolled, so typing in one field doesn't re-render
      the whole form — which matters on the long forms this product has (Einheit, Kosten
      erfassen, Zähler). It also wires validation errors to fields.
      **Alternatives:** Formik, TanStack Form, or raw React state.

    - What is Zod? For what do we need it? What are the alternatives?

      A TypeScript-first schema validator that checks data **at runtime** and derives the
      TypeScript type from the same schema. We need it because TypeScript types vanish at
      runtime: an API response is `any` until something actually checks it. Zod is the
      frontend half of the "validate at every boundary" rule; Pydantic is the backend half.
      **Alternatives:** Yup, Valibot, ArkType, io-ts.

    - What is RHF? For what do we need it? What are the alternatives?

      RHF is just the abbreviation for **React Hook Form** — same tool as above.

    - What is RLS? For what do we need it? What are the alternatives?

      RLS (Row-Level Security) is a PostgreSQL feature: a policy attached to a table decides,
      per row, whether the current session may see or change it. Our policies compare the row's
      `account_id` against a session variable the API sets per transaction. We need it because
      it is the **second** of the two isolation enforcements in CLAUDE.md rule 3 — application
      code can forget a `WHERE account_id = …`, and RLS catches that forgetting at the database.
      **Alternatives:** application-level filtering only (rejected — one missed filter leaks
      another landlord's data), a separate database per customer, or a schema per customer.

    - What is ORM? For what do we need it? What are the alternatives?

      ORM (Object-Relational Mapper) maps database tables to Python classes, so you write
      `session.query(Unit)` instead of SQL strings. Ours is SQLAlchemy 2.0, with Alembic for
      migrations (versioned schema-change scripts).
      **Alternatives:** raw SQL through psycopg, a query builder, SQLModel, Django ORM.

    - What is Redis? For what do we need it? What are the alternatives?

      An in-memory key-value store — very fast, used as scratch space rather than as the
      system of record. Three jobs here: caching computed responses, counting requests for
      rate limiting, and acting as the queue that background jobs are handed through.
      **Alternatives:** Valkey (the open-source fork), Memcached (cache only), or a
      Postgres-backed queue for the job part.

    - What is Celery? For what do we need it? What are the alternatives?

      The long-established Python distributed task queue: work that must not happen inside an
      HTTP (HyperText Transfer Protocol) request — bank sync, deadline watchers, email retries
      — is pushed onto Redis and executed by a separate worker process. Arrives at M6.
      **Alternatives:** Arq, Dramatiq, RQ (Redis Queue), APScheduler.

    - What is Arq? For what do we need it? What are the alternatives?

      The same job as Celery, but small and `asyncio`-native (built by the author of Pydantic),
      which fits FastAPI better. D7 leaves the pick open — "Celery **or** Arq" — because the
      choice only matters at M6.
      **Alternatives:** Celery, Dramatiq, RQ.

    - What is Husky? For what do we need it? What are the alternatives?

      A manager for Git hooks — scripts Git runs automatically on `commit` or `push`. We use it
      so linting and formatting run before a bad commit exists, rather than being caught later.
      **Alternatives:** lefthook, `pre-commit` (a Python tool that can cover both languages at
      once), hand-written files in `.git/hooks`, or enforcing it only in CI (Continuous
      Integration).

    - What is Pydantic? For what do we need it? What are the alternatives?

      Runtime validation for Python, driven by type hints: declare a model, and incoming JSON
      (JavaScript Object Notation) is parsed, coerced and rejected against it. FastAPI is built
      on it, so every request body and response is validated for free. It is the backend
      authority in "never trust the client".
      **Alternatives:** dataclasses plus hand-written checks, attrs + cattrs, marshmallow,
      msgspec.

    - What is mypy? For what do we need it? What are the alternatives?

      A static type checker: it reads the type hints and proves, without running anything, that
      the code is consistent with them. We run it in `--strict` mode as a gate, which is how a
      `float` can never quietly enter a money path.
      **Alternatives:** pyright / basedpyright, ty, pyre.

2) Question about D1/Supabase:
    - What does 'AVV' mean?

      AVV = **Auftragsverarbeitungsvertrag** — the German name for a data-processing agreement
      (English: DPA, Data Processing Agreement) under Art. 28 DSGVO (Datenschutz-Grundverordnung,
      the German name for the GDPR). Whenever another company processes personal data on our
      behalf, that contract is legally required, and the company is listed as a
      *Unterauftragsverarbeiter* (sub-processor).

    - Is it ok for us to pick Supabase?

      For the MVP (Minimum Viable Product), yes: EU region plus a signed DPA is a defensible
      position, and D1 records it as a conscious compromise with a revisit date rather than an
      oversight. It is not the answer for real tenant data — see below.

    - What is Supabase, what does it do?

      A hosted platform around PostgreSQL: it gives us the database, user authentication
      (password, magic link, verification, reset), file storage, and RLS wired up, instead of us
      building each. We use it as infrastructure only — our own FastAPI backend sits in front of
      it, and no client app talks to it directly.

    - Is supabase reliable for us? Since we're in germany(EU) so we have to be careful about laws.
      Would we have any problem in the future? If we'll have a problem, which alternatives do we have?

      The data sits in Frankfurt, so residency is fine. The unresolved risk is that Supabase Inc.
      is US-headquartered, and a US parent can in principle be reached by US law (the CLOUD Act)
      regardless of where the servers are — which is exactly what our own Datenschutz page
      promises against. That is why D1 says *revisit before onboarding real tenant data*.
      **Alternatives, cheapest first:** self-host Supabase on Hetzner (it is open source — same
      application programming interfaces, full EU control); plain PostgreSQL on Hetzner with our
      own authentication; or a European managed Postgres (Scaleway, OVH, Neon EU).
      The important part: everything above the database — FastAPI, SQLAlchemy, the pure engines,
      RLS — is identical either way, so this swap never reaches the money math.

3) Questions about D2:
    - Can you explain to me what are we talking about in " they call `apps/api` over HTTP; **the
      SQLAlchemy/DB layer lives in `apps/api`**, never in a client app.". What does it mean "never in
      a client app"? Are we talking about two sides one server and other side being the client?

      Yes — two sides. `apps/web` (running in the user's browser) and `apps/mobile` (on their
      phone) are **clients**; `apps/api` is the **server**, and it is the only thing holding the
      database credentials and the SQLAlchemy models. A client asks the server for data over
      HTTP and gets JSON back.
      The rule exists because a client runs on hardware the user controls: anything shipped to it
      — a connection string, a query — can be read and changed. If a client could reach the
      database itself, both isolation checks would be on the wrong side of the trust boundary.

    - What does it mean "- **Modular monolith:** one deployable FastAPI app, split into per-domain
      routers/modules with clear boundaries (nk, heating, ledger, tax, documents, …). Not
      microservices."

      One program, one deployment, one database — but internally divided into per-domain folders
      that only talk to each other through defined interfaces. Microservices would mean nk,
      heating and ledger each being their own deployed service calling the others over the
      network, which buys nothing at our size and costs a lot of operational work.
      Keeping the boundaries clean now means a module *could* be split out later if it ever earns
      it.

    - What does the sentence mean that starts with : "**Local auth without Supabase creds:** ..."

      We don't have a real Supabase project yet, but we still want the authentication guard to be
      real code that runs on every request rather than something bolted on later. So the API
      verifies tokens signed with a local secret using HS256 (a signing algorithm where signer and
      verifier share one secret key), and a development-only endpoint mints such a token so the
      guard is genuinely exercised. Switching to real Supabase means dropping in their secret —
      every place that needs changing is already marked `TODO(supabase)`.
      The warning attached to it: newer Supabase projects sign with asymmetric keys (a private key
      signs, a public key from a JWKS — JSON Web Key Set — verifies) instead of a shared secret, so
      check which one the project uses before wiring it.

    - Can explain the sentence starts with: "**Staged within this decision:** ..."

      The framework choice is settled now, but not all of it gets built now. The skeleton, the
      authentication layer and the NK (Nebenkosten) endpoints come early (M0–M3); the background
      worker layer — Celery or Arq on Redis — only arrives at M6, when bank sync, ledger and email
      actually create work that must happen outside a request.
      "Structure from day 1, heavy async features when earned": the shape is decided up front so
      the later addition is an addition, not a rewrite.

4) Questions about D4:
    - For this project specific, can't we make our own OCR?

      Not for the MVP, and probably never in the "train our own model" sense: reading arbitrary
      German invoices and utility statements reliably needs a labelled dataset, an evaluation
      harness, and permanent maintenance — that is a product of its own, and it isn't the product
      we're selling. A hosted vision model does it on day one.
      What *is* realistic later, and what the adapter exists for: running an open-source document
      model on our own EU hardware, which removes the sub-processor and the per-page cost without
      touching the extraction pipeline. That is a post-launch cost decision, not an MVP task.
      (OCR = Optical Character Recognition, turning an image of text into text.)

5) Questions about D5:
    - It's ok to use stub for pitch but during lunch of application to public we'll need finAPI.

      Correct — and note the reason is legal, not technical. Reading someone's bank account is a
      regulated activity under PSD2 (the second EU Payment Services Directive); doing it yourself
      requires a BaFin licence as an AISP (Account Information Service Provider). We will never
      hold that licence — we consume a company that does, such as finAPI or Tink.
      D5 schedules the real finAPI sandbox at M6, and the stub sits behind the same adapter
      interface, so switching is a swap of one implementation.

6) Questions about D6:
    - What is it that we're doing here?

      Deciding how a finished statement reaches the renter by email, and treating that as part of
      the legal product rather than a utility. §556 Abs. 3 BGB (Bürgerliches Gesetzbuch, the German
      Civil Code) puts a hard deadline on delivery, so a landlord may later have to demonstrate
      *what* was sent and *when* — which means delivery must be logged and immutable, not
      fire-and-forget.
      "Modell A" is the sender decision: mail goes out from **our** domain `@lokaraimmo.de` with the
      landlord's name shown as the sender, rather than pretending to come from the landlord's own
      address. That way the three authentication records — SPF (Sender Policy Framework), DKIM
      (DomainKeys Identified Mail) and DMARC (Domain-based Message Authentication, Reporting and
      Conformance) — are on a domain we control, so the mail authenticates and is not filtered as
      spam. The actual sending provider is picked at M9; until then it is stubbed and logged.

7) Questions about D9:
    - What is explained here?

      A security hole found during a review, and the fix for it. `.env.example` — the file everyone
      copies to create their own `.env` — ships with the development token minter on, the demo
      seeder on (which also deletes data), and a signing secret published in the repository. Nothing
      in the codebase reads whether it is running locally or in production, so all three would stay
      on in a real deployment, and none of them would complain.
      The fix: a required `ENVIRONMENT` setting (`local | ci | staging | production`) with **no
      default**, so a deployment that forgets it fails to start instead of quietly assuming `local`.
      When it says `staging` or `production`, the settings object refuses to be constructed at all
      if any of the three dev switches is still on.
      The reason it fails at startup rather than per request: an `if` inside a request handler is
      one forgotten branch away from being wrong, and it fails silently. Refusing to boot fails once,
      loudly, at the only moment where somebody is watching.
      Status: specified, **not implemented on `main`**. The failing test
      `apps/api/tests/test_environment_guard.py` exists and is red on purpose only on branch
      `slice/m5-pre-context-read`, which is unmerged — so on `main` today nothing guards the
      dev-token minter, the seeder or the published JWT secret. `ApiSettings` has no `environment`
      field yet. Do not read this entry as saying the gate is in place.

---

**Note on 0):** expanding abbreviations across the existing `docs/` files is a separate editing
pass over roughly a dozen files. Say the word and it gets done as its own commit, so the diff is
reviewable on its own.
