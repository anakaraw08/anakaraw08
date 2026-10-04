"""Run the whole pipeline:  python run_pipeline.py"""
from datetime import datetime
from pathlib import Path
import logging
import sys

from dotenv import load_dotenv

from etl.extract import extract_folder
from etl.transform import transform_orders
from etl.load import get_engine, load_table, create_views

BASE = Path(__file__).resolve().parent
RAW_DIR = BASE / "data" / "raw"
DB_PATH = BASE / "data" / "output" / "shop.db"
LOG_DIR = BASE / "logs"

load_dotenv(BASE / ".env")  # reads LOAD_TARGET, SQL_SERVER, etc. from the .env file


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"pipeline_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )


def main() -> int:
    setup_logging()
    log = logging.getLogger("pipeline")
    log.info("=== Pipeline started ===")
    try:
        raw = extract_folder(RAW_DIR)                 # E
        orders, items = transform_orders(raw)         # T
        engine = get_engine(DB_PATH)                  # L
        load_table(orders, "orders", engine)
        load_table(items, "order_items", engine)
        create_views(engine)
    except Exception:
        log.exception("Pipeline FAILED")
        return 1
    log.info("=== Pipeline finished OK ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
