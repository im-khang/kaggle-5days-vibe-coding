"""Olist Ecommerce Analytics Agent (Google ADK 2.3 multi-agent team).

Eval-compat shim: the Vertex eval SDK (used by `agents-cli eval generate`)
walks every agent's ``tools`` list and wraps each entry in
``FunctionTool(func=tool)`` to extract its declaration. Google's first-party
``BigQueryToolset`` and MCP ``McpToolset`` instances are not callables, so
this raises ``TypeError: ... is not a callable object`` and kills every eval
case before inference even starts.

We monkeypatch ``AgentConfig._get_tool_declarations_from_agent`` to filter
out non-callable, non-FunctionTool entries. This ONLY affects the eval SDK
import path — the normal ADK runtime never touches this class.
"""
from __future__ import annotations

from olist_ops import agent as agent
from olist_ops.agent import root_agent

__all__ = ["agent", "root_agent"]


def _patch_eval_sdk_tool_extraction() -> None:
    """Filter non-callable toolset objects from agent.tools for eval SDK."""
    try:
        from vertexai._genai.types import evals as _evals
    except ImportError:
        return

    _original = _evals.AgentConfig._get_tool_declarations_from_agent

    if getattr(_original, "_olist_patched", False):
        return

    def _patched_get_tool_declarations(cls, agent):
        # Filter out toolset instances that are not plain callables/FunctionTools.
        # Keep FunctionTool instances (have ._func) and bare functions.
        # Workflow agents (SequentialAgent etc.) have no ``tools`` field — skip
        # them (the inference runner already injects tools=[] via
        # _ensure_eval_compatible using object.__setattr__).
        raw_tools = getattr(agent, "tools", None)
        if raw_tools is None:
            return _original(agent)
        filtered = [
            t for t in raw_tools
            if callable(t) or hasattr(t, "_func") or hasattr(t, "func")
        ]
        # Use object.__setattr__ to bypass pydantic validation — the agent may
        # be a frozen model that rejects normal assignment.
        try:
            object.__setattr__(agent, "tools", filtered)
        except (AttributeError, TypeError):
            pass
        return _original(agent)

    _patched_get_tool_declarations._olist_patched = True  # type: ignore
    _evals.AgentConfig._get_tool_declarations_from_agent = (
        classmethod(_patched_get_tool_declarations)
    )


_patch_eval_sdk_tool_extraction()
