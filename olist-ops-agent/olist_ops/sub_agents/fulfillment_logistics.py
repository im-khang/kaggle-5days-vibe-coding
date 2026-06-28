"""Fulfillment & Logistics Department."""
from __future__ import annotations

from google.adk.agents import Agent

from olist_ops.sub_agents.common import DEPARTMENT_TRANSFER_RULES, MODEL
from olist_ops.sub_agents.specialists import geo_routing_agent, lane_agent, orders_agent

head_of_fulfillment = Agent(
    name="HeadOfFulfillment",
    model=MODEL,
    description=(
        "Fulfillment & Logistics department head. Routes order lifecycle,"
        " delivery timing, customer-state lane performance, and seller→customer"
        " geographic routing questions to the right specialist."
    ),
    instruction=(
        "You are Head of Fulfillment & Logistics for an Olist-style marketplace."
        " Your job is pure routing to one specialist, not cross-department"
        " synthesis.\n"
        "Route within your team:\n"
        "- OrdersAgent: order lifecycle, delivery days, last-mile time,"
        " on-time vs estimate, and delivery forecasts.\n"
        "- LaneAgent: customer-state lane performance, carrier proxy KPIs,"
        " lateness outliers, and contribution to late deliveries.\n"
        "- GeoRoutingAgent: seller_state→customer_state lanes, freight by lane,"
        " top/bottom lanes by freight, delivery days, or orders.\n"
        "If user asks for top/bottom lanes by freight, delivery days, or orders,"
        " route to GeoRoutingAgent. If user asks for a forecast, route to"
        " OrdersAgent."
        + DEPARTMENT_TRANSFER_RULES
    ),
    sub_agents=[orders_agent, lane_agent, geo_routing_agent],
)
