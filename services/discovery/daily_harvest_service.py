from datetime import datetime, timedelta, timezone
from typing import Any

from api.client import StratzClient
from api.queries import (
    HERO_STATS_WIN_WEEK_QUERY,
    PLAYERS_HERO_MATCHES_QUERY,
    PRO_PLAYERS_QUERY,
    PRO_RECENT_MATCHES_QUERY,
    RECENT_RAMPAGES_QUERY,
)
from config import Config
from core.time import parse_timestamp
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository

from .base import BaseDiscoveryService


class DailyHarvestService(BaseDiscoveryService):
    """Daily harvest of new match IDs, targeting Config.DAILY_MATCH_TARGET.

    Phases run in priority order and stop as soon as the target is reached:
    recent rampages, pro player matches, unique-mechanics heroes, most-played
    heroes of the patch, and highest-winrate heroes.
    """

    def __init__(
        self,
        client: StratzClient,
        hero_repository: HeroRepository,
        match_repository: MatchRepository,
    ) -> None:
        super().__init__(client, hero_repository, match_repository)
        self._known_ids: set[int] = set()
        self._saved_ids: set[int] = set()
        self._cutoff_ts = 0

    def harvest(self) -> list[int]:
        """Runs all harvest phases until the daily target is reached.

        Returns the list of match IDs saved during this run.
        """
        self._known_ids = self.match_repository.list_all_match_ids()
        self._saved_ids = set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=Config.DAILY_MATCH_MAX_AGE_DAYS)
        self._cutoff_ts = int(cutoff.timestamp())

        target = Config.DAILY_MATCH_TARGET
        print(f"\nObjetivo diario: {target} IDs nuevos (<= {Config.DAILY_MATCH_MAX_AGE_DAYS} días).")
        print(f"IDs ya conocidos en BD: {len(self._known_ids)}")

        self._phase_rampages()

        if not self._target_reached():
            self._phase_pro_players()

        if not self._target_reached():
            self._phase_hero_leaderboards(
                list(Config.SPECIFIC_TOP_HEROES.keys()),
                Config.RELEVANT_HERO_LEADERBOARD_TAKE,
                "héroes de mecánicas únicas",
            )

        if not self._target_reached():
            most_played, top_winrate = self._fetch_patch_hero_rankings()
            self._phase_hero_leaderboards(
                most_played,
                Config.TOP_HERO_LEADERBOARD_TAKE,
                "héroes más jugados del parche",
            )
            if not self._target_reached():
                self._phase_hero_leaderboards(
                    top_winrate,
                    Config.TOP_HERO_LEADERBOARD_TAKE,
                    "héroes con mayor winrate",
                )

        print(
            f"\nCosecha diaria finalizada: {len(self._saved_ids)} IDs nuevos guardados "
            f"(objetivo {target})."
        )
        return sorted(self._saved_ids)

    def _target_reached(self) -> bool:
        return len(self._saved_ids) >= Config.DAILY_MATCH_TARGET

    def _try_save(self, match_id: int, hero_id: int, played_at: str, steam_account_id: int) -> bool:
        """Saves a match if it is new (globally) and the target is not met."""
        if self._target_reached():
            return False
        if match_id in self._known_ids or match_id in self._saved_ids:
            return False
        self.match_repository.upsert(
            match_id=match_id,
            hero_id=hero_id,
            played_at=played_at,
            steam_account_id=steam_account_id,
        )
        self._saved_ids.add(match_id)
        return True

    def _phase_rampages(self) -> None:
        heroes = self.hero_repository.list_all()
        if not heroes:
            print("No hay héroes sincronizados. Ejecuta primero la sincronización.")
            return

        print(f"\n--- Fase 1: rampages recientes ({len(heroes)} héroes, todos los brackets) ---")
        for hero in heroes:
            if self._target_reached():
                break
            hero_id = hero["id"]
            hero_name = hero["display_name"]
            try:
                result = self.client.execute(
                    RECENT_RAMPAGES_QUERY,
                    {"heroId": hero_id, "take": Config.DAILY_RAMPAGE_TAKE},
                )
                rampages = result["heroStats"]["rampages"] or []
                new_for_hero = 0
                skipped_old = 0
                for entry in rampages:
                    match = entry.get("match") or {}
                    start = match.get("startDateTime")
                    if not start or int(start) < self._cutoff_ts:
                        skipped_old += 1
                        continue
                    if self._try_save(
                        match_id=entry["matchId"],
                        hero_id=hero_id,
                        played_at=parse_timestamp(start),
                        steam_account_id=entry["steamAccountId"],
                    ):
                        new_for_hero += 1
                    if self._target_reached():
                        break
                if new_for_hero:
                    print(f"  ✓ [{hero_id}] {hero_name}: +{new_for_hero} (total {len(self._saved_ids)})")
                elif skipped_old:
                    print(f"  → [{hero_id}] {hero_name}: solo rampages antiguos, nada nuevo.")
            except Exception as exc:
                print(f"  ✗ Error con héroe {hero_id}: {exc}")
            finally:
                self.client.pause()
        print(f"Fase 1 acumulado: {len(self._saved_ids)} IDs nuevos.")

    def _phase_pro_players(self) -> None:
        print("\n--- Fase 2: partidas recientes de jugadores profesionales ---")
        try:
            result = self.client.execute(PRO_PLAYERS_QUERY)
            pros = result.get("constants", {}).get("proSteamAccounts") or []
        except Exception as exc:
            print(f"  ✗ Error obteniendo pro players: {exc}")
            return

        pro_ids = [p["id"] for p in pros if p.get("id")][: Config.PRO_PLAYERS_LIMIT]
        print(f"  {len(pro_ids)} pro players a revisar (de {len(pros)} conocidos).")
        self._harvest_player_batches(pro_ids, hero_id=None, label="pros")
        print(f"Fase 2 acumulado: {len(self._saved_ids)} IDs nuevos.")

    def _phase_hero_leaderboards(self, hero_ids: list[int], leaderboard_take: int, label: str) -> None:
        if not hero_ids:
            return
        print(f"\n--- Fase: {label} ({len(hero_ids)} héroes, top {leaderboard_take} jugadores) ---")
        for hero_id in hero_ids:
            if self._target_reached():
                break
            try:
                top_players = self._fetch_top_players(hero_id, leaderboard_take)
                if not top_players:
                    print(f"  → [{hero_id}] sin top players.")
                    continue
                self._harvest_player_batches(top_players, hero_id=hero_id, label=f"héroe {hero_id}")
            except Exception as exc:
                print(f"  ✗ Error con leaderboard del héroe {hero_id}: {exc}")
            finally:
                self.client.pause()
        print(f"Fase {label} acumulado: {len(self._saved_ids)} IDs nuevos.")

    def _harvest_player_batches(self, player_ids: list[int], hero_id: int | None, label: str) -> None:
        """Fetches recent matches for players in batches and saves new ones.

        When hero_id is None (pro players), the hero is resolved from the
        match's own player list.
        """
        total_players = len(player_ids)
        for start in range(0, total_players, Config.PLAYERS_BATCH_SIZE):
            if self._target_reached():
                return
            batch = player_ids[start : start + Config.PLAYERS_BATCH_SIZE]
            batch_num = start // Config.PLAYERS_BATCH_SIZE + 1
            total_batches = (total_players + Config.PLAYERS_BATCH_SIZE - 1) // Config.PLAYERS_BATCH_SIZE
            try:
                if hero_id is None:
                    result = self.client.execute(
                        PRO_RECENT_MATCHES_QUERY,
                        {
                            "steamAccountIds": batch,
                            "startDateTime": self._cutoff_ts,
                            "take": Config.PLAYER_RECENT_MATCHES_TAKE,
                        },
                    )
                else:
                    result = self.client.execute(
                        PLAYERS_HERO_MATCHES_QUERY,
                        {
                            "steamAccountIds": batch,
                            "startDateTime": self._cutoff_ts,
                            "heroIds": [hero_id],
                            "take": Config.PLAYER_RECENT_MATCHES_TAKE,
                        },
                    )
                players = result.get("players") or []
                new_count = 0
                for player in players:
                    player_id = player.get("steamAccountId")
                    if player_id is None:
                        continue
                    for match in player.get("matches") or []:
                        start_ts = match.get("startDateTime")
                        # Red de seguridad: el filtro de fecha ya va en la query.
                        if start_ts and int(start_ts) < self._cutoff_ts:
                            continue
                        resolved_hero = hero_id or self._resolve_player_hero(match, player_id)
                        if resolved_hero is None:
                            continue
                        played_at = (
                            parse_timestamp(start_ts)
                            if start_ts
                            else datetime.now(timezone.utc).isoformat()
                        )
                        if self._try_save(
                            match_id=match["id"],
                            hero_id=resolved_hero,
                            played_at=played_at,
                            steam_account_id=player_id,
                        ):
                            new_count += 1
                        if self._target_reached():
                            break
                    if self._target_reached():
                        break
                if new_count:
                    print(f"  ✓ {label} lote {batch_num}/{total_batches}: +{new_count} (total {len(self._saved_ids)})")
            except Exception as exc:
                print(f"  ✗ Error en lote {batch_num}/{total_batches} ({label}): {exc}")
            finally:
                self.client.pause()

    @staticmethod
    def _resolve_player_hero(match: dict[str, Any], player_id: int) -> int | None:
        """Finds the hero played by a specific account inside a match."""
        for player in match.get("players") or []:
            if player.get("steamAccountId") == player_id:
                return player.get("heroId")
        return None

    def _fetch_patch_hero_rankings(self) -> tuple[list[int], list[int]]:
        """Ranks heroes by matches played and by winrate using winWeek stats."""
        print("\nConsultando estadísticas semanales de héroes (winWeek)...")
        try:
            result = self.client.execute(
                HERO_STATS_WIN_WEEK_QUERY,
                {"bracketIds": Config.HERO_STATS_BRACKETS},
            )
        except Exception as exc:
            print(f"  ✗ Error obteniendo winWeek: {exc}")
            return [], []

        heroes = {hero["id"] for hero in self.hero_repository.list_all()}
        entries = result.get("heroStats", {}).get("winWeek") or []

        match_counts: dict[int, int] = {}
        win_counts: dict[int, int] = {}
        for entry in entries:
            hero_id = entry.get("heroId")
            if not hero_id or hero_id not in heroes:
                continue
            match_counts[hero_id] = match_counts.get(hero_id, 0) + int(entry.get("matchCount") or 0)
            win_counts[hero_id] = win_counts.get(hero_id, 0) + int(entry.get("winCount") or 0)

        most_played = [
            hero_id
            for hero_id, _ in sorted(match_counts.items(), key=lambda item: item[1], reverse=True)
            [: Config.DAILY_TOP_HEROES_COUNT]
        ]

        winrate_ranked = sorted(
            (
                (hero_id, win_counts.get(hero_id, 0) / count)
                for hero_id, count in match_counts.items()
                if count >= Config.WINRATE_MIN_MATCHES
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        top_winrate = [hero_id for hero_id, _ in winrate_ranked[: Config.DAILY_WINRATE_HEROES_COUNT]]

        print(f"  → {len(most_played)} héroes más jugados y {len(top_winrate)} con mayor winrate.")
        return most_played, top_winrate
