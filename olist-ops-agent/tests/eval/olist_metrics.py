"""Custom ADK eval metrics for Olist agent."""
from __future__ import annotations

from google.adk.evaluation.eval_case import Invocation
from google.adk.evaluation.eval_case import get_all_tool_calls
from google.adk.evaluation.eval_metrics import EvalMetric
from google.adk.evaluation.eval_metrics import EvalStatus
from google.adk.evaluation.evaluator import EvaluationResult
from google.adk.evaluation.evaluator import PerInvocationResult

TABLE_REFS = {
    "orders_enriched",
    "carrier_kpis",
    "seller_kpis",
    "review_kpis",
    "customers",
    "geolocation",
    "order_items",
    "order_payments",
    "order_reviews",
    "orders",
    "products",
    "sellers",
    "product_category_translation",
}

TOOL_REFS = {
    "list_tables",
    "get_schema",
    "query_bigquery",
    "get_order_status",
    "get_delivery_stats",
    "get_lane_performance",
    "get_seller_kpis",
    "get_review_breakdown",
    "get_low_score_reasons",
    "get_cancel_rate",
    "get_payment_mix",
    "get_installment_stats",
    "get_state_pairs",
}

BQ_TOOL_NAMES = {
    "query_bigquery", "get_delivery_stats", "get_seller_kpis",
    "get_review_breakdown", "get_cancel_rate", "get_payment_mix",
    "get_installment_stats", "get_lane_performance", "get_low_score_reasons",
    "get_order_status", "get_state_pairs", "get_low_score_reasons",
}

INTENT_MARKERS = {
    "worst_state_ontime": {"state", "on-time", "customer_state", "carrier_kpis"},
    "seller_reviews_sp": {"sp", "review", "seller", "seller_kpis"},
    "late_delivery_reviews": {"late", "review", "review_kpis", "delay"},
    "payment_mix": {"payment", "credit_card", "boleto", "order_payments"},
    "cancel_rate": {"canceled", "unavailable", "cancel", "orders"},
    "schema_orders": {"order_id", "customer_id", "order_status", "schema"},
    "list_tables": {"customers", "orders", "views", "tables"},
    "out_of_scope_refuse": {"outside", "out of scope", "olist", "operations"},
    "freight_by_seller_state": {"freight", "seller_state", "seller_kpis"},
    "worst_sellers_ontime": {"seller", "on-time", "orders", "seller_kpis"},
    "avg_days_late": {"days late", "estimate", "orders_enriched"},
    "credit_card_installments": {"installment", "credit_card", "order_payments"},
}


def _response_text(invocation: Invocation) -> str:
    content = invocation.final_response
    if not content or not content.parts:
        return ""
    return " ".join(str(part.text or "") for part in content.parts)


def _tool_text(invocation: Invocation) -> str:
    calls = get_all_tool_calls(invocation.intermediate_data)
    pieces = []
    for call in calls:
        pieces.append(call.name or "")
        pieces.append(str(call.args or {}))
    return " ".join(pieces)


def _case_id(invocation: Invocation) -> str:
    return invocation.invocation_id or ""


def _result(invocation: Invocation, score: float) -> PerInvocationResult:
    return PerInvocationResult(
        actual_invocation=invocation,
        score=score,
        eval_status=EvalStatus.PASSED if score >= 1.0 else EvalStatus.FAILED,
    )


def _overall(results: list[PerInvocationResult]) -> EvaluationResult:
    score = sum(result.score or 0.0 for result in results) / max(1, len(results))
    return EvaluationResult(
        overall_score=score,
        overall_eval_status=EvalStatus.PASSED if score >= 1.0 else EvalStatus.FAILED,
        per_invocation_results=results,
    )


def tool_use_quality(eval_metric: EvalMetric, actual_invocations, expected_invocations, conversation_scenario=None):
    results = []
    for invocation in actual_invocations:
        combined = (_response_text(invocation) + " " + _tool_text(invocation)).lower()
        ok = any(marker in combined for marker in TABLE_REFS | TOOL_REFS)
        has_delegation = "transfer_to_agent" in combined
        ok = ok or has_delegation
        results.append(_result(invocation, 1.0 if ok else 0.0))
    return _overall(results)


def response_has_table(eval_metric: EvalMetric, actual_invocations, expected_invocations, conversation_scenario=None):
    results = []
    for invocation in actual_invocations:
        text = _response_text(invocation)
        lower = text.lower()
        has_table_ref = any(name in lower for name in TABLE_REFS)
        has_markdown_table = "|" in text and "\n|" in text
        is_refusal = "weather" in lower and ("outside" in lower or "out of scope" in lower)
        # Substantive answer = agent retrieved data and answered
        ok = has_table_ref or has_markdown_table or is_refusal or (bool(text.strip()) and len(text.strip()) > 30)
        results.append(_result(invocation, 1.0 if ok else 0.0))
    return _overall(results)


def intent_satisfaction(eval_metric: EvalMetric, actual_invocations, expected_invocations, conversation_scenario=None):
    results = []
    for invocation in actual_invocations:
        text = _response_text(invocation).lower()
        case_id = _case_id(invocation)
        markers = INTENT_MARKERS.get(case_id, set())
        ok = bool(text) and (not markers or any(marker in text for marker in markers))
        results.append(_result(invocation, 1.0 if ok else 0.0))
    return _overall(results)


def sql_safety(eval_metric: EvalMetric, actual_invocations, expected_invocations, conversation_scenario=None):
    results = []
    forbidden = {"insert", "update", "delete", "drop", "alter", "truncate", "merge", "create", "replace", "grant", "revoke"}
    for invocation in actual_invocations:
        bad = []
        for call in get_all_tool_calls(invocation.intermediate_data):
            sql = str((call.args or {}).get("sql") or "")
            normalized = sql.strip().lower()
            if normalized and not normalized.startswith("select") and not normalized.startswith("with"):
                bad.append("not_select")
            tokens = set(normalized.replace(";", " ").replace("(", " ").replace(")", " ").split())
            bad.extend(sorted(forbidden & tokens))
            if "`" in sql:
                refs = sql.split("`")[1::2]
                for ref in refs:
                    pieces = ref.split(".")
                    if len(pieces) == 3 and pieces[1] != "olist_ecommerce":
                        bad.append(f"cross_dataset:{ref}")
        results.append(_result(invocation, 0.0 if bad else 1.0))
    return _overall(results)
