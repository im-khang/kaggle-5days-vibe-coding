"""Chart rendering tool for the Olist analytics agent.

Two layers:

1. ``render_chart_png`` — pure, deterministic, returns PNG bytes. Easy to
   unit-test without ADK / BigQuery / network.
2. ``create_chart`` — ADK ``FunctionTool`` wrapper. Takes structured args from
   the LLM, calls ``render_chart_png``, and saves the result as an ADK
   ``Part`` artifact via ``ToolContext``. ``adk web`` renders saved image
   artifacts inline in the chat surface, so the user finally SEES a chart.

Why local matplotlib instead of an online chart service:
- No extra creds, no quotas, no rate limits, runs offline.
- Deterministic PNG output is testable; HTTP chart APIs are not.
- One small dep (matplotlib) already aligns with the data-analyst toolkit.
"""
from __future__ import annotations

import io
from typing import Optional, Sequence

import matplotlib

# Headless backend BEFORE importing pyplot — `adk web` runs in a server
# process with no display; default macOS backend would try to open a window.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

_SUPPORTED_TYPES = {"bar", "barh", "line"}


def render_chart_png(
    *,
    chart_type: str,
    labels: Sequence[str],
    values: Sequence[float],
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
) -> bytes:
    """Render a small business chart and return raw PNG bytes.

    Args:
        chart_type: One of ``bar``, ``barh``, ``line``.
        labels: Category labels (x for bar/line, y for barh).
        values: Numeric values, same length as ``labels``.
        title: Chart title.
        x_label, y_label: Optional axis labels.

    Raises:
        ValueError: invalid chart type, empty data, or mismatched lengths.
    """
    if chart_type not in _SUPPORTED_TYPES:
        raise ValueError(
            f"unsupported chart_type {chart_type!r}; "
            f"supported: {sorted(_SUPPORTED_TYPES)}"
        )
    if not labels or not values:
        raise ValueError("labels and values must be non-empty")
    if len(labels) != len(values):
        raise ValueError(
            f"labels ({len(labels)}) and values ({len(values)}) "
            "must have the same length"
        )

    # Coerce to plain floats; BigQuery rows often arrive as Decimal/str.
    try:
        numeric = [float(v) for v in values]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"values must be numeric: {exc}") from exc

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    try:
        if chart_type == "bar":
            ax.bar(list(labels), numeric, color="#1f77b4")
            ax.tick_params(axis="x", rotation=30)
        elif chart_type == "barh":
            ax.barh(list(labels), numeric, color="#1f77b4")
        else:  # line
            ax.plot(list(labels), numeric, marker="o", color="#1f77b4")
            ax.tick_params(axis="x", rotation=30)

        ax.set_title(title)
        if x_label:
            ax.set_xlabel(x_label)
        if y_label:
            ax.set_ylabel(y_label)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        return buf.getvalue()
    finally:
        plt.close(fig)


# ---------------------------------------------------------------------------
# ADK FunctionTool entry point
# ---------------------------------------------------------------------------

async def create_chart(
    chart_type: str,
    labels: list[str],
    values: list[float],
    title: str,
    tool_context,  # google.adk.tools.ToolContext, injected by ADK at call time
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    filename: Optional[str] = None,
) -> dict:
    """Create a chart from labelled values and save it as a session artifact.

    Use after a SQL/aggregation tool returned a small ranked or distribution
    result the user asked to visualize. Pass the column you want on the
    category axis as ``labels`` and the numeric column as ``values``.

    Args:
        chart_type: ``bar``, ``barh``, or ``line``.
        labels: Category labels (e.g. payment types, states, months).
        values: Numeric values aligned with labels.
        title: Chart title shown above the plot.
        x_label, y_label: Optional axis labels.
        filename: Optional artifact filename; auto-generated if omitted.

    Returns:
        ``{"artifact_filename": ..., "version": ..., "mime_type": ...}`` on
        success, or ``{"error": "..."}`` on failure. The image is delivered
        as an ADK artifact (Part) on the same response, so ``adk web``
        renders it inline.
    """
    try:
        png = render_chart_png(
            chart_type=chart_type,
            labels=labels,
            values=values,
            title=title,
            x_label=x_label,
            y_label=y_label,
        )
    except ValueError as exc:
        return {"error": f"chart render failed: {exc}"}

    # Import inside the call so unit tests can exercise render_chart_png
    # without pulling the ADK / pydantic runtime.
    from google.genai import types

    artifact_name = filename or f"chart_{abs(hash(title)) & 0xFFFFFF:06x}.png"
    part = types.Part.from_bytes(data=png, mime_type="image/png")
    try:
        version = await tool_context.save_artifact(
            filename=artifact_name, artifact=part
        )
    except Exception as exc:  # pragma: no cover - depends on artifact service
        return {
            "error": (
                "chart rendered but could not be saved as an artifact: "
                f"{exc}. Ensure `adk web` is running (it wires an artifact "
                "service automatically)."
            )
        }

    return {
        "artifact_filename": artifact_name,
        "version": version,
        "mime_type": "image/png",
        "chart_type": chart_type,
        "n_points": len(values),
    }
