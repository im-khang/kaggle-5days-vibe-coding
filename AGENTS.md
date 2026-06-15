# Agent Instructions

## Project: Kaggle 5-Day Vibe Coding

This repo is the working folder for the Kaggle "5 Days of Vibe Coding" challenge.

Goal: ship working ML/data-science notebooks and submissions across the 5-day program, with each day's work documented and reproducible.

Rules:
- Each day = one story packet (US-day-N) with a clear deliverable: notebook, submission, or experiment.
- Keep notebooks runnable end-to-end; no orphaned cells or hardcoded local paths.
- Pin dataset versions and record Kaggle competition/dataset slugs in story packets.
- Every claimed score/metric must trace to a real submission, CV output, or notebook run — no invented numbers.
- Prefer reproducible Python over manual UI steps; record exact commands.
- Working artifact > description of one. Run code before claiming results.

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
