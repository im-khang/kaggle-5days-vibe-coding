"""Olist Ops MCP Server — exposes all BigQuery analytics tools over MCP (stdio).

This wraps the same SELECT-only BigQuery tools used by the in-process ADK agents
and serves them as a standalone Model Context Protocol (MCP) server. Any MCP
client (Claude Desktop, ADK's McpToolset, mcporter, etc.) can connect over stdio
and call these tools.

Run directly:
    GOOGLE_CLOUD_PROJECT=<proj> uv run python -m olist_ops.mcp_server

The ADK agent in `olist_ops/mcp_agent.py` consumes this exact server via
`McpToolset`, demonstrating the MCP Server key concept end-to-end: one tool
implementation, exposed over the protocol, consumed by an agent.

Security: every tool here delegates to `olist_ops.tools`, which enforces
SELECT/CTE-only SQL, a 10 GiB billing cap, a 30s timeout, 1000-row truncation,
and a cross-dataset reference guard. No DML/DDL can pass through the protocol.
"""
from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from olist_ops import tools as _t

mcp = FastMCP(
    name="olist-ops",
    instructions=(
        "Olist Brazilian e-commerce marketplace analytics. SELECT-only BigQuery "
        "tools over the olist_ecommerce dataset: orders, deliveries, sellers, "
        "reviews, payments, cancellations, and seller-to-customer freight lanes. "
        "All tools are read-only and safety-capped."
    ),
)


# --- Shared / BI tools -----------------------------------------------------

@mcp.tool()
def list_tables() -> dict:
    """List all tables and views in the olist_ecommerce dataset."""
    return _t.list_tables()


@mcp.tool()
def get_schema(table_name: str) -> dict:
    """Return column names + types for a table or view in olist_ecommerce."""
    return _t.get_schema(table_name)


@mcp.tool()
def query_bigquery(sql: str, dry_run: bool = False) -> dict:
    """Run a SELECT-only query (10 GiB cap, 30s timeout, 1000-row truncation).

    DML/DDL keywords and cross-dataset references are rejected before execution.
    """
    return _t.query_bigquery(sql, dry_run=dry_run)


# --- Fulfillment tools -----------------------------------------------------

@mcp.tool()
def get_order_status(order_id: str) -> dict:
    """Lifecycle + delivery timing for one order from orders_enriched."""
    return _t.get_order_status(order_id)


@mcp.tool()
def get_delivery_stats(state: Optional[str] = None) -> dict:
    """Aggregate delivery KPIs from orders_enriched, optionally by customer_state."""
    return _t.get_delivery_stats(state)


@mcp.tool()
def get_lane_performance(state: Optional[str] = None) -> dict:
    """Per-state delivery-lane performance from carrier_kpis (carrier proxy)."""
    return _t.get_lane_performance(state)


@mcp.tool()
def get_state_pairs(limit: int = 20) -> dict:
    """Top seller_state -> customer_state lanes: orders, avg_freight, avg_delivery_days."""
    return _t.get_state_pairs(limit)


# --- Seller Ops tools ------------------------------------------------------

@mcp.tool()
def get_seller_kpis(
    seller_id: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 20,
    min_orders: int = 0,
    sort_by: str = "orders",
    ascending: bool = False,
) -> dict:
    """Per-seller KPIs from seller_kpis with min_orders filter and sortable columns.

    sort_by one of: orders, on_time_pct, avg_delivery_days, avg_review_score,
    avg_freight. ascending=True for worst/lowest questions.
    """
    return _t.get_seller_kpis(
        seller_id=seller_id,
        state=state,
        limit=limit,
        min_orders=min_orders,
        sort_by=sort_by,
        ascending=ascending,
    )


# --- Customer Experience tools ---------------------------------------------

@mcp.tool()
def get_review_breakdown() -> dict:
    """Review-score distribution per delivery-delay bucket from review_kpis."""
    return _t.get_review_breakdown()


@mcp.tool()
def get_low_score_reasons(limit: int = 20) -> dict:
    """Sample raw 1-2 star review messages from order_reviews."""
    return _t.get_low_score_reasons(limit)


@mcp.tool()
def get_cancel_rate(state: Optional[str] = None) -> dict:
    """Cancel/unavailable order rate, optionally per customer_state."""
    return _t.get_cancel_rate(state)


# --- Finance tools ---------------------------------------------------------

@mcp.tool()
def get_payment_mix() -> dict:
    """Distribution of payment types from order_payments."""
    return _t.get_payment_mix()


@mcp.tool()
def get_installment_stats() -> dict:
    """Installment distribution, focused on credit-card payments."""
    return _t.get_installment_stats()


def main() -> None:
    """Entry point: serve all tools over MCP stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
