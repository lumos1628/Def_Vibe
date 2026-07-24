from datetime import datetime, timezone
import json
import sqlite3
from database import Database

class MatchRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert(self, match_id: int, hero_id: int, played_at: str, steam_account_id: int) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO rampage_matches (match_id, hero_id, played_at, steam_account_id, extracted_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(hero_id, match_id) DO UPDATE SET
                    played_at=excluded.played_at,
                    steam_account_id=excluded.steam_account_id,
                    extracted_at=excluded.extracted_at
                RETURNING id;
                """,
                (match_id, hero_id, played_at, steam_account_id, now),
            )
            return cursor.fetchone() is not None

    def exists_for_hero(self, match_id: int, hero_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM rampage_matches WHERE match_id = ? AND hero_id = ?",
                (match_id, hero_id),
            )
            return cursor.fetchone() is not None

    def count_by_hero(self, hero_id: int) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM rampage_matches WHERE hero_id = ?",
                (hero_id,),
            )
            return cursor.fetchone()[0]

    def list_all(self) -> list[dict]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT rm.match_id, rm.hero_id, h.display_name AS hero_name,
                       rm.played_at, rm.steam_account_id, rm.extracted_at
                FROM rampage_matches rm
                JOIN heroes h ON h.id = rm.hero_id
                ORDER BY rm.played_at DESC;
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def count(self) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM rampage_matches")
            return cursor.fetchone()[0]

    def list_unparsed(self, limit: int | None = None) -> list[int]:
        with self.db.get_connection() as conn:
            sql = """
                SELECT DISTINCT match_id
                FROM rampage_matches
                WHERE parsed = 0
                ORDER BY match_id
            """
            params = ()
            if limit is not None:
                sql += " LIMIT ?"
                params = (limit,)
            cursor = conn.execute(sql, params)
            return [row[0] for row in cursor.fetchall()]

    def mark_parsed(self, match_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE rampage_matches SET parsed = 1 WHERE match_id = ?",
                (match_id,),
            )

    def save_match_details(self, match_id: int, opendota_data: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO match_details (match_id, opendota_data, parsed_at)
                VALUES (?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    opendota_data=excluded.opendota_data,
                    parsed_at=excluded.parsed_at;
                """,
                (match_id, json.dumps(opendota_data), now),
            )

    def get_match_details(self, match_id: int) -> dict | None:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT opendota_data FROM match_details WHERE match_id = ?",
                (match_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return json.loads(row[0])
