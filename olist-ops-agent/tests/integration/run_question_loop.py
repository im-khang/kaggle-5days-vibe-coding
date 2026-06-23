"""Integration smoke-test harness for the Olist supply-chain agent team.

Runs a battery of questions through the full ChiefSupplyChainOfficer loop and
reports, per question: which department tools were called, how many agent hops,
answer length, latency, and errors. Use this after any agent/tool change to
confirm departments still coordinate and tools still work.

Usage:
    set -a; source .env; set +a
    .venv/bin/python tests/integration/run_question_loop.py
    .venv/bin/python tests/integration/run_question_loop.py --json results.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from olist_ops.agent import root_agent

# (department_label, question, expectation)
QUESTIONS = [
    # Fulfillment & Logistics
    ("Fulfillment", "Average delivery days overall and for state SP?"),
    ("Fulfillment", "Which state has the worst on-time delivery rate?"),
    ("Fulfillment", "Top 5 seller to customer state lanes by freight cost."),
    ("Fulfillment", "Top 3 lanes with longest average delivery time."),
    # Seller Management
    ("SellerOps", "Top 5 worst sellers by on-time rate with at least 50 orders."),
    ("SellerOps", "Which sellers should be flagged for intervention based on poor performance?"),
    # Customer Experience
    ("CX", "Do late deliveries get worse reviews? Show me the data."),
    ("CX", "Show me 5 raw 1-2 star review comments."),
    ("CX", "How many orders were canceled by state?"),
    # Finance & Payments
    ("Finance", "What payment types are most common?"),
    ("Finance", "Installment distribution for credit card payments."),
    # Business Intelligence
    ("BI", "Show me the schema of the orders table."),
    # Cross-domain (CSCO must call multiple departments and synthesize)
    ("Cross", "Compare the 5 worst on-time sellers (min 50 orders) vs the 5 best. What is the gap in average review scores?"),
    ("Cross", "Which state has both the worst on-time delivery AND highest cancellation rate?"),
    # Executive briefing (full Sequential+Parallel pipeline)
    ("Exec", "Give me a full executive summary of our supply chain health."),
    # Out of scope
    ("Refuse", "What's the weather in Hanoi today?"),
]


async def run_all(save_path: str | None = None) -> list[dict]:
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, session_service=session_service, app_name="olist_ops")
    results: list[dict] = []

    for i, (dept, q) in enumerate(QUESTIONS, 1):
        t0 = time.time()
        session = await session_service.create_session(app_name="olist_ops", user_id="test")
        content = types.Content(parts=[types.Part(text=q)], role="user")

        final_text = ""
        tool_calls: list[str] = []
        errors: list[str] = []

        try:
            async for event in runner.run_async(
                session_id=session.id, user_id="test", new_message=content
            ):
                if getattr(event, "content", None) and getattr(event.content, "parts", None):
                    for part in event.content.parts:
                        if getattr(part, "function_call", None):
                            tool_calls.append(part.function_call.name)
                        if getattr(part, "text", None) and event.is_final_response():
                            final_text += part.text
                if getattr(event, "error_message", None):
                    errors.append(event.error_message)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

        elapsed = round(time.time() - t0, 1)
        ok = len(final_text) > 20 and not errors
        status = "PASS" if ok else "FAIL"
        print(f"Q{i:2d} [{status}] {dept:11s} {elapsed:5.1f}s tools={tool_calls}")
        print(f"     {q}")
        print(f"     -> {final_text[:140]}{'...' if len(final_text) > 140 else ''}")
        if errors:
            print(f"     ERRORS: {errors[:2]}")
        print()

        results.append({
            "q_num": i, "dept": dept, "question": q, "ok": ok,
            "elapsed": elapsed, "tool_calls": tool_calls,
            "answer_len": len(final_text), "errors": errors,
            "answer_preview": final_text[:400],
        })

    passed = sum(1 for r in results if r["ok"])
    print("=" * 60)
    print(f"TOTAL: {passed}/{len(results)} passed")

    if save_path:
        with open(save_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        print(f"Saved results to {save_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default=None, help="Save results to JSON path")
    args = parser.parse_args()
    asyncio.run(run_all(args.json_path))
