# LEAD-HANDOFF.md — next main session

Read `CLAUDE.md`, `AGENTS.md` and `PLAN.md` first. Verify this handoff with `git status`,
`git log` and the named branch before acting.

## Repository state — 20.08.2026

- Branch: `slice/docs-15-f03`, based on `main` at `d5e2f80`.
- `main` remains two commits ahead of `origin/main`; nothing was pushed.
- D1 is complete, approved and closed. `docs/09` is merged.
- `docs/15` is complete and approved by Emir on 20.08.2026, but not merged yet.
- Do not merge or push without Emir's separate instruction.

## F03 resolution

Berkay's tracked `08_BankMatching_F03_Patch.md` resolves the omitted F03 as E12. All thirteen
`BANKMATCH-F01…F13` oracle entries are executable. F03 keeps two mechanisms separate:

- `isPotentialDuplicate = true` forces Review and is never silently discarded;
- the same provider transaction `id` is deduplicated before channel selection and scoring.

The focused Page 08 suite passed 13 tests. Ruff, formatting, diff checks and the fast gate passed;
the fast gate reported 348 pure-package tests. These are data-only transcription checks, not
production bank-matching approval.

## D2 continuation

The F03 source blocker and `docs/15` review gate are closed. The next D2 document is `docs/12`,
followed by `docs/16`. Because every slice starts from `main`, first merge `slice/docs-15-f03` only
after Emir separately authorizes it, then create a fresh `slice/docs-12` from updated `main`.

Implementation, D3, Slices A–C and M5 remain paused. Do not edit `berkay-work/`, and do not read or
modify `docs/01-tech-stack-explanations.md`.
