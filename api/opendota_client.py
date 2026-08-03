import time
from typing import Any

import requests
from config import Config


class RateLimitError(Exception):
    """Raised when the OpenDota API returns 429 too many times."""

    def __init__(self, message: str = "Rate limit excedido") -> None:
        super().__init__(message)


class OpenDotaClient:
    def __init__(self) -> None:
        self.base_url = Config.OPENDOTA_BASE_URL
        self.session = requests.Session()
        self._rate_limit_count = 0

    def reset_rate_limit_count(self) -> None:
        self._rate_limit_count = 0

    def _build_url(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        if Config.OPENDOTA_API_KEY:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}api_key={Config.OPENDOTA_API_KEY}"
        return url

    def _request(
        self,
        method: str,
        path: str,
        max_retries: int | None = None,
        **kwargs,
    ) -> requests.Response:
        max_retries = max_retries if max_retries is not None else Config.PARSE_MAX_RETRIES
        url = self._build_url(path)
        last_error = None
        backoff = 1

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=30,
                    headers={"User-Agent": "stratz-rampage-scraper/1.0"},
                    **kwargs,
                )
                if response.status_code == 429:
                    self._rate_limit_count += 1
                    retry_after = int(response.headers.get("Retry-After", backoff))
                    if self._rate_limit_count >= Config.RATE_LIMIT_MAX_RETRIES:
                        raise RateLimitError(
                            f"Rate limit (429) recibido {self._rate_limit_count} veces consecutivas"
                        )
                    print(f"  ⚠ Rate limit (429) {self._rate_limit_count}/{Config.RATE_LIMIT_MAX_RETRIES}. Esperando {retry_after}s...")
                    time.sleep(retry_after)
                    backoff *= 2
                    continue
                self._rate_limit_count = 0
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < max_retries:
                    sleep_time = attempt * 2
                    print(f"  ⚠ Error en intento {attempt} para OpenDota ({path}), reintentando en {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    break
            finally:
                self.pause()

        raise last_error

    def get_match(self, match_id: int) -> dict[str, Any] | None:
        response = self._request("GET", f"/matches/{match_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def request_parse(self, match_id: int) -> str | None:
        response = self._request("POST", f"/request/{match_id}")
        if response.status_code in (404, 400):
            return None
        response.raise_for_status()
        data = response.json()
        job = data.get("job") if isinstance(data, dict) else None
        if job and isinstance(job, dict):
            job_id = job.get("jobId")
            if job_id is not None:
                return str(job_id)
        return None

    def get_request_status(self, job_id: str) -> dict[str, Any] | None:
        response = self._request("GET", f"/request/{job_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def pause(self) -> None:
        time.sleep(Config.OPENDOTA_REQUEST_DELAY)
