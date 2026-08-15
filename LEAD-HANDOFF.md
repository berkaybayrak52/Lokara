# LEAD-HANDOFF.md — context for the reviewing session

> **Who reads this.** The chat session that acts as lead: reviews Claude Code's output, decides
> what ships, writes the prompts, and talks to Berkay. Not an agent. Agents read `AGENTS.md`.
>
> **Why it exists.** `PLAN.md` records *what* to build and `AGENTS.md` records *how* work is
> executed. Neither records the reviewing posture — which claims turned out false, what to
> re-derive rather than trust, and which conventions are ours rather than Berkay's. That lived
> only in one long conversation, which is a bad place for it.
>
> Tracked in git, unlike `LAST_OUTPUT.md`. This is durable; that is scratch.

---

## 1. Where to look first

| Question | File |
| --- | --- |
| What is the contract? | `CLAUDE.md` |
| What is built, what is next, in what order? | `PLAN.md` → "Execution order" |
| How does the agent system work, and what has it got wrong? | `AGENTS.md` |
| What did the last Claude Code session do? | `LAST_OUTPUT.md` (verify it names HEAD) |
| What is Berkay still owed / owing? | `FRAGEN-an-Berkay-02.md` |
| What did Berkay actually write? | `berkay-work/` — agents edit only with Emir's explicit permission |

**Check this before believing `LAST_OUTPUT.md`:** `scripts/check_handoff.sh`. It has been red at
least once with a handoff two commits stale, because it only runs at `gate.sh full`/`demo` and
sessions close on `fast`.

---

## 2. The rule that is easiest to break

**`berkay-work/` is immutable to agents without Emir's explicit permission.** Its current view is
deliberately small: `Rechtsstand-Register/` holds the one authoritative register, and
the matching Notion pages with their additional notes; `Spec-Seiten/` holds the current specs,
replies and supporting material. The CSV remains authoritative for structured fields and flags. A
new export is integrated only as an authorised source update; agents never choose or rewrite it
themselves.

---

## 3. Conventions that are OURS, not Berkay's

These must never be cited as if they were German law or his spec. All three are flagged as ours
in `docs/03` § 9.2 and in `FRAGEN-an-Berkay-02.md` § 1.

1. **Several landlord parties → the residual goes to the *first* in deterministic order**, and the
   same one in all four blocks, so a single Eigentümer row explains every ±ct. *First*, not last,
   so appending a unit cannot move it.
2. **No landlord party at all → the block keeps largest-remainder.** The engine must never hand a
   residual to a renter to force a block to reconcile. **This is the majority of buildings**, which
   is why row 2 exists: without it, Berkay's rounding rule governs only buildings with a vacancy.
3. **`nk-engine` stays largest-remainder** until page 01/02 is transcribed. Deliberate, not an
   oversight — the canonical €1.200 fixture is identical under both methods (residual exactly 0),
   so nobody may claim the change moved it.

---

## 4. Berkay thread

**Answered (his `Antwort-an-Emir_01b-Uebergabe.md`, 13.08.2026):**

- **F19** — we were right, `abzug` = 90.121 ct. Corrected in Notion.
- **F16/F26** — *we* were wrong. 4.227 is the Verteilungsrest, not a rounded share. **Our fix.**
- Ho/Hu, K3, R1/R5/K9, H2 — unchanged.
- Emissionsfaktor Erdgas: **the register wins** (0,201 Hu / 0,181 Ho), not the looser figures in
  his earlier message.
- **7 flags flipped** to `geprüft` (3 Emissionsfaktoren, 3 AfA rates, the 15 % rule). Mietpreis-
  bremse was already `geprüft`, so his "8 verified" is accurate. Verified by diffing both CSVs.
- **DWD importer: two bugs.** CSV headers are `DatAnf;DatEnd;PLZ;KF`, not the XML names; the
  plausibility band widens to 0.40–1.80 because the real minimum is 0,49.
- **§ 6a Abs. 3 S. 4 Bekanntmachung exists** — BAnz AT 16.04.2021 B1. Its method *is* K12, so K12
  gets stronger. **But** it is nominally issued under GEG § 82 and whether it legally *is* the
  § 6a one needs a Fachanwalt. Record the qualification, do not cite it flat.
- **K12: 12-month Klimafaktor per billing period.** The 36-month mean is Energieausweis logic and
  would be wrong here.
- **CO₂: take `co2Cent` from the invoice's stated € amount**, never recompute from kg × price. We
  satisfy this today only because the K4 price fallback isn't built.
- **Block D2** — new: normed average-user fallback from the Heizspiegel when Block D has too few
  comparable units.

**Open — `FRAGEN-an-Berkay-02.md`:**

1. **Eigentümer line (blocking row 2).** He never saw this; his reply predates the question by
   three hours.
2. **The Heizspiegel norm includes Warmwasser, our figure can't.** § 9 HeizkostenV forces the
   split, so comparing our heating-only kWh against a combined norm flatters every renter — on a
   document § 6a Abs. 2 Nr. 3 makes mandatory.
3. **"über 500 m²" gap** — Wärmepumpe and Holzpellets values are missing from the CSV. A fallback
   with its own hole needs defined behaviour.
