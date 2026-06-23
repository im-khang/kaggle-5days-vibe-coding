"""Olist Ecommerce Analytics Agent — orchestrator + 8 specialists (ADK 2.3).

`root_agent` is exposed for `adk web` discovery. ADK 2.3 auto-injects
`transfer_to_agent` from `sub_agents`; do NOT add it manually.
"""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from olist_ops.tools import (
    PROJECT,
    DATASET,
    list_tables,
    get_schema,
    query_bigquery,
    get_order_status,
    get_delivery_stats,
    get_lane_performance,
    get_seller_kpis,
    get_review_breakdown,
    get_low_score_reasons,
    get_cancel_rate,
    get_payment_mix,
    get_installment_stats,
    get_state_pairs,
)

MODEL = "gemini-2.5-flash"

_SHARED_TAIL = (
    " Use tool results only. If a tool returns no data or an error, say so and"
    " list what IS available (e.g. available_states / available_buckets) — do"
    " NOT invent numbers, IDs, or rows. Refuse questions outside Olist"
    " ecommerce operations analytics. Reply in English."
)

# ---------------------------------------------------------------------------
# OrdersAgent
# ---------------------------------------------------------------------------
orders_agent = Agent(
    name="OrdersAgent",
    model=MODEL,
    description=(
        "Order lifecycle and delivery timing for individual orders or"
        " state-level delivery aggregates (reads orders_enriched)."
    ),
    instruction=(
        "You answer Olist order-lifecycle questions: order status, delivery"
        " days, last-mile time, on-time vs estimate, days late vs estimate."
        " Use get_order_status(order_id) for one order, or"
        " get_delivery_stats(state=None) for aggregates."
        + _SHARED_TAIL
    ),
    tools=[
        FunctionTool(get_order_status),
        FunctionTool(get_delivery_stats),
    ],
)

# ---------------------------------------------------------------------------
# CarriersAgent (lane proxy: customer_state)
# ---------------------------------------------------------------------------
carriers_agent = Agent(
    name="CarriersAgent",
    model=MODEL,
    description=(
        "State-level lane performance from carrier_kpis. Olist has no"
        " carrier_id, so 'carrier performance' is proxied by customer_state"
        " lane (last-mile + on-time)."
    ),
    instruction=(
        "You report carrier-style performance for Olist. IMPORTANT: Olist"
        " does not name carriers, so 'carrier' = customer_state lane proxy."
        " Always disclose this proxy when answering. Use"
        " get_lane_performance(state=None)."
        + _SHARED_TAIL
    ),
    tools=[FunctionTool(get_lane_performance)],
)

# ---------------------------------------------------------------------------
# SellersAgent
# ---------------------------------------------------------------------------
sellers_agent = Agent(
    name="SellersAgent",
    model=MODEL,
    description=(
        "Seller fulfillment + CSAT KPIs from seller_kpis: orders, on-time %,"
        " avg delivery days, avg review score, avg freight."
    ),
    instruction=(
        "You answer seller-performance questions, including freight cost by"
        " seller state. Use get_seller_kpis(seller_id=None, state=None,"
        " limit=20, min_orders=0, sort_by='orders', ascending=False)."
        " For 'worst/best N sellers' questions: ALWAYS set min_orders >= 50"
        " (otherwise tiny-volume sellers dominate and the answer is misleading);"
        " set sort_by to the relevant KPI (e.g. 'on_time_pct'); set"
        " ascending=True for 'worst on-time' or 'lowest review score', False"
        " for 'best' or 'highest'. For 'average freight by seller state', call"
        " get_seller_kpis(limit=200) and aggregate avg_freight grouped by"
        " seller_state in your answer. Present results as a markdown table."
        + _SHARED_TAIL
    ),
    tools=[FunctionTool(get_seller_kpis)],
)

# ---------------------------------------------------------------------------
# ReviewsAgent
# ---------------------------------------------------------------------------
reviews_agent = Agent(
    name="ReviewsAgent",
    model=MODEL,
    description=(
        "CSAT analytics: review-score distribution by delivery delay bucket"
        " (review_kpis) and raw 1-2 star comment text from order_reviews."
    ),
    instruction=(
        "You answer review/CSAT questions. Use get_review_breakdown for"
        " delay-bucket vs review-score (expect monotonic drop as lateness"
        " grows). Use get_low_score_reasons(limit) to surface raw 1-2 star"
        " comment text — quote verbatim, do not paraphrase numbers."
        + _SHARED_TAIL
    ),
    tools=[
        FunctionTool(get_review_breakdown),
        FunctionTool(get_low_score_reasons),
    ],
)

# ---------------------------------------------------------------------------
# ReturnsAgent
# ---------------------------------------------------------------------------
returns_agent = Agent(
    name="ReturnsAgent",
    model=MODEL,
    description=(
        "Cancellation / unavailable rates per customer_state (orders +"
        " customers join). Olist has no explicit returns table; canceled +"
        " unavailable is the closest analog."
    ),
    instruction=(
        "You answer cancellation / 'returns' questions. Use"
        " get_cancel_rate(state=None). Always note: Olist has no returns"
        " table; we treat order_status IN ('canceled','unavailable') as the"
        " return-equivalent surface."
        + _SHARED_TAIL
    ),
    tools=[FunctionTool(get_cancel_rate)],
)

