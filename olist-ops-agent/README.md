# Olist Ecommerce Analytics Agent

Capstone agent for Kaggle 5-Day AI Agents course. It answers Olist ecommerce operations questions from BigQuery using a Google ADK multi-agent team.

## Problem

Olist marketplace ops data lives across 9 CSVs: orders, items, payments, reviews, customers, sellers, geolocation, products, and category translations. Ops questions like delivery lateness, seller performance, review impact, and payment behavior need joins and safe SQL.

This agent gives natural-language answers with tool-backed BigQuery evidence.

## Architecture

- Framework: Google ADK 2.3
- Model: `gemini-2.5-flash`
- Data store: BigQuery dataset `<YOUR_GCP_PROJECT>.olist_ecommerce` in `US`
- Entrypoint: `olist_ops/agent.py`, exposing `root_agent`
- Auth: Vertex AI / Application Default Credentials (`GOOGLE_GENAI_USE_VERTEXAI=1`)
- Pattern: **AgentTool** (agents-as-tools) — CSCO calls department heads and synthesizes
- Workflow: **SequentialAgent + ParallelAgent** for executive briefing pipeline

### Agent Team (5 departments, 21 agents total)

```
ChiefSupplyChainOfficer (CSCO)
├── 📦 HeadOfFulfillment
│     ├── OrdersAgent            delivery timing, lifecycle
│     ├── LaneAgent              customer-state lane (carrier proxy)
│     └── GeoRoutingAgent        seller→customer pairs, freight by lane
├── 🤝 HeadOfSellerOps
│     ├── SellerPerformanceAgent per-seller KPIs, freight by seller state
│     └── SellerRiskAgent        risk scoring, intervention recommendations
├── 💬 HeadOfCX
│     ├── ReviewsAgent           CSAT by delay bucket
│     ├── ComplaintsAgent        low-score comments, customer impact
│     └── ReturnsAgent           cancellation/unavailable proxy
├── 💰 HeadOfFinance
│     └── PaymentsAgent          payment mix, installments
├── 📊 HeadOfBI
│     └── DataAnalystAgent       ad-hoc SQL, schema, cross-table joins
└── 📋 ExecutiveBriefingPipeline (SequentialAgent)
      ├── ParallelAgent[FulfillmentKPI, SellerKPI, CXKPI]
      └── SynthesisAgent → reads state keys → exec summary
```

Key design: the CSCO uses `AgentTool` (not `sub_agents`), so it can call
multiple departments one-by-one and synthesize cross-domain answers. The old
transfer pattern handed control to ONE specialist and ended the turn.

Important caveats disclosed in answers:
- No `carrier_id`: lane performance uses `customer_state` as proxy.
- No returns table: `canceled` + `unavailable` order status is the proxy.
- No inventory/warehouse data: Olist is a marketplace (sellers ship direct).

## Data

CSVs are **not** in this repo (120 MB). Download from Hugging Face:

```bash
cd olist-ops-agent
# Install huggingface-hub
pip install huggingface-hub
# Download all 9 CSVs into data/
python -c "
from huggingface_hub import snapshot_download
snapshot_download('miminmoons/olist-ecommerce-for-delivery-and-review-prediction',
                   local_dir='data/', repo_type='dataset',
                   allow_patterns=['*.csv'])
"
```

Raw tables loaded 1:1 from the Olist CSVs:

- `customers`
- `geolocation`
- `order_items`
- `order_payments`
- `order_reviews`
- `orders`
- `products`
- `sellers`
- `product_category_translation`

Derived views:

- `orders_enriched` — lifecycle timestamps, delivery days, days late vs estimate, last-mile days, on-time flag
- `seller_kpis` — seller orders, delivery days, on-time %, review score, freight
- `carrier_kpis` — state-lane delivered orders, last-mile days, delivery days, on-time %, lateness
- `review_kpis` — review score grouped by delivery-delay bucket

## Setup

```bash
cd olist-ops-agent
uv sync
```

Environment variables used by the code:

```bash
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
BQ_DATASET_ID=olist_ecommerce
BQ_DATASET_LOCATION=US
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_LOCATION=us-central1
```

Do not commit `.env`.

## Load BigQuery

The dataset is already loaded locally. To recreate it:

```bash
cd olist-ops-agent
set -a; source .env; set +a
uv run python scripts/bigquery_upload.py
```

The loader creates/replaces all raw tables and the 4 derived views.

## Run ADK Web

```bash
cd olist-ops-agent
set -a; source .env; set +a
uv run adk web --port 8001 .
```

Open the ADK web UI, select `olist_ops`, and ask examples:

Single-domain:
- `Which state has the worst on-time delivery?`
- `Do late deliveries get worse reviews?`
- `Installment distribution for credit card payments.`

Cross-domain (CSCO calls multiple departments and synthesizes):
- `Which state has both the worst on-time delivery AND highest cancellation rate?`
- `Compare the 5 worst on-time sellers (min 50 orders) vs the 5 best. What is the review-score gap?`

Executive briefing (full Sequential + Parallel pipeline):
- `Give me a full executive summary of our supply chain health.`

## Eval

Eval assets live in:

- `tests/eval/datasets/olist_cases.json`
- `tests/eval/eval_config.json`

Run after ADK eval support is installed:

```bash
cd olist-ops-agent
uv sync --extra eval
uv run adk eval olist_ops tests/eval/datasets/olist_cases.json --config_file_path tests/eval/eval_config.json --print_detailed_results
```

Target custom metrics:

- `tool_use_quality`
- `response_has_table`
- `intent_satisfaction`
- `sql_safety`

## Safety

- `query_bigquery` accepts SELECT / CTE-only SQL.
- DML/DDL keywords are rejected.
- Cross-dataset references are rejected.
- Query cap: 10 GB billed, 30s timeout, 1000 returned rows.
- `geolocation` is large; agent instructions require aggregation, never raw `SELECT *`.
