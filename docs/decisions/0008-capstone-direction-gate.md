# 0008 Capstone Direction Gate

Date: 2026-06-15

## Status

Proposed (decision gate: June 19, 2026 — end of Day 5)

## Context

This repo builds the capstone for the 5-Day AI Agents Course (Google × Kaggle).
The capstone direction must be locked at the Day 5 gate (June 19) before the
build sprint starts, to protect the June 30 submission deadline.

The authoritative decision record lives in the Obsidian vault:
`02-PROJECTS/Vibe Coding Capstone Kaggle/decisions.md` (D1). This ADR mirrors
that gate into the harness decision layer so repo and vault stay consistent.

## Decision

Lock exactly ONE capstone direction at the June 19 gate. Candidates:

1. AI-assisted weekly ops report agent — reads a KPI table, finds
   deltas/exceptions, explains drivers, cites source rows, verifier loop checks
   math. Reuses AI Automation for Operations patterns. High portfolio fit.
2. Document-to-knowledge agent — ingests PDFs, OCRs figures, structures into a
   queryable cited knowledge base. Head start: PaddleOCR + extraction pipeline
   already built. Risk: scope creep on "queryable."
3. Code-task orchestrator — issue spec → plan → multi-file edit → run tests →
   self-correct → open PR. Matches the course subject. Hardest to ship in 7 days.

Chosen direction, problem statement, and measurable success metric to be filled
at the gate. Until then this ADR stays Proposed and the build sprint (US-006)
does not start.

## Alternatives Considered

1. Start building before the gate. Rejected — risks building the wrong thing and
   missing the June 30 deadline.
2. Build all three. Rejected — no path to ship four deliverables for three agents
   in ~7 days.

## Consequences

Positive:
- One bounded agent with a real eval loop is shippable by June 30.
- Repo decision layer stays consistent with vault truth.

Tradeoffs:
- Locking on June 19 leaves no slack to pivot direction late.

## Follow-Up

- Fill the chosen direction here AND in the vault `decisions.md` D1 on June 19.
- Then move US-006 (build sprint) to in_progress.
