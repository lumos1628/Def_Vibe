import time
from typing import Any
import cloudscraper
import requests
from config import Config

class StratzClient:
    def __init__(self) -> None:
        self.url = Config.BASE_URL
        self.headers = {
            "Authorization": f"Bearer {Config.API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "stratz-rampage-scraper/1.0",
        }
        self.scraper = cloudscraper.create_scraper()

    def execute(self, query: str, variables: dict | None = None) -> dict[str, Any]:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        last_error = None
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                response = self.scraper.post(
                    self.url,
                    json=payload,
                    headers=self.headers,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    raise StratzApiError(data["errors"])

                return data["data"]
            except (requests.RequestException, StratzApiError) as exc:
                last_error = exc
                if attempt < Config.MAX_RETRIES:
                    sleep_time = attempt * 2
                    print(f"  ⚠ Error en intento {attempt}, reintentando en {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    break

        raise last_error

    def pause(self) -> None:
        time.sleep(Config.REQUEST_DELAY)

class StratzApiError(Exception):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(str(errors))
