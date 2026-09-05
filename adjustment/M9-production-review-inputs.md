# M9 production-review inputs

M9 is technically complete and review-clean on `development`. It is not production-approved.

Please confirm or provide the following items:

## 1. Delivery provider

- Provider: ______________________________
- Scheduler/worker: ______________________
- EU/DE data-processing and DPA check: ☐ confirmed
- Automation remains default-off until this is approved: ☐ confirmed

## 2. UVI authority and artifact

- Frozen renter-visible UVI PDF/artifact: ______________________________
- Selected and implemented PLZ/geodata source: `WZBSocialScienceCenter/plz_geocoord`,
  version `2019-01`, commit `927da8a86e9b6e5ebb499cd9259cd1afd3e3c6d2`, Apache-2.0;
  SHA-256 `d427a6687a7cb286b3a9b4091831a06aaf0a0da40bd7c76cab7a82ac96e0d9a2`.
  The pinned source and attribution are recorded in `docs/16` § 7.2; source selection is closed.
- Missing UVI register rows supplied and primary-source checked: ☐ yes
- Exact monthly content authority and Rechtsstand: ____________________
- Delivery cadence: ______________________________

## 3. Checklist catalogue

- Production checklist catalogue/version: ______________________________
- Effective date and source: ______________________________

## 4. Open legal/runtime decisions

Please mark each as “fix required”, “accepted for later”, or provide the authoritative source:

- Guard runs must not trust client-supplied `today`/`now`: ____________________
- Discovery-token expansion and undeletable-row risk: ______________________
- `StubEmailGateway` idempotency and cross-account PDF isolation: ___________
- Hardcoded legal values and missed exact-day warnings in evaluators: _______

These remain `verify-before-production` until resolved. They must not be presented as settled
legal authority without the required primary source or decision.

## 5. Promotion decision

- Commit this checkpoint: ☐ yes ☐ no
- Merge/promote from `development`: ☐ yes ☐ no
- Push: ☐ yes ☐ no

No commit, merge, or push will happen without your separate authorization.