# ---------------------------------------------------------------------------
# PaymentsAgent
# ---------------------------------------------------------------------------
payments_agent = Agent(
    name="PaymentsAgent",
    model=MODEL,
    description=(
        "Payment mix and installment statistics from order_payments:"
        " payment types, installment distribution for credit cards."
    ),
    instruction=(
        "You answer payment-mix and installment questions. Use"
        " get_payment_mix for type distribution and get_installment_stats"
        " for credit-card installment breakdown. Present results as a"
        " markdown table."
        + _SHARED_TAIL
    ),
    tools=[
        FunctionTool(get_payment_mix),
        FunctionTool(get_installment_stats),
    ],
)

# ---------------------------------------------------------------------------
# GeoAgent
# ---------------------------------------------------------------------------
geo_agent = Agent(
    name="GeoAgent",
    model=MODEL,
    description=(
        "Seller-state x customer-state lane analytics (orders, freight,"
        " delivery days). Always aggregated; never SELECT * on geolocation."
    ),
    instruction=(
        "You answer geographic / lane questions. Use get_state_pairs(limit)"
        " — this aggregates seller_state x customer_state across orders +"
        " order_items + sellers + customers. The geolocation table has ~1M"
        " rows; never request raw rows from it."
        + _SHARED_TAIL
    ),
    tools=[FunctionTool(get_state_pairs)],
)

# ---------------------------------------------------------------------------
# DataAnalystAgent (ad-hoc SQL fallback)
# ---------------------------------------------------------------------------
DATA_ANALYST_INSTRUCTION = f"""\
You are the ad-hoc data-science fallback for the Olist Ecommerce Analytics
team. Data lives in BigQuery dataset `{DATASET}` of project `{PROJECT}`.

Tables and views you can use:
- Raw tables: customers, geolocation, order_items, order_payments,
  order_reviews, orders, products, sellers, product_category_translation.
- Views: orders_enriched, seller_kpis, carrier_kpis, review_kpis.

Workflow per question:
  1. Call list_tables() once per session if you do not know the layout.
  2. Call get_schema(table_name) before writing SQL — never invent column
     names. Note Olist preserved original CSV typos: `product_name_lenght`,
     `product_description_lenght`.
  3. Write a SELECT-only query (CTE-then-SELECT is fine). Reference only
     the `{DATASET}` dataset. Tools enforce: SELECT-only,
     maximum_bytes_billed=10 GB, 30s timeout, 1000-row truncation.
  4. Aggregate when touching `geolocation` (~1M rows) — never SELECT *.
  5. Quote the table or view used in your answer
     (e.g. "From view `seller_kpis`...").

Rules:
- No INSERT/UPDATE/DELETE/DDL/MERGE — the validator will reject them.
- If query_bigquery returns an error, read it, correct the SQL, retry up
  to 2 times, then report the failure honestly.
- If the result set is empty, say so explicitly; do NOT invent rows.
- Refuse out-of-scope questions (anything outside Olist ecommerce ops).
- Reply in English with a markdown table when listing multiple rows.
"""

data_analyst_agent = Agent(
    name="DataAnalystAgent",
    model=MODEL,
    description=(
        "Ad-hoc SQL fallback. Lists tables, returns schemas, and runs"
        " SELECT-only queries on the olist_ecommerce dataset."
    ),
    instruction=DATA_ANALYST_INSTRUCTION,
    tools=[
        FunctionTool(list_tables),
        FunctionTool(get_schema),
        FunctionTool(query_bigquery),
    ],
)

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
ORCHESTRATOR_INSTRUCTION = """\
You are the orchestrator for the Olist Ecommerce Analytics team. Route every
user question to exactly ONE specialist below; do not answer directly.

Specialists:
- OrdersAgent: order status by order_id, delivery timing aggregates
  (delivery days, last-mile, days late vs estimate, on-time %).
- CarriersAgent: state-level lane performance (Olist proxy for carriers — no
  carrier_id exists in the data). Use for "which state has worst delivery".
- SellersAgent: per-seller KPIs (orders, on-time %, avg review, avg
  freight); supports filter by seller_id or state. ALSO handles freight
  cost by seller state — route freight questions HERE, not to GeoAgent.
- ReviewsAgent: review-score breakdown by delivery delay bucket and raw
  1-2 star comment text.
- ReturnsAgent: cancellation / unavailable rates (Olist has no explicit
  returns table).
- PaymentsAgent: payment-type mix and credit-card installment stats.
- GeoAgent: seller-state x customer-state lane analytics (pair routing,
  delivery days per lane). Only for geographic PAIR questions, NOT for
  "freight by state" (that's SellersAgent).
- DataAnalystAgent: ad-hoc SQL, list_tables, get_schema, anything that
  does not match a specialist above.

Routing rules:
- Pick exactly ONE specialist. If the question is genuinely ambiguous,
  ask ONE concise clarifying question instead of guessing.
- For schema / "what tables exist" / generic SQL questions, route to
  DataAnalystAgent.
- For "freight by seller state" or "seller performance" → SellersAgent.
- For "delivery by customer state" or "carrier performance" → CarriersAgent.
- If the question is outside Olist ecommerce operations analytics
  (weather, stocks, general chit-chat, code generation, etc.), refuse
  politely in one sentence and suggest the kinds of questions you can
  answer (orders, deliveries, sellers, carriers/lanes, reviews, returns,
  payments, geography).
- Reply in English.
"""

root_agent = Agent(
    name="OlistOrchestrator",
    model=MODEL,
    description=(
        "Routes user questions to one of 8 Olist specialist agents over"
        " the BigQuery dataset olist_ecommerce."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    sub_agents=[
        orders_agent,
        carriers_agent,
        sellers_agent,
        reviews_agent,
        returns_agent,
        payments_agent,
        geo_agent,
        data_analyst_agent,
    ],
)
