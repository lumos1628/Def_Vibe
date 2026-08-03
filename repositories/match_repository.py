from datetime import datetime, timedelta, timezone
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

    @staticmethod
    def has_replay_data(opendota_data: dict) -> bool:
        players = opendota_data.get("players") or []
        has_kills_log = any(
            isinstance(player.get("kills_log"), list) and len(player["kills_log"]) > 0
            for player in players
        )
        has_chat = isinstance(opendota_data.get("chat"), list) and len(opendota_data["chat"]) > 0
        return has_kills_log or has_chat

    def list_unparsed(self, limit: int | None = None) -> list[int]:
        with self.db.get_connection() as conn:
            sql = """
                SELECT DISTINCT match_id
                FROM rampage_matches
                WHERE parse_status IN ('pending', 'queued', 'parsing')
                  AND unparseable = 0
                  AND has_replay_data = 0
                ORDER BY data_verified ASC, match_id
            """
            params = ()
            if limit is not None:
                sql += " LIMIT ?"
                params = (limit,)
            cursor = conn.execute(sql, params)
            return [row[0] for row in cursor.fetchall()]

    def get_parse_state(self, match_id: int) -> dict:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT data_verified, parse_status, unparseable, has_replay_data
                FROM rampage_matches
                WHERE match_id = ?
                LIMIT 1
                """,
                (match_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return {
                    "data_verified": False,
                    "parse_status": "pending",
                    "unparseable": False,
                    "has_replay_data": False,
                }
            return {
                "data_verified": bool(row[0]),
                "parse_status": row[1] or "pending",
                "unparseable": bool(row[2]),
                "has_replay_data": bool(row[3]),
            }

    def mark_data_verified(self, match_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE rampage_matches
                SET data_verified = 1
                WHERE match_id = ?
                """,
                (match_id,),
            )

    def list_queued(self) -> list[tuple[int, str]]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT match_id, parse_job_id
                FROM rampage_matches
                WHERE parse_status IN ('queued', 'parsing')
                  AND parse_job_id IS NOT NULL
                  AND has_replay_data = 0
                  AND unparseable = 0
                ORDER BY match_id
                """
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]

    def update_parse_status(
        self,
        match_id: int,
        status: str,
        job_id: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            if job_id is not None:
                conn.execute(
                    """
                    UPDATE rampage_matches
                    SET parse_status = ?,
                        parse_job_id = ?,
                        last_parse_attempt_at = ?
                    WHERE match_id = ?
                    """,
                    (status, job_id, now, match_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE rampage_matches
                    SET parse_status = ?,
                        last_parse_attempt_at = ?
                    WHERE match_id = ?
                    """,
                    (status, now, match_id),
                )

    def mark_parse_requested(self, match_id: int, job_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE rampage_matches
                SET parse_requested_at = ?,
                    parse_request_count = parse_request_count + 1,
                    parse_job_id = ?,
                    parse_status = 'queued',
                    last_parse_attempt_at = ?,
                    data_verified = 1
                WHERE match_id = ?
                """,
                (now, job_id, now, match_id),
            )

    def mark_parsed(
        self,
        match_id: int,
        has_replay_data: bool = False,
        unparseable: bool = False,
    ) -> None:
        status = "done" if has_replay_data else ("failed" if unparseable else "pending")
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE rampage_matches
                SET parsed = 1,
                    has_replay_data = ?,
                    unparseable = ?,
                    parse_status = ?,
                    data_verified = 1
                WHERE match_id = ?
                """,
                (1 if has_replay_data else 0, 1 if unparseable else 0, status, match_id),
            )

    def save_match_details(self, match_id: int, opendota_data: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        has_replay = self.has_replay_data(opendota_data)
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
            conn.execute(
                """
                UPDATE rampage_matches
                SET has_replay_data = ?,
                    parse_status = ?,
                    data_verified = 1
                WHERE match_id = ?
                """,
                (1 if has_replay else 0, "done" if has_replay else "pending", match_id),
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

    def get_hero_ids_for_match(self, match_id: int) -> list[int]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT hero_id FROM rampage_matches WHERE match_id = ?",
                (match_id,),
            )
            return [row[0] for row in cursor.fetchall()]

    def list_all_match_details(self) -> list[tuple[int, dict]]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT match_id, opendota_data FROM match_details ORDER BY match_id"
            )
            return [(row["match_id"], json.loads(row["opendota_data"])) for row in cursor.fetchall()]

    def list_matches_to_export(self, today_iso: str) -> list[tuple[int, dict, bool, bool]]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT md.match_id, md.opendota_data,
                       MAX(rm.has_replay_data) AS has_replay_data,
                       MAX(rm.unparseable) AS unparseable
                FROM match_details md
                JOIN rampage_matches rm ON rm.match_id = md.match_id
                WHERE md.parsed_at LIKE ? || '%'
                  AND md.match_id NOT IN (
                      SELECT match_id FROM export_log
                  )
                GROUP BY md.match_id
                ORDER BY md.match_id
                """,
                (today_iso,),
            )
            return [
                (
                    row["match_id"],
                    json.loads(row["opendota_data"]),
                    bool(row["has_replay_data"]),
                    bool(row["unparseable"]),
                )
                for row in cursor.fetchall()
            ]

    def mark_exported(self, match_id: int, exported_at: str, output_path: str) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO export_log (match_id, exported_at, output_path)
                VALUES (?, ?, ?)
                ON CONFLICT(match_id) DO NOTHING
                """,
                (match_id, exported_at, output_path),
            )

    def clear_export_log_for_date(self, date_str: str) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM export_log WHERE exported_at LIKE ? || '%'",
                (date_str,),
            )
            return cursor.rowcount

    def clear_export_log_for_parsed_today(self, today_iso: str) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM export_log
                WHERE match_id IN (
                    SELECT match_id FROM match_details WHERE parsed_at LIKE ? || '%'
                )
                """,
                (today_iso,),
            )
            return cursor.rowcount

    def delete_old_matches(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT match_id, opendota_data FROM match_details"
            )
            to_delete = set()
            for match_id, data_json in cursor.fetchall():
                try:
                    data = json.loads(data_json)
                except json.JSONDecodeError:
                    continue
                start_time = data.get("start_time")
                if start_time is None:
                    continue
                try:
                    match_date = datetime.fromtimestamp(int(start_time), tz=timezone.utc)
                except (ValueError, TypeError):
                    continue
                if match_date < cutoff:
                    to_delete.add(match_id)

            cursor = conn.execute(
                "SELECT match_id FROM rampage_matches WHERE played_at < ?",
                (cutoff_iso,),
            )
            for match_id in cursor.fetchall():
                to_delete.add(match_id[0])

            if not to_delete:
                return 0

            placeholders = ",".join("?" * len(to_delete))
            params = list(to_delete)
            conn.execute(
                f"DELETE FROM rampage_matches WHERE match_id IN ({placeholders})",
                params,
            )
            conn.execute(
                f"DELETE FROM match_details WHERE match_id IN ({placeholders})",
                params,
            )
            conn.execute(
                f"DELETE FROM export_log WHERE match_id IN ({placeholders})",
                params,
            )
            return len(to_delete)
