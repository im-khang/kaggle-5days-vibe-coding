"""Customer Experience Department."""
from __future__ import annotations

from google.adk.agents import Agent

from olist_ops.sub_agents.common import DEPARTMENT_TRANSFER_RULES, MODEL
from olist_ops.sub_agents.specialists import complaints_agent, returns_agent, reviews_agent

head_of_cx = Agent(
    name="HeadOfCX",
    model=MODEL,
    description=(
        "Customer Experience department head. Routes review analytics, complaint"
        " themes, low-score evidence, and cancellation/unavailable proxy questions."
    ),
    instruction=(
        "You are Head of Customer Experience for an Olist-style marketplace."
        " Your job is pure routing to one specialist, not cross-department"
        " synthesis.\n"
        "Route within your team:\n"
        "- ReviewsAgent: numeric CSAT analysis, review-score distribution by"
        " delivery-delay bucket, score trends.\n"
        "- ComplaintsAgent: qualitative complaint work, clustering/grouping raw"
        " 1-2 star comments, customer-impact themes.\n"
        "- ReturnsAgent: cancellation/unavailable rates, returns proxy questions.\n"
        "Any request to cluster comments, group complaints, or extract themes from"
        " reviews goes to ComplaintsAgent, not ReviewsAgent."
        + DEPARTMENT_TRANSFER_RULES
    ),
    sub_agents=[reviews_agent, complaints_agent, returns_agent],
)
