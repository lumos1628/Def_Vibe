from datetime import datetime, timedelta, timezone
import json
import sqlite3
from pathlib import Path
from config import Config
from core.replay_store import ReplayStore

class Database:
    def __init__(self, db_path: Path = Config.DB_PATH):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def init(self) -> None:
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS heroes (
                    id INTEGER PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    short_name TEXT NOT NULL,
                    synced_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rampage_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    hero_id INTEGER NOT NULL,
                    played_at TEXT NOT NULL,
                    steam_account_id INTEGER NOT NULL,
                    extracted_at TEXT NOT NULL,
                    parsed INTEGER NOT NULL DEFAULT 0,
                    has_replay_data INTEGER NOT NULL DEFAULT 0,
                    data_verified INTEGER NOT NULL DEFAULT 0,
                    parse_requested_at TEXT,
                    parse_request_count INTEGER NOT NULL DEFAULT 0,
                    parse_job_id TEXT,
                    parse_status TEXT DEFAULT 'pending',
                    last_parse_attempt_at TEXT,
                    unparseable INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (hero_id) REFERENCES heroes(id),
                    UNIQUE (hero_id, match_id)
                );

                CREATE INDEX IF NOT EXISTS idx_rampage_hero
                ON rampage_matches(hero_id);

                CREATE TABLE IF NOT EXISTS export_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    exported_at TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    UNIQUE(match_id)
                );

                CREATE TABLE IF NOT EXISTS chat_wheels (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    label TEXT NOT NULL,
                    message TEXT NOT NULL,
                    all_chat INTEGER DEFAULT 0,
                    synced_at TEXT NOT NULL
                );
            """)

    def migrate(self) -> None:
        self._migrate_match_details_to_files()

        with self.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(rampage_matches)")
            columns = [row[1] for row in cursor.fetchall()]
            if "parsed" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN parsed INTEGER NOT NULL DEFAULT 0"
                )
            if "has_replay_data" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN has_replay_data INTEGER NOT NULL DEFAULT 0"
                )
            if "parse_requested_at" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN parse_requested_at TEXT"
                )
            if "parse_request_count" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN parse_request_count INTEGER NOT NULL DEFAULT 0"
                )
            if "unparseable" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN unparseable INTEGER NOT NULL DEFAULT 0"
                )
            if "parse_job_id" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN parse_job_id TEXT"
                )
            if "parse_status" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN parse_status TEXT DEFAULT 'pending'"
                )
            if "last_parse_attempt_at" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN last_parse_attempt_at TEXT"
                )
            if "data_verified" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN data_verified INTEGER NOT NULL DEFAULT 0"
                )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rampage_parse_status ON rampage_matches(parse_status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rampage_last_attempt ON rampage_matches(last_parse_attempt_at)"
            )

            # Backfill has_replay_data from existing match_details files
            if self.table_exists("match_details"):
                store = ReplayStore()
                cursor = conn.execute(
                    "SELECT match_id, file_path FROM match_details"
                )
                for match_id, file_path in cursor.fetchall():
                    if not file_path:
                        continue
                    data = store.load(Path(file_path))
                    if data is None:
                        continue
                    players = data.get("players") or []
                    has_kills_log = any(
                        isinstance(player.get("kills_log"), list) and len(player["kills_log"]) > 0
                        for player in players
                    )
                    has_chat = isinstance(data.get("chat"), list) and len(data["chat"]) > 0
                    has_replay = 1 if (has_kills_log or has_chat) else 0
                    conn.execute(
                        """
                        UPDATE rampage_matches
                        SET has_replay_data = ?
                        WHERE match_id = ? AND has_replay_data = 0
                        """,
                        (has_replay, match_id),
                    )

            # Backfill parse_status based on existing flags
            conn.execute(
                """
                UPDATE rampage_matches
                SET parse_status = 'done'
                WHERE has_replay_data = 1 AND (parse_status IS NULL OR parse_status = 'pending')
                """
            )
            conn.execute(
                """
                UPDATE rampage_matches
                SET parse_status = 'failed'
                WHERE unparseable = 1 AND (parse_status IS NULL OR parse_status = 'pending')
                """
            )
            conn.execute(
                """
                UPDATE rampage_matches
                SET parse_status = 'pending'
                WHERE parse_status IS NULL
                """
            )

            # Backfill data_verified based on existing state
            conn.execute(
                """
                UPDATE rampage_matches
                SET data_verified = 1
                WHERE data_verified = 0
                  AND (has_replay_data = 1 OR unparseable = 1 OR parse_job_id IS NOT NULL OR parse_request_count > 0)
                """
            )

            # Reset unparseable flag for recent matches so they can be retried
            cutoff = datetime.now(timezone.utc) - timedelta(days=Config.MAX_REPLAY_AGE_DAYS)
            conn.execute(
                """
                UPDATE rampage_matches
                SET unparseable = 0,
                    parse_status = 'pending'
                WHERE unparseable = 1
                  AND played_at >= ?
                  AND has_replay_data = 0
                """,
                (cutoff.isoformat(),),
            )

            cursor = conn.execute("PRAGMA table_info(heroes)")
            hero_columns = [row[1] for row in cursor.fetchall()]
            if "short_name" not in hero_columns:
                conn.execute("ALTER TABLE heroes ADD COLUMN short_name TEXT")
                conn.execute("DELETE FROM heroes")

            conn.executescript("""
                CREATE INDEX IF NOT EXISTS idx_rampage_parsed ON rampage_matches(parsed);
                CREATE TABLE IF NOT EXISTS match_details (
                    match_id INTEGER PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    match_date TEXT NOT NULL,
                    parsed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS export_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    exported_at TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    UNIQUE(match_id)
                );
                CREATE INDEX IF NOT EXISTS idx_export_match ON export_log(match_id);

                CREATE TABLE IF NOT EXISTS chat_wheels (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    label TEXT NOT NULL,
                    message TEXT NOT NULL,
                    all_chat INTEGER DEFAULT 0,
                    synced_at TEXT NOT NULL
                );
            """)

    def _migrate_match_details_to_files(self) -> None:
        """Migrate inline JSON blobs in `match_details` to per-match files.

        Old rows have an `opendota_data` column with the full JSON. This dumps
        each row to `data/replays/` and replaces the column with `file_path`
        and `match_date`. Idempotent: safe to re-run if interrupted.
        """
        if not self.table_exists("match_details"):
            return
        with self.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(match_details)")
            columns = [row[1] for row in cursor.fetchall()]
        if "opendota_data" not in columns:
            return

        print("\nMigrando match_details: volcando JSON a archivos de replay...")
        with self.get_connection() as conn:
            if "file_path" not in columns:
                conn.execute("ALTER TABLE match_details ADD COLUMN file_path TEXT")
            if "match_date" not in columns:
                conn.execute("ALTER TABLE match_details ADD COLUMN match_date TEXT")

            store = ReplayStore()
            updates: list[tuple[str, str, int]] = []
            cursor = conn.execute(
                "SELECT match_id, file_path, opendota_data, parsed_at FROM match_details"
            )
            for match_id, file_path, data_json, _parsed_at in cursor:
                if file_path is not None:
                    continue
                try:
                    data = json.loads(data_json)
                except json.JSONDecodeError:
                    continue
                path = store.save(match_id, data)
                updates.append((str(path), store.match_date(data), match_id))
            conn.executemany(
                "UPDATE match_details SET file_path = ?, match_date = ? WHERE match_id = ?",
                updates,
            )
            missing = conn.execute(
                """
                SELECT COUNT(*) FROM match_details
                WHERE file_path IS NULL AND opendota_data IS NOT NULL
                """
            ).fetchone()[0]

        if missing == 0:
            with self.get_connection() as conn:
                conn.execute("ALTER TABLE match_details DROP COLUMN opendota_data")
            print(f"✓ {len(updates)} partida(s) migradas a archivos en {Config.REPLAY_DATA_DIR}.")
        else:
            print(
                f"⚠ {missing} fila(s) sin migrar (JSON inválido). "
                "Se conserva la columna opendota_data y se reintentará en el próximo arranque."
            )

    def table_exists(self, name: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (name,)
            )
            return cursor.fetchone() is not None

    def count_heroes(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM heroes")
            return cursor.fetchone()[0]
