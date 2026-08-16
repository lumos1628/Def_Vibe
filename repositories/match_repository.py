from datetime import datetime, timedelta, timezone
import sqlite3
from pathlib import Path
from database import Database
from core.replay_store import ReplayStore

class MatchRepository:
    def __init__(self, db: Database):
        self.db = db
        self.replay_store = ReplayStore()

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

    def count(self) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM rampage_matches")
            return cursor.fetchone()[0]

    def count_distinct(self) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(DISTINCT match_id) FROM rampage_matches")
            return cursor.fetchone()[0]

    def list_all_match_ids(self) -> set[int]:
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT match_id FROM rampage_matches")
            return {row[0] for row in cursor.fetchall()}

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

    def count_pending_status(self, match_ids: list[int]) -> int:
        """Count distinct match IDs still pending/queued/parsing (not unparseable)."""
        if not match_ids:
            return 0
        placeholders = ",".join("?" * len(match_ids))
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT COUNT(DISTINCT match_id)
                FROM rampage_matches
                WHERE match_id IN ({placeholders})
                  AND parse_status IN ('pending', 'queued', 'parsing')
                  AND unparseable = 0
                """,
                list(match_ids),
            )
            return cursor.fetchone()[0]

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
        path = self.replay_store.save(match_id, opendota_data)
        match_date = self.replay_store.match_date(opendota_data)
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO match_details (match_id, file_path, match_date, parsed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    file_path=excluded.file_path,
                    match_date=excluded.match_date,
                    parsed_at=excluded.parsed_at;
                """,
                (match_id, str(path), match_date, now),
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
                "SELECT file_path FROM match_details WHERE match_id = ?",
                (match_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self.replay_store.load(Path(row[0]))

    def get_hero_ids_for_match(self, match_id: int) -> list[int]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT hero_id FROM rampage_matches WHERE match_id = ?",
                (match_id,),
            )
            return [row[0] for row in cursor.fetchall()]

    def list_dates_with_parsed(self) -> list[tuple[str, int]]:
        """Returns (played date, distinct match count) for matches done with replay data."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT substr(rm.played_at, 1, 10) AS d, COUNT(DISTINCT rm.match_id) AS n
                FROM rampage_matches rm
                JOIN match_details md ON md.match_id = rm.match_id
                WHERE rm.parse_status = 'done' AND rm.has_replay_data = 1
                GROUP BY d
                ORDER BY d DESC
                """
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]

    def list_parsed_rows_by_date(self, date_prefix: str | None = None) -> list[tuple[int, str, int]]:
        """Returns (match_id, played_at, hero_id) rows for matches done with replay data,
        optionally filtered by a played_at date prefix."""
        sql = """
            SELECT DISTINCT rm.match_id, rm.played_at, rm.hero_id
            FROM rampage_matches rm
            JOIN match_details md ON md.match_id = rm.match_id
            WHERE rm.parse_status = 'done' AND rm.has_replay_data = 1
        """
        params: tuple = ()
        if date_prefix is not None:
            sql += " AND substr(rm.played_at, 1, ?) = ?"
            params = (len(date_prefix), date_prefix)
        sql += " ORDER BY rm.match_id"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [(row[0], row[1], row[2]) for row in cursor.fetchall()]

    def list_downloadable(self, match_ids: list[int]) -> list[int]:
        """Return the match IDs that still need downloading.

        Excludes matches already parsed with replay data (`done` + `has_replay_data`)
        and matches marked `unparseable`. IDs not present in the database are kept
        (the JSON file is still saved). Order of the input list is preserved.
        """
        if not match_ids:
            return []
        placeholders = ",".join("?" * len(match_ids))
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT match_id FROM rampage_matches
                WHERE match_id IN ({placeholders})
                  AND (parse_status = 'done' AND has_replay_data = 1
                       OR unparseable = 1)
                """,
                list(match_ids),
            )
            skip = {row[0] for row in cursor.fetchall()}
        return [match_id for match_id in match_ids if match_id not in skip]

    def list_matches_to_export(self, today_iso: str) -> list[tuple[int, dict, bool, bool]]:
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT md.match_id, md.file_path,
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
            rows = cursor.fetchall()

        results: list[tuple[int, dict, bool, bool]] = []
        for row in rows:
            data = self.replay_store.load(Path(row["file_path"]))
            if data is None:
                continue
            results.append(
                (
                    row["match_id"],
                    data,
                    bool(row["has_replay_data"]),
                    bool(row["unparseable"]),
                )
            )
        return results

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
        cutoff_date = cutoff.date().isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT match_id FROM rampage_matches WHERE played_at < ?",
                (cutoff_iso,),
            )
            to_delete = {row[0] for row in cursor.fetchall()}

            cursor = conn.execute(
                "SELECT match_id, file_path FROM match_details WHERE match_date < ?",
                (cutoff_date,),
            )
            detail_paths: dict[int, Path] = {}
            for match_id, file_path in cursor.fetchall():
                to_delete.add(match_id)
                detail_paths[match_id] = Path(file_path)

            if not to_delete:
                return 0

            # Recover file paths for matches deleted via rampage_matches only
            # (e.g. rows with unknown match_date).
            placeholders = ",".join("?" * len(to_delete))
            cursor = conn.execute(
                f"SELECT match_id, file_path FROM match_details WHERE match_id IN ({placeholders})",
                list(to_delete),
            )
            for match_id, file_path in cursor.fetchall():
                if file_path and match_id not in detail_paths:
                    detail_paths[match_id] = Path(file_path)

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

        for match_id in to_delete:
            self.replay_store.delete(detail_paths.get(match_id))
        return len(to_delete)
