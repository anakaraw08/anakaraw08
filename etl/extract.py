"""EXTRACT: read raw files into pandas DataFrames, without changing anything."""
from pathlib import Path
import logging

import pandas as pd

log = logging.getLogger(__name__)


def extract_file(path: Path) -> pd.DataFrame:
    """Read one CSV or Excel file. Everything is read as text so nothing is
    silently converted; the Transform step decides the real data types."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        raise ValueError(f"Unsupported file type: {path.name}")

    df["source_file"] = path.name  # remember where each row came from
    log.info("Extracted %d rows from %s", len(df), path.name)
    return df


def extract_folder(folder: Path, pattern: str = "orders_export*") -> pd.DataFrame:
    """Read every matching CSV/Excel file in a folder and stack them together."""
    files = sorted(p for p in folder.glob(pattern) if p.suffix.lower() in (".csv", ".xlsx", ".xls"))
    if not files:
        raise FileNotFoundError(f"No files matching '{pattern}' in {folder}")
    return pd.concat([extract_file(p) for p in files], ignore_index=True)
