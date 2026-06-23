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

Agent team:

| Agent | Purpose | Main data |
|---|---|---|
| `OlistOrchestrator` | Routes each question to one specialist | ADK `sub_agents` |
| `OrdersAgent` | Order status, delivery timing, late vs estimate | `orders_enriched` |
| `CarriersAgent` | State-lane delivery performance | `carrier_kpis` |
| `SellersAgent` | Seller fulfillment + CSAT KPIs | `seller_kpis` |
| `ReviewsAgent` | Review score vs delivery delay + low-score comments | `review_kpis`, `order_reviews` |
| `ReturnsAgent` | Canceled/unavailable order-rate proxy | `orders`, `customers` |
| `PaymentsAgent` | Payment mix and installment behavior | `order_payments` |
| `GeoAgent` | Seller-state to customer-state lanes | `orders`, `items`, `sellers`, `customers` |
| `DataAnalystAgent` | Schema, table listing, safe ad-hoc SQL | all allowed tables/views |

Important honesty note: Olist has no `carrier_id`. `CarriersAgent` uses `customer_state` lane performance as a carrier-style proxy and must disclose this in answers.

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

- `Which state has the worst on-time delivery?`
- `Do late deliveries get worse reviews?`
- `Show me the schema of the orders table.`
- `Installment distribution for credit card payments.`

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
