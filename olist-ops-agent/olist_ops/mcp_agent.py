"""ADK agent variant that consumes Olist tools through an MCP server.

This entrypoint exists to demonstrate the official Kaggle key concept:
"MCP Server — Where to Demonstrate: Code".

The production multi-agent team in `olist_ops/agent.py` keeps the in-process
FunctionTool wiring for lower latency and simpler eval. This variant proves the
same BigQuery analytics tools are also available through a protocol boundary:

    ChiefSupplyChainOfficerMCP -> McpToolset(stdio) -> olist_ops.mcp_server

Use it when a judge/reviewer wants explicit MCP evidence, or when connecting the
Olist tool layer to another MCP client.
"""
from __future__ import annotations

import os
import sys

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

from olist_ops.sub_agents.common import MODEL

_MCP_ENV = {
    key: value
    for key, value in os.environ.items()
    if key.startswith("GOOGLE_")
    or key in {
        "BQ_DATASET_ID",
        "BQ_DATASET_LOCATION",
        "PATH",
        "HOME",
        "USER",
        "LANG",
        "LC_ALL",
        "TERM",
        "TMPDIR",
    }
}

olist_mcp_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "olist_ops.mcp_server"],
            env=_MCP_ENV,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        ),
        timeout=30.0,
    ),
    tool_name_prefix="olist_",
)

root_agent = Agent(
    name="ChiefSupplyChainOfficerMCP",
    model=MODEL,
    description=(
        "MCP-backed Olist marketplace analytics agent. Uses the Olist MCP server"
        " for read-only BigQuery tools covering fulfillment, sellers, CX, finance,"
        " and BI."
    ),
    instruction="""\
You are the MCP-backed Chief Supply Chain Officer for an Olist-style Brazilian
e-commerce marketplace. You answer business operations questions using ONLY the
Olist MCP tools exposed to you.

Use cases:
- Delivery, on-time %, last-mile, customer-state lane performance.
- Seller KPIs, seller risk, freight by seller state.
- Review scores, low-star comments, cancellation/unavailable proxy.
- Payment mix and installments.
- Schema lookup and safe ad-hoc SQL.

Rules:
- Always call at least one MCP tool before giving a data answer.
- Never invent numbers, rows, or seller IDs.
- Disclose dataset caveats when relevant: no carrier_id (lane proxy), no returns
  table (canceled/unavailable proxy), no inventory/warehouse data.
- If the question is outside Olist ecommerce operations analytics, refuse briefly.
- Reply in English with a concise, decision-oriented answer.
""",
    tools=[olist_mcp_tools],
)
