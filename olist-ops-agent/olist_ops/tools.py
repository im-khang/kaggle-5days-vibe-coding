"""Shared and specialist tools for the Olist Ecommerce Analytics Agent.

All tools are SELECT-only against BigQuery dataset `olist_ecommerce`.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from google.cloud import bigquery

def _require_project() -> str:
    """Return the GCP project id, failing only when a tool actually runs.

    Lazy so importing this module (and the agent tree) does not require env
    vars to be set — important for `adk web` discovery, notebook import, and
    unit tests that never hit BigQuery.
    """
    try:
        return os.environ["GOOGLE_CLOUD_PROJECT"]
    except KeyError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is not set. Export it (or put it in .env) "
            "before running any BigQuery-backed tool."
        ) from exc


PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")  # may be empty until a tool runs
DATASET = os.getenv("BQ_DATASET_ID", "olist_ecommerce")
LOCATION = os.getenv("BQ_DATASET_LOCATION", "US")

# Cost / safety caps
MAX_BYTES_BILLED = 10 * 1024 ** 3  # 10 GiB
QUERY_TIMEOUT_S = 30
ROW_TRUNCATION_LIMIT = 1000

_FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "truncate",
    "merge", "create", "replace", "grant", "revoke",
)


def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT, location=LOCATION)


def _escape(value: str) -> str:
    """Escape single quotes for safe string interpolation into SQL literals."""
    return value.replace("'", "''")


def _validate_select_sql(sql: str) -> tuple[bool, str]:
    """Reject anything that is not a pure SELECT / WITH ... SELECT."""
    if not sql or not sql.strip():
        return False, "empty SQL"
    stripped = sql.strip().rstrip(";").strip()
    lower = stripped.lower()
    if not (lower.startswith("select") or lower.startswith("with")):
        return False, "Only SELECT / CTE-then-SELECT statements are allowed."
    # word-boundary forbidden-keyword scan
    for kw in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", lower):
            return False, f"DML/DDL keyword '{kw}' is not allowed."
    # cross-dataset guard: any `project.dataset.table` reference must be our dataset
    for match in re.finditer(r"`([^`]+)`", stripped):
        ref = match.group(1)
        parts = ref.split(".")
        if len(parts) == 3 and parts[1] != DATASET:
            return False, f"cross-dataset reference not allowed: {ref}"
    return True, "ok"


# ---------------------------------------------------------------------------
# Shared tools (DataAnalystAgent)
# ---------------------------------------------------------------------------

def list_tables() -> dict:
    """Return all tables and views available in the olist_ecommerce dataset."""
    try:
        client = _client()
        dataset_ref = client.dataset(DATASET)
        items = list(client.list_tables(dataset_ref))
        tables = [t.table_id for t in items if t.table_type == "TABLE"]
        views = [t.table_id for t in items if t.table_type == "VIEW"]
        return {
            "project_id": PROJECT,
            "dataset_id": DATASET,
            "tables": tables,
            "views": views,
        }
    except Exception as e:
        return {"error": str(e)}


def get_schema(table_name: str) -> dict:
    """Return column names + types for a table or view in olist_ecommerce."""
    try:
        client = _client()
        table_ref = client.dataset(DATASET).table(table_name)
        table = client.get_table(table_ref)
        schema = [
            {"name": f.name, "type": f.field_type, "mode": f.mode}
            for f in table.schema
        ]
        return {"table": table_name, "schema": schema}
    except Exception as e:
        return {"error": str(e), "table": table_name}


def query_bigquery(sql: str, dry_run: bool = False) -> dict:
    """Run a SELECT-only query on the olist_ecommerce dataset.

    Validates SELECT-only, enforces 10 GiB billing cap, 30s timeout, and
    truncates results to 1000 rows.
    """
    ok, reason = _validate_select_sql(sql)
    if not ok:
        return {"error": f"unsafe SQL rejected: {reason}"}
    try:
        client = _client()
        job_config = bigquery.QueryJobConfig(
            dry_run=dry_run,
            use_query_cache=True,
            maximum_bytes_billed=MAX_BYTES_BILLED,
        )
        query_job = client.query(sql, job_config=job_config)
        if dry_run:
            return {
                "dry_run": True,
                "valid": True,
                "total_bytes_processed": query_job.total_bytes_processed,
            }
        results = query_job.result(timeout=QUERY_TIMEOUT_S)
        rows = []
        for i, row in enumerate(results):
            if i >= ROW_TRUNCATION_LIMIT:
                break
            rows.append({k: _jsonable(v) for k, v in dict(row).items()})
        return {
            "rows": rows,
            "total_rows": len(rows),
            "truncated": len(rows) >= ROW_TRUNCATION_LIMIT,
            "schema": [
                {"name": f.name, "type": f.field_type} for f in results.schema
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def _jsonable(v):
    """Stringify non-JSON BigQuery types (TIMESTAMP, DATE, Decimal, etc.)."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


