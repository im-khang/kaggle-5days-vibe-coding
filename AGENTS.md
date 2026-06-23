# Agent Instructions

## Project: Kaggle 5-Day AI Agents Capstone (Vibe Coding with Google)

This repo is the build folder for the capstone of the **5-Day AI Agents:
Intensive Vibe Coding Course with Google** (Google × Kaggle, free). It is NOT a
generic ML/data-science notebook competition.

Course dates: June 15–19, 2026. Capstone opens June 19 (end of Day 5).
**Submission deadline: June 30, 2026.** Completion → Kaggle badge + certificate.

Goal: build and submit ONE working AI agent that solves a real, defined problem
with a real harness (tools, context, guardrails, evals) — not a toy demo.

Required capstone deliverables (all four, on Kaggle):
1. Working AI agent — actually runs, solves a defined task.
2. Kaggle writeup — the submission notebook/post.
3. Video explanation — walkthrough of what it does + how.
4. Design rationale — architecture, context design, tradeoffs, failures.
5. Code link — public GitHub repo.

Source of truth = Obsidian vault, not this repo. Before working, read:
- Project: `02-PROJECTS/Olist Ecommerce Analytics Agent/{overview,tasks,decisions}.md`
- MOC: `03-NOTES/MOCs/Kaggle AI Agents Course MOC.md`
- Vault path: `OBSIDIAN_VAULT_PATH` in `~/.hermes/.env`.
Repo `docs/` (stories, decisions, product) must stay consistent with the vault.
When they drift, the vault wins; update the repo to match, not the reverse.

Rules:
- The capstone direction is locked at the **Day 5 gate (June 19)** in the vault
  `decisions.md` (D1). Do not start the build sprint before that gate is filled.
- Mirror vault milestones M0–M7 as harness stories; one story per milestone, not
  one ad-hoc "baseline notebook."
- Keep notebooks/scripts runnable end-to-end; no orphaned cells or hardcoded
  local paths.
- The agent must have an eval/verification loop that catches bad output
  (Day 4 principle: verification is the differentiator).
- Every claimed score/metric must trace to a real run — no invented numbers.
- Prefer reproducible Python over manual UI steps; record exact commands.
- Working artifact > description of one. Run code before claiming results.
- Write a receipt to `05-HERMES-OUTPUTS/receipts/` in the vault after material
  repo changes that affect project truth.

<!-- HARNESS:BEGIN -->
## Harness

This repo uses Harness. Before work, read:

- `README.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTEXT_RULES.md`
- `docs/TOOL_REGISTRY.md`
- `scripts/bin/harness-cli query matrix` on macOS/Linux, or `.\scripts\bin\harness-cli.exe query matrix` on Windows

Use the Rust Harness CLI at `scripts/bin/harness-cli` on macOS/Linux or
`scripts/bin/harness-cli.exe` on Windows as the main operational tool. Before a
step that could use an external tool, run `scripts/bin/harness-cli query tools
--capability <name> --status present` to see what is equipped; an absent
capability is a clean skip.
<!-- HARNESS:END -->
