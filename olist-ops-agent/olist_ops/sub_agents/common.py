"""Shared constants and prompt fragments for Olist agents."""

MODEL = "gemini-2.5-flash"

SHARED_TAIL = (
    " Use tool results only. If a tool returns no data or an error, say so and"
    " list what IS available (e.g. available_states / available_buckets) — do"
    " NOT invent numbers, IDs, or rows. Refuse questions outside Olist"
    " ecommerce operations analytics. Reply in English."
)

DEPARTMENT_SYNTHESIS_RULES = """Department rules:
- Call the specialist agents/tools one by one; wait for each result before calling the next.
- Use multiple specialists when the question spans multiple metrics.
- Synthesize the department answer yourself. Do not just paste raw outputs.
- Never mention internal agent/tool names unless the user explicitly asks for debugging.
- State dataset caveats plainly: Olist has no carrier_id, no explicit returns table, no inventory table, no warehouse table.
- Use concise markdown tables for ranked results.
"""
