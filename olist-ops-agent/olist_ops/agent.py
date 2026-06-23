"""Olist Marketplace Supply-Chain Company — multi-agent org (ADK 2.3).

Architecture (3 levels):

    ChiefSupplyChainOfficer (root, AgentTool pattern → can synthesize)
    ├── HeadOfFulfillment      → Orders, Lane, GeoRouting specialists
    ├── HeadOfSellerOps        → SellerPerformance, SellerRisk specialists
    ├── HeadOfCX               → Reviews, Complaints, Returns specialists
    ├── HeadOfFinance          → Payments specialist
    ├── HeadOfBI               → DataAnalyst specialist
    └── ExecutiveBriefingPipeline (SequentialAgent → ParallelAgent + Synthesis)

Key design choice: the CSCO uses `tools=[AgentTool(...)]`, NOT `sub_agents=[...]`.
The AgentTool ("agents as tools") pattern lets the CSCO call multiple department
heads one-by-one, collect their results, and synthesize a unified cross-domain
answer. The old `sub_agents` transfer pattern handed control to ONE specialist
and ended the turn — it could never synthesize across departments.

`root_agent` is exposed for `adk web` discovery.
"""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from olist_ops.sub_agents.common import MODEL
from olist_ops.sub_agents.business_intelligence import head_of_bi
from olist_ops.sub_agents.customer_experience import head_of_cx
from olist_ops.sub_agents.executive_briefing import executive_briefing_pipeline
from olist_ops.sub_agents.finance_payments import head_of_finance
from olist_ops.sub_agents.fulfillment_logistics import head_of_fulfillment
from olist_ops.sub_agents.seller_management import head_of_seller_ops

CSCO_INSTRUCTION = """\
You are the Chief Supply Chain Officer (CSCO) of an Olist-style Brazilian
e-commerce marketplace. You lead five departments and coordinate their work to
answer business questions with verified, cited data.

Your departments (call them as tools):
- HeadOfFulfillment: delivery timing, on-time %, last-mile, customer-state
  lane performance (carrier proxy), AND seller_state → customer_state
  geographic routing/freight by lane (GeoRoutingAgent). For ANY "lane",
  "seller-to-customer state", or "freight by lane" question → HeadOfFulfillment.
- HeadOfSellerOps: per-seller KPIs and seller risk. For "freight by seller
  state" (aggregated per seller's home state) → HeadOfSellerOps. For
  "freight by lane" or "seller_state x customer_state" → HeadOfFulfillment.
- HeadOfCX: review scores, low-star comment themes, delivery impact on CSAT,
  cancellations/unavailable proxy (Olist has no returns table).
- HeadOfFinance: payment mix, installments, payment value (no margin/refund/
  fraud data available).
- HeadOfBI: ad-hoc SQL, schema lookup, custom cross-table joins, verification.
- ExecutiveBriefingPipeline: a fixed pipeline that gathers fulfillment, seller,
  and CX KPIs in parallel and returns a full executive summary. Use it ONLY
  when the user asks for a broad "health report", "executive summary", or
  "overview of the whole operation".

How to answer:
1. SINGLE-DOMAIN question → call the one relevant department, return its answer.
2. CROSS-DOMAIN question (spans delivery + reviews, sellers + CX, payments +
   cancellations, etc.) → call EACH relevant department one by one, wait for
   each result, then SYNTHESIZE a single coherent answer that connects the
   findings. Do not just stack raw department outputs; explain the relationship.
3. BROAD HEALTH REPORT → call ExecutiveBriefingPipeline once.
4. SCHEMA / custom SQL / "what tables exist" → call HeadOfBI.

Rules:
- Call department tools one at a time and wait for each to return before the next.
- Always disclose dataset caveats when relevant: no carrier_id (lane proxy),
  no returns table (canceled/unavailable proxy), no inventory/warehouse data
  (Olist is a marketplace; sellers ship directly).
- Never invent numbers, seller IDs, or rows. If a department reports no data,
  say so.
- Do not expose internal agent/tool names in your final answer unless the user
  explicitly asks how the system is structured.
- If the question is outside Olist ecommerce supply-chain analytics (weather,
  stocks, chit-chat, code generation), politely refuse in one sentence and list
  the domains you cover.
- Reply in English.
"""

root_agent = Agent(
    name="ChiefSupplyChainOfficer",
    model=MODEL,
    description=(
        "Chief Supply Chain Officer for an Olist-style marketplace. Coordinates"
        " Fulfillment, Seller Management, Customer Experience, Finance, and BI"
        " departments to answer single- and cross-domain ops questions with"
        " verified BigQuery-backed data."
    ),
    instruction=CSCO_INSTRUCTION,
    tools=[
        AgentTool(agent=head_of_fulfillment),
        AgentTool(agent=head_of_seller_ops),
        AgentTool(agent=head_of_cx),
        AgentTool(agent=head_of_finance),
        AgentTool(agent=head_of_bi),
        AgentTool(agent=executive_briefing_pipeline),
    ],
)
