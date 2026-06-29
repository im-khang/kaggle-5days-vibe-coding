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
- Auth: Vertex AI / Application Default Credentials (`GOOGLE_GENAI_USE_VERTEXAI=1`) or Google AI Studio (`GOOGLE_API_KEY`)
- Pattern: **sub_agents transfer** (canonical ADK multi-agent tree) — the CSCO routes each question to the single best agent via `transfer_to_agent`
- Workflow: **SequentialAgent + ParallelAgent** for executive briefing pipeline

### Agent Team (3 departments + 2 direct specialists, transfer routing)

```
ChiefSupplyChainOfficer (CSCO)   ← sub_agents transfer: routes to ONE agent
├── 📦 HeadOfFulfillment
│     ├── OrdersAgent            delivery timing, lifecycle, forecast
│     ├── LaneAgent              customer-state lane (carrier proxy)
│     └── GeoRoutingAgent        seller→customer pairs, freight by lane
├── 🤝 HeadOfSellerOps
│     ├── SellerPerformanceAgent per-seller KPIs, freight by seller state
│     └── SellerRiskAgent        risk scoring, intervention recommendations
├── 💬 HeadOfCX
│     ├── ReviewsAgent           CSAT by delay bucket
│     ├── ComplaintsAgent        low-score comments, customer impact
│     └── ReturnsAgent           cancellation/unavailable proxy
├── 💳 PaymentsAgent             payment mix, installments (direct specialist)
├── 📊 DataAnalystAgent          ad-hoc SQL, schema, charts (direct specialist)
└── 📋 ExecutiveBriefingPipeline (SequentialAgent)
      ├── ParallelAgent[FulfillmentKPI, SellerKPI, CXKPI]
      └── SynthesisAgent → reads state keys → exec summary
```

Key design: the CSCO uses `sub_agents=[...]`, so ADK exposes a real multi-agent
transfer graph and the orchestrator hands control to exactly one agent per turn.
Single-specialist departments (Finance, BI) were collapsed — `PaymentsAgent` and
`DataAnalystAgent` sit directly under the CSCO to avoid a redundant routing hop.
Broad multi-department reporting is handled by the `ExecutiveBriefingPipeline`
(deterministic Parallel + Sequential synthesis), not by orchestrator-level
free-form synthesis.

## MCP Servers & Tools (standing on giants)

Beyond the in-process Python tools, this project wires real, public MCP servers
and Google's first-party BigQuery toolset to each agent by role. We do **not**
ship a bespoke MCP server as the primary integration — we stand on existing
servers from the open-source and Google ecosystems.

### Google first-party BigQuery toolset (read-only)

`olist_ops/mcp_toolsets.py::google_bigquery_toolset()` returns Google's official
`BigQueryToolset` (`google.adk.integrations.bigquery`) configured with
`WriteMode.PROTECTED` (temporary session writes only, no permanent table
mutations). It exposes `execute_sql`, `forecast` (TimesFM),
`analyze_contribution`, `detect_anomalies`, `ask_data_insights`, and
`search_catalog`. Each agent receives only the subset it needs via `tool_filter`.

### Public MCP servers (stdio)

| Factory | Server | Transport |
|---|---|---|
| `fetch_toolset()` | `mcp-server-fetch` | `uvx` |
| `duck_search_toolset()` | `duckduckgo-mcp-server` | `uvx` |
| `sequential_thinking_toolset()` | `@modelcontextprotocol/server-sequential-thinking` | `npx` |
| `memory_toolset()` | `@modelcontextprotocol/server-memory` | `npx` |

### Agent → tool mapping

| Agent | Role-matched tools |
|---|---|
| OrdersAgent | Google BQ `forecast` (delivery-time projections) |
| LaneAgent | Google BQ `detect_anomalies`, `analyze_contribution` |
| GeoRoutingAgent | Google BQ `analyze_contribution` (freight drivers) |
| SellerPerformanceAgent | DuckDuckGo search (industry benchmarks) |
| SellerRiskAgent | Sequential-thinking + Google BQ `detect_anomalies`, `analyze_contribution` |
| ComplaintsAgent | Sequential-thinking (complaint clustering) |
| SynthesisAgent | Sequential-thinking (risk prioritization) |
| DataAnalystAgent | fetch + memory + full Google BQ toolset |

