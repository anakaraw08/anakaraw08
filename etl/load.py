"""LOAD: write the cleaned tables into a database (SQLite or SQL Server)."""
from pathlib import Path
import logging
import os

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

log = logging.getLogger(__name__)


def get_engine(sqlite_path: Path):
    """Pick the destination from the LOAD_TARGET setting in your .env file.
    LOAD_TARGET=sqlite     -> data/output/shop.db (default)
    LOAD_TARGET=sqlserver  -> the SQL Server database in SQL_SERVER / SQL_DATABASE
    """
    target = os.getenv("LOAD_TARGET", "sqlite").strip().lower()

    if target == "sqlserver":
        server = os.environ["SQL_SERVER"]          # e.g. localhost\SQLEXPRESS
        database = os.environ["SQL_DATABASE"]      # e.g. ShopETL
        driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
        user = os.getenv("SQL_USER", "").strip()

        conn = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};TrustServerCertificate=yes;"
        if user:   # SQL Server login (username + password)
            conn += f"UID={user};PWD={os.environ['SQL_PASSWORD']};"
        else:      # Windows login (the same account you use in SSMS)
            conn += "Trusted_Connection=yes;"

        url = URL.create("mssql+pyodbc", query={"odbc_connect": conn})
        log.info("Load target: SQL Server %s / %s", server, database)
        return create_engine(url, fast_executemany=True)

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    log.info("Load target: SQLite %s", sqlite_path)
    return create_engine(f"sqlite:///{sqlite_path}")


def load_table(df: pd.DataFrame, table: str, engine) -> None:
    """Full refresh: replace the table with the new data.
    (In Step 6 we'll switch to loading only new/changed records.)"""
    df.to_sql(table, engine, if_exists="replace", index=False, chunksize=500)
    log.info("Loaded %d rows into table '%s'", len(df), table)


# Written in SQL that works on both SQLite and SQL Server
# (views can't contain ORDER BY in SQL Server, so sort when you query them).
VIEWS = {
    "monthly_sales": """
        SELECT order_month,
               COUNT(*)                 AS orders,
               ROUND(SUM(net_sales), 2) AS net_sales,
               ROUND(AVG(net_sales), 2) AS avg_order_value
        FROM orders
        WHERE payment_status <> 'pending'
        GROUP BY order_month
    """,
    "top_products": """
        SELECT sku, product_name,
               SUM(quantity)             AS units_sold,
               ROUND(SUM(line_total), 2) AS revenue
        FROM order_items
        GROUP BY sku, product_name
    """,
}


def create_views(engine) -> None:
    """Ready-made summary queries you can open in SSMS or DB Browser."""
    for name, sql in VIEWS.items():
        with engine.begin() as conn:
            conn.execute(text(f"DROP VIEW IF EXISTS {name}"))
        with engine.begin() as conn:   # SQL Server needs CREATE VIEW in its own batch
            conn.execute(text(f"CREATE VIEW {name} AS {sql}"))
    log.info("Created views: %s", ", ".join(VIEWS))
