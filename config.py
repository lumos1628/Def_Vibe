import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("STRATZ_API_KEY", "")
    OPENDOTA_API_KEY = os.getenv("OPENDOTA_API_KEY", "")
    BASE_URL = "https://api.stratz.com/graphql"
    OPENDOTA_BASE_URL = "https://api.opendota.com/api"
    DB_PATH = Path("data.db")
    EXPORT_DIR = Path("exports")
    BRACKET = "DIVINE_IMMORTAL"
    REQUEST_DELAY = 0.5
    OPENDOTA_REQUEST_DELAY = 1.0
    EXPORT_WINDOW_SECONDS = None
    MAX_RETRIES = 3
    RAMPAGE_TAKE = 2
    MAX_REPLAY_AGE_DAYS = 8
    CLEAN_OLD_MATCHES_DAYS = 7

    PARSE_BATCH_SIZE = 1000
    PARSE_POLL_INTERVAL = 300  # 5 minutos
    PARSE_MAX_POLLS = 4
    PARSE_MAX_RETRIES = 3
    OPENDOTA_POLL_DELAY = 1.0

    RATE_LIMIT_MAX_RETRIES = 10
    RATE_LIMIT_PAUSE_SECONDS = 300  # 5 minutos

    TOP_HEROES_COUNT = 60
    TOP_PLAYERS_PER_HERO = 3
    TOP_MATCHES_PER_PLAYER = 3
    LEADERBOARD_BRACKET = "IMMORTAL"

    # Búsqueda específica top
    SPECIFIC_TOP_HEROES = {
        86: 50,   # Rubick
        74: 25,   # Invoker
        10: 25,   # Morphling
        71: 10,   # Spirit Breaker
        17: 10,   # Storm Spirit
        2: 5,     # Axe
    }
    SPECIFIC_TOP_MATCHES_PER_PLAYER = 2

    HERO_STATS_BRACKETS = [
        "HERALD",
        "GUARDIAN",
        "CRUSADER",
        "ARCHON",
        "LEGEND",
        "ANCIENT",
        "DIVINE",
        "IMMORTAL",
    ]

    @classmethod
    def validate(cls) -> None:
        if not cls.API_KEY:
            raise ValueError("Falta STRATZ_API_KEY en el archivo .env o variables de entorno.")
