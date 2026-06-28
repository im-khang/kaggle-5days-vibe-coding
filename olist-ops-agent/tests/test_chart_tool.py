"""Unit tests for the chart rendering tool (no BigQuery, no network)."""
from __future__ import annotations

import struct

import pytest

from olist_ops.chart_tool import render_chart_png

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _png_dims(png: bytes) -> tuple[int, int]:
    # IHDR is the first chunk; width/height are big-endian uint32 at offset 16/20
    assert png[:8] == _PNG_MAGIC
    width, height = struct.unpack(">II", png[16:24])
    return width, height


def test_bar_chart_returns_valid_png():
    png = render_chart_png(
        chart_type="bar",
        labels=["credit_card", "boleto", "voucher"],
        values=[76.0, 19.0, 5.0],
        title="Payment Mix (%)",
        x_label="Payment type",
        y_label="Share %",
    )
    assert isinstance(png, bytes)
    assert png[:8] == _PNG_MAGIC
    w, h = _png_dims(png)
    assert w > 0 and h > 0


def test_line_chart_returns_valid_png():
    png = render_chart_png(
        chart_type="line",
        labels=["Jan", "Feb", "Mar", "Apr"],
        values=[100, 140, 120, 180],
        title="Sales over time",
    )
    assert png[:8] == _PNG_MAGIC


def test_barh_chart_returns_valid_png():
    png = render_chart_png(
        chart_type="barh",
        labels=["SP", "RJ", "MG"],
        values=[92.1, 88.4, 90.0],
        title="On-time % by state",
    )
    assert png[:8] == _PNG_MAGIC


def test_rejects_unknown_chart_type():
    with pytest.raises(ValueError):
        render_chart_png(
            chart_type="pie3d_exploded",
            labels=["a"],
            values=[1],
            title="x",
        )


def test_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        render_chart_png(
            chart_type="bar",
            labels=["a", "b"],
            values=[1],
            title="x",
        )


def test_rejects_empty_data():
    with pytest.raises(ValueError):
        render_chart_png(chart_type="bar", labels=[], values=[], title="x")
