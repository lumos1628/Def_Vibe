import json
import time
from typing import Any

import requests
from config import Config


class OpenDotaClient:
    def __init__(self) -> None:
        self.base_url = Config.OPENDOTA_BASE_URL
        self.session = requests.Session()

    def get_match(self, match_id: int) -> dict[str, Any] | None:
        url = f"{self.base_url}/matches/{match_id}"
        last_error = None

        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    url,
                    timeout=30,
                    headers={"User-Agent": "stratz-rampage-scraper/1.0"},
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt < Config.MAX_RETRIES:
                    sleep_time = attempt * 2
                    print(f"  ⚠ Error en intento {attempt} para OpenDota, reintentando en {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    break
            finally:
                self.pause()

        raise last_error

    def pause(self) -> None:
        time.sleep(Config.OPENDOTA_REQUEST_DELAY)
