from datetime import datetime, timezone
from typing import Any

from api.client import StratzClient
from api.queries import (
    HERO_STATS_WIN_WEEK_QUERY,
    LEADERBOARD_HERO_QUERY,
    PLAYER_MATCHES_QUERY,
)
from config import Config
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository


class TopHeroesService:
    def __init__(
        self,
        client: StratzClient,
        hero_repository: HeroRepository,
        match_repository: MatchRepository,
    ) -> None:
        self.client = client
        self.hero_repository = hero_repository
        self.match_repository = match_repository

    def fetch_top_heroes_matches(self) -> int:
        heroes = {hero["id"]: hero for hero in self.hero_repository.list_all()}
        top_heroes = self._fetch_top_heroes(heroes)
        if not top_heroes:
            print("No se encontraron héroes en winWeek.")
            return 0

        total_saved = 0
        for hero_id in top_heroes:
            hero_name = heroes.get(hero_id, {}).get("display_name", f"hero_{hero_id}")
            print(f"\n[{hero_id}] {hero_name}: buscando top players...")

            try:
                top_players = self._fetch_top_players(hero_id)
                if not top_players:
                    print("  → Sin top players.")
                    continue
                print(f"  → {len(top_players)} top players encontrados.")

                for player_id in top_players:
                    print(f"    Player {player_id}: buscando últimas partidas...")
                    try:
                        matches = self._fetch_player_matches(player_id, hero_id)
                        if not matches:
                            print("      → Sin partidas.")
                            continue

                        saved_for_player = 0
                        for match in matches:
                            match_id = match["id"]
                            played_at = self._parse_timestamp(
                                match.get("startDateTime")
                            )

                            if self.match_repository.exists_for_hero(
                                match_id, hero_id
                            ):
                                print(
                                    f"      ⚠ Match {match_id} ya existe para este héroe, se omite."
                                )
                                continue

                            self.match_repository.upsert(
                                match_id=match_id,
                                hero_id=hero_id,
                                played_at=played_at,
                                steam_account_id=player_id,
                            )
                            total_saved += 1
                            saved_for_player += 1
                            print(f"      ✓ Guardado match {match_id} ({played_at})")

                        print(
                            f"    → {saved_for_player} partidas nuevas guardadas para el player."
                        )
                    except Exception as exc:
                        print(f"    ✗ Error buscando partidas: {exc}")
                    finally:
                        self.client.pause()
            except Exception as exc:
                print(f"  ✗ Error buscando top players: {exc}")
            finally:
                self.client.pause()

        print(f"\nTotal de partidas guardadas: {total_saved}")
        return total_saved

    def _fetch_top_heroes(self, heroes: dict[int, dict]) -> list[int]:
        print("Consultando héroes más jugados...")
        result = self.client.execute(
            HERO_STATS_WIN_WEEK_QUERY,
            {"bracketIds": Config.HERO_STATS_BRACKETS},
        )
        entries = result.get("heroStats", {}).get("winWeek") or []
        if not entries:
            return []

        counts: dict[int, int] = {}
        for entry in entries:
            hero_id = entry.get("heroId")
            if not hero_id or hero_id not in heroes:
                continue
            counts[hero_id] = counts.get(hero_id, 0) + int(
                entry.get("matchCount") or 0
            )

        ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        top_heroes = [hero_id for hero_id, _ in ranked[: Config.TOP_HEROES_COUNT]]
        print(f"Top {len(top_heroes)} héroes seleccionados.")
        return top_heroes

    def _fetch_top_players(self, hero_id: int) -> list[int]:
        result = self.client.execute(
            LEADERBOARD_HERO_QUERY,
            {
                "heroIds": [hero_id],
                "bracketIds": [Config.LEADERBOARD_BRACKET],
                "take": Config.TOP_PLAYERS_PER_HERO,
            },
        )
        leaderboard = result.get("leaderboard", {}).get("hero") or []
        return [
            entry["steamAccountId"]
            for entry in leaderboard
            if entry.get("steamAccountId")
        ]

    def _fetch_player_matches(self, player_id: int, hero_id: int) -> list[dict[str, Any]]:
        result = self.client.execute(
            PLAYER_MATCHES_QUERY,
            {
                "steamAccountId": player_id,
                "heroIds": [hero_id],
                "take": Config.TOP_MATCHES_PER_PLAYER,
            },
        )
        return result.get("player", {}).get("matches") or []

    @staticmethod
    def _parse_timestamp(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        return datetime.now(timezone.utc).isoformat()
