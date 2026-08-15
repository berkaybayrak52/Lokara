# LEAD-HANDOFF.md — permanent guide for the main session

This file defines how the main conversation reviews and closes work. It is tracked and durable.
It is not a session log, backlog, legal specification or status report. Update this file in place
only when a lasting review practice changes. Git keeps its history; never create dated copies.

## 1. Where truth lives

| Question | Source |
| --- | --- |
| What rules override everything? | `CLAUDE.md` |
| What is built and what comes next? | `PLAN.md` → execution order |
| How do agents, lanes, worktrees and gates operate? | `AGENTS.md` |
| What is the architecture? | `lokara-arch.md` |
| What is the calculation source? | `berkay-work/` → `docs/` → engines |
| What does a specific feature require? | The matching file under `docs/` |
| What happened in the latest session? | `LAST_OUTPUT.md` |

`LAST_OUTPUT.md` is only Emir's short summary window. It never overrides Git or tracked docs.
Use `scripts/check_handoff.sh` only to confirm that it names the current HEAD.

## 2. What the main session owns

- Emir controls scope, priorities and whether work is merged or pushed.
- The main session reads agent reports, verifies them, decides what ships and writes
  `LAST_OUTPUT.md`.
- Agents do not decide what to build next, mark milestones complete, merge, push or write the
  session summary.
- Preserve existing user changes. Separate unrelated edits before committing or merging.
- Ask Emir only when a missing choice would materially change the result or expand the scope.

## 3. Review standard

- Re-derive counts, survey results, arithmetic and every claim that says "verified".
- Check the code and command output, not the plan or an agent's confidence.
- A correct conclusion with the wrong mechanism is still wrong.
- Verify accusations and destructive Git advice with `git log`, `git show`, `git status` and the
  exact diff before acting.
- Treat a new tool as unverified until it runs locally and produces a known, non-empty result.
- Label every convention invented by Lokara as ours. Never present it as Berkay's rule or law.
- Preserve legal flags and provenance. `geprüft` does not mean lawyer-approved.

## 4. Reviewing agent work

- Worktree edits do not sync back. Inspect the worktree status, copy the exact files, then rerun
  gates in the main tree.
- Never run `scripts/verify_demo_path.sh` from an agent worktree. The database and Docker stack are
  shared resources.
- Read-only reviewers report findings; they never fix them.
- Implementers never write their own tests. Missing fixtures go back to `spec-scribe`.
- Keep `.claude` and `.codex` aligned. `check_agent_parity.py` is the authority.
- Do not widen a write lane to make an agent finish. A refusal can be the correct result.

## 5. Before merging

- Confirm the slice was cut from `main` and contains only the intended work.
- Inspect staged and unstaged changes separately. Preserve unrelated local edits.
- Run `scripts/gate.sh full`; use the demo gate when the milestone or output requires it.
- Record the PDF fingerprint before and after any slice that claims the document changed or stayed
  unchanged.
- Merge only green work. Do not push unless Emir asks.

## 6. Closing a session

- Overwrite `LAST_OUTPUT.md` using the short format in `CLAUDE.md`.
- Put temporary status in `LAST_OUTPUT.md`, execution status in `PLAN.md`, legal questions in the
  relevant `FRAGEN-an-Berkay-*.md`, specifications in `docs/`, and history in Git.
- Keep this file free of completed threads, old commit hashes, housekeeping lists and session
  stories. Add only guidance that should still be useful in a future conversation.
