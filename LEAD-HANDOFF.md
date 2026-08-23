# LEAD-HANDOFF.md — Slice B review-complete; Block-(c) follow-up pending

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status` and
`git log` before acting. The dated material below is preserved as historical evidence. This current
update overrides its pre-review and pre-transcription status claims.

## Current update — 23.08.2026

- M5's bootstrap foundation was locally merged into `main` as `1300db1`; no push occurred. It adds
  only subject-scoped bootstrap contexts and the `0014` bounded identity read, not the M5 UI remainder.
- M5's backend role and assigned-building guard was locally merged into `main` as `99ac47e`; no push
  occurred. It covers OWNER, EMPLOYEE and TAX_ADVISOR behaviour across current `/a/{accountId}/…`
  routes, with `404` for inaccessible building resources. The switcher, renter portal and tax routes
  remain separate work.
- Its full and non-fresh demo gates are green (993 Python tests) and its boundary audit is clean. The
  statement review found two pre-existing Page-01 PDF/spec mismatches but no M5 regression; `PLAN.md`
  records the separate follow-up.
- Round 4 was transcribed and merged locally into `main` (`d9b3ace`, `24e5818`, `bff2e68`).
  `Antwort-an-Emir_04.md` remains untracked at the repository root pending Emir's filing decision.
- Slice B is review-complete: the boundary audit found no confirmed isolation or immutability issue;
  the statement review found no rendering/calculation regression and required the status correction
  now recorded in `PLAN.md`.
- Migration `0009` makes confirmed MDL rows append-only to the app role, rejects overlapping
  `person_count` periods, and makes the Fiktivbelegung setting immutable. The full gate passed
  with 875 Python and 33 web tests before this rebase.
- Slice B remains pending the narrow Round-4 Block-(c) PDF correction. Do not implement §12
  reductions in that follow-up; they require a separate Page-01b engine slice.

## Repository state — 22.08.2026

- Branch `slice/b-page01-closure` at `b115192`, one commit ahead of local `main` (`184a84d`).
- Nothing merged, nothing pushed. M5 remains paused.
- Working tree clean except one untracked file: `Antwort-an-Emir_04.md` (see § 3).
- Slice A remains complete, approved and merged locally. D1–D3 remain complete and merged locally.

## 1. Slice B — what is true

Implemented and committed: the persisted Page 01 path. Real building and period selection replacing
the module constants; D0 Fiktivbelegung person-days entering the denominator via a derived
landlord-side row; `consumptions` reaching `NkInput` so a persisted CONSUMPTION cost no longer 500s;
German 422s for an over-long window and for overlapping occupancy; the server-side
`OWNER`/`TENANT`/`TAX` projection; migrations `0007` (`person_count`, Fiktivbelegung mode + waiver
CHECK) and `0008` (`mdl_statement`, `mdl_statement_position`, append-only); confirmed-MDL ingestion
through `routers/mdl.py`; the PDF passthrough table.

Gate evidence, all re-run at `b115192`:

- `scripts/gate.sh full` green — 869 Python tests, 33 web tests, ruff, format, `mypy --strict`,
  engine purity, agent parity.
- `scripts/gate.sh demo` — demo path green: RLS clean over 18 tenant tables, 22 tenant FKs scoped,
  seed → render → 22 goldens present and 8 de-scaling canaries absent.
- PDF fingerprint `a45fa3d1e3d69957948e58885b4ab797`, 149280 bytes, re-rendered after a full reseed:
  **unchanged** from the Slice A baseline. The demo document did not move.

### What is NOT true: Slice B is not reviewed

`statement-reviewer` and `boundary-auditor` are both mandatory for this slice under `AGENTS.md` § 7
— it changed statement data, the engines, the PDF, a landlord-facing screen, two tenant tables and
an authorization surface. **Both were launched and both died to a 600-second watchdog stall,
returning no findings at all.** That is an infrastructure failure, not a clean bill of health.

So "green" here means the implementation passes its own tests. It does not mean reviewed. Run both
before proposing a merge, one at a time rather than concurrently over the same 37-file diff, and
scope each prompt to a named file list.

### One finding carried forward, unconfirmed

`uq_mdl_statement_building_period_version` (migration `0008`) is **not account-scoped**. A test
author observed that Postgres therefore raises `UniqueViolation` on it *before* the FK check on a
cross-account parent insert. Likely benign rejection ordering — a `building_id` belongs to exactly
one account and the row is rejected either way — but assess whether the error is an
information-disclosure channel. Nobody has ruled on it.

### Slice B's own open assumption

The partial-self-use rule is shipped as a **flagged Lokara assumption, not a transcribed source
rule**: a full-unit `SelfUsePeriod` removes those days from the D0 vacancy derivation; a partial one
leaves the day a vacancy day and emits a German finding. Page 01 has no rule for the constellation.
Recorded in `docs/02` § 5 and asked in `FRAGEN-an-Berkay-04.md`. It is **not** answered by the new
Berkay document.

## 2. Deliberately left stale

`PLAN.md` still says Slice B "is next", and its M3/M4 headings still read "Page 01 reconciliation
pending". That is **not an oversight** — Slice B is not closed until the reviews run, and § 3 below
will move several `docs/` status rows anyway. Writing "closed" now would make `PLAN.md` claim more
than is true. Update it when the reviews land, not before.

## 3. `Antwort-an-Emir_04.md` — new source authority, UNPROCESSED

1,164 lines, Berkay's round-4 answers, dated 21.08.2026. It appeared in the working tree on
22.08.2026 and **no part of it has been transcribed**. It is untracked, unmoved and uncommitted.

`CLAUDE.md` § 4 governs it: transcribe the rule, inputs, formula, edge cases, legal basis and
`Rechtsstand` into the owning `docs/` file. Do not copy it into `docs/`. Where it supersedes an
existing rule, § 4 requires the reason be recorded in the transcribed spec **so the old rule is not
restored later**.

### It supersedes approved rules — do not plan against the current text

| Approved doc currently says | Berkay's round-4 answer | Owning doc |
| --- | --- | --- |
| `01b-F25`: the 3 % right is "not added together with" the 15 % right | **Wrong in that absoluteness.** They do combine — they hit *different cost masses*. The 15 % runs only on the part actually not billed by consumption; the 3 % on the whole share. There are **two** 3 % rights (§ 12 Abs. 1 S. 2 and S. 3), not three: S. 2 is one Tatbestand with two triggers. Max 21 %. Build three separately switchable summands on the same ungekürzt base, never cascading. Warn (non-blocking) from two grounds. | `docs/03` |
| Block-(c) copy is provisional; "do not invent final wording" | **Final and binding.** Two texts for two readers. Block (c) is a **sub-line of the Eigentümer residual**, never added beside it; no Bemessung and no quota; **printed only when ≠ 0,00 €** but always carried in the audit log; the word "Rundungsdifferenz" is mandatory. | `docs/03`, `docs/08` |
| `docs/09`: `elektropruefung` is "instanzgerichtlich uneinheitlich" | **Overruled.** BGH VIII ZR 123/06 (14.02.2007): recurring safety inspections are § 2 Nr. 17 Betriebskosten. The "uneinheitlich" note must go; flag rises to `geprüft`. Needs a new `pruefungOhneMaengelbeseitigung` rule — the inspection is allocable, fixing what it finds is not. | `docs/09` |
| `docs/09`: `trinkwasseruntersuchung` = Nr. 2 | **Nr. 17 + `benennungspflichtig`, with a fallback route to Nr. 2** instead of a hard zero. Chosen as the dominant strategy under asymmetric risk, not as the better doctrine. `09-F28` stays valid unchanged as variant B; variant A is added beside it. No recomputation. | `docs/09` |
| `docs/12`: the 5-year/6-year meter conflict is unresolved | **Not a source conflict — a Rechtsstand problem.** Six years for all four device types since the Third MessEV amendment, in force 04.11.2021. Any source saying five years predates it. | `docs/12` |
| `docs/12`: Eichfrist arithmetic | **A bug he raises unasked.** § 34 Abs. 2 MessEV: periods of a year or more end at **31.12. of the year the period expires**, not on the anniversary. A day-exact guard alarms up to 10½ months early and produces replacement advice that costs the landlord money. Also: **Heizkostenverteiler have no Eichfrist** — remove them from the guard. | `docs/12` |
| `docs/10`: the F11 month/day authority choice is open | **Decided by statute, not convention.** § 7 Abs. 1 S. 4 EStG knows only twelfthing; day-exact AfA apportionment does not exist. K09 = full started month, `453.798 ct`; `447.887 ct` is discarded. The reverse case (letting → self-use) ends with the month *before* and needs its own fixture. | `docs/10` |
| `docs/13`: Page 06 § 559 Abs. 3a | **A gap he raises unasked.** Abs. 3a has **three** sentences. S. 3 is a **€0.50/m² heating sub-cap** (§ 555b Nr. 1/1a, echoed by § 559e Abs. 3) that Page 06 carries nowhere. Needs a **second parallel counter**, and `massnahmeArt` in the data model — without it the split is not reconstructible later. Also: the six-year window is a sliding backward window anchored on *Wirksamwerden*, labelled `UNSICHER` (Wortlautauslegung, no BGH). | `docs/13` |

### Also delivered

- **`09-K01`–`K11`**, the eleven Page 02 register rows `PLAN.md` lists as production-blocking for
  Slice C. Five carry a **double Rechtsnatur** (`Konvention (X) / Rechtsprechung (Y)`) and he warns
  they must be entered that way or the coverage check drops them. `09-K01` records that person-count,
  unit and direct keys have **no legal basis at all** — pure `Vereinbarungssache` under § 556a BGB.
- Page 07 interest cascade (R13 → R3 proxy → "—", source persisted and displayed, never mixed);
  Zielrendite stays deliberately empty and must be recorded as a decision so nobody fills it in.
- UVI: the monthly DWD dataset for Block C is found and free (`hdd_3807/monthly`); station→PLZ
  mapping must be **persisted**, not computed live.
- Page 06: falling index → two equal buttons and no auto-send; Kaution → `floor, floor, Rest`,
  explicitly **not** through the largest-remainder distributor.

### Three discrepancies to resolve BEFORE transcribing

1. **Register arithmetic does not match.** He writes "Registergröße 51 → **62**". The authoritative
   CSV `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv` has **180 rows**, and `CLAUDE.md`
   pins that number (130 `verify-before-production` + 50 `geprüft`). His 51/62 counts something else.
   Reconcile with Emir; do not renumber the CSV to match a count whose basis is unknown.
2. **Two files he says ship with the package are absent.** `Lokara_Investitionsmodul_Demo.html` and
   `AfA-Wizard_Konzept_Entwurf.md` — his § 6.2 answers a question about them with "sie fehlen
   nicht". They are not in this repository. Ask Emir for them before planning Page 07 work.
3. **The file sits at the repository root**, not under `berkay-work/`. `CLAUDE.md` § 4 forbids agents
   changing `berkay-work/` without Emir's explicit permission, so **filing it is Emir's decision**.

### What it does not do

It does not contradict anything Slice B shipped. It does not answer the partial-self-use question.
And it **predates** the questions added to `FRAGEN-an-Berkay-04.md` on 22.08.2026 — those are
unanswered, and belong to a round five.

## 4. Boundaries that remain

- Keep every 3 % risk separate. There is no automatic sum or deduction. (The *cumulation rule* above
  is a legal finding for `docs/03`; it does not authorize an engine to net risks into one figure.)
- `berkay-work/` is read-only for agents. Its maintained top level is `Rechtsstand-Register/` and
  `Spec-Seiten/` only.
- Never present a flagged value, uncertain citation or Lokara convention as settled law. Several
  decisions above are explicitly labelled `Konvention` or `UNSICHER` and remain Anwaltspunkte.
- M6 still owns actual paid advances, Saldo/Nachzahlung/Guthaben, immutable finalization, archived
  bytes and hashes, and the rendered tenant document. There is no tenant PDF.
- Slice C applies renter-side half-up rounding and one NK owner residual; its flagged Page-02
  authority remains production-blocking.
- M5's bootstrap foundation is locally merged as `1300db1`; its migration is `0014`, following
  Slice C's `0013`.

## 5. Next decisions — all Emir's

1. Run the two Slice B reviews and close the slice, or start the Berkay transcription slice first.
2. Whether to merge `b115192` into `main`.
3. Where `Antwort-an-Emir_04.md` is filed, and whether the two missing companion files exist.
