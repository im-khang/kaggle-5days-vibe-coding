"""Finance & Payments Department."""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from olist_ops.sub_agents.common import DEPARTMENT_SYNTHESIS_RULES, MODEL
from olist_ops.sub_agents.specialists import payments_agent

head_of_finance = Agent(
    name="HeadOfFinance",
    model=MODEL,
    description=(
        "Finance & Payments department head. Coordinates payment mix, installment"
        " behavior, AOV/payment-value views, and finance caveats."
    ),
    instruction=(
        "You are Head of Finance & Payments for an Olist-style marketplace."
        " Your scope: payment mix, installment distribution, payment value, and"
        " finance caveats. Olist has no margin, settlement, refund, or fraud"
        " data, so disclose those limits. Use PaymentsAgent for all payment"
        " metrics.\n"
        + DEPARTMENT_SYNTHESIS_RULES
    ),
    tools=[AgentTool(agent=payments_agent)],
)
