"""TRANSFORM: clean the raw Shopify orders export and split it into two tables.

A Shopify export has one row per LINE ITEM, and the order-level columns
(email, total, status...) are only filled on the first row of each order.
We turn that into:
  - orders       -> one row per order
  - order_items  -> one row per product in an order
"""
import logging

import pandas as pd

log = logging.getLogger(__name__)

ORDER_COLUMNS = {
    "Name": "order_number",
    "Id": "shopify_order_id",
    "Created at": "created_at",
    "Paid at": "paid_at",
    "Email": "customer_email",
    "Billing Name": "customer_name",
    "Financial Status": "payment_status",
    "Fulfillment Status": "fulfillment_status",
    "Payment Method": "payment_method",
    "Currency": "currency",
    "Subtotal": "subtotal",
    "Discount Code": "discount_code",
    "Discount Amount": "discount_amount",
    "Shipping": "shipping",
    "Taxes": "taxes",
    "Total": "total",
    "Refunded Amount": "refunded_amount",
    "Shipping Method": "shipping_method",
    "Shipping City": "ship_city",
    "Shipping Province": "ship_province",
    "Shipping Country": "ship_country",
    "source_file": "source_file",
}

ITEM_COLUMNS = {
    "Name": "order_number",
    "Lineitem sku": "sku",
    "Lineitem name": "product_name",
    "Lineitem quantity": "quantity",
    "Lineitem price": "unit_price",
}

MONEY_COLUMNS = ["subtotal", "discount_amount", "shipping", "taxes", "total", "refunded_amount"]


def _clean_text(df: pd.DataFrame) -> pd.DataFrame:
    """Trim spaces in every text column and turn empty strings into missing values."""
    for col in df.columns:
        df[col] = df[col].str.strip().replace("", pd.NA)
    return df


def transform_orders(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = _clean_text(raw.copy())

    # 1. Remove exact duplicate rows (e.g. the same file exported twice)
    before = len(df)
    df = df.drop_duplicates(subset=[c for c in df.columns if c != "source_file"])
    if before != len(df):
        log.warning("Removed %d duplicate rows", before - len(df))

    # 2. ORDERS: keep only the first row of each order (the one with order-level data)
    orders = df[df["Created at"].notna()][list(ORDER_COLUMNS)].rename(columns=ORDER_COLUMNS)
    orders = orders.drop_duplicates(subset="order_number", keep="last")

    orders["customer_email"] = orders["customer_email"].str.lower()
    for col in ("created_at", "paid_at"):
        orders[col] = pd.to_datetime(orders[col], utc=True, errors="coerce").dt.tz_convert("Asia/Manila")
    for col in MONEY_COLUMNS:
        orders[col] = pd.to_numeric(orders[col], errors="coerce").fillna(0.0)
    orders["fulfillment_status"] = orders["fulfillment_status"].fillna("unfulfilled")
    orders["net_sales"] = (orders["total"] - orders["refunded_amount"]).round(2)
    orders["order_date"] = orders["created_at"].dt.date.astype(str)
    orders["order_month"] = orders["created_at"].dt.strftime("%Y-%m")

    # 3. ORDER ITEMS: every row is a line item
    items = df[list(ITEM_COLUMNS)].rename(columns=ITEM_COLUMNS)
    items = items.drop_duplicates()
    items["quantity"] = pd.to_numeric(items["quantity"], errors="coerce").fillna(0).astype(int)
    items["unit_price"] = pd.to_numeric(items["unit_price"], errors="coerce").fillna(0.0)
    items["line_total"] = (items["quantity"] * items["unit_price"]).round(2)

    # 4. Data quality checks: report problems instead of hiding them
    missing = orders["created_at"].isna().sum()
    if missing:
        log.warning("%d orders have an unreadable 'Created at' date", missing)
    orphans = ~items["order_number"].isin(orders["order_number"])
    if orphans.any():
        log.warning("%d line items have no matching order and were dropped", orphans.sum())
        items = items[~orphans]

    # SQLite has no timezone type, so store dates as readable text
    for col in ("created_at", "paid_at"):
        orders[col] = orders[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    log.info("Transformed into %d orders and %d line items", len(orders), len(items))
    return orders.reset_index(drop=True), items.reset_index(drop=True)