# ---------------------------------------------------------------------------
# OrdersAgent tools
# ---------------------------------------------------------------------------

def get_order_status(order_id: str) -> dict:
    """Return lifecycle + delivery timing for one order from orders_enriched."""
    oid = _escape(order_id)
    sql = f"""
    SELECT
      order_id, customer_id, customer_state, customer_city, order_status,
      purchased_at, delivered_carrier_at, delivered_customer_at,
      estimated_delivery_at, delivery_days, days_late_vs_estimate,
      last_mile_days, on_time
    FROM `{PROJECT}.{DATASET}.orders_enriched`
    WHERE order_id = '{oid}'
    LIMIT 1
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {"order": rows[0]}
    return {
        "error": f"No order found with order_id={order_id!r}.",
        "available_order_id_sample": _sample_order_ids(),
    }


def _sample_order_ids() -> list[str]:
    sql = (
        f"SELECT order_id FROM `{PROJECT}.{DATASET}.orders_enriched` LIMIT 5"
    )
    result = query_bigquery(sql)
    return [r["order_id"] for r in result.get("rows", [])]


def get_delivery_stats(state: Optional[str] = None) -> dict:
    """Aggregate delivery KPIs from orders_enriched, optionally filtered by state."""
    where = "WHERE order_status = 'delivered'"
    if state:
        where += f" AND customer_state = '{_escape(state).upper()}'"
    sql = f"""
    SELECT
      COUNT(*) AS delivered_orders,
      ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
      ROUND(AVG(last_mile_days), 2) AS avg_last_mile_days,
      ROUND(AVG(days_late_vs_estimate), 2) AS avg_days_late_vs_estimate,
      ROUND(100 * AVG(CASE WHEN on_time THEN 1
                           WHEN on_time IS NULL THEN NULL
                           ELSE 0 END), 2) AS on_time_pct
    FROM `{PROJECT}.{DATASET}.orders_enriched`
    {where}
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows and rows[0].get("delivered_orders"):
        return {"filter_state": state, "stats": rows[0]}
    return {
        "error": (
            f"No delivered orders for state={state!r}."
            if state
            else "No delivered orders found."
        ),
        "available_states": _available_customer_states(),
    }


def _available_customer_states() -> list[str]:
    sql = f"""
    SELECT DISTINCT customer_state
    FROM `{PROJECT}.{DATASET}.orders_enriched`
    WHERE customer_state IS NOT NULL
    ORDER BY customer_state
    """
    result = query_bigquery(sql)
    return [r["customer_state"] for r in result.get("rows", [])]


# ---------------------------------------------------------------------------
# CarriersAgent tools (Olist has no carrier_id; lane = customer_state)
# ---------------------------------------------------------------------------

