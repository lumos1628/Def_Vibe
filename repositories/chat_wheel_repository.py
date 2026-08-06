from datetime import datetime, timezone
from typing import Iterable
import sqlite3
from database import Database


class ChatWheelRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, entries: Iterable[dict]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for entry in entries:
            rows.append(
                (
                    int(entry["id"]),
                    entry.get("name", ""),
                    entry.get("label", ""),
                    entry.get("message", ""),
                    1 if entry.get("all_chat") else 0,
                    now,
                )
            )
        with self.db.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO chat_wheels (id, name, label, message, all_chat, synced_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    label=excluded.label,
                    message=excluded.message,
                    all_chat=excluded.all_chat,
                    synced_at=excluded.synced_at;
                """,
                rows,
            )

    def get_by_id(self, chat_wheel_id: int) -> dict | None:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, name, label, message, all_chat FROM chat_wheels WHERE id = ?",
                (chat_wheel_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    def count(self) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chat_wheels")
            return cursor.fetchone()[0]


