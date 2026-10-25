import os
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv

from pipeline.sources import TweetSource
from pipeline.storage import save_raw
from pipeline.transform import transform_day
from pipeline.registry import record


def run(first_day: date, last_day: date, mode: str, source: TweetSource) -> None:
    """Process every UTC day from first_day to last_day (both included)."""
    if mode not in ("full", "reprocess"):
        raise ValueError(f"Unknown mode: {mode}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    load_dotenv()  # Reads .env and loads its lines as environment variables
    anon_key = os.environ["ANON_SALT"]  # Reads the environment variable ANON_SALT

    day = first_day
    while day <= last_day:
        try:
            if mode == "full":
                window_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
                window_end = window_start + timedelta(days=1)
                response = source.fetch(window_start, window_end)
                save_raw(day, response, run_id)

            rows = transform_day(day, run_id, anon_key)
            if rows > 0:
                status = "success"
            else:
                status = "empty"
            print(f"{day}: {status} ({rows} rows)")
            record(run_id, day, mode, status, rows, None)
            
        except Exception as error:
            print(f"{day}: failed - {error}")
            record(run_id, day, mode, "failed", None, str(error))
        day = day + timedelta(days=1)