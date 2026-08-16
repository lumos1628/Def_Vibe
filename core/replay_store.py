import json
from datetime import datetime, timezone
from pathlib import Path

from config import Config


class ReplayStore:
    """Store raw OpenDota match JSON as one file per match.

    Files are sharded by match date (UTC) under `data/replays/`:

        data/replays/2026-08-11/{match_id}.json

    This keeps SQLite as a lightweight index instead of a giant blob store.
    """

    def __init__(self, root: Path = Config.REPLAY_DATA_DIR) -> None:
        self.root = root

    @staticmethod
    def match_date(data: dict) -> str:
        """Return the match date (YYYY-MM-DD) derived from `start_time`, UTC."""
        start_time = data.get("start_time")
        if start_time is None:
            return "unknown"
        try:
            return datetime.fromtimestamp(int(start_time), tz=timezone.utc).date().isoformat()
        except (ValueError, TypeError, OverflowError):
            return "unknown"

    def path_for(self, match_id: int, data: dict) -> Path:
        """Build the file path for a match without writing anything."""
        return self.root / self.match_date(data) / f"{match_id}.json"

    def save(self, match_id: int, data: dict) -> Path:
        """Atomically write the match JSON to disk and return its path."""
        path = self.path_for(match_id, data)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(path)
        return path

    def load(self, path: Path) -> dict | None:
        """Load the match JSON from disk; None if missing or invalid."""
        if path is None or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def delete(self, path: Path | None) -> None:
        """Remove a match file and prune any empty parent directories."""
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
            current = path.parent
            while current != self.root and current != current.parent:
                try:
                    current.rmdir()
                except OSError:
                    break
                current = current.parent
        except OSError:
            pass
