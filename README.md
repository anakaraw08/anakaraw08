# Shopify Orders ETL Pipeline

A Python ETL pipeline that turns raw Shopify order exports into clean, query-ready tables in **SQLite** or **SQL Server**.

```
data/raw/*.csv|xlsx  ──►  Extract  ──►  Transform  ──►  Load  ──►  SQLite / SQL Server
                          (pandas)      (clean, split)   (SQLAlchemy)
```

## What it does

| Stage | File | Details |
|---|---|---|
| **Extract** | `etl/extract.py` | Reads every `orders_export*` CSV/Excel file in `data/raw`, all as text, tagging each row with its source file |
| **Transform** | `etl/transform.py` | Removes duplicate rows, trims and lowercases emails, parses dates to Asia/Manila time, converts money fields, and splits Shopify's one-row-per-line-item export into `orders` and `order_items` tables. Logs data-quality warnings instead of hiding them |
| **Load** | `etl/load.py` | Writes both tables and creates two summary views, `monthly_sales` and `top_products`. The target database is chosen in `.env` |
| **Run** | `run_pipeline.py` | Runs E → T → L with logging to the console and `logs/` |

## Output

- `orders`: one row per order (status, totals, net sales after refunds, shipping location, order month)
- `order_items`: one row per product in an order (SKU, quantity, unit price, line total)
- `monthly_sales` view: orders, net sales, and average order value per month
- `top_products` view: units sold and revenue per SKU

## Setup (Windows)

```powershell
git clone <this-repo-url>
cd <repo-folder>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
python run_pipeline.py
```

By default, data loads into `data/output/shop.db` (SQLite). To load into SQL Server, create the database (`CREATE DATABASE ShopETL;`), set `LOAD_TARGET=sqlserver` and your server name in `.env`, and install the Microsoft ODBC Driver 18 for SQL Server.

## Sample data

`data/raw/orders_export.csv` contains **synthetic** orders (fake names, `example.com` emails) in Shopify's export format, with realistic issues included on purpose: a duplicate row, inconsistent email formatting, and order fields that appear only on the first line item.

## Roadmap

- [x] CSV/Excel → SQLite / SQL Server
- [ ] Incremental loading (upsert + processed-file tracking)
- [ ] Database source
- [ ] Web API source
- [ ] Shopify Admin API source
- [ ] Scheduled runs with Windows Task Scheduler

## Tech

Python · pandas · SQLAlchemy · pyodbc · SQLite · SQL Server
