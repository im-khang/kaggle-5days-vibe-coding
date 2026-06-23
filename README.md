# Olist Ecommerce Analytics Agent

Multi-agent AI team for Brazilian e-commerce operations analytics.

GitHub: https://github.com/im-khang/kaggle-5days-vibe-coding

## What It Does

Answer Olist ops questions in natural language using Google ADK + BigQuery:

- delivery lateness and on-time rate
- seller performance
- review impact from late delivery
- payment mix and installments
- geographic lane performance
- safe ad-hoc SQL via data analyst fallback

## Why This Repo Exists

This repo is the build folder for the Kaggle 5-Day AI Agents capstone. The actual product is Olist. Harness is only the structure that keeps the work organized and verifiable.

Source of truth:
- `02-PROJECTS/Olist Ecommerce Analytics Agent/{overview,tasks,decisions}.md`
- `03-NOTES/MOCs/Kaggle AI Agents Course MOC.md`
- `OBSIDIAN_VAULT_PATH` in `~/.hermes/.env`

## Current Status

- M0–M5 done
- GitHub repo public
- 12/12 eval cases passing
- Next: Kaggle notebook writeup, video, final submission

## Repo Layout

- `olist-ops-agent/` — actual Olist app
- `AGENTS.md` — local project rules for agents
- `docs/` — harness docs and decision records
- `scripts/` — harness tooling

## Olist App

The working agent lives in `olist-ops-agent/`.

Main files:
- `olist-ops-agent/olist_ops/agent.py`
- `olist-ops-agent/olist_ops/tools.py`
- `olist-ops-agent/scripts/bigquery_upload.py`
- `olist-ops-agent/tests/eval/`

Run:

```bash
cd olist-ops-agent
uv sync
cp .env.example .env   # fill GCP project first
uv run adk web --port 8001 .
```

Data is not committed. Download the 9 CSVs from Hugging Face:

```bash
cd olist-ops-agent
pip install huggingface-hub
python -c "
from huggingface_hub import snapshot_download
snapshot_download('miminmoons/olist-ecommerce-for-delivery-and-review-prediction',
                   local_dir='data/', repo_type='dataset',
                   allow_patterns=['*.csv'])
"
```

Eval:

```bash
uv run adk eval olist_ops tests/eval/datasets/olist_cases.json \
  --config_file_path tests/eval/eval_config.json \
  --print_detailed_results
```

## Harness Note

Harness is still here as repo structure, docs, and validation support. It is not the product.

If you want the harness docs, start with:
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_MATRIX.md`
