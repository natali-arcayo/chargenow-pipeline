"""Run registry: one row per day per run."""

from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

from pipeline.transform import DB_FILE


def record(run_id: str, day: date, mode: str, status: str, rows_loaded: int | None, error_message: str | None) -> None:
    """Add one row to the run registry: one day processed by one run."""
    con = duckdb.connect(DB_FILE)
    try:
        con.execute(Path("sql/create_tables.sql").read_text(encoding="utf-8"))
        con.execute(
            "INSERT INTO run_registry "
            "(run_id, run_date, mode, status, rows_loaded, finished_at, error_message) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [run_id, day, mode, status, rows_loaded, datetime.now(timezone.utc), error_message],
        )
    finally:
        con.close()