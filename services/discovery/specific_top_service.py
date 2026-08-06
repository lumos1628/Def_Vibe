from api.client import StratzClient
from config import Config
from core.time import parse_timestamp
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository

from .base import BaseDiscoveryService


class SpecificTopService(BaseDiscoveryService):

    def fetch_specific_top_matches(self) -> int:
        heroes = {hero["id"]: hero for hero in self.hero_repository.list_all()}
        total_saved = 0

        for hero_id, top_count in Config.SPECIFIC_TOP_HEROES.items():
            hero_name = heroes.get(hero_id, {}).get("display_name", f"hero_{hero_id}")
            print(f"\n[{hero_id}] {hero_name}: buscando top {top_count} players...")

            try:
                top_players = self._fetch_top_players(hero_id, top_count)
                if not top_players:
                    print("  → Sin top players.")
                    continue
                print(f"  → {len(top_players)} top players encontrados.")

                for player_id in top_players:
                    print(
                        f"    Player {player_id}: buscando últimas {Config.SPECIFIC_TOP_MATCHES_PER_PLAYER} partidas..."
                    )
                    try:
                        matches = self._fetch_player_matches(
                            player_id, hero_id, Config.SPECIFIC_TOP_MATCHES_PER_PLAYER
                        )
                        if not matches:
                            print("      → Sin partidas.")
                            continue

                        saved_for_player = 0
                        for match in matches:
                            match_id = match["id"]
                            played_at = parse_timestamp(match.get("startDateTime"))

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

