# 00 — Product overview

## Product promise

Lokara is a responsive German operating-cost and heating-cost statement platform for private
landlords and property managers, from one unit upward. It prioritizes auditable calculations,
tenant isolation and clear German output. The web app comes first; native apps are future M10 work.

`rechtskonform` describes the product's intended use, not a warranty that every current preview is a
sendable legal statement. Lokara is a tool, not legal or tax advice, and never uses `rechtssicher`.

## Shipped floor

M1–M4 are a green, demoable floor:

- persisted buildings, units, tenancies, operating costs, allocation keys, meters/readings and
  heating-cost inputs behind a FastAPI API and account-scoped Postgres access;
- pure NK and heating/CO₂ engines with deterministic fixtures;
- a responsive Next.js landlord portal for the demo workflow;
- a landlord-only calculation/QA overview and PDF that reconcile the seeded NK and heating paths;
- canned document extraction behind a provider adapter, with human review before a cost is stored.

This floor is not yet legal-production approved. The current demo PDF is **not** the finalized Page
01 tenant document: it remains a live landlord building-wide preview. M6-B separately ships
owner-only technical archives with frozen actual advances, Saldo and independently rendered tenancy
documents. Those archives are neither renter delivery nor portal publication; the approved D1–D3
documentation baseline and M6-B technical closure do not clear `verify-before-production` flags.

## Billing-period boundary

Page 01 is binding for residential operating-cost statements:

- a shorter Rumpfperiode is allowed and uses its actual inclusive day count;
- a billing period **longer than 12 months is a hard block** before calculation or rendering;
- leap years use 366 actual days.

The former product claim that periods over 12 months were a differentiator is withdrawn. No product,
demo or sales copy may advertise that case as supported.

## Intended audience and future scope

The account model supports `SOLO` and `HAUSVERWALTUNG`, with roles on Membership rather than Account.
The shipped demo uses one owner membership and one account. Employee role enforcement and account
switching are shipped. Renter activation/portal, tax-adviser guest access, bank matching, tax export,
contracts, billing and native apps remain future milestones in `PLAN.md`.

Future product breadth includes the BetrKV catalogue, final tenant statements, UVI, a payment ledger,
Anlage V/DATEV, guards/reminders and mobile clients. Those are roadmap dependencies, not shipped
capabilities.

## Competitive thesis

Lokara competes on:

1. auditable, cent-exact domain depth rather than a shallow form-to-PDF flow;
2. freely changeable allocation assignments without deleting entered cost data;
3. account isolation in both application logic and Postgres RLS;
4. adapter-backed extraction, bank, meter and delivery edges;
5. clear pricing, exportability and human support as product commitments once implemented.

The current demo should be framed exactly as `docs/06` and `DEMO-RUNBOOK.md` describe: a real
persisted landlord workflow with stubs named as stubs, ending in an internal calculation/QA PDF.
