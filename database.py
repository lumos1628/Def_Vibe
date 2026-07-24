import sqlite3
from pathlib import Path
from config import Config

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
                    synced_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rampage_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    hero_id INTEGER NOT NULL,
                    played_at TEXT NOT NULL,
                    steam_account_id INTEGER NOT NULL,
                    extracted_at TEXT NOT NULL,
                    FOREIGN KEY (hero_id) REFERENCES heroes(id),
                    UNIQUE (hero_id, match_id)
                );

                CREATE INDEX IF NOT EXISTS idx_rampage_hero
                ON rampage_matches(hero_id);
            """)

    def migrate(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(rampage_matches)")
            columns = [row[1] for row in cursor.fetchall()]
            if "parsed" not in columns:
                conn.execute(
                    "ALTER TABLE rampage_matches ADD COLUMN parsed INTEGER NOT NULL DEFAULT 0"
                )

            conn.executescript("""
                CREATE INDEX IF NOT EXISTS idx_rampage_parsed ON rampage_matches(parsed);
                CREATE TABLE IF NOT EXISTS match_details (
                    match_id INTEGER PRIMARY KEY,
                    opendota_data TEXT NOT NULL,
                    parsed_at TEXT NOT NULL
                );
            """)

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
