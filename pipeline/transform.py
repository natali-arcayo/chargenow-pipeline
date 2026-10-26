"""Raw to curated: validate one day and replace it in DuckDB."""

import logging
from datetime import date
from pathlib import Path

import duckdb

DB_FILE = "data/curated.duckdb"


def transform_day(day: date, run_id: str, anon_key: str) -> int:
    """Rebuild the curated rows of one day from its raw file. Returns the rows loaded."""
    raw_file = Path("data/raw") / f"date={day}" / "response.json"
    if not raw_file.exists():
        raise FileNotFoundError(f"No raw data for {day}")
    
    query = Path("sql/curated_tweets.sql").read_text(encoding="utf-8")
    query = query.replace("{raw_path}", str(raw_file))
    params = {"day": day, "run_id": run_id, "anon_key": anon_key}

    con = duckdb.connect(DB_FILE)
    try:
        con.execute("SET TimeZone = 'UTC'")
        con.execute(Path("sql/create_tables.sql").read_text(encoding="utf-8"))

        # Validation: every tweet must have the mandatory fields
        not_valid_row_count = con.execute(
            f"SELECT count(*) FROM (\n{query}\n) "
            "WHERE tweet_id IS NULL OR created_at IS NULL OR anonymized_user_id IS NULL",
            params
            ).fetchone()[0]
        if not_valid_row_count > 0:
            raise ValueError(f"{not_valid_row_count} tweets with missing required fields on {day}")

        # Replace the day: all or nothing
        con.execute("BEGIN TRANSACTION")
        con.execute("DELETE FROM curated_tweets WHERE day = ?", [day])
        con.execute(
            f"INSERT INTO curated_tweets "
            "(day, run_id, tweet_id, anonymized_user_id, created_at, location, follower_count, tweet_count, hashtags, is_retweet) "
            f"SELECT * FROM (\n{query}\n)",
            params
            )
        con.execute("COMMIT")
        
        # A NULL follower_count means the author from includes.users was missing:
        # curated does not have includes.users.id (only the hash of data.author_id),
        # since location is optional, only follower_count or tweet_count can be used.        
        missing_user_row_count = con.execute(
            "SELECT count(*) FROM curated_tweets WHERE day = ? AND follower_count IS NULL", [day]
            ).fetchone()[0]
        if missing_user_row_count > 0:
            logging.warning(f"{day}: {missing_user_row_count} tweets without user data (kept with NULL user fields)")

        return con.execute("SELECT count(*) FROM curated_tweets WHERE day = ?", [day]).fetchone()[0]
    finally:
        con.close()