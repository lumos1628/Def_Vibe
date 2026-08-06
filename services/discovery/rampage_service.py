from datetime import datetime, timezone

from api.client import StratzClient
from api.queries import LATEST_RAMPAGES_QUERY, MATCH_DATE_QUERY, RAMPAGES_QUERY
from config import Config
from core.time import parse_timestamp
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository


class RampageService:
    def __init__(
        self,
        client: StratzClient,
        hero_repository: HeroRepository,
        match_repository: MatchRepository,
    ) -> None:
        self.client = client
        self.hero_repository = hero_repository
        self.match_repository = match_repository

    def fetch_by_rampages(self) -> int:
        return self._run_rampage_search(
            query=RAMPAGES_QUERY,
            bracket=Config.BRACKET,
            take=Config.RAMPAGE_TAKE,
            label="divine_inmortal",
        )

    def fetch_latest_rampages(self) -> int:
        return self._run_rampage_search(
            query=LATEST_RAMPAGES_QUERY,
            bracket=None,
            take=5,
            label="últimos 5",
        )

    def _run_rampage_search(
        self,
        query: str,
        bracket: str | None,
        take: int,
        label: str,
    ) -> int:
        heroes = self.hero_repository.list_all()
        if not heroes:
            print("No hay héroes sincronizados. Ejecuta primero la sincronización.")
            return 0

        total_saved = 0
        for hero in heroes:
            hero_id = hero["id"]
            hero_name = hero["display_name"]
            print(f"[{hero_id}] {hero_name}: buscando rampages ({label})...")

            try:
                variables: dict = {"heroId": hero_id, "take": take}
                if bracket is not None:
                    variables["bracketBasicIds"] = [bracket]

                result = self.client.execute(query, variables)
                rampages = result["heroStats"]["rampages"] or []
                if not rampages:
                    print("  → Sin rampages encontrados.")
                    continue

                saved_for_hero = 0
                skipped_for_hero = 0
                for match in rampages:
                    match_id = match["matchId"]
                    steam_account_id = match["steamAccountId"]

                    if self.match_repository.exists_for_hero(match_id, hero_id):
                        skipped_for_hero += 1
                        print(f"  ⚠ Match {match_id} ya existe para este héroe, se omite.")
                        continue

                    played_at = self._fetch_match_date(match_id)
                    self.match_repository.upsert(
                        match_id=match_id,
                        hero_id=hero_id,
                        played_at=played_at,
                        steam_account_id=steam_account_id,
                    )
                    saved_for_hero += 1
                    total_saved += 1
                    print(f"  ✓ Guardado match {match_id} ({played_at})")

                if saved_for_hero == 0 and skipped_for_hero > 0:
                    print("  → Todos los rampages encontrados ya estaban guardados.")
                elif saved_for_hero == 0:
                    print("  → Sin rampages nuevos para guardar.")
            except Exception as exc:
                print(f"  ✗ Error: {exc}")
            finally:
                self.client.pause()

        print(f"\nTotal de partidas guardadas: {total_saved}")
        return total_saved

    def _fetch_match_date(self, match_id: int) -> str:
        data = self.client.execute(MATCH_DATE_QUERY, {"matchId": match_id})
        match = data.get("match")
        if not match:
            return datetime.now(timezone.utc).isoformat()

        start_dt = match.get("startDateTime")
        if not start_dt:
            return datetime.now(timezone.utc).isoformat()

        return parse_timestamp(start_dt)
