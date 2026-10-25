from datetime import date
from pathlib import Path

import duckdb

DB_FILE = "data/curated.duckdb"


def transform_day(day: date, run_id: str, anon_key: str) -> int:
    """Rebuild the curated rows of one day from its raw file. Returns the rows loaded."""
    raw_file = Path("data/raw") / f"date={day}" / "response.json"
    query = Path("sql/curated_tweets.sql").read_text(encoding="utf-8")
    query = query.replace("{raw_path}", str(raw_file))
    params = {"day": day, "run_id": run_id, "anon_key": anon_key}

    con = duckdb.connect(DB_FILE)
    try:
        con.execute("SET TimeZone = 'UTC'")
        con.execute(Path("sql/create_tables.sql").read_text(encoding="utf-8"))

        # Validation: every tweet must have its required fields
        missing = con.execute(
            f"SELECT count(*) FROM (\n{query}\n) "
            "WHERE tweet_id IS NULL OR created_at IS NULL OR anonymized_user_id IS NULL",
            params
            ).fetchone()[0]
        if missing > 0:
            raise ValueError(f"{missing} tweets with missing required fields on {day}")

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

        return con.execute("SELECT count(*) FROM curated_tweets WHERE day = ?", [day]).fetchone()[0]
    finally:
        con.close()