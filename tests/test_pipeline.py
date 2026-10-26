"""Pipeline tests. Run from the project folder with: python -m pytest"""

from datetime import date, datetime, timezone

import duckdb
import pytest

from pipeline.run import fetch_with_retries, run
from pipeline.sources import MockSource, SourceUnavailableError, TweetSource

DB_FILE = "data/curated.duckdb"


def first_value(sql: str):
    """Run a query on the curated database and return the first value of the first row."""
    con = duckdb.connect(DB_FILE)
    value = con.execute(sql).fetchone()[0]
    con.close()
    return value


def output_value(column: str, tweet_id: str):
    """Return one column of one tweet in the output (curated) table."""
    return first_value(f"SELECT {column} FROM curated_tweets WHERE tweet_id = '{tweet_id}'")


# ---------- Robustness: one status per day ----------

def test_each_day_gets_the_right_status():
    """Days 22 and 25 fail (no fixture / missing required field); the other days still run."""
    run(date(2026, 10, 20), date(2026, 10, 25), "full", MockSource("tests/fixtures"))

    con = duckdb.connect(DB_FILE)
    statuses = con.execute(
        "SELECT run_date, status FROM run_registry "
        "WHERE run_id = (SELECT max(run_id) FROM run_registry) "
        "ORDER BY run_date"
    ).fetchall()
    con.close()

    assert statuses == [
        (date(2026, 10, 20), "success"),  # J1
        (date(2026, 10, 21), "success"),  # J2: no optional fields at all
        (date(2026, 10, 22), "failed"),   # J3: no fixture file
        (date(2026, 10, 23), "empty"),    # J4: no tweets
        (date(2026, 10, 24), "success"),  # J5: missing author, reply, no hashtags
        (date(2026, 10, 25), "failed"),   # J6: tweet without created_at
    ]


# ---------- Output values ----------

def test_output_fields():
    """The output values match what we know about each fixture tweet."""
    run(date(2026, 10, 20), date(2026, 10, 25), "full", MockSource("tests/fixtures"))

    # J1 (day 20): retweet, quote, user without location, same user twice
    assert output_value("is_retweet", "1849001000000000002") == True
    assert output_value("is_retweet", "1849001000000000003") == False  # a quote is not a retweet
    assert output_value("location", "1849001000000000002") is None
    assert output_value("anonymized_user_id", "1849001000000000001") == output_value(
        "anonymized_user_id", "1849001000000000003"
    )

    # J5 (day 24): author missing from includes.users, reply, tweet without hashtags
    assert output_value("follower_count", "1849005000000000001") is None
    assert output_value("anonymized_user_id", "1849005000000000001") is not None
    assert output_value("is_retweet", "1849005000000000002") == False  # a reply is not a retweet
    assert output_value("hashtags", "1849005000000000003") == []

    # J6 (day 25): the failed day leaves nothing in curated
    assert first_value("SELECT count(*) FROM curated_tweets WHERE day = '2026-10-25'") == 0


# ---------- Fault tolerance ----------

def test_reloading_a_day_does_not_duplicate():
    """Loading the same day twice leaves the same rows (idempotency)."""
    run(date(2026, 10, 20), date(2026, 10, 20), "full", MockSource("tests/fixtures"))
    run(date(2026, 10, 20), date(2026, 10, 20), "full", MockSource("tests/fixtures"))

    assert first_value("SELECT count(*) FROM curated_tweets WHERE day = '2026-10-20'") == 3


def test_reprocess_without_raw_fails():
    """J3: reprocessing a day that has no raw file fails with a clear status."""
    run(date(2026, 10, 22), date(2026, 10, 22), "reprocess", MockSource("tests/fixtures"))

    status = first_value(
        "SELECT status FROM run_registry "
        "WHERE run_date = '2026-10-22' AND mode = 'reprocess' "
        "ORDER BY finished_at DESC LIMIT 1"
    )
    assert status == "failed"


# ---------- Source unavailability: retries ----------

class FlakySource(TweetSource):
    """A fake source that fails once with a temporary error, then works."""

    def __init__(self):
        self.calls = 0

    def fetch(self, start: datetime, end: datetime) -> dict:
        self.calls = self.calls + 1
        if self.calls == 1:
            raise SourceUnavailableError("timeout")
        return {"meta": {"result_count": 0}}


class AlwaysDownSource(TweetSource):
    """A fake source that is always temporarily unavailable."""

    def __init__(self):
        self.calls = 0

    def fetch(self, start: datetime, end: datetime) -> dict:
        self.calls = self.calls + 1
        raise SourceUnavailableError("timeout")


# Any one-day window works: the fake sources ignore start and end
START = datetime(2026, 10, 20, tzinfo=timezone.utc)
END = datetime(2026, 10, 21, tzinfo=timezone.utc)


def test_temporary_error_is_retried():
    """The first call fails with a temporary error; the retry succeeds."""
    source = FlakySource()

    response = fetch_with_retries(source, START, END)

    assert source.calls == 2
    assert response == {"meta": {"result_count": 0}}


def test_temporary_error_gives_up_after_three_attempts():
    """If the source stays down, the error goes up after 3 attempts."""
    source = AlwaysDownSource()

    with pytest.raises(SourceUnavailableError):
        fetch_with_retries(source, START, END)

    assert source.calls == 3