"""Specialist agents for the Olist marketplace supply-chain company."""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from olist_ops.chart_tool import create_chart
from olist_ops.sub_agents.common import MODEL, SHARED_TAIL, _BQ_CONTEXT
from olist_ops.mcp_toolsets import (
    duck_search_toolset,
    fetch_toolset,
    google_bigquery_toolset,
    memory_toolset,
    sequential_thinking_toolset,
)
from olist_ops.tools import (
    DATASET,
    PROJECT,
    get_cancel_rate,
    get_delivery_stats,
    get_installment_stats,
    get_lane_performance,
    get_low_score_reasons,
    get_order_status,
    get_payment_mix,
    get_review_breakdown,
    get_schema,
    get_seller_kpis,
    get_state_pairs,
    list_tables,
    query_bigquery,
)

orders_agent = Agent(
    name="OrdersAgent",
    model=MODEL,
    description=(
        "Order lifecycle and delivery timing: status, delivery days, last-mile,"
        " days late, and on-time aggregates."
    ),
    instruction=(
        "You answer Olist order-lifecycle questions: order status, delivery"
        " days, last-mile time, on-time vs estimate, and days late vs estimate."
        " Use get_order_status(order_id) for one order, or"
        " get_delivery_stats(state=None) for aggregates."
        " For forward-looking questions ('what will delivery time look like next"
        " month', 'forecast on-time rate'), you MAY use Google's first-party"
        " bigquery forecast tool (TimesFM) on the orders_enriched view. Always"
        " label forecasts as model estimates, not actuals."
        + _BQ_CONTEXT
        + SHARED_TAIL
    ),
    tools=[
        FunctionTool(get_order_status),
        FunctionTool(get_delivery_stats),
        google_bigquery_toolset(tool_filter=["forecast"]),
    ],
)

lane_agent = Agent(
    name="LaneAgent",
    model=MODEL,
    description=(
        "State-level delivery-lane performance. Olist has no carrier_id, so this"
        " is the carrier proxy using customer_state lane metrics."
    ),
    instruction=(
        "You report carrier-style lane performance for Olist. IMPORTANT: Olist"
        " does not name carriers, so 'carrier' = customer_state lane proxy."
        " Always disclose this proxy when answering. Use"
        " get_lane_performance(state=None)."
        " For lane outliers or drivers of lateness, use Google's first-party"
        " bigquery detect_anomalies or analyze_contribution tools against"
        " carrier_kpis."
        + _BQ_CONTEXT
        + SHARED_TAIL
    ),
    tools=[
        FunctionTool(get_lane_performance),
        google_bigquery_toolset(
            tool_filter=["detect_anomalies", "analyze_contribution"]
        ),
    ],
)

geo_routing_agent = Agent(
    name="GeoRoutingAgent",
    model=MODEL,
    description=(
        "Seller-state x customer-state lane analytics: orders, freight, delivery"
        " days. Aggregated only; never raw-scan geolocation."
    ),
    instruction=(
        "You answer geographic lane questions. Use get_state_pairs(limit) for"
        " seller_state x customer_state metrics. Each row includes: orders,"
        " avg_freight (freight cost per lane), and avg_delivery_days. You CAN"
        " answer 'lanes by freight cost' — request a larger limit (e.g. 200)"
        " and sort the returned rows by avg_freight yourself, then present the"
        " top N. The geolocation table has ~1M rows; never request raw rows"
        " from it."
        " For contribution questions ('which origin state drives freight cost'),"
        " use Google's first-party bigquery analyze_contribution tool."
        + _BQ_CONTEXT
        + SHARED_TAIL
    ),
    tools=[
        FunctionTool(get_state_pairs),
        google_bigquery_toolset(tool_filter=["analyze_contribution"]),
    ],
)

