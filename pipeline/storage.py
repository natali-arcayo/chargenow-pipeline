import json
from datetime import date, datetime, timezone
from pathlib import Path

def save_raw(day: date, response: dict, run_id: str) -> None:
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

def load_raw(day: date) -> dict:
    file = Path("data/raw") / f"date={day}" / "response.json"
    with open (file, encoding="utf-8") as f:
        return json.load(f)