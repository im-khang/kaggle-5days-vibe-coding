"""Load 9 Olist CSVs into BigQuery dataset olist_ecommerce + create 4 views.

Usage:
    uv run python scripts/bigquery_upload.py
or
    python scripts/bigquery_upload.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]  # must be set in .env
DATASET = os.getenv("BQ_DATASET_ID", "olist_ecommerce")
LOCATION = os.getenv("BQ_DATASET_LOCATION", "US")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# CSV file -> BigQuery table name. Encodings handle Olist quirks.
CSV_TO_TABLE = [
    ("olist_customers_dataset.csv",            "customers",      "utf-8"),
    ("olist_geolocation_dataset.csv",          "geolocation",    "utf-8"),
    ("olist_order_items_dataset.csv",          "order_items",    "utf-8"),
    ("olist_order_payments_dataset.csv",       "order_payments", "utf-8"),
    ("olist_order_reviews_dataset.csv",        "order_reviews",  "utf-8"),
    ("olist_orders_dataset.csv",               "orders",         "utf-8"),
    ("olist_products_dataset.csv",             "products",       "utf-8"),
    ("olist_sellers_dataset.csv",              "sellers",        "utf-8"),
    ("product_category_name_translation.csv",  "product_category_translation",
        "utf-8-sig"),
]

VIEW_SQL = {
    "orders_enriched": f"""
CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.orders_enriched` AS
SELECT
  o.order_id,
  o.customer_id,
  c.customer_state,
  c.customer_city,
  o.order_status,
  SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_purchase_timestamp, '')) AS purchased_at,
  SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_delivered_carrier_date, '')) AS delivered_carrier_at,
  SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_delivered_customer_date, '')) AS delivered_customer_at,
  SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_estimated_delivery_date, '')) AS estimated_delivery_at,
  TIMESTAMP_DIFF(
    SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_delivered_customer_date, '')),
    SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_purchase_timestamp, '')),
    DAY) AS delivery_days,
  TIMESTAMP_DIFF(
    SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_delivered_customer_date, '')),
    SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_estimated_delivery_date, '')),
    DAY) AS days_late_vs_estimate,
  TIMESTAMP_DIFF(
    SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_delivered_customer_date, '')),
    SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_delivered_carrier_date, '')),
    DAY) AS last_mile_days,
  CASE WHEN o.order_status = 'delivered'
       AND SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_delivered_customer_date, ''))
           <= SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', NULLIF(o.order_estimated_delivery_date, ''))
       THEN TRUE
       WHEN o.order_status = 'delivered' THEN FALSE
       ELSE NULL END AS on_time
FROM `{PROJECT}.{DATASET}.orders` o
LEFT JOIN `{PROJECT}.{DATASET}.customers` c USING (customer_id)
""",

    "seller_kpis": f"""
CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.seller_kpis` AS
SELECT
  i.seller_id,
  s.seller_state,
  COUNT(DISTINCT i.order_id) AS orders,
  ROUND(AVG(oe.delivery_days), 2) AS avg_delivery_days,
  ROUND(100 * AVG(CASE WHEN oe.on_time THEN 1
                       WHEN oe.on_time IS NULL THEN NULL
                       ELSE 0 END), 2) AS on_time_pct,
  ROUND(AVG(r.review_score), 2) AS avg_review_score,
  ROUND(AVG(i.freight_value), 2) AS avg_freight
FROM `{PROJECT}.{DATASET}.order_items` i
LEFT JOIN `{PROJECT}.{DATASET}.sellers` s USING (seller_id)
LEFT JOIN `{PROJECT}.{DATASET}.orders_enriched` oe USING (order_id)
LEFT JOIN `{PROJECT}.{DATASET}.order_reviews` r USING (order_id)
GROUP BY i.seller_id, s.seller_state
""",

    "carrier_kpis": f"""
CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.carrier_kpis` AS
SELECT
  customer_state,
  COUNT(*) AS delivered_orders,
  ROUND(AVG(last_mile_days), 2) AS avg_last_mile_days,
  ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
  ROUND(100 * AVG(CASE WHEN on_time THEN 1
                       WHEN on_time IS NULL THEN NULL
                       ELSE 0 END), 2) AS on_time_pct,
  ROUND(AVG(days_late_vs_estimate), 2) AS avg_days_late_vs_estimate
FROM `{PROJECT}.{DATASET}.orders_enriched`
WHERE order_status = 'delivered'
GROUP BY customer_state
""",

    "review_kpis": f"""
CREATE OR REPLACE VIEW `{PROJECT}.{DATASET}.review_kpis` AS
SELECT
  CASE
    WHEN oe.days_late_vs_estimate IS NULL THEN 'unknown'
    WHEN oe.days_late_vs_estimate <= 0 THEN 'on_or_early'
    WHEN oe.days_late_vs_estimate <= 3 THEN 'late_1_3d'
    WHEN oe.days_late_vs_estimate <= 7 THEN 'late_4_7d'
    ELSE 'late_8d_plus' END AS delay_bucket,
  COUNT(*) AS reviews,
  ROUND(AVG(r.review_score), 2) AS avg_review_score,
  ROUND(100 * AVG(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END), 2) AS pct_1_2_star
FROM `{PROJECT}.{DATASET}.order_reviews` r
JOIN `{PROJECT}.{DATASET}.orders_enriched` oe USING (order_id)
GROUP BY delay_bucket
""",
}


def ensure_dataset(client: bigquery.Client) -> None:
    ds_ref = bigquery.Dataset(f"{PROJECT}.{DATASET}")
    ds_ref.location = LOCATION
    client.create_dataset(ds_ref, exists_ok=True)
    print(f"[ok] dataset {PROJECT}.{DATASET} ready ({LOCATION})")


def load_csv(client: bigquery.Client, csv_name: str, table: str, encoding: str) -> None:
    path = DATA_DIR / csv_name
    if not path.exists():
        print(f"[skip] {csv_name} not found at {path}")
        return
    print(f"[load] {csv_name} -> {table}")
    df = pd.read_csv(path, encoding=encoding, keep_default_na=False, na_values=[""])
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    table_ref = f"{PROJECT}.{DATASET}.{table}"
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"  rows loaded: {client.get_table(table_ref).num_rows:,}")


def create_views(client: bigquery.Client) -> None:
    for name, sql in VIEW_SQL.items():
        print(f"[view] {name}")
        client.query(sql).result()
        print(f"  ok: {PROJECT}.{DATASET}.{name}")


def main() -> int:
    client = bigquery.Client(project=PROJECT, location=LOCATION)
    ensure_dataset(client)
    for csv_name, table, enc in CSV_TO_TABLE:
        load_csv(client, csv_name, table, enc)
    create_views(client)
    print("\nAll done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
