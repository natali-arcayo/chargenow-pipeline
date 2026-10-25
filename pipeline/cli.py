import argparse
from datetime import date

from pipeline.run import run
from pipeline.sources import MockSource


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest #ChargeNow tweets for a range of UTC days.")
    parser.add_argument("--start", required=True, help="First UTC day, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Last UTC day (included), YYYY-MM-DD")
    parser.add_argument("--mode", choices=["full", "reprocess"], default="full")
    args = parser.parse_args()

    run(
        date.fromisoformat(args.start),
        date.fromisoformat(args.end),
        args.mode,
        MockSource("tests/fixtures"),
    )


if __name__ == "__main__":
    main()