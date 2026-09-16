# Lead handoff — M10-I4 technically complete locally

## Current state — 16.09.2026

I4 starts from `62c9fda` on `slice/m10-i4-investment-cockpit`. M10-I3 remains locally merged into
`main`; M10-I4 is unmerged. Emir authorized its commit and slice-branch push. `.lokara-red` is absent.

The owner cockpit, complete euro/percent input flow, account-scoped immutable default layout and
frozen deterministic Bank-PDF satisfy `docs/14` § 4.9 without a new migration beyond `0046`.
Source-derived missing-financing output stays renderable without fabricated values or a no-debt
claim. Mobile financial tables scroll locally without splitting digits.

Focused PDF/cockpit/API tests pass `18 + 7 + 22`. Both required reviews are clean. The demo gate
passes `2310` Python and `265` web tests plus the non-fresh demo path; RLS covers `81` tenant tables
and all `163` tenant foreign keys preserve account isolation. The ordinary statement fingerprint
is unchanged at `c4eecb355d57cec620dfcb0134fc9141` / `149275` bytes.

Browser proof uses intercepted actual engine fixtures at desktop, 390px and 720px equivalent
reflow widths, not database-backed UI or true browser 200% zoom. Direct renter-only PDF identity
and changed-canonical default-successor fixtures remain coverage limits; source guards were
audited. M10-F programme closure and all Page-07 production blockers remain pending.

Preserve the five unrelated untracked `adjustment/` files. Merging still requires Emir's authorization.
