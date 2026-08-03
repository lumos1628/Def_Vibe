from datetime import datetime, timezone
import sqlite3
from typing import Iterable
from database import Database

class HeroRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, heroes: Iterable[dict]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (h["id"], h["displayName"], h.get("shortName", ""), now)
            for h in heroes
        ]
        with self.db.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO heroes (id, display_name, short_name, synced_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    display_name=excluded.display_name,
                    short_name=excluded.short_name,
                    synced_at=excluded.synced_at;
                """,
                rows,
            )

    def list_all(self) -> list[dict]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT id, display_name, short_name FROM heroes ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]

    def count(self) -> int:
        return self.db.count_heroes()