4. **co2online licence** — general use confirmed by mail; the § 6a-UVI use is not.
5. Housekeeping: date future exports.

**Do not guess any of these into `docs/`.** Row 2's fixture values differ depending on answer 1.

---

## 5. How to review a Claude Code report

The reports are careful and mostly right. They are also the only account of work you did not
watch. Both worktree runs so far contained one wrong number.

**Re-derive, don't accept:**

- **Counts and survey results.** "Six of ten call sites", "four cannot move money", "25 red
  fixtures" — check them. One near-miss: a claimed 10 sites vs 6 found reconciled only because
  party allocations share a dispatch helper.
- **Arithmetic against Berkay's fixtures.** Recomputing all three disputed values is what
  established that F19 was his error and F16/F26 were ours.
- **"Verified X" claims.** Ask what command produced the evidence. `gate.sh fast` does not run
  `check_handoff.sh`, `pytest`, `eslint`, `tsc`, `vitest` or the demo path.
- **Whether a gate has ever been red.** A check that has only ever passed is an assertion. Ask for
  the failing output, or better, a test that pins the failure.

**Structural checks:**

- **Worktrees do not sync back.** `git -C .claude/worktrees/agent-<id> status --short` is the
  truth; the report is not. Re-run gates in the main tree.
- **Did `LAST_OUTPUT.md` get rewritten?** It is the next session's only inheritance.
- **Is a new convention labelled as ours?** Anything invented at the seam between his model and
  our data structure is ours until he confirms it.

---

## 6. Failure modes that have actually happened

Recorded because each one cost real time and none was obvious in advance.

**From the lead (me):**

| What | Lesson |
| --- | --- |
| `pdf_fingerprint.sh` piped to GNU-only `md5sum` with no `-e`; printed an empty hash and exited 0 — I "verified" it on Linux | **A tool handed over is unverified until it runs on their machine.** A verification tool that can pass by producing nothing is worse than none. |
| Relayed `git reset --hard origin/main` on a claim about "6 commits from a backed-out fast-forward" | Two of them existed nowhere else. **Never relay a destructive command from an unverified premise.** |
| Said Phase G was `MIGRATION-PLAN.md`'s only live content | §8 held an RLS rule two scripts cite as their reason for existing. **Read the whole file before recommending deletion.** |
| Told Berkay four rule changes were "eingebaut" | Only two were wired. **Check the code, not the plan, before telling a third party something shipped.** |
| Diagnosed K9/F26 with the right conclusion and the wrong mechanism | The named call site did not exist. Right answer, wrong reason, still wrong. |

**From the agents:**

- `engine-implementer` uses a worktree even when told to work in place. Check for one.
- `statement-reviewer` never returns an empty finding list, so it can loop indefinitely and pull
  sessions off the execution order. Only a human stops it.
- Both implementers correctly **refused to end green the wrong way** (satisfying their own
  fixtures, editing the write-scope hook). That refusal is the system working — do not "unblock"
  it by widening a lane. Finish the step yourself.

---

## 7. Housekeeping backlog

Small, none blocking, all easy to lose:

- [ ] `LAST_OUTPUT.md` is stale — records `4cce4ee`, HEAD is `c796e0d`
- [ ] F16/F26: fix our reading; `FEEDBACK-to-Berkay-01b.md` claims two defects where there is one
- [ ] Import the fresh register (180 rows) into `rules-store` **with provenance** — `geprüft` must
      record who verified and when, or nobody can later tell "spec author read the statute" from
      "lawyer signed off"
- [ ] Cherry-pick the ENVIRONMENT guard + `gate.sh` skip-hole fix from `slice/m5-pre-context-read`
      onto main — main currently has nothing guarding the dev-token minter, the seeder, or the
      published JWT secret
- [ ] `check_agent_parity.py`: a reorder-only divergence prints "0 lines only in .claude, 0 only in
      .codex" and no detail
- [ ] Reported, no legal exposure: Framer Motion is a locked decision and a UI-DoD checkbox but is
      installed nowhere; `docs/04` lists four packages that do not exist; `README`/`AGENTS` do not
      explain the `berkay-work/` source precedence; `pyproject` pins `httpx2` unrecorded

---

## 8. Standing decisions

- **No deadline.** Stated twice, including after a 27.08 pitch date surfaced. Hard rule 3 makes a
  demo date cheap anyway: show the last `demo-green-<n>` tag, never reorder work to reach one.
- **Transcription is the first step of each row, not a separate phase.** Hard rule 1. A
  transcription's only real test is a golden fixture that passes, and 130 of 180 register values
  are still `verify-before-production` — batch-transcribing would bake placeholders into `docs/`
  at scale. The one exception is the register itself: structured data, import it nearly as-is.
- **`.codex/` stays** as the fallback for when tokens run out. Now at real parity (hooks identical
  modulo the env-var name; `check_agent_parity.py` compares definitions, hook scripts and wiring,
  with nine tests). **Nobody has actually run `codex` against the repo since** — equivalent on
  paper, unproven in practice.
- **New Claude Code session per row.** Hard rule 4. The repo is the memory.
