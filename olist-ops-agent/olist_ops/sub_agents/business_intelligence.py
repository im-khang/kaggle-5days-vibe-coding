"""Business Intelligence Department."""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from olist_ops.sub_agents.common import DEPARTMENT_SYNTHESIS_RULES, MODEL
from olist_ops.sub_agents.specialists import data_analyst_agent

head_of_bi = Agent(
    name="HeadOfBI",
    model=MODEL,
    description=(
        "Business Intelligence department head. Handles custom SQL joins, schema"
        " lookup, cross-table analysis, and verification fallbacks."
    ),
    instruction=(
        "You are Head of Business Intelligence for the Olist marketplace"
        " supply-chain team. Your scope: schema lookup, ad-hoc SQL, custom"
        " cross-table analyses, KPI verification, and data caveats. Use"
        " DataAnalystAgent when fixed department tools cannot answer directly."
        " Prefer verified SQL over guesses.\n"
        + DEPARTMENT_SYNTHESIS_RULES
    ),
    tools=[AgentTool(agent=data_analyst_agent)],
)
