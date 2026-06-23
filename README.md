# Olist Ecommerce Analytics Agent

A multi-agent AI team that answers Brazilian e-commerce operations questions using natural language, backed by BigQuery and Google ADK.

Built as a capstone for the [Kaggle 5-Day AI Agents Course](https://www.kaggle.com/learn-guide/5-day-ai-agents) (Google × Kaggle, June 2026).

## What It Does

- Answers ops questions about orders, delivery, sellers, reviews, payments, and geography
- Routes each question to the right specialist agent (9-agent team)
- Returns cited, SQL-backed answers — no hallucinated numbers
- Enforces SELECT-only safety: no writes, 10 GB cap, 30s timeout

## Architecture

```
┌──────────────────────────────────────────────────────┐
│               OlistOrchestrator                       │
│         Routes to ONE specialist per question         │
├──────────┬───────────┬───────────┬───────────────────┤
│  Orders  │  Carriers │  Sellers  │     Reviews       │
├──────────┼───────────┼───────────┼───────────────────┤
│ Returns  │ Payments  │    Geo    │   DataAnalyst     │
└──────────┴───────────┴───────────┴───────────────────┘
                         │
                    BigQuery
               olist_ecommerce
              (9 tables + 4 views)
```

| Layer | Choice |
|---|---|
| Framework | Google ADK 2.3 |
| Model | Gemini 2.5 Flash (Vertex AI) |
| Data | BigQuery dataset `olist_ecommerce` |
| Auth | Application Default Credentials |
| Eval | ADK eval, 12 cases, 4 custom metrics |

## Quick Start

```bash
git clone https://github.com/im-khang/kaggle-5days-vibe-coding.git
cd kaggle-5days-vibe-coding/olist-ops-agent

# Install dependencies
uv sync

# Configure
cp .env.example .env
# Edit .env: set GOOGLE_CLOUD_PROJECT to your GCP project
gcloud auth application-default login

# Download data (9 CSVs, ~120 MB)
pip install huggingface-hub
python -c "
from huggingface_hub import snapshot_download
snapshot_download('miminmoons/olist-ecommerce-for-delivery-and-review-prediction',
                   local_dir='data/', repo_type='dataset', allow_patterns=['*.csv'])
"

# Load into BigQuery
uv run python scripts/bigquery_upload.py

# Run the agent
uv run adk web --port 8001 .
```

## Eval Results

12/12 cases passing:

| Case | Status |
|---|---|
| worst_state_ontime | ✅ |
| seller_reviews_sp | ✅ |
| late_delivery_reviews | ✅ |
| payment_mix | ✅ |
| cancel_rate | ✅ |
| schema_orders | ✅ |
| list_tables | ✅ |
| out_of_scope_refuse | ✅ |
| freight_by_seller_state | ✅ |
| worst_sellers_ontime | ✅ |
| avg_days_late | ✅ |
| credit_card_installments | ✅ |

Custom metrics: `tool_use_quality`, `grounded_response`, `intent_satisfaction`, `sql_safety`

Run eval yourself:

```bash
uv run adk eval olist_ops tests/eval/datasets/olist_cases.json \
  --config_file_path tests/eval/eval_config.json \
  --print_detailed_results
```

## Repo Structure

```
olist-ops-agent/           # The agent application
  olist_ops/
    agent.py               # OlistOrchestrator + 8 specialists
    tools.py               # BigQuery tools (SELECT-only, safety caps)
    olist_metrics.py       # Custom eval metrics
  scripts/
    bigquery_upload.py     # Load CSVs → BigQuery + create views
  tests/eval/             # Eval cases + config
  .env.example            # Environment template
  pyproject.toml
  README.md               # Detailed app docs
docs/                     # Project decisions and architecture notes
AGENTS.md                 # Agent coding conventions
```

## Data

9 tables from the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (public, ~100k orders):

- `orders`, `order_items`, `order_payments`, `order_reviews`
- `customers`, `sellers`, `geolocation`, `products`, `product_category_translation`

4 derived views: `orders_enriched`, `seller_kpis`, `carrier_kpis`, `review_kpis`

## Tech Stack

- [Google ADK 2.3](https://google.github.io/adk-docs/) — multi-agent framework
- [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models) — LLM for routing + specialists
- [BigQuery](https://cloud.google.com/bigquery) — data warehouse
- [Vertex AI](https://cloud.google.com/vertex-ai) — model hosting
- Python 3.11+, uv

## License

MIT

## Acknowledgments

- Olist Brazilian E-Commerce Dataset (via [HuggingFace mirror](https://huggingface.co/datasets/miminmoons/olist-ecommerce-for-delivery-and-review-prediction))
- Google × Kaggle — 5-Day AI Agents Intensive Vibe Coding Course
