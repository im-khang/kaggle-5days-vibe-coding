"""Executive Briefing Pipeline — SequentialAgent + ParallelAgent demo.

Workflow:
  1. ParallelAgent gathers KPIs from 3 departments concurrently.
  2. SynthesisAgent reads all state keys and produces an executive summary.

This demonstrates deterministic ADK workflow composition (not LLM-driven routing).
"""
from __future__ import annotations

from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.tools import FunctionTool

from olist_ops.mcp_toolsets import sequential_thinking_toolset
from olist_ops.sub_agents.common import MODEL
from olist_ops.tools import (
    get_delivery_stats,
    get_lane_performance,
    get_seller_kpis,
    get_review_breakdown,
    get_cancel_rate,
    get_payment_mix,
)

# --- KPI Collector Agents (each writes to output_key) ---

fulfillment_kpi_agent = Agent(
    name="FulfillmentKPICollector",
    model=MODEL,
    instruction=(
        "Collect fulfillment KPIs for the executive briefing. Call"
        " get_delivery_stats() for overall delivery timing, then"
        " get_lane_performance() for top/bottom lanes. Format as a concise"
        " bullet-point summary with exact numbers."
    ),
    tools=[FunctionTool(get_delivery_stats), FunctionTool(get_lane_performance)],
    output_key="fulfillment_kpis",
)

seller_kpi_agent = Agent(
    name="SellerKPICollector",
    model=MODEL,
    instruction=(
        "Collect seller KPIs for the executive briefing. Call"
        " get_seller_kpis(limit=5, min_orders=50, sort_by='on_time_pct',"
        " ascending=True) for worst performers, then"
        " get_seller_kpis(limit=5, min_orders=50, sort_by='avg_review_score',"
        " ascending=True) for lowest-review sellers. Format as concise"
        " bullet-point summary with seller_id (first 8 chars) and numbers."
    ),
    tools=[FunctionTool(get_seller_kpis)],
    output_key="seller_kpis",
)

cx_kpi_agent = Agent(
    name="CXKPICollector",
    model=MODEL,
    instruction=(
        "Collect customer experience KPIs for the executive briefing. Call"
        " get_review_breakdown() for delay-vs-review data, then"
        " get_cancel_rate() for cancellation rates. Format as concise"
        " bullet-point summary with exact numbers."
    ),
    tools=[
        FunctionTool(get_review_breakdown),
        FunctionTool(get_cancel_rate),
        FunctionTool(get_payment_mix),
    ],
    output_key="cx_kpis",
)

# --- Parallel gather ---

parallel_kpi_gather = ParallelAgent(
    name="ParallelKPIGather",
    sub_agents=[fulfillment_kpi_agent, seller_kpi_agent, cx_kpi_agent],
)

# --- Synthesis Agent ---

synthesis_agent = Agent(
    name="SynthesisAgent",
    model=MODEL,
    instruction="""\
You are the executive briefing writer for the Olist marketplace supply-chain
company. Three department KPI reports have been collected:

1. Fulfillment KPIs: {fulfillment_kpis}
2. Seller KPIs: {seller_kpis}
3. Customer Experience KPIs: {cx_kpis}

Write a structured 1-page executive summary with:
- **Status Overview** (1 paragraph health statement)
- **Key Metrics Table** (markdown table of top 8 metrics)
- **Top 3 Risks** (numbered, each with evidence + recommended action)
- **Bright Spots** (2-3 positive findings)

Be concise, data-driven, and cite actual numbers from the reports above.
Do not invent numbers not found in the reports.
For prioritising the Top 3 Risks, you MAY use the seq_sequentialthinking tool
to reason through severity before writing the final list.
""",
    output_key="executive_briefing",
    tools=[sequential_thinking_toolset()],
)

# --- Sequential Pipeline ---

executive_briefing_pipeline = SequentialAgent(
    name="ExecutiveBriefingPipeline",
    sub_agents=[parallel_kpi_gather, synthesis_agent],
)
