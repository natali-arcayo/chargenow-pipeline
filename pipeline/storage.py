"""Raw layer: one JSON file per UTC day."""

import json
from datetime import date, datetime, timezone
from pathlib import Path

def save_raw(day: date, response: dict, run_id: str) -> None:
    """Save one day's API response to data/raw/date=<day>/response.json, wrapped in an envelope with run metadata.

    Writes to a .tmp file first and then renames it, so a crash while writing never leaves a half-written file.
    """
    folder = Path("data/raw") / f"date={day}"
    folder.mkdir(parents=True, exist_ok=True)

    envelope = {
        "run_id": run_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "day": str(day),
        "response": response,
    }

    tmp_file = folder / "response.json.tmp"
    final_file = folder / "response.json"

    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2)

    tmp_file.replace(final_file)