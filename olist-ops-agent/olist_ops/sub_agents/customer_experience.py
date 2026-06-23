"""Customer Experience Department."""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from olist_ops.sub_agents.common import DEPARTMENT_SYNTHESIS_RULES, MODEL
from olist_ops.sub_agents.specialists import complaints_agent, returns_agent, reviews_agent

head_of_cx = Agent(
    name="HeadOfCX",
    model=MODEL,
    description=(
        "Customer Experience department head. Coordinates review analytics,"
        " complaints, low-score evidence, and cancellation/unavailable proxy."
    ),
    instruction=(
        "You are Head of Customer Experience for an Olist-style marketplace."
        " Your scope: review scores, low-star comment themes, delivery impact"
        " on CSAT, cancellations/unavailable proxy, and customer recovery"
        " priorities. Use ReviewsAgent for CSAT/delay analysis, ComplaintsAgent"
        " for low-score comments and customer-impact evidence, and ReturnsAgent"
        " for cancellation/unavailable rates.\n"
        + DEPARTMENT_SYNTHESIS_RULES
    ),
    tools=[
        AgentTool(agent=reviews_agent),
        AgentTool(agent=complaints_agent),
        AgentTool(agent=returns_agent),
    ],
)
