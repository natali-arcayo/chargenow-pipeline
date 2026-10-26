import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from pipeline.registry import record
from pipeline.sources import SourceUnavailableError, TweetSource
from pipeline.storage import save_raw
from pipeline.transform import transform_day


WAIT_SECONDS = [2, 4]  # waits between attempts: 3 attempts in total

def setup_logging(run_id: str) -> None:
    """Log to the console and to logs/<run_id>.log, with times in UTC."""
    Path("logs").mkdir(exist_ok=True)
    logging.Formatter.converter = time.gmtime  # log times in UTC

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s UTC %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),                    # console
            logging.FileHandler(f"logs/{run_id}.log"),  # file, one per run
        ],
    )

def fetch_with_retries(source: TweetSource, start: datetime, end: datetime) -> dict:
    """Call source.fetch; on a temporary error, wait and try again."""
    for wait in WAIT_SECONDS:
        try:
            return source.fetch(start, end)
        except SourceUnavailableError as error:
            logging.warning(f"Source unavailable: {error}. Retrying in {wait} s")
            time.sleep(wait)
    return source.fetch(start, end)  # last attempt: if it fails, the error goes up to run()

def run(first_day: date, last_day: date, mode: str, source: TweetSource) -> None:
    """Process every UTC day from first_day to last_day (both included)."""
    if mode not in ("full", "reprocess"):
        raise ValueError(f"Unknown mode: {mode}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    setup_logging(run_id)
    # The run id goes in this first message as the console doesn't show the log file name
    logging.info(f"Run {run_id} started: {first_day} to {last_day}, mode={mode}")

    load_dotenv()  # Reads .env and loads its lines as environment variables
    anon_key = os.environ["ANON_SALT"]  # Reads the environment variable ANON_SALT

    day = first_day
    while day <= last_day:
        try:
            if mode == "full":
                window_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
                window_end = window_start + timedelta(days=1)
                response = fetch_with_retries(source, window_start, window_end)
                save_raw(day, response, run_id)

            rows = transform_day(day, run_id, anon_key)
            if rows > 0:
                status = "success"
            else:
                status = "empty"
            logging.info(f"{day}: {status} ({rows} rows)")
            record(run_id, day, mode, status, rows, None)
            
        except Exception as error:
            logging.error(f"{day}: failed - {error}")
            record(run_id, day, mode, "failed", None, str(error))
        day = day + timedelta(days=1)
    logging.info(f"Run {run_id} finished")