"""Run the forecast question through the real agent team and capture output.

Usage:
    set -a; source .env; set +a
    .venv/bin/python tests/integration/run_forecast_test.py
"""
from __future__ import annotations

import asyncio
import os
import time

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from olist_ops.agent import root_agent
from olist_ops.tools import PROJECT, DATASET

QUESTION = "Forecast average delivery days for the next 30 days for SP customers."


async def run_forecast():
    print(f"PROJECT={PROJECT}")
    print(f"DATASET={DATASET}")
    print(f"Question: {QUESTION}")
    print("=" * 80)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        app_name="olist_ops_forecast_test",
    )

    session = await session_service.create_session(
        app_name="olist_ops_forecast_test", user_id="test"
    )
    content = types.Content(parts=[types.Part(text=QUESTION)], role="user")

    t0 = time.time()
    events_count = 0
    tool_calls = []
    tool_responses = []
    final_text = ""
    errors = []

    async for event in runner.run_async(
        session_id=session.id, user_id="test", new_message=content
    ):
        events_count += 1
        if getattr(event, "content", None) and getattr(event.content, "parts", None):
            for part in event.content.parts:
                if getattr(part, "function_call", None):
                    fc = part.function_call
                    tool_calls.append(f"{fc.name}({dict(fc.args)})")
                    print(f"\n[TOOL CALL] {fc.name}")
                    print(f"  args: {dict(fc.args)}")
                if getattr(part, "function_response", None):
                    fr = part.function_response
                    resp = dict(fr.response) if fr.response else {}
                    tool_responses.append(f"{fr.name}: {resp}")
                    # Truncate large responses
                    resp_str = str(resp)
                    if len(resp_str) > 2000:
                        resp_str = resp_str[:2000] + "... [truncated]"
                    print(f"\n[TOOL RESPONSE] {fr.name}")
                    print(f"  {resp_str}")
                if getattr(part, "text", None):
                    if event.is_final_response():
                        final_text += part.text
                    else:
                        print(f"\n[TEXT] {part.text[:500]}")
        if getattr(event, "error_message", None):
            errors.append(event.error_message)
            print(f"\n[ERROR] {event.error_message}")

    elapsed = time.time() - t0
    print("\n" + "=" * 80)
    print(f"Events: {events_count}")
    print(f"Tool calls: {len(tool_calls)}")
    for tc in tool_calls:
        print(f"  - {tc}")
    print(f"Tool responses: {len(tool_responses)}")
    print(f"Errors: {len(errors)}")
    for e in errors:
        print(f"  - {e}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"\nFinal answer:\n{final_text}")


if __name__ == "__main__":
    asyncio.run(run_forecast())
