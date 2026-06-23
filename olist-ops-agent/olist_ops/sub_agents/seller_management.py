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
        " Use SellerPerformanceAgent for KPI tables and SellerRiskAgent for"
        " risky-seller diagnosis/recommendations.\n"
        + DEPARTMENT_SYNTHESIS_RULES
    ),
    tools=[
        AgentTool(agent=seller_performance_agent),
        AgentTool(agent=seller_risk_agent),
    ],
)
