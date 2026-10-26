"""Command-line entry point."""

import argparse
from datetime import date

from pipeline.run import run
from pipeline.sources import MockSource


def main() -> None:
    """Read the command-line arguments and start the run."""
    parser = argparse.ArgumentParser(description="Ingest #ChargeNow tweets for a range of UTC days.")
    parser.add_argument("--start", required=True, help="First UTC day, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Last UTC day (included), YYYY-MM-DD")
    parser.add_argument("--mode", choices=["full", "reprocess"], default="full")
    args = parser.parse_args()

    run(
        date.fromisoformat(args.start),
        date.fromisoformat(args.end),
        args.mode,
        MockSource("tests/fixtures"),  # the only source for now; the real API would be another object TweetSource here
    )


if __name__ == "__main__":
    main()