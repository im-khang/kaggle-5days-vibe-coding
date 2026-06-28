"""Shared constants and prompt fragments for Olist agents."""

from __future__ import annotations

import os


def _build_model():
    """Return ADK model config.

    Public/default config uses Google's Gemini providers (Vertex AI or Google AI
    Studio, selected by ADK env vars). The OpenAI-compatible branch supports
    private localhost routing without changing agent definitions.
    """
    provider = os.getenv("OLIST_MODEL_PROVIDER", "vertex").lower()
    model_name = os.getenv("OLIST_MODEL", "gemini-2.5-flash")

    if provider in {"openai", "openai-compatible"}:
        from google.adk.models.lite_llm import LiteLlm

        api_base = os.getenv("OLIST_OPENAI_BASE_URL", "http://localhost:20128/v1")
        api_key = os.getenv("OLIST_OPENAI_API_KEY", "not-needed")
        return LiteLlm(
            model=f"openai/{model_name}",
            api_base=api_base,
            api_key=api_key,
        )

    if provider != "vertex":
        raise ValueError(
            "OLIST_MODEL_PROVIDER must be 'vertex' or 'openai-compatible' "
            f"(got {provider!r})"
        )

    # Vertex AI model name. Must be available to your project + region, or /run
    # returns 404 NOT_FOUND from Google GenAI.
    return model_name


# All agents read the same model. Public users should keep provider=vertex and
# choose Vertex AI (GOOGLE_GENAI_USE_VERTEXAI=1) or Google AI Studio
# (GOOGLE_API_KEY). Local maintainer override only:
#   OLIST_MODEL_PROVIDER=openai-compatible OLIST_MODEL=main \
#     OLIST_OPENAI_BASE_URL=http://localhost:20128/v1 uv run adk web --port 8001 .
MODEL = _build_model()

SHARED_TAIL = (
    " Use tool results only. If a tool returns no data or an error, say so and"
    " list what IS available (e.g. available_states / available_buckets) — do"
    " NOT invent numbers, IDs, or rows. Refuse questions outside Olist"
    " ecommerce operations analytics. Reply in English."
)

DEPARTMENT_TRANSFER_RULES = """

Routing rules (you delegate, you do not answer):
- You are a router. Pick exactly ONE specialist and transfer control to it.
- Do not call any tools yourself. Do not answer the question yourself.
- Do not synthesize across specialists — that is the orchestrator's job, not yours.
- State dataset caveats only when the user asks how the data is structured;
  otherwise let the specialist disclose them.
"""
