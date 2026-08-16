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
    REPLAY_DATA_DIR = Path("data/replays")
    EXPORT_DIR = Path("exports")
    ANALYSIS_EXPORT_DIR = Path("exports/rampages")

    # Google Drive (carpeta compartida para el CSV de IDs)
    # OAuth de usuario: client secret + token guardado localmente.
    GOOGLE_DRIVE_CLIENT_SECRETS = os.getenv("GOOGLE_DRIVE_CLIENT_SECRETS", "")
    GOOGLE_DRIVE_TOKEN_PATH = os.getenv("GOOGLE_DRIVE_TOKEN_PATH", "data/drive_token.json")
    GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    BRACKET = "DIVINE_IMMORTAL"
    REQUEST_DELAY = 0.5
    # Sin sleep artificial: el límite de OpenDota es 60 calls/seg y 3000/día,
    # y la duración del propio GET ya espacia las peticiones.
    OPENDOTA_REQUEST_DELAY = 0.65
    MAX_RETRIES = 3
    RAMPAGE_TAKE = 2
    MAX_REPLAY_AGE_DAYS = 8
    CLEAN_OLD_MATCHES_DAYS = 7

    PARSE_BATCH_SIZE = 3000
    PARSE_POLL_INTERVAL = 150  # 5 minutos
    PARSE_MAX_POLLS = 4
    PARSE_MAX_RETRIES = 3
    OPENDOTA_POLL_DELAY = 1.0

    # Modo solo-GET: no encola jobs en OpenDota, solo consulta datos ya parseados.
    PARSE_GET_ONLY = True

    RATE_LIMIT_MAX_RETRIES = 10
    RATE_LIMIT_PAUSE_SECONDS = 300  # 5 minutos

    # Análisis de rampages (menú 4)
    ANALYSIS_TOP_N = 10
    ANALYSIS_REACTION_WINDOW_SECONDS = 60

    TOP_HEROES_COUNT = 60
    TOP_PLAYERS_PER_HERO = 3
    TOP_MATCHES_PER_PLAYER = 3
    LEADERBOARD_BRACKET = "IMMORTAL"

    # Cosecha diaria (objetivo de IDs nuevos por día)
    DAILY_MATCH_TARGET = 2900
    DAILY_MATCH_MAX_AGE_DAYS = 7
    DAILY_RAMPAGE_TAKE = 20        # máximo permitido por Stratz en heroStats.rampages
    PLAYERS_BATCH_SIZE = 5         # máximo permitido por Stratz en players(steamAccountIds)
    PLAYER_RECENT_MATCHES_TAKE = 5
    PRO_PLAYERS_LIMIT = 600
    RELEVANT_HERO_LEADERBOARD_TAKE = 25
    TOP_HERO_LEADERBOARD_TAKE = 10
    DAILY_TOP_HEROES_COUNT = 40
    DAILY_WINRATE_HEROES_COUNT = 20
    WINRATE_MIN_MATCHES = 1000     # filtro anti-ruido para el ranking de winrate

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
