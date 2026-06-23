# 0008 Capstone Direction Gate

Date: 2026-06-19

## Status

Accepted

## Context

This repo builds the capstone for the 5-Day AI Agents Course (Google × Kaggle).
The capstone direction was locked at the Day 5 gate (June 19, 2026) before the
build sprint started.

Three options were evaluated:
- A: VN 3PL Performance Excel agent (single-table, limited)
- B: Generic chat agent (no real problem to solve)
- C: Olist Brazilian E-Commerce multi-table analytics agent

## Decision

Option C: build the Olist Ecommerce Analytics Agent.

Rationale:
- Multi-table dataset (9 tables, ~100k orders) models real ops complexity
- Real lifecycle dates enable delivery timeliness analysis
- Reviews + CSAT data enables root-cause analytics
- Public dataset, auth-free (HuggingFace mirror)
- Proven ADK multi-agent pattern reusable from prior prototype

## Consequences

- Full re-scaffold of repo from prior 3PL prototype
- 8-day build sprint to deadline (June 30)
- Mitigated by reusing the proven ADK agent pattern
