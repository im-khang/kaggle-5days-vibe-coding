# Agent Instructions

This repo contains the Olist Ecommerce Analytics Agent — a Google ADK multi-agent team that answers Brazilian e-commerce ops questions over BigQuery.

## What Lives Where

- `olist-ops-agent/` — the agent application (Python, uv)
- `docs/` — architecture notes and decision records
- `AGENTS.md` — this file
- `README.md` — public-facing project intro

When you make changes, keep these consistent: code, docs, and decisions should not drift.

## Coding Rules

- Keep scripts and notebooks runnable end-to-end. No hardcoded local paths.
- Read existing code before adding new patterns. Match the project's style.
- The agent must have an eval/verification loop. Every claimed metric must trace to a real run — no invented numbers.
- Prefer reproducible Python over manual UI steps. Record exact commands when needed.
- Working artifact beats a description of one. Run code before claiming results.
- Do not commit secrets, real project IDs, or local environment files. `.env` is gitignored; use `.env.example` as the template.

## Agent Application

The agent lives in `olist-ops-agent/`:

- `olist_ops/agent.py` — `root_agent = ChiefSupplyChainOfficer` with department heads + direct specialists routed via canonical ADK `sub_agents` transfer
- `olist_ops/tools.py` — BigQuery tools (SELECT-only, billing cap, timeout)
- `tests/eval/` — eval cases + custom metrics
- `scripts/bigquery_upload.py` — load CSVs into BigQuery + create views

See `olist-ops-agent/README.md` for setup, run, and eval commands.

## Repository Notes

This repository was scaffolded with a project harness that provides templates for
architecture notes (`docs/ARCHITECTURE.md`), test/proof matrices
(`docs/TEST_MATRIX.md`), and decision records (`docs/decisions/`). Those docs are
informational; the source of truth for the agent's behavior is the code in
`olist-ops-agent/` and the eval set in `olist-ops-agent/tests/eval/`.
