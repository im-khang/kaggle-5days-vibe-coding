"""Seller Management Department."""
from __future__ import annotations

from google.adk.agents import Agent

from olist_ops.sub_agents.common import DEPARTMENT_TRANSFER_RULES, MODEL
from olist_ops.sub_agents.specialists import seller_performance_agent, seller_risk_agent

head_of_seller_ops = Agent(
    name="HeadOfSellerOps",
    model=MODEL,
    description=(
        "Seller Management department head. Routes seller KPI, benchmark,"
        " freight/seller-state, and seller-risk questions to the right specialist."
    ),
    instruction=(
        "You are Head of Seller Management for an Olist-style marketplace."
        " Your job is pure routing to one specialist, not cross-department"
        " synthesis.\n"
        "Route within your team:\n"
        "- SellerPerformanceAgent: descriptive KPI tables, per-seller on-time %,"
        " review scores, order counts, quartiles, freight by seller state, and"
        " external/public benchmark comparisons.\n"
        "- SellerRiskAgent: risk diagnosis and action — flag risky sellers, risk"
        " tiers, multi-factor late+review+freight scoring, anomalies, and"
        " intervention recommendations.\n"
        "If user asks to flag, tier, intervene, identify risky sellers, or combine"
        " multiple seller KPIs into an action list, route to SellerRiskAgent."
        + DEPARTMENT_TRANSFER_RULES
    ),
    sub_agents=[seller_performance_agent, seller_risk_agent],
)
