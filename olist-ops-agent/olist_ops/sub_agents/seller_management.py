"""Seller Management Department."""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from olist_ops.sub_agents.common import DEPARTMENT_SYNTHESIS_RULES, MODEL
from olist_ops.sub_agents.specialists import seller_performance_agent, seller_risk_agent

head_of_seller_ops = Agent(
    name="HeadOfSellerOps",
    model=MODEL,
    description=(
        "Seller Management department head. Coordinates seller KPI reporting,"
        " freight/seller-state analysis, and seller risk/intervention logic."
    ),
    instruction=(
        "You are Head of Seller Management for an Olist-style marketplace."
        " Your scope: seller reliability, on-time performance, seller review"
        " quality, freight by seller/seller_state, and intervention priorities."
        " Routing within your team:\n"
        " - SellerPerformanceAgent → descriptive KPI tables and benchmarking:"
        " per-seller on-time %, review scores, order counts, quartiles, and"
        " comparisons against external/public benchmarks.\n"
        " - SellerRiskAgent → risk diagnosis and ACTION: flagging sellers for"
        " intervention, multi-factor risk scoring/tiering (e.g. low on-time AND"
        " low review score), anomaly sellers, and recommended interventions."
        " ANY request to 'flag', 'identify risky sellers', 'risk tier', or"
        " 'who should we intervene on' goes to SellerRiskAgent.\n"
        " For multi-factor questions that need both KPI numbers and a risk"
        " verdict, call SellerRiskAgent (it owns the multi-factor logic).\n"
        + DEPARTMENT_SYNTHESIS_RULES
    ),
    tools=[
        AgentTool(agent=seller_performance_agent),
        AgentTool(agent=seller_risk_agent),
    ],
)
