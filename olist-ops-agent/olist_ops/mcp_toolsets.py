"""MCP toolset factories for public MCP servers.

Each specialist agent can receive a toolset that connects to an existing
open-source MCP server. We do not create a custom server here; we stand on public
servers that already expose web fetch, DuckDuckGo search, sequential reasoning,
and memory tools.

We also wire Google's first-party `BigQueryToolset` (from
`google.adk.integrations.bigquery`) — write-protected via `WriteMode.PROTECTED` — so any
agent that needs richer BigQuery primitives (forecast, anomaly detection,
contribution analysis, ask-data-insights, catalog search) gets them directly
from Google instead of through our small custom tool wrapper. PROTECTED mode
allows temporary session artifacts (needed by forecast/detect_anomalies which
internally run CREATE MODEL) but still blocks permanent writes to user tables.
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

from google.adk.tools.google_tool import GoogleTool

from olist_ops.tools import PROJECT, DATASET, LOCATION


class _ProjectInjectedBigQueryToolset(BigQueryToolset):
    """BigQueryToolset that auto-injects project_id into ML tool calls.

    Google's ``forecast``, ``detect_anomalies``, and ``analyze_contribution``
    take ``project_id`` as a required parameter that the LLM must fill. Even
    with instruction context, models sometimes pass an empty string, causing
    "ProjectId must be non-empty" errors.

    This subclass overrides ``get_tools`` to replace the three ML tools with
    ``_ProjectInjectedGoogleTool`` instances that pre-fill ``project_id`` from
    the ``GOOGLE_CLOUD_PROJECT`` env var and hide the parameter from the LLM's
    schema entirely.
    """

    async def get_tools(self, readonly_context=None):
        tools = await super().get_tools(readonly_context)
        if not PROJECT:
            return tools

        _ML_TOOL_NAMES = {"forecast", "detect_anomalies", "analyze_contribution"}
        patched = []
        for tool in tools:
            if tool.name in _ML_TOOL_NAMES:
                patched.append(
                    _ProjectInjectedGoogleTool(
                        func=tool.func,
                        project_id=PROJECT,
                        credentials_config=tool._credentials_manager.credentials_config
                        if tool._credentials_manager
                        else None,
                        tool_settings=tool._tool_settings,
                    )
                )
            else:
                patched.append(tool)
        return patched


class _ProjectInjectedGoogleTool(GoogleTool):
    """GoogleTool that pre-fills project_id and hides it from the LLM schema."""

    def __init__(self, *, project_id: str, **kwargs):
        super().__init__(**kwargs)
        self._project_id = project_id
        self._ignore_params.append("project_id")

    async def _run_async_with_credential(
        self, credentials, tool_settings, args, tool_context
    ):
        # Force-override project_id regardless of what the LLM passed.
        # This fixes "ProjectId must be non-empty" even if the model
        # hallucinates an empty project_id despite it being hidden from schema.
        args["project_id"] = self._project_id
        return await super()._run_async_with_credential(
            credentials, tool_settings, args, tool_context
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
    """Return Google's official `BigQueryToolset` with writes protected.

    Use this whenever an agent needs first-party BigQuery primitives beyond our
    small custom wrappers. Tools exposed (subset configurable via tool_filter):

        - list_dataset_ids / list_table_ids
        - get_dataset_info / get_table_info
        - get_job_info
        - execute_sql                (write-protected — WriteMode.PROTECTED)
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
    config = BigQueryToolConfig(
        write_mode=WriteMode.PROTECTED,
        compute_project_id=PROJECT or None,
        location=LOCATION or None,
    )
    creds_config = None
    try:
        import google.auth  # type: ignore

        creds, _ = google.auth.default()
        creds_config = BigQueryCredentialsConfig(credentials=creds)
    except Exception:  # pragma: no cover - ADC may be missing at import time
        creds_config = None

    return _ProjectInjectedBigQueryToolset(
        tool_filter=tool_filter,
        credentials_config=creds_config,
        bigquery_tool_config=config,
    )