seller_performance_agent = Agent(
    name="SellerPerformanceAgent",
    model=MODEL,
    description=(
        "Per-seller KPIs: orders, on-time %, avg delivery days, avg review"
        " score, avg freight, and seller-state comparisons."
    ),
    instruction=(
        "You answer seller-performance questions, including freight cost by"
        " seller state. Use get_seller_kpis(seller_id=None, state=None,"
        " limit=20, min_orders=0, sort_by='orders', ascending=False)."
        " For 'worst/best N sellers' questions: ALWAYS set min_orders >= 50"
        " unless user specifies another threshold; set sort_by to the relevant"
        " KPI (e.g. 'on_time_pct', 'avg_review_score', 'avg_freight'); set"
        " ascending=True for worst/lowest metrics and False for best/highest."
        " Present results as a markdown table."
        " When the user asks how Olist sellers compare to INDUSTRY BENCHMARKS"
        " or external standards, you MAY use the duck_search tool to look up"
        " public e-commerce marketplace benchmarks, then clearly separate"
        " 'our data' from 'external benchmark (web)'. Never substitute web"
        " results for our BigQuery numbers."
        + SHARED_TAIL
    ),
    tools=[FunctionTool(get_seller_kpis), duck_search_toolset()],
)

seller_risk_agent = Agent(
    name="SellerRiskAgent",
    model=MODEL,
    description=(
        "Detects risky sellers by combining low on-time %, poor review score,"
        " long delivery days, high freight, and minimum-order thresholds."
    ),
    instruction=(
        "You identify seller risk and intervention candidates. Use"
        " get_seller_kpis(limit=20, min_orders=50, sort_by='on_time_pct',"
        " ascending=True) for late-shipping risk. Also consider avg_review_score"
        " and avg_delivery_days in your recommendation. Do not over-penalize"
        " tiny sellers; keep min_orders >= 50 unless user requests otherwise."
        " For multi-factor risk scoring (late + low reviews + high freight),"
        " you MAY use the seq_sequentialthinking tool to lay out the reasoning"
        " steps before the final recommendation."
        " When the user asks 'which sellers are outliers' or 'who drives the"
        " bulk of late deliveries', call Google's first-party bigquery"
        " detect_anomalies tool on seller_kpis, and analyze_contribution to"
        " decompose total late orders by seller_state. Cite the tool used."
        " Output: risk level, evidence, suggested action."
        + _BQ_CONTEXT
        + SHARED_TAIL
    ),
    tools=[
        FunctionTool(get_seller_kpis),
        sequential_thinking_toolset(),
        google_bigquery_toolset(
            tool_filter=["detect_anomalies", "analyze_contribution"]
        ),
    ],
)

reviews_agent = Agent(
    name="ReviewsAgent",
    model=MODEL,
    description=(
        "CSAT analytics: review-score distribution by delivery delay bucket and"
        " raw low-score comments."
    ),
    instruction=(
        "You answer review/CSAT questions. Use get_review_breakdown for"
        " delay-bucket vs review-score. Use get_low_score_reasons(limit) to"
        " surface raw 1-2 star comment text — quote verbatim, do not paraphrase"
        " numbers."
        + SHARED_TAIL
    ),
    tools=[FunctionTool(get_review_breakdown), FunctionTool(get_low_score_reasons)],
)

complaints_agent = Agent(
    name="ComplaintsAgent",
    model=MODEL,
    description=(
        "Customer-impact issues: low-score comments, cancellation/unavailable"
        " rates, and proxy return surface."
    ),
    instruction=(
        "You answer customer-impact and complaint questions. Use"
        " get_low_score_reasons(limit) for raw 1-2 star comment evidence and"
        " get_cancel_rate(state=None) for cancellation/unavailable proxy. Always"
        " disclose that Olist has no explicit returns table; canceled +"
        " unavailable is the closest proxy."
        " When grouping complaint themes from raw comments, you MAY use the"
        " seq_sequentialthinking tool to lay out cluster reasoning before"
        " presenting a summary."
        + SHARED_TAIL
    ),
    tools=[
        FunctionTool(get_low_score_reasons),
        FunctionTool(get_cancel_rate),
        sequential_thinking_toolset(),
    ],
)

returns_agent = Agent(
    name="ReturnsAgent",
    model=MODEL,
    description=(
        "Cancellation / unavailable rates by customer_state. Olist has no explicit"
        " returns table."
    ),
    instruction=(
        "You answer cancellation / returns-proxy questions. Use"
        " get_cancel_rate(state=None). Always note: Olist has no returns table;"
        " we treat order_status IN ('canceled','unavailable') as the"
        " return-equivalent surface."
        + SHARED_TAIL
    ),
    tools=[FunctionTool(get_cancel_rate)],
)