def get_lane_performance(state: Optional[str] = None) -> dict:
    """Per-state lane performance from carrier_kpis (Olist proxy for carriers)."""
    where = ""
    if state:
        where = f"WHERE customer_state = '{_escape(state).upper()}'"
    sql = f"""
    SELECT customer_state, delivered_orders, avg_last_mile_days,
           avg_delivery_days, on_time_pct, avg_days_late_vs_estimate
    FROM `{PROJECT}.{DATASET}.carrier_kpis`
    {where}
    ORDER BY on_time_pct DESC
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {"filter_state": state, "lanes": rows}
    available = query_bigquery(
        f"SELECT customer_state FROM `{PROJECT}.{DATASET}.carrier_kpis` "
        f"ORDER BY customer_state"
    )
    return {
        "error": f"No lane (state) matching {state!r} in carrier_kpis.",
        "available_states": [
            r["customer_state"] for r in available.get("rows", [])
        ],
    }


# ---------------------------------------------------------------------------
# SellersAgent tools
# ---------------------------------------------------------------------------

_SELLER_SORT_COLUMNS = {
    "orders": "orders",
    "on_time_pct": "on_time_pct",
    "avg_delivery_days": "avg_delivery_days",
    "avg_review_score": "avg_review_score",
    "avg_freight": "avg_freight",
}


def get_seller_kpis(
    seller_id: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 20,
    min_orders: int = 0,
    sort_by: str = "orders",
    ascending: bool = False,
) -> dict:
    """Per-seller KPIs from seller_kpis.

    Filters: seller_id, state, min_orders (only sellers with at least this many
    orders — use this for "worst/best N sellers" questions so tiny-volume
    sellers do not dominate). Sorting: sort_by one of orders, on_time_pct,
    avg_delivery_days, avg_review_score, avg_freight; ascending=True for
    "worst on-time" / "lowest" style questions.
    """
    limit = max(1, min(int(limit or 20), ROW_TRUNCATION_LIMIT))
    min_orders = max(0, int(min_orders or 0))
    sort_col = _SELLER_SORT_COLUMNS.get(sort_by, "orders")
    direction = "ASC" if ascending else "DESC"
    clauses = []
    if seller_id:
        clauses.append(f"seller_id = '{_escape(seller_id)}'")
    if state:
        clauses.append(f"seller_state = '{_escape(state).upper()}'")
    if min_orders > 0:
        clauses.append(f"orders >= {min_orders}")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
    SELECT seller_id, seller_state, orders, avg_delivery_days,
           on_time_pct, avg_review_score, avg_freight
    FROM `{PROJECT}.{DATASET}.seller_kpis`
    {where}
    ORDER BY {sort_col} {direction}
    LIMIT {limit}
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {
            "filter_seller_id": seller_id,
            "filter_state": state,
            "min_orders": min_orders,
            "sort_by": sort_col,
            "ascending": ascending,
            "sellers": rows,
        }
    avail = query_bigquery(
        f"""SELECT DISTINCT seller_state
            FROM `{PROJECT}.{DATASET}.seller_kpis`
            WHERE seller_state IS NOT NULL
            ORDER BY seller_state"""
    )
    return {
        "error": (
            f"No sellers match seller_id={seller_id!r} state={state!r}."
        ),
        "available_states": [
            r["seller_state"] for r in avail.get("rows", [])
        ],
    }


# ---------------------------------------------------------------------------
# ReviewsAgent tools
# ---------------------------------------------------------------------------

def get_review_breakdown() -> dict:
    """Review-score distribution per delivery delay bucket from review_kpis."""
    sql = f"""
    SELECT delay_bucket, reviews, avg_review_score, pct_1_2_star
    FROM `{PROJECT}.{DATASET}.review_kpis`
    ORDER BY
      CASE delay_bucket
        WHEN 'on_or_early' THEN 1
        WHEN 'late_1_3d'   THEN 2
        WHEN 'late_4_7d'   THEN 3
        WHEN 'late_8d_plus' THEN 4
        WHEN 'unknown'     THEN 5
      END
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {"breakdown": rows}
    return {
        "error": "review_kpis returned no rows.",
        "available_buckets": [
            "on_or_early", "late_1_3d", "late_4_7d", "late_8d_plus", "unknown",
        ],
    }


