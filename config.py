import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("STRATZ_API_KEY", "")
    BASE_URL = "https://api.stratz.com/graphql"
    OPENDOTA_BASE_URL = "https://api.opendota.com/api"
    DB_PATH = Path("data.db")
    BRACKET = "DIVINE_IMMORTAL"
    REQUEST_DELAY = 0.5
    OPENDOTA_REQUEST_DELAY = 1.0
    MAX_RETRIES = 3
    RAMPAGE_TAKE = 2

    @classmethod
    def validate(cls) -> None:
        if not cls.API_KEY:
            raise ValueError("Falta STRATZ_API_KEY en el archivo .env o variables de entorno.")
