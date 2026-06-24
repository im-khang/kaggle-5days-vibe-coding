"""MCP toolset factories for public MCP servers.

Each specialist agent can receive a toolset that connects to an existing
open-source MCP server. We do not create a custom server here; we stand on public
servers that already expose web fetch, DuckDuckGo search, sequential reasoning,
and memory tools.

We also wire Google's first-party `BigQueryToolset` (from
`google.adk.integrations.bigquery`) — read-only via `WriteMode.BLOCKED` — so any
agent that needs richer BigQuery primitives (forecast, anomaly detection,
contribution analysis, ask-data-insights, catalog search) gets them directly
from Google instead of through our small custom tool wrapper.
"""

from __future__ import annotations

import os
import warnings

# Silence ADK experimental-feature warnings emitted at import time.
warnings.filterwarnings("ignore", category=UserWarning, module="google.adk.features")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

# Google first-party BigQuery toolset (read-only). Import is lazy via a factory
# below — instantiating it requires Application Default Credentials, which we
# only need when the agent actually runs.
from google.adk.integrations.bigquery.bigquery_credentials import (
    BigQueryCredentialsConfig,
)
from google.adk.integrations.bigquery.bigquery_toolset import BigQueryToolset
from google.adk.integrations.bigquery.config import (
    BigQueryToolConfig,
    WriteMode,
)


def _safe_env() -> dict[str, str]:
    """Return filtered env for public MCP subprocesses.

    Public MCP servers do not need Google credentials. Keep only boring process
    variables and avoid leaking tokens or secrets into subprocesses.
    """
    safe_keys = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM", "TMPDIR"}
    return {k: v for k, v in os.environ.items() if k in safe_keys}


# ---------------------------------------------------------------------------
# Public-MCP factories (stdio).
# ---------------------------------------------------------------------------

def fetch_toolset() -> McpToolset:
    """uvx mcp-server-fetch: fetch URL content for source-grounded research."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="uvx",
                args=["mcp-server-fetch"],
                env=_safe_env(),
                cwd=os.getcwd(),
            ),
            timeout=30.0,
        ),
        tool_name_prefix="fetch_",
    )


def duck_search_toolset() -> McpToolset:
    """uvx duckduckgo-mcp-server: public web search without API key."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="uvx",
                args=["duckduckgo-mcp-server"],
                env=_safe_env(),
                cwd=os.getcwd(),
            ),
            timeout=30.0,
        ),
        tool_name_prefix="duck_",
    )


def sequential_thinking_toolset() -> McpToolset:
    """npx @modelcontextprotocol/server-sequential-thinking: stepwise synthesis."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
                env=_safe_env(),
                cwd=os.getcwd(),
            ),
            timeout=30.0,
        ),
        tool_name_prefix="seq_",
    )


def memory_toolset() -> McpToolset:
    """npx @modelcontextprotocol/server-memory: lightweight MCP memory graph."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-memory"],
                env=_safe_env(),
                cwd=os.getcwd(),
            ),
            timeout=30.0,
        ),
        tool_name_prefix="mem_",
    )


# ---------------------------------------------------------------------------
# Google first-party BigQuery toolset (read-only).
# ---------------------------------------------------------------------------

def google_bigquery_toolset(
    *,
    tool_filter: list[str] | None = None,
) -> BigQueryToolset:
    """Return Google's official `BigQueryToolset` with writes blocked.

    Use this whenever an agent needs first-party BigQuery primitives beyond our
    small custom wrappers. Tools exposed (subset configurable via tool_filter):

        - list_dataset_ids / list_table_ids
        - get_dataset_info / get_table_info
        - get_job_info
        - execute_sql                (read-only — WriteMode.BLOCKED)
        - forecast                   (TimesFM forecasting)
        - analyze_contribution
        - detect_anomalies
        - ask_data_insights          (Conversational Analytics API)
        - search_catalog

    Requires Application Default Credentials with `bigquery.dataViewer` and
    `bigquery.jobUser` on the target dataset. Falls back gracefully when ADC is
    not set (the underlying toolset constructor accepts no credentials and
    inherits ADC at call time).
    """
    config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)
    creds_config = None
    try:
        import google.auth  # type: ignore

        creds, _ = google.auth.default()
        creds_config = BigQueryCredentialsConfig(credentials=creds)
    except Exception:  # pragma: no cover - ADC may be missing at import time
        creds_config = None

    return BigQueryToolset(
        tool_filter=tool_filter,
        credentials_config=creds_config,
        bigquery_tool_config=config,
    )
