"""Orchestrator routing test — runs 10 advanced questions and captures the
full agent/tool call chain (CSCO → department → specialist → leaf tool) via an
ADK Plugin, so we can verify the orchestrator routes each question to the
right specialist.

Usage:
    set -a; source .env; set +a
    uv run python tests/orchestrator_routing_check.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import InMemoryRunner
from google.genai import types

# Ensure project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from olist_ops.agent import root_agent  # noqa: E402


class RoutingTracePlugin(BasePlugin):
    """Capture every agent activation and tool call, including nested ones."""

    def __init__(self) -> None:
        super().__init__(name="routing_trace")
        self.agents: list[str] = []
        self.tools: list[str] = []
        self.events: list[str] = []

    async def before_agent_callback(self, *, agent, callback_context):  # type: ignore[override]
        name = getattr(agent, "name", "?")
        self.agents.append(name)
        self.events.append(f"AGENT:{name}")
        return None

    async def before_tool_callback(self, *, tool, tool_args, tool_context):  # type: ignore[override]
        name = getattr(tool, "name", type(tool).__name__)
        self.tools.append(name)
        self.events.append(f"TOOL:{name}")
        return None


QUESTIONS = [
    (
        "Q1 / SellerRiskAgent",
        "Identify 5 sellers (min 50 orders) whose on-time % is below 80 AND "
        "average review score is below 3.5. Use multi-factor reasoning, give "
        "each a risk tier and a concrete intervention.",
        ["HeadOfSellerOps", "SellerRiskAgent"],
    ),
    (
        "Q2 / OrdersAgent (forecast)",
        "Forecast the average delivery days for the next 30 days for orders "
        "shipped from SP using the orders_enriched view. Label it as a model "
        "estimate.",
        ["HeadOfFulfillment", "OrdersAgent"],
    ),
    (
        "Q3 / LaneAgent (anomaly + contribution)",
        "Which customer-state lanes are statistical outliers for lateness, "
        "and which lanes contribute most to total late deliveries?",
        ["HeadOfFulfillment", "LaneAgent"],
    ),
    (
        "Q4 / GeoRoutingAgent (contribution)",
        "Decompose total freight cost by seller_state for the top 50 lanes by "
        "volume. Which origin state drives the most freight cost?",
        ["HeadOfFulfillment", "GeoRoutingAgent"],
    ),
    (
        "Q5 / SellerPerformanceAgent (external benchmark)",
        "How does our top-quartile seller on-time % compare to public "
        "e-commerce marketplace on-time benchmarks?",
        ["HeadOfSellerOps", "SellerPerformanceAgent"],
    ),
    (
        "Q6 / ComplaintsAgent (clustering)",
        "Cluster the top 50 raw 1-2 star comments into 4 themes and rank by "
        "frequency. Reason step by step before grouping.",
        ["HeadOfCX", "ComplaintsAgent"],
    ),
    (
        "Q7 / ReviewsAgent (delay buckets)",
        "Show review-score distribution by delivery-delay bucket and explain "
        "the CSAT drop pattern.",
        ["HeadOfCX", "ReviewsAgent"],
    ),
    (
        "Q8 / ReturnsAgent (cancel proxy)",
        "Rank the 5 worst customer states by cancellation/unavailable rate "
        "and disclose the dataset caveat about returns.",
        ["HeadOfCX", "ReturnsAgent"],
    ),
    (
        "Q9 / PaymentsAgent (installments)",
        "Installment distribution for credit-card payments — show the long "
        "tail and average installment count.",
        ["PaymentsAgent"],
    ),
    (
        "Q10 / DataAnalystAgent (catalog + insights)",
        "Use the BigQuery catalog to find any view that joins orders with "
        "review scores, then return its column list and a one-line summary "
        "of what it contains.",
        ["DataAnalystAgent"],
    ),
]


async def _run_one(plugin: RoutingTracePlugin, runner: InMemoryRunner,
                   app_name: str, user_id: str, prompt: str) -> tuple[list[str], list[str], str]:
    # Reset per-question state.
    plugin.agents.clear()
    plugin.tools.clear()
    plugin.events.clear()

    session = await runner.session_service.create_session(
        app_name=app_name, user_id=user_id
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=msg
    ):
        content = getattr(event, "content", None)
        if content is not None:
            for p in getattr(content, "parts", []) or []:
                txt = getattr(p, "text", None)
                if txt:
                    final_text = txt
    return list(plugin.agents), list(plugin.tools), final_text


async def main() -> int:
    app_name = "olist_ops_routing_check"
    user_id = "routing-check"
    plugin = RoutingTracePlugin()
    runner = InMemoryRunner(agent=root_agent, app_name=app_name, plugins=[plugin])

    results: list[dict[str, Any]] = []
    for label, prompt, expected_agents in QUESTIONS:
        print(f"\n=== {label} ===")
        print(f"Q: {prompt}")
        try:
            agents, tools, final = await _run_one(
                plugin, runner, app_name, user_id, prompt
            )
        except Exception as exc:
            print(f"  ⚠ runtime error: {exc}")
            results.append({"label": label, "agents": [], "tools": [],
                            "expected": expected_agents, "ok": False})
            continue

        agents_set = set(agents)
        ok = all(t in agents_set for t in expected_agents)
        print(f"  agents activated: {agents}")
        print(f"  tools called:     {tools}")
        print(f"  expected agents:  {expected_agents}  →  {'PASS' if ok else 'FAIL'}")
        print(f"  final (first 200 chars): {final[:200].replace(chr(10), ' ')}")
        results.append({
            "label": label,
            "agents": agents,
            "tools": tools,
            "expected": expected_agents,
            "ok": ok,
            "final_preview": final[:240],
        })

    await runner.close()

    summary_path = ROOT / "tests" / "eval" / "orchestrator_routing_report.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    passed = sum(1 for r in results if r["ok"])
    print(f"\n=== ROUTING SUMMARY: {passed}/{len(results)} passed ===")
    print(f"Report: {summary_path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
