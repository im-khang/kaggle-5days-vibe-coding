"""Fulfillment & Logistics Department."""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from olist_ops.sub_agents.common import DEPARTMENT_SYNTHESIS_RULES, MODEL
from olist_ops.sub_agents.specialists import geo_routing_agent, lane_agent, orders_agent

head_of_fulfillment = Agent(
    name="HeadOfFulfillment",
    model=MODEL,
    description=(
        "Fulfillment & Logistics department head. Coordinates order lifecycle,"
        " delivery timing, customer-state lane performance, and seller→customer"
        " geographic routing."
    ),
    instruction=(
        "You are Head of Fulfillment & Logistics for an Olist-style marketplace."
        " Your scope: delivery speed, on-time %, last-mile performance, lane"
        " risk, seller_state→customer_state routing, and carrier proxy caveats."
        " Use OrdersAgent for order timing, LaneAgent for customer-state lane"
        " performance, and GeoRoutingAgent for seller→customer state pairs."
        " If user asks for top/bottom lanes by freight, delivery days, or"
        " orders, call GeoRoutingAgent with limit=200 and rank the returned"
        " rows yourself by the requested metric. For cross-metric logistics"
        " questions, call multiple tools and synthesize.\n"
        + DEPARTMENT_SYNTHESIS_RULES
    ),
    tools=[
        AgentTool(agent=orders_agent),
        AgentTool(agent=lane_agent),
        AgentTool(agent=geo_routing_agent),
    ],
)
