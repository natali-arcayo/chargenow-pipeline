"""Tweet sources: the contract (TweetSource) and the mock implementation (MockSource)."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class SourceError(Exception):
    """Base class for all source errors."""


class SourceUnavailableError(SourceError):
    """Temporary problem (timeout, 503, rate limit). Worth retrying."""


class SourcePermanentError(SourceError):
    """Permanent problem (bad credentials, bad request, missing data). Retrying won't help."""


class TweetSource(ABC):
    """Contract every tweet source must follow (mock today, real X API later)."""

    @abstractmethod
    def fetch(self, start: datetime, end: datetime) -> dict:
        """Return the API response for the window [start, end) as a dict in X API v2 structure."""


class MockSource(TweetSource):
    """Reads one JSON file per day from a folder, e.g. 2026-10-20.json."""

    def __init__(self, fixtures_dir: str):
        self.fixtures_dir = Path(fixtures_dir)

    def fetch(self, start: datetime, end: datetime) -> dict:
        file_path = self.fixtures_dir / f"{start:%Y-%m-%d}.json"

        if not file_path.exists():
            raise SourcePermanentError(f"No fixture file for {start:%Y-%m-%d}")

        with open(file_path, encoding="utf-8") as f:
            return json.load(f)