A standalone custom MCP server (`olist_ops/mcp_server.py`) and an MCP-consuming
agent variant (`olist_ops/mcp_agent.py`) are also included to demonstrate the
full MCP server/client loop in code.

## Agent Skills (ADK skills + CLI)

`skills/` contains role-specific, state-aware ADK skills (`SKILL.md` with YAML
frontmatter): `executive-briefing`, `seller-risk-audit`, `freight-lane-analysis`.
Each encodes trigger conditions, numbered steps, pitfalls, and output format.

`olist_ops/skill_registry.py` implements a concrete ADK `SkillRegistry`
(`LocalSkillRegistry`) that loads these skills and supports `get_skill` /
`search_skills`. CLI:

```bash
uv run python -m olist_ops.skill_registry --list
uv run python -m olist_ops.skill_registry --show executive-briefing
```

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

# Option A: Vertex AI + ADC
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_LOCATION=us-central1
OLIST_MODEL_PROVIDER=vertex
OLIST_MODEL=gemini-2.5-flash

# Option B: Google AI Studio API key
# GOOGLE_GENAI_USE_VERTEXAI=0
# GOOGLE_API_KEY=your-g...y
# OLIST_MODEL_PROVIDER=vertex
# OLIST_MODEL=gemini-2.5-flash
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

Executive briefing (full Sequential + Parallel pipeline):
- `Give me a full executive summary of our supply chain health.`

Note: this canonical transfer tree routes each question to one agent. For broad
cross-department reporting, use the Executive Briefing pipeline instead of
expecting orchestrator-level free-form synthesis.

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

## Orchestrator Routing Probes

`tests/orchestrator_routing_check.py` is a live routing test: it runs 10
advanced prompts through `root_agent` with an ADK `BasePlugin` that records
every agent activation and tool call (including nested specialist + MCP calls),
then asserts the orchestrator reached the correct department **and** specialist.

```bash
cd olist-ops-agent
set -a; source .env; set +a
uv run python tests/orchestrator_routing_check.py
```

Each probe forces the CSCO to route past the department head down to one
specific specialist — proving the hierarchy resolves, not just the top level.
Result: **10/10 passing** (report written to
`tests/eval/orchestrator_routing_report.json`).

| # | Prompt focus | Expected path | Proves |
|---|---|---|---|
| Q1 | 5 sellers, on-time <80% AND review <3.5, risk tier + intervention | CSCO → HeadOfSellerOps → **SellerRiskAgent** | Multi-factor risk routed to risk agent, not KPI agent |
| Q2 | Forecast avg delivery days next 30d for SP | CSCO → HeadOfFulfillment → **OrdersAgent** | Forecast delegated (Google BQ `forecast`), not refused |
| Q3 | Lateness outliers + lanes contributing most | CSCO → HeadOfFulfillment → **LaneAgent** | Anomaly/contribution lane analysis |
| Q4 | Decompose freight by seller_state, top 50 lanes | CSCO → HeadOfFulfillment → **GeoRoutingAgent** | Lane vs seller-state disambiguation |
| Q5 | Top-quartile seller on-time vs public benchmarks | CSCO → HeadOfSellerOps → **SellerPerformanceAgent** | External-benchmark question still delegated (DuckDuckGo MCP), not refused |
| Q6 | Cluster top 50 1-2★ comments into 4 themes | CSCO → HeadOfCX → **ComplaintsAgent** | Qualitative clustering routed to complaints, not reviews (sequential-thinking MCP) |
| Q7 | Review-score distribution by delay bucket | CSCO → HeadOfCX → **ReviewsAgent** | Numeric CSAT routed to reviews |
| Q8 | 5 worst states by cancel/unavailable rate | CSCO → HeadOfCX → **ReturnsAgent** | Returns proxy + caveat |
| Q9 | Credit-card installment distribution | CSCO → **PaymentsAgent** (direct) | Payments routed without a redundant head |
| Q10 | Find a view joining orders + reviews, list columns | CSCO → **DataAnalystAgent** (direct) | Catalog/schema lookup (Google BQ `search_catalog`) |

## Safety

- `query_bigquery` accepts SELECT / CTE-only SQL.
- DML/DDL keywords are rejected.
- Cross-dataset references are rejected.
- Query cap: 10 GB billed, 30s timeout, 1000 returned rows.
- `geolocation` is large; agent instructions require aggregation, never raw `SELECT *`.
