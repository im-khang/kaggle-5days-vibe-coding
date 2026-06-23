# Olist Ecommerce Analytics Agent

A multi-agent AI team that answers Brazilian e-commerce operations questions using natural language, backed by BigQuery and Google ADK.

Built as a capstone for the [Kaggle 5-Day AI Agents Course](https://www.kaggle.com/learn-guide/5-day-ai-agents) (Google × Kaggle, June 2026).

## What It Does

- Answers ops questions about orders, delivery, sellers, reviews, payments, and geography
- 21-agent team in 5 supply-chain departments (AgentTool pattern for cross-domain synthesis)
- Routes single-domain Q to one specialist; cross-domain Q calls multiple departments and synthesizes
- Returns cited, SQL-backed answers — no hallucinated numbers
- Enforces SELECT-only safety: no writes, 10 GB cap, 30s timeout

## Architecture

```
ChiefSupplyChainOfficer (CSCO)  ← AgentTool pattern: calls depts, synthesizes
│
├── 📦 HeadOfFulfillment
│     ├── OrdersAgent            delivery timing, lifecycle
│     ├── LaneAgent              customer-state lane (carrier proxy)
│     └── GeoRoutingAgent        seller→customer state pairs, freight by lane
│
├── 🤝 HeadOfSellerOps
│     ├── SellerPerformanceAgent KPIs, freight by seller state
│     └── SellerRiskAgent        risk scoring, intervention recommendations
│
├── 💬 HeadOfCX
│     ├── ReviewsAgent           CSAT by delay bucket
│     ├── ComplaintsAgent        low-score comments, customer impact
│     └── ReturnsAgent           cancellation/unavailable proxy
│
├── 💰 HeadOfFinance
│     └── PaymentsAgent          payment mix, installments
│
├── 📊 HeadOfBI
│     └── DataAnalystAgent       ad-hoc SQL, schema, cross-table joins
│
└── 📋 ExecutiveBriefingPipeline (SequentialAgent)
      ├── ParallelAgent: [Fulfillment, Seller, CX] KPI collectors
      └── SynthesisAgent → executive summary from state keys
```

| Layer | Choice |
|---|---|
| Framework | Google ADK 2.3 |
| Model | Gemini 2.5 Flash (Vertex AI) |
| Data | BigQuery dataset `olist_ecommerce` |
| Auth | Application Default Credentials |
| Pattern | AgentTool (agents-as-tools) for cross-domain synthesis |
| Workflow | SequentialAgent + ParallelAgent for executive briefing |
| Eval | ADK eval, 17 cases, 4 custom metrics |

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

17/17 cases passing (4 custom metrics: `tool_use_quality`, `grounded_response`, `intent_satisfaction`, `sql_safety`):

| Case | Domain | Status |
|---|---|---|
| worst_state_ontime | Fulfillment | ✅ |
| seller_reviews_sp | SellerOps | ✅ |
| late_delivery_reviews | Cross-domain (Fulfillment + CX) | ✅ |
| payment_mix | Finance | ✅ |
| cancel_rate | CX | ✅ |
| schema_orders | BI | ✅ |
| list_tables | BI | ✅ |
| out_of_scope_refuse | Refusal | ✅ |
| freight_by_seller_state | SellerOps | ✅ |
| worst_sellers_ontime | SellerOps | ✅ |
| avg_days_late | Fulfillment | ✅ |
| credit_card_installments | Finance | ✅ |
| cross_state_delivery_cancel | Cross-domain (Fulfillment + CX) | ✅ |
| executive_summary | Executive Briefing Pipeline | ✅ |
| cross_seller_review_gap | Cross-domain (SellerOps + CX) | ✅ |
| lane_by_freight | Fulfillment | ✅ |
| seller_intervention | SellerOps (risk) | ✅ |

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
    agent.py               # ChiefSupplyChainOfficer (root) + AgentTool wiring
    sub_agents/            # 5 departments, 11 specialists, Executive Briefing Pipeline
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
