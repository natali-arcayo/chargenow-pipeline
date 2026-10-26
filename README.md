# chargenow-pipeline

Tweet ingestion pipeline for #ChargeNow (DCS Data Engineering challenge, Part B).

```
mock source (X API v2 structure) ──► raw: one JSON per UTC day ──► curated: DuckDB table, one row per tweet
                                    data/raw/date=YYYY-MM-DD/        data/curated.duckdb
```

Python orchestrates; the transformation is SQL in DuckDB. Each run writes one row per day to `run_registry` (status, rows, error).

## How to run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "import secrets; print('ANON_SALT=' + secrets.token_hex(32))" > .env   # secret key for the user id hash

python -m pipeline.cli --start 2026-10-20 --end 2026-10-25 --mode full        # source → raw → curated
python -m pipeline.cli --start 2026-10-20 --end 2026-10-25 --mode reprocess   # raw → curated only
python -m pytest -v
```

Days are UTC and both included. Logs go to the console and `logs/<run_id>.log`.

## Robustness

- **Empty results:** a day with no tweets is `empty`, not an error.
- **API changes:** the schema is declared, not inferred. Missing optional fields become `NULL`; a missing required field (`id`, `created_at`, `author_id`) fails the day before curated is touched.
- **Source unavailability:** temporary errors are retried (3 attempts); after that the day is `failed` and the run moves on.
- **Fault tolerance:** each day is overwritten in one transaction, so any range can be rerun without duplicates. `reprocess` rebuilds curated from raw.
- **Scalability:** days are independent partitions. Not tested with large volumes.

## Changes from the design document

- The CLI takes UTC days instead of timestamps.
- No scheduler: Airflow or another orchestrator would call the CLI with yesterday's date.
- Raw keeps the response unchanged, inside an envelope with `run_id` and `fetched_at`.
- The user id is a SHA-256 with a secret key (pseudonymisation, not full anonymisation).
- Curated has three more columns than the seven requested: `day`, `run_id`, `tweet_id`.

## Tests

One fixture per day in `tests/fixtures/`, 20–25 Oct: normal day, day without optional fields, missing file, empty day, author missing from `includes.users`, tweet without `created_at`. Plus idempotency, reprocess without raw, and retries.

Limitation: the tests write to the same `data/` folder as the pipeline, so running them overwrites the actual results with the test results. They also need the `.env` file with the key. With more time, each test would use its own temporary folder.