def get_low_score_reasons(limit: int = 20) -> dict:
    """Sample raw 1-2 star review messages from order_reviews."""
    limit = max(1, min(int(limit or 20), 100))
    sql = f"""
    SELECT review_id, order_id, review_score,
           review_comment_title, review_comment_message,
           review_creation_date
    FROM `{PROJECT}.{DATASET}.order_reviews`
    WHERE review_score <= 2
      AND review_comment_message IS NOT NULL
      AND TRIM(review_comment_message) != ''
    ORDER BY review_creation_date DESC
    LIMIT {limit}
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {"low_score_reviews": rows, "limit": limit}
    return {
        "error": "No low-score reviews with comment text found.",
        "available_score_range": [1, 2, 3, 4, 5],
    }


# ---------------------------------------------------------------------------
# ReturnsAgent tools (canceled / unavailable)
# ---------------------------------------------------------------------------

def get_cancel_rate(state: Optional[str] = None) -> dict:
    """Cancel/unavailable rate, optionally per customer_state."""
    state_filter = ""
    if state:
        state_filter = f"AND c.customer_state = '{_escape(state).upper()}'"
    sql = f"""
    SELECT
      c.customer_state,
      COUNT(*) AS total_orders,
      COUNTIF(o.order_status IN ('canceled','unavailable')) AS canceled_orders,
      ROUND(100 * COUNTIF(o.order_status IN ('canceled','unavailable'))
            / COUNT(*), 2) AS cancel_rate_pct
    FROM `{PROJECT}.{DATASET}.orders` o
    LEFT JOIN `{PROJECT}.{DATASET}.customers` c USING (customer_id)
    WHERE c.customer_state IS NOT NULL
      {state_filter}
    GROUP BY c.customer_state
    ORDER BY cancel_rate_pct DESC
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {"filter_state": state, "by_state": rows}
    avail = query_bigquery(
        f"SELECT DISTINCT customer_state FROM "
        f"`{PROJECT}.{DATASET}.customers` ORDER BY customer_state"
    )
    return {
        "error": f"No cancel-rate data for state={state!r}.",
        "available_states": [
            r["customer_state"] for r in avail.get("rows", [])
        ],
    }


# ---------------------------------------------------------------------------
# PaymentsAgent tools
# ---------------------------------------------------------------------------

def get_payment_mix() -> dict:
    """Distribution of payment types from order_payments."""
    sql = f"""
    SELECT
      payment_type,
      COUNT(*) AS payments,
      ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct,
      ROUND(AVG(payment_value), 2) AS avg_payment_value,
      ROUND(SUM(payment_value), 2) AS total_payment_value
    FROM `{PROJECT}.{DATASET}.order_payments`
    GROUP BY payment_type
    ORDER BY payments DESC
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {"payment_mix": rows}
    return {
        "error": "order_payments returned no rows.",
        "available_payment_types": [
            "credit_card", "boleto", "voucher", "debit_card", "not_defined",
        ],
    }


def get_installment_stats() -> dict:
    """Installment distribution, focused on credit-card payments."""
    sql = f"""
    SELECT
      payment_type,
      payment_installments,
      COUNT(*) AS payments,
      ROUND(AVG(payment_value), 2) AS avg_payment_value
    FROM `{PROJECT}.{DATASET}.order_payments`
    WHERE payment_type = 'credit_card'
    GROUP BY payment_type, payment_installments
    ORDER BY payment_installments
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {"installment_stats": rows, "filter_payment_type": "credit_card"}
    return {
        "error": "No credit-card installment data found.",
        "available_payment_types": [
            "credit_card", "boleto", "voucher", "debit_card",
        ],
    }


# ---------------------------------------------------------------------------
# GeoAgent tools
# ---------------------------------------------------------------------------

def get_state_pairs(limit: int = 20) -> dict:
    """Top seller_state -> customer_state lanes with orders, avg_freight, avg_delivery_days."""
    limit = max(1, min(int(limit or 20), 200))
    sql = f"""
    SELECT
      s.seller_state,
      c.customer_state,
      COUNT(DISTINCT o.order_id) AS orders,
      ROUND(AVG(i.freight_value), 2) AS avg_freight,
      ROUND(AVG(TIMESTAMP_DIFF(
          SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S',
              NULLIF(o.order_delivered_customer_date, '')),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S',
              NULLIF(o.order_purchase_timestamp, '')),
          DAY)), 2) AS avg_delivery_days
    FROM `{PROJECT}.{DATASET}.orders` o
    JOIN `{PROJECT}.{DATASET}.order_items` i USING (order_id)
    JOIN `{PROJECT}.{DATASET}.sellers` s USING (seller_id)
    JOIN `{PROJECT}.{DATASET}.customers` c USING (customer_id)
    WHERE s.seller_state IS NOT NULL AND c.customer_state IS NOT NULL
    GROUP BY s.seller_state, c.customer_state
    ORDER BY orders DESC
    LIMIT {limit}
    """
    result = query_bigquery(sql)
    rows = result.get("rows", [])
    if rows:
        return {"state_pairs": rows, "limit": limit}
    return {
        "error": "No seller-customer state pairs found.",
        "available_states": _available_customer_states(),
    }
