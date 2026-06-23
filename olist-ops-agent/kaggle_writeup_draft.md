---
title: "Olist Ecommerce Analytics Agent"
subtitle: "Multi-Agent AI Team for Brazilian E-Commerce Operations Analytics"
author: "Khang Nguyen"
date: "June 2026"
---

# Olist Ecommerce Analytics Agent

**Multi-Agent AI Team for Brazilian E-Commerce Operations Analytics**

Built for the Kaggle 5-Day AI Agents Capstone (Google × Kaggle, June 2026).

GitHub: [im-khang/kaggle-5days-vibe-coding](https://github.com/im-khang/kaggle-5days-vibe-coding)

---

## 1. The Problem

Olist is Brazil's largest online marketplace — connecting ~3,000 sellers to customers across 27 states. Their operations data lives in 9 separate CSV files (orders, items, payments, reviews, customers, sellers, geolocation, products, category translations).

An ops analyst trying to answer "Which state has the worst delivery performance, and is that dragging down review scores?" needs to:

1. Stitch 6+ tables in SQL or Excel
2. Figure out which "late" means (late vs estimate? vs carrier handoff? vs purchase date?)
3. Repeat for every new question

This agent solves that in seconds — ask a question in natural language, get a cited, data-backed answer.

---

## 2. Architecture: Why a Multi-Agent Team

Instead of one big prompt, I built a **21-agent supply-chain company** using Google ADK 2.3 (Agent Development Kit). Agents are organized into 5 departments under a Chief Supply Chain Officer (CSCO). The CSCO calls departments as tools (AgentTool pattern), stays in control, and synthesizes cross-domain answers:

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

**Why this over a single-agent or flat-orchestrator approach?**

- **Cross-domain synthesis** — The CSCO uses `AgentTool` (not `sub_agents` transfer), so it can call 2+ departments for one question, gather their outputs, and synthesize a combined answer. The old flat orchestrator could only route to ONE specialist and end the turn.
- **Focused tools per agent** — OrdersAgent only sees delivery tools, not payment tools. Less noise, more accurate routing.
- **Department heads as middle managers** — Each head wraps 1-3 specialists via AgentTool, adds domain context, and handles intra-department routing.
- **Deterministic workflow demo** — The ExecutiveBriefingPipeline uses `SequentialAgent` + `ParallelAgent` to gather KPIs concurrently and synthesize a briefing — a fixed pipeline that complements the LLM-driven Q&A.
- **Honest about data gaps** — Each agent discloses limitations (e.g., "Olist has no carrier_id" or "Olist has no returns table") rather than hallucinating.

---

## 3. The Data

**9 raw tables** loaded from the Olist dataset (via HuggingFace mirror):

| Table | Rows | What it captures |
|---|---|---|
| `orders` | 99,441 | Order lifecycle: purchase → carrier → customer → estimate |
| `order_items` | 112,650 | Items per order, freight cost, seller link |
| `order_payments` | 103,886 | Payment type, installments, value |
| `order_reviews` | 104,719 | Review score + free-text comments |
| `customers` | 99,441 | Customer location (state, city) |
| `sellers` | 3,095 | Seller location |
| `geolocation` | 1,000,163 | Zip-code level lat/lng (aggregation only) |
| `products` | 32,951 | Product category + dimensions |
| `category_translation` | 70 | Portuguese → English category names |

**4 derived views** pre-computed in BigQuery:

| View | Purpose |
|---|---|
| `orders_enriched` | Lifecycle timestamps, delivery_days, days_late_vs_estimate, last_mile_days, on_time flag |
| `seller_kpis` | Per-seller: orders, on-time %, avg delivery days, avg review, avg freight |
| `carrier_kpis` | Per-state lane: delivered orders, last-mile days, on-time % |
| `review_kpis` | Review score grouped by delivery delay bucket |

---

## 4. How It Works

### Tool Design

Each specialist has 1-2 tightly-scoped Python tools that query BigQuery:

```python
# Example: OrdersAgent tool
def get_delivery_stats(state=None):
    """Aggregate delivery KPIs from orders_enriched."""
    # Filters to delivered orders, optionally by state
    # Returns: avg_delivery_days, on_time_pct, avg_days_late_vs_estimate
```

**Safety layer** on every query:
- SELECT-only validation (INSERT/UPDATE/DELETE/DDL rejected at the Python level)
- `maximum_bytes_billed = 10 GB` — prevents runaway scan costs
- 30-second query timeout
- Results truncated to 1,000 rows
- Cross-dataset references blocked
- `geolocation` table (~1M rows) requires aggregation — never `SELECT *`

### Agent Instructions

Every specialist follows the same core rules:

> "Use tool results only. If a tool returns no data or an error, say so and list what IS available — do NOT invent numbers, IDs, or rows. Refuse questions outside Olist ecommerce operations analytics."

The CSCO adds routing and synthesis rules:
- Call the relevant department(s) as tools — one for single-domain, multiple for cross-domain
- Synthesize a combined answer when multiple departments are called
- If ambiguous, ask one clarifying question
- If out-of-scope (weather, stocks, code generation), refuse politely

---

## 5. Demo: Real Questions, Real Answers

### Q1: Which state has the worst on-time delivery?

> Routes to: **HeadOfFulfillment** → LaneAgent → `get_lane_performance()`

| State | Delivered Orders | On-Time % | Avg Delivery Days | Avg Late vs Estimate |
|---|---|---|---|---|
| RO | 243 | 97.12% | 18.91 | -19.13 |
| ... | | | | |
| MA | 717 | 80.33% | 21.12 | -8.77 |
| **AL** | **397** | **76.07%** | **24.04** | **-7.95** |

**AL (Alagoas)** has the worst on-time rate at **76.07%** — nearly 1 in 4 deliveries arrive late. Average delivery takes 24 days.

The agent discloses: *"Olist does not name carriers. 'Carrier performance' is proxied by customer_state lane."*

---

### Q2: Do late deliveries get worse reviews?

> Routes to: **HeadOfCX** → ReviewsAgent → `get_review_breakdown()`

| Delay Bucket | Reviews | Avg Score | % 1-2 Stars |
|---|---|---|---|
| On/Early | 89,949 | 4.29 | 9.28% |
| Late 1-3 days | 1,856 | 3.29 | 32.17% |
| Late 4-7 days | 1,756 | 2.10 | **67.65%** |
| Late 8+ days | 2,798 | 1.70 | **79.16%** |

Clear monotonic relationship: **late = bad reviews**. Orders late by 8+ days have a **79% chance of 1-2 star reviews**, vs only **9%** for on-time orders.

This is the kind of insight that takes an analyst 30 minutes of SQL joins. The agent returns it in 5 seconds.

---

### Q3: Payment types and installment patterns

> Routes to: **HeadOfFinance** → PaymentsAgent → `get_payment_mix()` + `get_installment_stats()`

**Payment Mix:**
| Type | Payments | % |
|---|---|---|
| Credit Card | 76,795 | 73.92% |
| Boleto | 19,784 | 19.04% |
| Voucher | 5,775 | 5.56% |
| Debit Card | 1,529 | 1.47% |

**Key finding:** 74% of all payments are credit card. This matters for ops — if payment processing delays cause fulfillment holds, it affects ~3/4 of all orders.

---

### Q4: Which sellers are dragging SLA?

> Routes to: **HeadOfSellerOps** → SellerPerformanceAgent → `get_seller_kpis(state=None, limit=20, min_orders=50)`

| Seller ID | State | Orders | On-Time % | Avg Score |
|---|---|---|---|---|
| 54965bbe... | PR | 78 | 67.90% | 2.94 |
| 2a1348e9... | MG | 52 | 70.59% | 3.00 |
| 602044f2... | SP | 50 | 74.14% | 2.93 |

Bottom 5 sellers (min 50 orders) have on-time rates between **67-75%**, compared to the platform average of **91.88%**. Their review scores are also below 3.0.

An ops team can use this to have targeted seller improvement conversations.

---

### Q5: Out-of-scope refusal

> User: "What's the weather in Hanoi today?"

> Agent: "I can only answer questions about Olist ecommerce operations: orders, deliveries, sellers, carriers/lanes, reviews, returns, payments, and geography."

The agent refuses politely without attempting to answer or hallucinating a weather response.

---

## 6. Evaluation

### Setup

- **17 eval cases** covering: schema listing, delivery timing, reviews, seller KPIs, payment mix, cancellation rates, geographic lanes, out-of-scope refusal, cross-domain synthesis (Fulfillment + CX, SellerOps + CX), executive briefing pipeline, seller risk intervention, and lane-by-freight analysis
- **4 custom metrics:** `tool_use_quality`, `grounded_response`, `intent_satisfaction`, `sql_safety`
- **Model:** `gemini-2.5-flash` (Vertex AI, us-central1)

### Results

```
Eval Id: worst_state_ontime         PASSED  (Fulfillment)
Eval Id: seller_reviews_sp          PASSED  (SellerOps)
Eval Id: late_delivery_reviews      PASSED  (Cross-domain: Fulfillment + CX)
Eval Id: payment_mix                PASSED  (Finance)
Eval Id: cancel_rate                PASSED  (CX)
Eval Id: schema_orders              PASSED  (BI)
Eval Id: list_tables                PASSED  (BI)
Eval Id: out_of_scope_refuse        PASSED  (Refusal)
Eval Id: freight_by_seller_state    PASSED  (SellerOps)
Eval Id: worst_sellers_ontime       PASSED  (SellerOps)
Eval Id: avg_days_late              PASSED  (Fulfillment)
Eval Id: credit_card_installments   PASSED  (Finance)
Eval Id: cross_state_delivery_cancel PASSED (Cross-domain: Fulfillment + CX)
Eval Id: executive_summary          PASSED  (Executive Briefing Pipeline)
Eval Id: cross_seller_review_gap    PASSED  (Cross-domain: SellerOps + CX)
Eval Id: lane_by_freight            PASSED  (Fulfillment)
Eval Id: seller_intervention        PASSED  (SellerOps risk)

passed=17, failed=0, total=17
```

### What was tested that failed

- `gemini-3.1-flash-lite` — returned 404 NOT_FOUND on Vertex AI (not yet available in us-central1)
- `gemini-3-flash-preview` — same 404 error

Decision: keep `gemini-2.5-flash` as production model. It is GA, available, and passed all 12 eval cases.

---

## 7. Design Rationale

### Why ADK 2.3 multi-agent instead of LangChain / single prompt?

- **Google-native stack** — ADK + Vertex AI + BigQuery = one GCP project, no third-party dependencies
- **Agent routing built in** — ADK auto-injects `transfer_to_agent`, so the orchestrator naturally delegates
- **Eval framework included** — `adk eval` runs the eval set with custom metrics, no external tooling needed

### Why specialist tools instead of raw SQL?

Raw SQL means the LLM writes the query, and you hope it gets it right. Specialist tools mean:
- The SQL is **pre-written and tested** — the LLM just picks the right function and fills in parameters
- **Safety is enforced at the tool level** — SELECT-only validation, billing caps, timeouts
- **No hallucinated column names** — the tool uses the actual schema; if the filter is wrong, it returns available keys

### Why not a dashboard?

A dashboard answers pre-defined questions. This agent answers **any question** an ops analyst can think of — including ones that haven't been asked yet. That's the difference between a report and an analytics capability.

---

## 8. What I'd Change

1. **Add a ReportAgent** — weekly ops digest that auto-runs the key KPIs and generates a markdown summary. Currently manual.

2. **Add carrier identity** — Olist doesn't publish carrier names, but a real deployment would join with carrier performance data. The current state-level proxy is honest but limited.

3. **ETA prediction** — a classifier on `orders_enriched` that predicts "this order will be late" at purchase time, based on seller state, product category, and historical patterns.

4. **Vietnamese locale** — the agent currently responds in English. For a VN ops team, add Vietnamese prompt templates.

---

## 9. How to Run Locally

```bash
# Clone
git clone https://github.com/im-khang/kaggle-5days-vibe-coding.git
cd kaggle-5days-vibe-coding/olist-ops-agent

# Install
uv sync

# Download data (9 CSVs from HuggingFace)
pip install huggingface-hub
python -c "
from huggingface_hub import snapshot_download
snapshot_download('miminmoons/olist-ecommerce-for-delivery-and-review-prediction',
                   local_dir='data/', repo_type='dataset', allow_patterns=['*.csv'])
"

# Set up BigQuery
cp .env.example .env   # Fill in your GCP project ID
gcloud auth application-default login
uv run python scripts/bigquery_upload.py

# Run
uv run adk web --port 8001 .

# Evaluate
uv run adk eval olist_ops tests/eval/datasets/olist_cases.json \
  --config_file_path tests/eval/eval_config.json \
  --print_detailed_results
```

---

## 10. Acknowledgments

- **Google ADK 2.3** — multi-agent framework
- **Olist Brazilian E-Commerce Dataset** (via HuggingFace mirror by miminmoons)
- **BigQuery** — serverless data warehouse
- **Gemini 2.5 Flash** — model for routing + specialist agents
- **Kaggle × Google** — 5-Day AI Agents Intensive Vibe Coding Course
