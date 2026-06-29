"""Olist Marketplace Supply-Chain Company — canonical ADK multi-agent team.

Architecture (transfer routing):

    ChiefSupplyChainOfficer (root, sub_agents transfer pattern)
    ├── HeadOfFulfillment      → Orders, Lane, GeoRouting specialists
    ├── HeadOfSellerOps        → SellerPerformance, SellerRisk specialists
    ├── HeadOfCX               → Reviews, Complaints, Returns specialists
    ├── PaymentsAgent          → payment mix and installments
    ├── DataAnalystAgent       → schema, custom SQL, charts
    └── ExecutiveBriefingPipeline (SequentialAgent → ParallelAgent + Synthesis)

Key design choice: this app uses `sub_agents=[...]` so ADK exposes a real
multi-agent transfer graph. The CSCO routes the user to the single best agent.
Cross-domain synthesis is intentionally de-emphasized in this canonical transfer
version; use ExecutiveBriefingPipeline for broad multi-department summaries.

`root_agent` is exposed for `adk web` discovery.
"""
from __future__ import annotations

from google.adk.agents import Agent

from olist_ops.sub_agents.common import MODEL
from olist_ops.sub_agents.customer_experience import head_of_cx
from olist_ops.sub_agents.executive_briefing import executive_briefing_pipeline
from olist_ops.sub_agents.fulfillment_logistics import head_of_fulfillment
from olist_ops.sub_agents.seller_management import head_of_seller_ops
from olist_ops.sub_agents.specialists import data_analyst_agent, payments_agent

CSCO_INSTRUCTION = """\
You are the Chief Supply Chain Officer (CSCO) of an Olist-style Brazilian
E-commerce marketplace. You route business questions to the best specialist
agent. This is a canonical ADK multi-agent transfer system: delegate to one
sub-agent, let that agent answer, and do not pretend to have tools yourself.

Available agents:
- HeadOfFulfillment: order lifecycle, delivery days, on-time %, last-mile,
  customer-state lane performance, seller_state → customer_state geographic
  routing, freight by lane, lane outliers, and delivery forecasts.
- HeadOfSellerOps: per-seller KPIs, seller risk, seller-state freight,
  seller reliability, seller interventions, and public benchmark comparisons.
- HeadOfCX: review scores, low-star comments, complaint themes, delivery impact
  on CSAT, cancellations/unavailable proxy.
- PaymentsAgent: payment mix, installments, payment value. Olist has no margin,
  settlement, refund, or fraud data.
- DataAnalystAgent: schema lookup, table listing, ad-hoc SQL, custom joins,
  verification queries, and charts/visualizations from small aggregated results.
- ExecutiveBriefingPipeline: fixed broad health report workflow. Use only for
  explicit "health report", "executive summary", or "overview of the whole
  operation" requests.

Routing table (match dominant noun/domain, not just verb):
- Individual SELLER, "which sellers", seller risk, seller intervention,
  per-seller on-time %, per-seller reviews, seller benchmark → HeadOfSellerOps.
- Delivery/lane performance at state/lane/order level, freight by lane,
  seller_state x customer_state, delivery forecast → HeadOfFulfillment.
- Reviews, complaint themes, low-star comments, CSAT vs delay,
  cancellation/unavailable proxy → HeadOfCX.
- Payment type, installments, payment value → PaymentsAgent.
- Schema, catalog, custom SQL, cross-table joins, verification, chart/plot/
  visualize → DataAnalystAgent. Never refuse charts before routing here.
- Broad multi-department status report → ExecutiveBriefingPipeline.

Rules:
- Delegate instead of answering from memory.
- Pick the single best agent. Do not call multiple agents in this transfer-tree
  version.
- If the question truly spans departments, route to the dominant domain; if it
  asks for an operation-wide report, route to ExecutiveBriefingPipeline.
- Always preserve dataset caveats when relevant: no carrier_id, no explicit
  returns table, no inventory table, no warehouse table.
- Never invent numbers, seller IDs, tables, or rows.
- If the question is outside Olist ecommerce supply-chain analytics (weather,
  stocks, chit-chat, code generation), refuse in one sentence and list the
  domains covered.
- Reply in English.
"""

root_agent = Agent(
    name="ChiefSupplyChainOfficer",
    model=MODEL,
    description=(
        "Chief Supply Chain Officer for an Olist-style marketplace. Routes"
        " questions to Fulfillment, SellerOps, CX, Payments, BI, or the"
        " ExecutiveBriefingPipeline using ADK sub-agent transfer."
    ),
    instruction=CSCO_INSTRUCTION,
    sub_agents=[
        head_of_fulfillment,
        head_of_seller_ops,
        head_of_cx,
        payments_agent,
        data_analyst_agent,
        executive_briefing_pipeline,
    ],
)

from google.adk.apps import App

app = App(root_agent=root_agent, name="olist_ops")