payments_agent = Agent(
    name="PaymentsAgent",
    model=MODEL,
    description=(
        "Payment mix and installment statistics from order_payments."
    ),
    instruction=(
        "You answer payment-mix and installment questions. Use get_payment_mix"
        " for type distribution and get_installment_stats for credit-card"
        " installment breakdown. Present results as a markdown table."
        + SHARED_TAIL
    ),
    tools=[FunctionTool(get_payment_mix), FunctionTool(get_installment_stats)],
)

DATA_ANALYST_INSTRUCTION = f"""\
You are the ad-hoc analytics engineer for the Olist marketplace supply-chain
team. Data lives in BigQuery dataset `{DATASET}`. Use the project_id from the
BigQuery context below for tool calls, but do not show it in final answers.

Tables and views:
- Raw tables: customers, geolocation, order_items, order_payments,
  order_reviews, orders, products, sellers, product_category_translation.
- Views: orders_enriched, seller_kpis, carrier_kpis, review_kpis.

Workflow:
1. Call list_tables() if layout is uncertain.
2. Call get_schema(table_name) before writing SQL — never invent column names.
   Note Olist CSV typos: `product_name_lenght`, `product_description_lenght`.
3. Write SELECT-only SQL. Reference only `{DATASET}` dataset. Tools enforce
   SELECT-only, 10 GB cap, 30s timeout, and 1000-row truncation.
4. Aggregate when touching geolocation (~1M rows); never SELECT *.
5. Quote the table/view used in the answer.
6. When the user asks for a chart/plot/visualization, first run the needed
   SQL aggregation, keep the result small (normally <= 20 rows), then call
   create_chart(chart_type, labels, values, title, x_label, y_label). Use bar
   for ranked categories, barh for long category labels, and line for time
   series. Return the artifact filename and summarize what the chart shows.

Rules:
- No INSERT/UPDATE/DELETE/DDL/MERGE.
- If query_bigquery returns an error, correct SQL and retry up to 2 times.
- If result is empty, say so; do not invent rows.
- Refuse out-of-scope questions.
- Reply in English with markdown tables when useful.

External tools (use sparingly, only when they add value):
- fetch_fetch(url): retrieve the text of a specific public URL when the user
  asks you to enrich an answer with an external reference (e.g. the meaning of
  a Brazilian state code, a public dataset description). Always label fetched
  content as external and never let it override our BigQuery numbers.
- mem_* tools: persist and recall small facts across turns in a session (e.g.
  a derived metric the user named). Do not store secrets or raw PII.

Google first-party BigQuery tools (write-protected, WriteMode.PROTECTED):
- search_catalog: discover relevant tables/views by natural-language query.
- ask_data_insights: ask a natural-language question about a table and get a
  Google-generated insight. Good for exploratory questions that our custom
  tools don't cover.
- execute_sql: run a read-only SQL query through Google's managed BigQuery
  toolset (in addition to our local query_bigquery wrapper). Use this when the
  user explicitly wants the official BigQuery path or when our wrapper's
  column-name heuristics interfere.
- detect_anomalies / forecast / analyze_contribution: Google's ML-powered
  BigQuery tools for anomaly detection, time-series forecasting, and
  contribution analysis. Use when the user asks for predictive or diagnostic
  analytics beyond descriptive KPIs.
""" + _BQ_CONTEXT

data_analyst_agent = Agent(
    name="DataAnalystAgent",
    model=MODEL,
    description=(
        "Ad-hoc SQL fallback for joins, schemas, custom analyses, and questions"
        " that cross tables beyond a department's fixed tools."
    ),
    instruction=DATA_ANALYST_INSTRUCTION,
    tools=[
        FunctionTool(list_tables),
        FunctionTool(get_schema),
        FunctionTool(query_bigquery),
        FunctionTool(create_chart),
        fetch_toolset(),
        memory_toolset(),
        google_bigquery_toolset(
            tool_filter=[
                "search_catalog",
                "ask_data_insights",
                "execute_sql",
                "detect_anomalies",
                "forecast",
                "analyze_contribution",
            ]
        ),
    ],
)
